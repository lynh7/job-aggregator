from io import BytesIO
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.database import Base
from app.models import Candidate, CandidateProfile, CandidateTask, JobMatch, RawJob
from candidate_service.service import create_candidate_submission, process_candidate_submission
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


def test_candidate_submission_creates_profile_and_matches(tmp_path):
    session, settings = build_session(tmp_path)
    session.add(
        RawJob(
            provider="mock",
            api_version="v1",
            source_record_id="job-1",
            rule_version="raw-v1",
            payload={
                "title": "Python Backend Engineer",
                "company": "Example Co",
                "location": "Remote",
                "description": "Need python docker kubernetes and sql with 3 years experience",
                "url": "https://example.com/jobs/job-1",
            },
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
        {"full_name": "Alex Example", "location": "Remote"},
    )

    assert task_id > 0
    process_candidate_submission(session, settings, candidate.id, document.id)

    stored_candidate = session.get(Candidate, candidate.id)
    assert stored_candidate is not None
    assert stored_candidate.status == "matched"

    profile = session.scalar(select(CandidateProfile).where(CandidateProfile.candidate_id == candidate.id))
    assert profile is not None
    assert "python" in profile.skills

    matches = list(session.scalars(select(JobMatch).where(JobMatch.candidate_id == candidate.id)))
    assert len(matches) == 1
    assert matches[0].match_score > 0
    assert "python" in matches[0].matched_skills


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
