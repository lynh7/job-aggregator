from hashlib import sha256

from app.connectors.base import JobProvider, ProviderApplicationRequest, ProviderApplicationResult
from app.schemas import RawJobRecord


class MockProvider(JobProvider):
    name = "mock"
    api_version = "v1"

    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        jobs: list[RawJobRecord] = []
        for keyword in keywords[:limit]:
            external_id = sha256(f"{keyword}:{location}".encode()).hexdigest()[:16]
            payload = {
                "id": external_id,
                "title": f"{keyword.title()} Engineer",
                "company": "Example Company",
                "location": location or "Remote",
                "description": f"Example listing generated for keyword: {keyword}",
                "employment_type": "Full-time",
                "salary": None,
                "url": f"https://example.com/jobs/{external_id}",
            }
            jobs.append(
                RawJobRecord(
                    provider=self.name,
                    api_version=self.api_version,
                    source_record_id=external_id,
                    payload=payload,
                )
            )
        return jobs

    async def apply(self, request: ProviderApplicationRequest) -> ProviderApplicationResult:
        external_application_id = f"mock-{request.job_source_record_id}-{request.candidate_id}"
        request_payload = {
            "candidate_id": request.candidate_id,
            "job_source_record_id": request.job_source_record_id,
            "cv_filename": request.cv_filename,
            "email": request.email,
        }
        response_payload = {
            "status": "submitted",
            "application_id": external_application_id,
            "job_url": request.job_url,
        }
        return ProviderApplicationResult(
            status="submitted",
            external_application_id=external_application_id,
            request_payload=request_payload,
            response_payload=response_payload,
        )
