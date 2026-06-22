from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.business_rules.registry import build_business_rules_registry
from app.database import Base
from app.models import Job
from app.schemas import RawJobRecord
from app.services.collector import apply_business_rules, store_master_jobs, store_raw_jobs


def build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory()


def test_master_jobs_are_populated_and_controlled_from_raw_results():
    session = build_session()
    records = [
        RawJobRecord(
            provider="mock",
            api_version="v1",
            source_record_id="job-1",
            payload={
                "id": "job-1",
                "title": "Python Backend Engineer",
                "company": "Example Co",
                "location": "Remote",
                "description": "Build APIs",
                "employment_type": "Full-time",
                "url": "https://example.com/jobs/job-1",
            },
            fetched_at=datetime.now(UTC),
        )
    ]

    results = apply_business_rules(build_business_rules_registry(), records)
    raw_jobs = store_raw_jobs(session, results)
    master_jobs = store_master_jobs(session, results, raw_jobs)

    assert len(raw_jobs) == 1
    assert len(master_jobs) == 1
    assert master_jobs[0].raw_job_id == raw_jobs[0].id
    assert master_jobs[0].normalization_status == "normalized"
    assert master_jobs[0].rule_version == "master-v1"


def test_master_jobs_are_upserted_per_provider_version_source_record():
    session = build_session()
    registry = build_business_rules_registry()

    first = RawJobRecord(
        provider="mock",
        api_version="v1",
        source_record_id="job-1",
        payload={
            "id": "job-1",
            "title": "Python Backend Engineer",
            "url": "https://example.com/jobs/job-1",
        },
    )
    second = RawJobRecord(
        provider="mock",
        api_version="v1",
        source_record_id="job-1",
        payload={
            "id": "job-1",
            "title": "Senior Python Backend Engineer",
            "url": "https://example.com/jobs/job-1",
        },
    )

    for record in (first, second):
        results = apply_business_rules(registry, [record])
        raw_jobs = store_raw_jobs(session, results)
        store_master_jobs(session, results, raw_jobs)

    jobs = list(session.scalars(select(Job)))
    assert len(jobs) == 1
    assert jobs[0].title == "Senior Python Backend Engineer"
