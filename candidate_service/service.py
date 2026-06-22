import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.connectors.base import ProviderApplicationRequest
from app.connectors.registry import build_providers
from app.models import Candidate, CandidateDocument, CandidateProfile, Job, JobApplication, JobMatch
from candidate_service.job_projection import project_master_job
from candidate_service.matching import MATCH_RULE_VERSION, score_candidate_job
from candidate_service.parsing import PARSER_VERSION, extract_document_text, parse_candidate_profile
from candidate_service.task_queue import enqueue_candidate_task


SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt"}
PROFILE_VERSION = "candidate-profile-v1"


def create_candidate_submission(
    session: Session,
    settings: Settings,
    upload: UploadFile,
    metadata: dict,
) -> tuple[Candidate, CandidateDocument, int]:
    _validate_upload(upload)
    settings.candidate_storage_dir.mkdir(parents=True, exist_ok=True)

    candidate = Candidate(
        full_name=metadata.get("full_name"),
        email=metadata.get("email"),
        phone=metadata.get("phone"),
        location=metadata.get("location"),
        status="uploaded",
        consent_given=True,
    )
    session.add(candidate)
    session.flush()

    storage_name = f"{candidate.id}-{uuid.uuid4().hex}{Path(upload.filename or '').suffix.lower()}"
    storage_path = settings.candidate_storage_dir / storage_name
    with storage_path.open("wb") as target:
        shutil.copyfileobj(upload.file, target)

    document = CandidateDocument(
        candidate_id=candidate.id,
        filename=upload.filename or storage_name,
        content_type=upload.content_type or "application/octet-stream",
        storage_path=str(storage_path),
        file_size_bytes=storage_path.stat().st_size,
    )
    session.add(document)
    session.commit()
    session.refresh(candidate)
    session.refresh(document)

    task = enqueue_candidate_task(
        session,
        task_type="parse_and_match",
        candidate_id=candidate.id,
        payload={"document_id": document.id},
    )
    return candidate, document, task.id


def process_candidate_submission(session: Session, settings: Settings, candidate_id: int, document_id: int) -> None:
    candidate = session.get(Candidate, candidate_id)
    document = session.get(CandidateDocument, document_id)
    if candidate is None or document is None:
        raise ValueError("Candidate submission is incomplete")

    text = extract_document_text(Path(document.storage_path))
    parsed = parse_candidate_profile(text)

    document.extracted_text = text
    document.parser_version = PARSER_VERSION
    candidate.email = candidate.email or parsed["email"]
    candidate.phone = candidate.phone or parsed["phone"]
    candidate.location = candidate.location or _derive_location(parsed, text)
    candidate.status = "parsed"
    candidate.latest_profile_version = PROFILE_VERSION

    profile = CandidateProfile(
        candidate_id=candidate.id,
        profile_version=PROFILE_VERSION,
        summary=parsed["summary"],
        years_experience=parsed["years_experience"],
        preferred_roles=parsed["preferred_roles"],
        skills=parsed["skills"],
        languages=parsed["languages"],
        raw_profile=parsed,
    )
    session.add(profile)
    session.commit()

    rematch_candidate(session, settings, candidate.id)
    candidate.status = "matched"
    session.commit()


def rematch_candidate(session: Session, settings: Settings, candidate_id: int, limit: int | None = None) -> int:
    candidate = session.get(Candidate, candidate_id)
    profile = session.scalar(
        select(CandidateProfile)
        .where(CandidateProfile.candidate_id == candidate_id)
        .order_by(CandidateProfile.created_at.desc())
        .limit(1)
    )
    if candidate is None or profile is None:
        raise ValueError("Candidate profile is missing")

    session.execute(
        delete(JobMatch).where(
            JobMatch.candidate_id == candidate_id,
            JobMatch.rule_version == MATCH_RULE_VERSION,
        )
    )

    projected_jobs = [
        projected
        for projected in (project_master_job(job) for job in session.scalars(select(Job)))
        if projected is not None
    ]
    scored = sorted(
        (
            (projected, score_candidate_job({**profile.raw_profile, "location": candidate.location}, projected))
            for projected in projected_jobs
        ),
        key=lambda item: item[1].score,
        reverse=True,
    )

    max_results = limit or settings.candidate_match_limit
    for projected, result in scored[:max_results]:
        values = {
            "candidate_id": candidate_id,
            "job_key": projected.job_key,
            "provider": projected.provider,
            "api_version": projected.api_version,
            "job_source_record_id": projected.source_record_id,
            "title": projected.title,
            "company": projected.company,
            "location": projected.location,
            "job_url": projected.url,
            "match_score": result.score,
            "score_breakdown": result.score_breakdown,
            "matched_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
            "rule_version": MATCH_RULE_VERSION,
        }
        if session.bind is not None and session.bind.dialect.name == "sqlite":
            statement = sqlite_insert(JobMatch).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["candidate_id", "job_key", "rule_version"],
                set_=values,
            )
            session.execute(statement)
        else:
            session.add(JobMatch(**values))
    session.commit()
    return min(len(scored), max_results)


def enqueue_rematch(session: Session, candidate_id: int, limit: int | None = None) -> int:
    task = enqueue_candidate_task(
        session,
        task_type="rematch",
        candidate_id=candidate_id,
        payload={"limit": limit},
    )
    return task.id


def enqueue_job_applications(session: Session, candidate_id: int, match_ids: list[int]) -> list[int]:
    task_ids: list[int] = []
    for match_id in match_ids:
        match = session.get(JobMatch, match_id)
        if match is None or match.candidate_id != candidate_id:
            raise ValueError(f"Match {match_id} is not available for candidate {candidate_id}")

        application = session.scalar(
            select(JobApplication).where(
                JobApplication.candidate_id == candidate_id,
                JobApplication.match_id == match_id,
            )
        )
        if application is None:
            application = JobApplication(
                candidate_id=candidate_id,
                match_id=match.id,
                provider=match.provider,
                api_version=match.api_version,
                job_source_record_id=match.job_source_record_id,
                status="pending",
            )
            session.add(application)
            session.commit()
            session.refresh(application)
        else:
            application.status = "pending"
            application.last_error = None
            session.commit()

        task = enqueue_candidate_task(
            session,
            task_type="apply_to_job",
            candidate_id=candidate_id,
            payload={"application_id": application.id},
        )
        task_ids.append(task.id)
    return task_ids


def process_job_application(session: Session, settings: Settings, application_id: int) -> None:
    application = session.get(JobApplication, application_id)
    if application is None:
        raise ValueError("Application not found")

    candidate = session.get(Candidate, application.candidate_id)
    match = session.get(JobMatch, application.match_id)
    if candidate is None or match is None:
        raise ValueError("Application context is incomplete")

    document = session.scalar(
        select(CandidateDocument)
        .where(CandidateDocument.candidate_id == candidate.id)
        .order_by(CandidateDocument.created_at.desc())
        .limit(1)
    )
    if document is None:
        raise ValueError("Candidate document is missing")

    providers = build_providers(settings)
    provider = providers.get(application.provider)
    if provider is None:
        raise ValueError(f"Provider {application.provider} is not configured")

    cv_path = Path(document.storage_path)
    cv_bytes = cv_path.read_bytes()
    request = ProviderApplicationRequest(
        candidate_id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        cv_text=document.extracted_text,
        cv_filename=document.filename,
        cv_content_type=document.content_type,
        cv_bytes=cv_bytes,
        job_source_record_id=match.job_source_record_id,
        job_url=match.job_url,
    )

    application.status = "processing"
    application.document_id = document.id
    session.commit()

    try:
        result = asyncio.run(provider.apply(request))
    except Exception as exc:
        session.rollback()
        managed = session.get(JobApplication, application.id)
        if managed is not None:
            managed.mark_failed(str(exc))
            session.commit()
        raise

    application = session.get(JobApplication, application.id)
    assert application is not None
    application.external_application_id = result.external_application_id
    application.request_payload = result.request_payload
    application.response_payload = result.response_payload
    application.mark_submitted()
    session.commit()


def _validate_upload(upload: UploadFile) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix or 'missing extension'}")
    if upload.content_type and upload.content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError(f"Unsupported content type: {upload.content_type}")


def _derive_location(parsed: dict, text: str) -> str | None:
    if parsed.get("summary") and "remote" in parsed["summary"].lower():
        return "Remote"
    for line in text.splitlines():
        if "location" in line.lower() and ":" in line:
            _, value = line.split(":", 1)
            value = value.strip()
            if value:
                return value
    return None
