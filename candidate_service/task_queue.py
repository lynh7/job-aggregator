from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.logging import get_logger
from app.models import CandidateTask

logger = get_logger(__name__)


def enqueue_candidate_task(
    session: Session,
    *,
    task_type: str,
    candidate_id: int,
    payload: dict,
    max_attempts: int = 5,
) -> CandidateTask:
    task = CandidateTask(
        task_type=task_type,
        status="pending",
        candidate_id=candidate_id,
        payload=payload,
        max_attempts=max_attempts,
        available_at=datetime.now(UTC),
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info(
        "task.queued",
        task_id=task.id,
        task_type=task.task_type,
        candidate_id=task.candidate_id,
        available_at=task.available_at.isoformat(),
    )
    return task


def claim_candidate_task(session: Session, *, worker_id: str) -> CandidateTask | None:
    now = datetime.now(UTC)
    query: Select[tuple[CandidateTask]] = (
        select(CandidateTask)
        .where(CandidateTask.status == "pending", CandidateTask.available_at <= now)
        .order_by(CandidateTask.created_at.asc())
        .limit(1)
    )
    if session.bind is not None and session.bind.dialect.name != "sqlite":
        query = query.with_for_update(skip_locked=True)

    task = session.scalar(query)
    if task is None:
        return None

    task.status = "processing"
    task.locked_by = worker_id
    task.locked_at = now
    task.attempts += 1
    session.commit()
    session.refresh(task)
    logger.info(
        "task.claimed",
        task_id=task.id,
        task_type=task.task_type,
        candidate_id=task.candidate_id,
        worker_id=worker_id,
        attempts=task.attempts,
    )
    return task


def complete_candidate_task(session: Session, task: CandidateTask) -> None:
    task.status = "completed"
    task.locked_by = None
    task.locked_at = None
    task.last_error = None
    session.commit()
    logger.info("task.completed", task_id=task.id, task_type=task.task_type, candidate_id=task.candidate_id)


def fail_candidate_task(session: Session, task: CandidateTask, error: str) -> None:
    task.last_error = error[:2000]
    task.locked_by = None
    task.locked_at = None
    if task.attempts >= task.max_attempts:
        task.status = "failed"
    else:
        task.status = "pending"
        task.available_at = datetime.now(UTC) + timedelta(seconds=min(task.attempts * 10, 60))
    session.commit()
    logger.warning(
        "task.failed",
        task_id=task.id,
        task_type=task.task_type,
        candidate_id=task.candidate_id,
        attempts=task.attempts,
        status=task.status,
        error=task.last_error,
    )
