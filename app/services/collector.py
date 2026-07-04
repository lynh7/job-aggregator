import asyncio
from pathlib import Path

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.business_rules.base import RuleResult
from app.logging import get_logger
from app.business_rules.registry import BusinessRulesRegistry
from app.config import Settings
from app.connectors.base import JobProvider
from app.models import Job, RawJob
from app.schemas import RawJobRecord
from app.services.exporter import export_jobs

logger = get_logger(__name__)


async def collect_jobs(
    providers: list[JobProvider],
    keywords: list[str],
    location: str | None,
    limit: int,
) -> list[RawJobRecord]:
    logger.info(
        "collector.fetch.start",
        provider_count=len(providers),
        keywords=keywords,
        location=location,
        limit_per_provider=limit,
    )
    batches = await asyncio.gather(
        *(provider.search(keywords, location, limit) for provider in providers)
    )
    records = [job for batch in batches for job in batch]
    deduped = dedupe_raw_job_records(records)
    logger.info(
        "collector.fetch.completed",
        fetched=len(records),
        unique_records=len(deduped),
        duplicates_filtered=len(records) - len(deduped),
    )
    return deduped


def apply_business_rules(
    registry: BusinessRulesRegistry, records: list[RawJobRecord]
) -> list[RuleResult]:
    logger.info("collector.rules.apply", record_count=len(records))
    return [registry.apply(record) for record in records]


def persist_results(
    session: Session,
    settings: Settings,
    results: list[RuleResult],
    *,
    export: bool = True,
) -> tuple[list[Job], Path | None, Path | None]:
    stored_raw = store_raw_jobs(session, results)
    stored_master = store_master_jobs(session, results, stored_raw)
    logger.info(
        "collector.persist.completed",
        raw_jobs=len(stored_raw),
        master_jobs=len(stored_master),
        exports_enabled=export,
    )
    if not export:
        return stored_master, None, None
    json_path, xlsx_path = export_jobs(stored_master, settings.export_dir)
    return stored_master, json_path, xlsx_path


def store_raw_jobs(session: Session, results: list[RuleResult]) -> list[RawJob]:
    if not results:
        return []

    keys = [_raw_key(result.raw.provider, result.raw.api_version, result.raw.source_record_id) for result in results]
    existing_keys = set(
        session.execute(
            select(RawJob.provider, RawJob.api_version, RawJob.source_record_id).where(
                tuple_(RawJob.provider, RawJob.api_version, RawJob.source_record_id).in_(keys)
            )
        ).all()
    )
    for result in results:
        values = result.raw.model_dump()
        values["rule_version"] = result.rule_version
        if session.bind is not None and session.bind.dialect.name == "sqlite":
            statement = sqlite_insert(RawJob).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["provider", "api_version", "source_record_id"],
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"provider", "api_version", "source_record_id"}
                },
            )
            session.execute(statement)
        else:
            existing = session.scalar(
                select(RawJob).where(
                    RawJob.provider == result.raw.provider,
                    RawJob.api_version == result.raw.api_version,
                    RawJob.source_record_id == result.raw.source_record_id,
                )
            )
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                session.add(RawJob(**values))
    session.commit()
    stored = list(
        session.scalars(
            select(RawJob).where(
                tuple_(
                    RawJob.provider,
                    RawJob.api_version,
                    RawJob.source_record_id,
                ).in_(keys)
            )
        )
    )
    logger.info(
        "collector.raw_jobs.stored",
        total=len(stored),
        created=max(len(stored) - len(existing_keys), 0),
        updated=min(len(existing_keys), len(stored)),
    )
    return stored


def store_master_jobs(session: Session, results: list[RuleResult], raw_jobs: list[RawJob]) -> list[Job]:
    raw_index = {
        _raw_key(raw.provider, raw.api_version, raw.source_record_id): raw
        for raw in raw_jobs
    }
    master_keys: list[tuple[str, str, str]] = []
    candidate_keys = [
        _raw_key(result.raw.provider, result.raw.api_version, result.raw.source_record_id)
        for result in results
        if result.standard is not None
    ]
    existing_keys = set(
        session.execute(
            select(Job.provider, Job.api_version, Job.source_record_id).where(
                tuple_(Job.provider, Job.api_version, Job.source_record_id).in_(candidate_keys)
            )
        ).all()
    ) if candidate_keys else set()

    for result in results:
        if result.standard is None:
            continue

        raw = raw_index.get(_raw_key(result.raw.provider, result.raw.api_version, result.raw.source_record_id))
        values = result.standard.model_dump()
        values.update(
            {
                "api_version": result.raw.api_version,
                "source_record_id": result.raw.source_record_id,
                "raw_job_id": raw.id if raw is not None else None,
                "rule_version": result.rule_version,
                "normalization_status": "normalized",
                "last_seen_at": raw.fetched_at if raw is not None else result.raw.fetched_at,
            }
        )
        master_key = _raw_key(result.raw.provider, result.raw.api_version, result.raw.source_record_id)
        master_keys.append(master_key)

        if session.bind is not None and session.bind.dialect.name == "sqlite":
            statement = sqlite_insert(Job).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["provider", "api_version", "source_record_id"],
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"provider", "api_version", "source_record_id"}
                },
            )
            session.execute(statement)
        else:
            existing = session.scalar(
                select(Job).where(
                    Job.provider == result.raw.provider,
                    Job.api_version == result.raw.api_version,
                    Job.source_record_id == result.raw.source_record_id,
                )
            )
            if existing:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                session.add(Job(**values))

    if not master_keys:
        return []
    session.commit()
    stored = list(
        session.scalars(
            select(Job).where(
                tuple_(
                    Job.provider,
                    Job.api_version,
                    Job.source_record_id,
                ).in_(master_keys)
            )
        )
    )
    logger.info(
        "collector.master_jobs.stored",
        total=len(stored),
        created=max(len(stored) - len(existing_keys), 0),
        updated=min(len(existing_keys), len(stored)),
    )
    return stored


def dedupe_raw_job_records(records: list[RawJobRecord]) -> list[RawJobRecord]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[RawJobRecord] = []
    for record in records:
        key = _raw_key(record.provider, record.api_version, record.source_record_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _raw_key(provider: str, api_version: str, source_record_id: str) -> tuple[str, str, str]:
    return (provider, api_version, source_record_id)
