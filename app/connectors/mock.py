from hashlib import sha256

from app.connectors.base import JobProvider
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
