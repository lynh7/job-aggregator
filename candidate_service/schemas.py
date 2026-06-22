from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CandidateCreateResponse(BaseModel):
    candidate_id: int
    document_id: int
    task_id: int
    status: str


class CandidateResponse(BaseModel):
    id: int
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    status: str
    latest_profile_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateProfileResponse(BaseModel):
    id: int
    candidate_id: int
    profile_version: str
    summary: str | None
    years_experience: float | None
    preferred_roles: list[str]
    skills: list[str]
    languages: list[str]
    raw_profile: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateMatchResponse(BaseModel):
    id: int
    candidate_id: int
    job_key: str
    provider: str
    api_version: str
    job_source_record_id: str
    title: str
    company: str | None
    location: str | None
    job_url: str | None
    match_score: float
    score_breakdown: dict
    matched_skills: list[str]
    missing_skills: list[str]
    rule_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateTaskResponse(BaseModel):
    id: int
    task_type: str
    status: str
    candidate_id: int | None
    payload: dict
    attempts: int
    max_attempts: int
    locked_by: str | None
    last_error: str | None
    available_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    match_id: int
    document_id: int | None
    provider: str
    api_version: str
    job_source_record_id: str
    status: str
    external_application_id: str | None
    request_payload: dict
    response_payload: dict
    last_error: str | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateApplyRequest(BaseModel):
    match_ids: list[int] = Field(min_length=1)


class CandidateApplyResponse(BaseModel):
    queued: int
    task_ids: list[int]


class CandidateDetailResponse(BaseModel):
    candidate: CandidateResponse
    latest_profile: CandidateProfileResponse | None
    tasks: list[CandidateTaskResponse]


class CandidateRematchRequest(BaseModel):
    limit: int | None = None


class CandidateSubmissionMetadata(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
