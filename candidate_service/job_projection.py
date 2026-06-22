from dataclasses import dataclass
from typing import Any

from app.models import RawJob


@dataclass(frozen=True)
class ProjectedJob:
    job_key: str
    provider: str
    api_version: str
    source_record_id: str
    title: str
    company: str | None
    location: str | None
    description: str | None
    employment_type: str | None
    salary_text: str | None
    url: str | None


def project_raw_job(job: RawJob) -> ProjectedJob | None:
    payload: dict[str, Any] = job.payload or {}
    title = _first_str(payload, "title", "job_title", "position")
    if not title:
        return None
    return ProjectedJob(
        job_key=f"{job.provider}:{job.api_version}:{job.source_record_id}",
        provider=job.provider,
        api_version=job.api_version,
        source_record_id=job.source_record_id,
        title=title,
        company=_first_str(payload, "company", "company_name", "employer"),
        location=_first_str(payload, "location", "city", "work_location"),
        description=_first_str(payload, "description", "job_description", "summary"),
        employment_type=_first_str(payload, "employment_type", "employmentType", "type"),
        salary_text=_first_str(payload, "salary", "salary_text", "salary_range"),
        url=_first_str(payload, "url", "job_url", "link"),
    )


def _first_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

