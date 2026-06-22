from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.business_rules.registry import build_business_rules_registry
from app.config import Settings, get_settings
from app.connectors.registry import build_providers
from app.database import get_db
from app.models import Job, RawJob
from app.schemas import (
    IngestRawJobsRequest,
    IngestResponse,
    JobResponse,
    RawJobResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.collector import apply_business_rules, collect_jobs, persist_results

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(limit: int = 100, session: Session = Depends(get_db)) -> list[Job]:
    return list(session.scalars(select(Job).order_by(Job.last_seen_at.desc()).limit(min(limit, 500))))


@router.get("/raw-jobs", response_model=list[RawJobResponse])
def list_raw_jobs(limit: int = 100, session: Session = Depends(get_db)) -> list[RawJob]:
    return list(
        session.scalars(
            select(RawJob).order_by(RawJob.fetched_at.desc()).limit(min(limit, 500))
        )
    )


@router.get("/business-rules")
def list_business_rules() -> dict[str, list[str]]:
    return build_business_rules_registry().supported_versions()


@router.post("/search", response_model=SearchResponse)
async def search_jobs(
    request: SearchRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    registry = build_providers(settings)
    requested = request.providers or settings.providers
    unknown = [name for name in requested if name not in registry]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unavailable providers: {unknown}")

    providers = [registry[name] for name in requested]
    fetched = await collect_jobs(
        providers, request.keywords, request.location, request.limit_per_provider
    )
    results = apply_business_rules(build_business_rules_registry(), fetched)
    stored_master, json_path, xlsx_path = persist_results(session, settings, results, export=True)
    return SearchResponse(
        fetched=len(fetched),
        stored=len(stored_master),
        providers=requested,
        json_export=str(json_path),
        xlsx_export=str(xlsx_path),
    )


@router.post("/ingest/raw-jobs", response_model=IngestResponse)
def ingest_raw_jobs(
    request: IngestRawJobsRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> IngestResponse:
    _authorize_ingest(settings, ingest_token)
    results = apply_business_rules(build_business_rules_registry(), request.records)
    stored_master, json_path, xlsx_path = persist_results(
        session,
        settings,
        results,
        export=request.export,
    )
    providers = sorted({record.provider for record in request.records})
    return IngestResponse(
        fetched=len(request.records),
        stored=len(stored_master),
        providers=providers,
        json_export=str(json_path) if json_path is not None else None,
        xlsx_export=str(xlsx_path) if xlsx_path is not None else None,
    )


@router.get("/exports/{filename}")
def download_export(filename: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = settings.export_dir / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, filename=filename)


def _authorize_ingest(settings: Settings, ingest_token: str | None) -> None:
    if settings.ingest_api_token and ingest_token != settings.ingest_api_token:
        raise HTTPException(status_code=401, detail="Invalid ingest token")
