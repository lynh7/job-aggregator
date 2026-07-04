import httpx

from app.logging import get_logger
from app.schemas import IngestRawJobsRequest, RawJobRecord
from app.services.collector import dedupe_raw_job_records
from crawler_service.config import CrawlerSettings
from crawler_service.crawlers.registry import build_crawlers
from crawler_service.schemas import CrawlRequest, CrawlResponse

logger = get_logger(__name__)


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
    deduped = dedupe_raw_job_records(records)
    logger.info(
        "crawler.fetch.completed",
        providers=requested,
        keywords=request.keywords,
        location=request.location,
        fetched=len(records),
        unique_records=len(deduped),
        duplicates_filtered=len(records) - len(deduped),
    )
    return requested, deduped


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
    result = CrawlResponse.model_validate(body)
    logger.info(
        "crawler.push.completed",
        providers=requested,
        fetched=result.fetched,
        stored=result.stored,
        duplicates_filtered=result.duplicates_filtered,
    )
    return result
