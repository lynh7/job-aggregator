import asyncio

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.business_rules.base import RuleResult
from app.business_rules.registry import BusinessRulesRegistry
from app.connectors.base import JobProvider
from app.models import RawJob
from app.schemas import RawJobRecord


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
    keys = [
        (result.raw.provider, result.raw.api_version, result.raw.source_record_id)
        for result in results
    ]
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
