from app.schemas import RawJobRecord
from crawler_service.crawlers.base import JobCrawler


class MockCrawler(JobCrawler):
    name = "mock"

    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        payload = {
            "id": "mock-1",
            "title": f"Mock {' / '.join(keywords)} role",
            "company": "Mock Company",
            "location": location or "Remote",
            "description": "Mock crawl result",
            "employment_type": "full-time",
            "salary_text": "Negotiable",
            "url": "https://example.com/mock-job",
        }
        return [self.build_record(payload, payload["url"])] if limit > 0 else []
