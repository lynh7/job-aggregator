from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    location: str | None = None
    providers: list[str] | None = None
    limit_per_provider: int = Field(default=50, ge=1, le=200)


class JobRecord(BaseModel):
    provider: str
    external_id: str
    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    salary_text: str | None = None
    url: str
    posted_at: datetime | None = None


class JobResponse(JobRecord):
    id: int
    api_version: str
    source_record_id: str
    raw_job_id: int | None
    rule_version: str
    normalization_status: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RawJobRecord(BaseModel):
    provider: str
    api_version: str
    source_record_id: str
    payload: dict[str, Any]
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RawJobResponse(RawJobRecord):
    id: int
    rule_version: str

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    fetched: int
    stored: int
    providers: list[str]
    json_export: str
    xlsx_export: str


class IngestRawJobsRequest(BaseModel):
    records: list[RawJobRecord] = Field(min_length=1)
    export: bool = True


class IngestResponse(BaseModel):
    fetched: int
    stored: int
    duplicates_filtered: int = 0
    providers: list[str]
    json_export: str | None = None
    xlsx_export: str | None = None
