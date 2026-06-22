import asyncio
from pathlib import Path

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.business_rules.base import RuleResult
from app.business_rules.registry import BusinessRulesRegistry
from app.config import Settings
from app.connectors.base import JobProvider
from app.models import Job, RawJob
from app.schemas import RawJobRecord
from app.services.exporter import export_jobs


async def collect_jobs(
    providers: list[JobProvider],
    keywords: list[str],
    location: str | None,
    limit: int,
) -> list[RawJobRecord]:
    batches = await asyncio.gather(
        *(provider.search(keywords, location, limit) for provider in providers)
    )
    return [job for batch in batches for job in batch]


def apply_business_rules(
    registry: BusinessRulesRegistry, records: list[RawJobRecord]
) -> list[RuleResult]:
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
    if not export:
        return stored_master, None, None
    json_path, xlsx_path = export_jobs(stored_master, settings.export_dir)
    return stored_master, json_path, xlsx_path


def store_raw_jobs(session: Session, results: list[RuleResult]) -> list[RawJob]:
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
    keys = [_raw_key(result.raw.provider, result.raw.api_version, result.raw.source_record_id) for result in results]
    return list(
        session.scalars(
            select(RawJob).where(
                tuple_(
                    RawJob.provider,
                    RawJob.api_version,
                    RawJob.source_record_id,
                ).in_(keys)
            )
        )
    ) if keys else []


def store_master_jobs(session: Session, results: list[RuleResult], raw_jobs: list[RawJob]) -> list[Job]:
    raw_index = {
        _raw_key(raw.provider, raw.api_version, raw.source_record_id): raw
        for raw in raw_jobs
    }
    master_keys: list[tuple[str, str, str]] = []

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

    session.commit()
    return list(
        session.scalars(
            select(Job).where(
                tuple_(
                    Job.provider,
                    Job.api_version,
                    Job.source_record_id,
                ).in_(master_keys)
            )
        )
    ) if master_keys else []


def _raw_key(provider: str, api_version: str, source_record_id: str) -> tuple[str, str, str]:
    return (provider, api_version, source_record_id)
