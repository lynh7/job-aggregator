from datetime import datetime
from typing import Any, Sequence

from app.schemas import JobRecord, RawJobRecord


def build_standard_job(raw: RawJobRecord) -> JobRecord | None:
    return build_standard_job_from_aliases(
        raw,
        external_id_keys=("id", "job_id", "external_id", "jobId"),
        title_keys=("title", "job_title", "position", "position_name"),
        company_keys=("company", "company_name", "employer"),
        location_keys=("location", "city", "work_location"),
        description_keys=("description", "job_description", "summary"),
        employment_type_keys=("employment_type", "employmentType", "type"),
        salary_keys=("salary", "salary_text", "salary_range"),
        url_keys=("url", "job_url", "link", "application_url", "apply_url"),
        posted_at_keys=("posted_at", "postedAt", "published_at", "created_at", "createdAt"),
    )


def build_standard_job_from_aliases(
    raw: RawJobRecord,
    *,
    external_id_keys: Sequence[str],
    title_keys: Sequence[str],
    company_keys: Sequence[str],
    location_keys: Sequence[str],
    description_keys: Sequence[str],
    employment_type_keys: Sequence[str],
    salary_keys: Sequence[str],
    url_keys: Sequence[str],
    posted_at_keys: Sequence[str],
) -> JobRecord | None:
    payload = raw.payload or {}
    title = first_str(payload, *title_keys)
    if not title:
        return None

    external_id = first_str(payload, *external_id_keys) or raw.source_record_id
    url = first_str(payload, *url_keys) or f"provider://{raw.provider}/{raw.api_version}/{raw.source_record_id}"

    return JobRecord(
        provider=raw.provider,
        external_id=external_id,
        title=title,
        company=first_str(payload, *company_keys),
        location=first_str(payload, *location_keys),
        description=first_str(payload, *description_keys),
        employment_type=first_str(payload, *employment_type_keys),
        salary_text=first_str(payload, *salary_keys),
        url=url,
        posted_at=first_datetime(payload, *posted_at_keys),
    )


def first_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def first_datetime(payload: dict[str, Any], *keys: str) -> datetime | None:
    for key in keys:
        value = payload.get(key)
        parsed = parse_datetime(value)
        if parsed is not None:
            return parsed
    return None


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
