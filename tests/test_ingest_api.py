import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/job-aggregator-test.db")
os.environ.setdefault("EXPORT_DIR", "/tmp/job-aggregator-exports")
os.environ.setdefault("INGEST_API_TOKEN", "test-ingest-token")

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from shared.database import Base, SessionLocal, engine
from shared.models import Job, RawJob

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Path("/tmp/job-aggregator-exports").mkdir(parents=True, exist_ok=True)


def test_ingest_requires_token() -> None:
    response = client.post(
        "/api/v1/ingest/raw-jobs",
        json={
            "records": [
                {
                    "provider": "topcv",
                    "api_version": "v1",
                    "source_record_id": "job-1",
                    "payload": {"job_id": "job-1", "job_title": "Data Engineer", "url": "https://example.com/job-1"},
                }
            ]
        },
    )
    assert response.status_code == 401


def test_ingest_stores_raw_and_master_jobs() -> None:
    response = client.post(
        "/api/v1/ingest/raw-jobs",
        headers={"X-Ingest-Token": "test-ingest-token"},
        json={
            "records": [
                {
                    "provider": "topcv",
                    "api_version": "v1",
                    "source_record_id": "job-1",
                    "payload": {
                        "job_id": "job-1",
                        "job_title": "Data Engineer",
                        "company_name": "Example Co",
                        "city": "Ho Chi Minh City",
                        "job_description": "Build pipelines",
                        "job_type": "full-time",
                        "salary_range": "$1000-$2000",
                        "apply_url": "https://example.com/job-1",
                    },
                }
            ],
            "export": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] == 1
    assert body["stored"] == 1
    assert body["duplicates_filtered"] == 0
    assert body["providers"] == ["topcv"]
    assert body["json_export"] is None
    assert body["xlsx_export"] is None

    with SessionLocal() as session:
        raw_jobs = list(session.scalars(select(RawJob)))
        jobs = list(session.scalars(select(Job)))

    assert len(raw_jobs) == 1
    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].company == "Example Co"
    assert jobs[0].provider == "topcv"


def test_ingest_filters_duplicate_records() -> None:
    payload = {
        "provider": "topcv",
        "api_version": "v1",
        "source_record_id": "job-dup",
        "payload": {
            "job_id": "job-dup",
            "job_title": "Data Engineer",
            "company_name": "Example Co",
            "city": "Ho Chi Minh City",
            "job_description": "Build pipelines",
            "job_type": "full-time",
            "salary_range": "$1000-$2000",
            "apply_url": "https://example.com/job-dup",
        },
    }
    response = client.post(
        "/api/v1/ingest/raw-jobs",
        headers={"X-Ingest-Token": "test-ingest-token"},
        json={"records": [payload, payload], "export": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] == 2
    assert body["stored"] == 1
    assert body["duplicates_filtered"] == 1

    with SessionLocal() as session:
        raw_jobs = list(session.scalars(select(RawJob)))
        jobs = list(session.scalars(select(Job)))

    assert len(raw_jobs) == 1
    assert len(jobs) == 1
