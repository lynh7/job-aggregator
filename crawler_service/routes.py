from fastapi import APIRouter, Depends, HTTPException

from crawler_service.config import CrawlerSettings, get_settings
from crawler_service.schemas import CrawlRequest, CrawlResponse
from crawler_service.service import crawl_jobs, push_to_core

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/crawl", response_model=CrawlResponse)
async def crawl(request: CrawlRequest, settings: CrawlerSettings = Depends(get_settings)) -> CrawlResponse:
    try:
        requested, records = await crawl_jobs(request, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not records:
        return CrawlResponse(fetched=0, stored=0, providers=requested, json_export=None, xlsx_export=None)
    return await push_to_core(requested, records, request, settings)
