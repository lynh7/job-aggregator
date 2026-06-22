import asyncio

from app.connectors.base import ProviderApplicationRequest
from app.connectors.mock import MockProvider


def test_mock_provider_returns_unchanged_raw_payloads():
    jobs = asyncio.run(MockProvider().search(["python"], "Remote", 10))

    assert len(jobs) == 1
    assert jobs[0].provider == "mock"
    assert jobs[0].api_version == "v1"
    assert jobs[0].payload["title"] == "Python Engineer"


def test_mock_provider_accepts_application_submission():
    result = asyncio.run(
        MockProvider().apply(
            ProviderApplicationRequest(
                candidate_id=1,
                full_name="Alex Example",
                email="alex@example.com",
                phone=None,
                location="Remote",
                cv_text="Python developer",
                cv_filename="cv.txt",
                cv_content_type="text/plain",
                cv_bytes=b"Python developer",
                job_source_record_id="job-1",
                job_url="https://example.com/jobs/job-1",
            )
        )
    )

    assert result.status == "submitted"
    assert result.external_application_id == "mock-job-1-1"
