import httpx

from app.config import Settings
from app.logging import get_logger
from crawler_service.schemas import CrawlRequest, CrawlResponse

logger = get_logger(__name__)


def trigger_candidate_crawl(
    settings: Settings,
    *,
    candidate_id: int,
    keywords: list[str],
    location: str | None,
    limit_per_provider: int,
) -> CrawlResponse:
    request = CrawlRequest(
        keywords=keywords,
        location=location,
        limit_per_provider=limit_per_provider,
        export=False,
    )
    logger.info(
        "candidate_crawl.dispatch",
        candidate_id=candidate_id,
        keywords=keywords,
        location=location,
        limit_per_provider=limit_per_provider,
    )
    with httpx.Client(timeout=settings.request_timeout_seconds) as client:
        response = client.post(
            f"{settings.crawler_api_base_url.rstrip('/')}{settings.crawler_api_crawl_path}",
            json=request.model_dump(mode="json"),
        )
        response.raise_for_status()
    body = CrawlResponse.model_validate(response.json())
    logger.info(
        "candidate_crawl.completed",
        candidate_id=candidate_id,
        fetched=body.fetched,
        stored=body.stored,
        providers=body.providers,
    )
    return body
