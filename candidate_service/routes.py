from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Candidate, CandidateProfile, CandidateTask, JobApplication, JobMatch
from candidate_service.schemas import (
    CandidateApplicationResponse,
    CandidateApplyRequest,
    CandidateApplyResponse,
    CandidateCreateResponse,
    CandidateDetailResponse,
    CandidateMatchResponse,
    CandidateProfileResponse,
    CandidateRematchRequest,
    CandidateResponse,
    CandidateSubmissionMetadata,
    CandidateTaskResponse,
)
from candidate_service.service import create_candidate_submission, enqueue_job_applications, enqueue_rematch

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/candidates", response_model=CandidateCreateResponse, status_code=202)
def submit_candidate(
    file: UploadFile = File(...),
    full_name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    phone: str | None = Form(default=None),
    location: str | None = Form(default=None),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CandidateCreateResponse:
    metadata = CandidateSubmissionMetadata(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
    ).model_dump()
    try:
        candidate, document, task_id = create_candidate_submission(session, settings, file, metadata)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CandidateCreateResponse(
        candidate_id=candidate.id,
        document_id=document.id,
        task_id=task_id,
        status=candidate.status,
    )


@router.get("/candidates", response_model=list[CandidateResponse])
def list_candidates(limit: int = 100, session: Session = Depends(get_db)) -> list[Candidate]:
    return list(session.scalars(select(Candidate).order_by(Candidate.created_at.desc()).limit(min(limit, 500))))


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(candidate_id: int, session: Session = Depends(get_db)) -> CandidateDetailResponse:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    profile = session.scalar(
        select(CandidateProfile)
        .where(CandidateProfile.candidate_id == candidate_id)
        .order_by(CandidateProfile.created_at.desc())
        .limit(1)
    )
    tasks = list(
        session.scalars(
            select(CandidateTask)
            .where(CandidateTask.candidate_id == candidate_id)
            .order_by(CandidateTask.created_at.desc())
        )
    )
    return CandidateDetailResponse(
        candidate=CandidateResponse.model_validate(candidate),
        latest_profile=CandidateProfileResponse.model_validate(profile) if profile else None,
        tasks=[CandidateTaskResponse.model_validate(task) for task in tasks],
    )


@router.get("/candidates/{candidate_id}/matches", response_model=list[CandidateMatchResponse])
def list_candidate_matches(candidate_id: int, session: Session = Depends(get_db)) -> list[JobMatch]:
    return list(
        session.scalars(
            select(JobMatch)
            .where(JobMatch.candidate_id == candidate_id)
            .order_by(JobMatch.match_score.desc(), JobMatch.created_at.desc())
        )
    )


@router.post("/candidates/{candidate_id}/rematch", response_model=CandidateTaskResponse, status_code=202)
def rematch_candidate(
    candidate_id: int,
    request: CandidateRematchRequest,
    session: Session = Depends(get_db),
) -> CandidateTaskResponse:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    task_id = enqueue_rematch(session, candidate_id, request.limit)
    task = session.get(CandidateTask, task_id)
    assert task is not None
    return CandidateTaskResponse.model_validate(task)


@router.post("/candidates/{candidate_id}/apply", response_model=CandidateApplyResponse, status_code=202)
def apply_to_jobs(
    candidate_id: int,
    request: CandidateApplyRequest,
    session: Session = Depends(get_db),
) -> CandidateApplyResponse:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    try:
        task_ids = enqueue_job_applications(session, candidate_id, request.match_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CandidateApplyResponse(queued=len(task_ids), task_ids=task_ids)


@router.get("/candidates/{candidate_id}/applications", response_model=list[CandidateApplicationResponse])
def list_candidate_applications(candidate_id: int, session: Session = Depends(get_db)) -> list[JobApplication]:
    return list(
        session.scalars(
            select(JobApplication)
            .where(JobApplication.candidate_id == candidate_id)
            .order_by(JobApplication.created_at.desc())
        )
    )


@router.get("/tasks", response_model=list[CandidateTaskResponse])
def list_tasks(limit: int = 100, session: Session = Depends(get_db)) -> list[CandidateTask]:
    return list(
        session.scalars(select(CandidateTask).order_by(CandidateTask.created_at.desc()).limit(min(limit, 500)))
    )
