from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.database import Base
from app.models import Candidate, CandidateJobSearch, CandidateTask, Job, JobApplication, JobMatch
from candidate_service.service import (
    create_candidate_submission,
    enqueue_due_job_search_tasks,
    enqueue_job_applications,
    process_candidate_submission,
    process_candidate_job_search,
    process_job_application,
    upsert_candidate_job_search,
)
from candidate_service.task_queue import claim_candidate_task, enqueue_candidate_task


class UploadStub:
    def __init__(self, filename: str, content: str, content_type: str = "text/plain") -> None:
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(content.encode("utf-8"))


def build_session(tmp_path: Path) -> tuple[Session, Settings]:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        database_url=database_url,
        candidate_storage_dir=tmp_path / "candidates",
        candidate_match_limit=10,
    )
    return session_factory(), settings


def test_candidate_submission_creates_profile_matches_and_application(tmp_path):
    session, settings = build_session(tmp_path)
    session.add(
        Job(
            provider="mock",
            api_version="v1",
            source_record_id="job-1",
            external_id="job-1",
            title="Python Backend Engineer",
            company="Example Co",
            location="Remote",
            description="Need python docker kubernetes and sql with 3 years experience",
            employment_type="Full-time",
            salary_text=None,
            url="https://example.com/jobs/job-1",
            rule_version="master-v1",
            normalization_status="normalized",
        )
    )
    session.commit()

    candidate, document, task_id = create_candidate_submission(
        session,
        settings,
        UploadStub(
            "cv.txt",
            "\n".join(
                [
                    "Alex Example",
                    "Email: alex@example.com",
                    "Location: Remote",
                    "Backend engineer with 4 years experience in Python, Docker, Kubernetes, SQL",
                ]
            ),
        ),
        {"full_name": "Alex Example", "location": "Remote", "email": "alex@example.com"},
    )

    assert task_id > 0
    process_candidate_submission(session, settings, candidate.id, document.id)

    stored_candidate = session.get(Candidate, candidate.id)
    assert stored_candidate is not None
    assert stored_candidate.status == "matched"

    matches = list(session.scalars(select(JobMatch).where(JobMatch.candidate_id == candidate.id)))
    assert len(matches) == 1
    assert matches[0].match_score > 0
    assert "python" in matches[0].matched_skills

    task_ids = enqueue_job_applications(session, candidate.id, [matches[0].id])
    assert len(task_ids) == 1

    application = session.scalar(select(JobApplication).where(JobApplication.candidate_id == candidate.id))
    assert application is not None
    process_job_application(session, settings, application.id)

    submitted = session.get(JobApplication, application.id)
    assert submitted is not None
    assert submitted.status == "submitted"
    assert submitted.external_application_id == f"mock-{matches[0].job_source_record_id}-{candidate.id}"


def test_candidate_tasks_can_be_claimed_by_parallel_workers(tmp_path):
    session, _settings = build_session(tmp_path)
    candidate = Candidate(status="uploaded", consent_given=True)
    session.add(candidate)
    session.commit()
    session.refresh(candidate)

    enqueue_candidate_task(
        session,
        task_type="parse_and_match",
        candidate_id=candidate.id,
        payload={"document_id": 1},
    )
    enqueue_candidate_task(
        session,
        task_type="rematch",
        candidate_id=candidate.id,
        payload={"limit": 5},
    )

    second_session = Session(bind=session.bind, expire_on_commit=False)
    first_claim = claim_candidate_task(session, worker_id="worker-a")
    second_claim = claim_candidate_task(second_session, worker_id="worker-b")

    assert first_claim is not None
    assert second_claim is not None
    assert first_claim.id != second_claim.id
    assert first_claim.locked_by == "worker-a"
    assert second_claim.locked_by == "worker-b"

    claimed = list(session.scalars(select(CandidateTask).order_by(CandidateTask.id.asc())))
    assert [task.status for task in claimed] == ["processing", "processing"]


def test_candidate_job_search_schedules_crawl_task_and_rematch(tmp_path, monkeypatch):
    session, settings = build_session(tmp_path)
    candidate = Candidate(status="matched", consent_given=True, location="Remote")
    session.add(candidate)
    session.add(
        Job(
            provider="mock",
            api_version="v1",
            source_record_id="job-1",
            external_id="job-1",
            title="Python Backend Engineer",
            company="Example Co",
            location="Remote",
            description="Need python docker kubernetes and sql with 3 years experience",
            employment_type="Full-time",
            salary_text=None,
            url="https://example.com/jobs/job-1",
            rule_version="master-v1",
            normalization_status="normalized",
        )
    )
    session.commit()
    session.refresh(candidate)

    search = upsert_candidate_job_search(
        session,
        settings,
        candidate_id=candidate.id,
        keywords=["Python", "python", "Backend"],
        location="Remote",
    )
    search.next_crawl_at = datetime.now(UTC) - timedelta(minutes=1)
    session.commit()

    enqueued = enqueue_due_job_search_tasks(session, settings)
    assert enqueued == 1

    crawl_task = session.scalar(select(CandidateTask).where(CandidateTask.task_type == "crawl_jobs_for_candidate"))
    assert crawl_task is not None
    assert crawl_task.payload["search_id"] == search.id

    class FakeResponse:
        fetched = 3
        stored = 2
        duplicates_filtered = 1

    monkeypatch.setattr(
        "candidate_service.service.trigger_candidate_crawl",
        lambda *args, **kwargs: FakeResponse(),
    )

    process_candidate_job_search(session, settings, search.id)

    refreshed_search = session.get(CandidateJobSearch, search.id)
    assert refreshed_search is not None
    assert refreshed_search.last_crawled_at is not None

    rematch_task = session.scalar(select(CandidateTask).where(CandidateTask.task_type == "rematch"))
    assert rematch_task is not None
    assert rematch_task.candidate_id == candidate.id
