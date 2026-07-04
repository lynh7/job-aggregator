from dataclasses import dataclass

from shared.models import Job


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


def project_master_job(job: Job) -> ProjectedJob | None:
    if not job.title:
        return None
    return ProjectedJob(
        job_key=f"{job.provider}:{job.api_version}:{job.source_record_id}",
        provider=job.provider,
        api_version=job.api_version,
        source_record_id=job.source_record_id,
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        employment_type=job.employment_type,
        salary_text=job.salary_text,
        url=job.url,
    )
