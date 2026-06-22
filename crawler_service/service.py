import httpx

from app.schemas import IngestRawJobsRequest, RawJobRecord
from crawler_service.config import CrawlerSettings
from crawler_service.crawlers.registry import build_crawlers
from crawler_service.schemas import CrawlRequest, CrawlResponse


async def crawl_jobs(request: CrawlRequest, settings: CrawlerSettings) -> tuple[list[str], list[RawJobRecord]]:
    registry = build_crawlers(settings)
    requested = request.providers or settings.crawler_providers
    unknown = [name for name in requested if name not in registry]
    if unknown:
        raise ValueError(f"Unavailable crawler providers: {unknown}")

    records: list[RawJobRecord] = []
    for name in requested:
        crawler = registry[name]
        remaining = request.limit_per_provider
        if remaining <= 0:
            continue
        records.extend(await crawler.search(request.keywords, request.location, remaining))
    return requested, records


async def push_to_core(
    requested: list[str],
    records: list[RawJobRecord],
    request: CrawlRequest,
    settings: CrawlerSettings,
) -> CrawlResponse:
    payload = IngestRawJobsRequest(records=records, export=request.export).model_dump(mode="json")
    headers: dict[str, str] = {}
    if settings.ingest_api_token:
        headers["X-Ingest-Token"] = settings.ingest_api_token
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(
            f"{settings.core_api_base_url.rstrip('/')}{settings.core_api_ingest_path}",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
    body = response.json()
    body["providers"] = requested
    return CrawlResponse.model_validate(body)
