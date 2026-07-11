import socket
import time

from sqlalchemy.orm import Session

from candidate_service.service import (
    process_candidate_job_search,
    process_candidate_submission,
    process_job_application,
    rematch_candidate,
)
from candidate_service.task_queue import claim_candidate_task, complete_candidate_task, fail_candidate_task
from shared.config import get_settings
from shared.database import Base, SessionLocal, engine
from shared.logging import configure_logging, get_logger
from shared.models import Candidate

logger = get_logger(__name__)


def process_one_task(session: Session, worker_id: str) -> bool:
    settings = get_settings()
    task = claim_candidate_task(session, worker_id=worker_id)
    if task is None:
        return False

    logger.info(
        "worker.task.claimed",
        worker_id=worker_id,
        task_id=task.id,
        task_type=task.task_type,
        candidate_id=task.candidate_id,
    )
    try:
        if task.task_type == "parse_and_match":
            document_id = int(task.payload["document_id"])
            process_candidate_submission(session, settings, int(task.candidate_id), document_id)
        elif task.task_type == "rematch":
            candidate = session.get(Candidate, task.candidate_id)
            if candidate is None:
                raise ValueError("Candidate not found")
            rematch_candidate(session, settings, candidate.id, task.payload.get("limit"))
            candidate.status = "matched"
            session.commit()
        elif task.task_type == "crawl_jobs_for_candidate":
            search_id = int(task.payload["search_id"])
            process_candidate_job_search(session, settings, search_id)
        elif task.task_type == "apply_to_job":
            application_id = int(task.payload["application_id"])
            process_job_application(session, settings, application_id)
        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")
        complete_candidate_task(session, task)
        logger.info("worker.task.completed", worker_id=worker_id, task_id=task.id, task_type=task.task_type)
        return True
    except Exception as exc:
        session.rollback()
        managed = session.get(type(task), task.id)
        if managed is not None:
            fail_candidate_task(session, managed, str(exc))
        logger.exception(
            "worker.task.failed",
            worker_id=worker_id,
            task_id=task.id,
            task_type=task.task_type,
            candidate_id=task.candidate_id,
        )
        return True


def main() -> None:
    settings = get_settings()
    configure_logging(service_name="candidate-worker", level=settings.log_level, json_logs=settings.log_json)
    Base.metadata.create_all(bind=engine)
    worker_id = f"{socket.gethostname()}:{time.time_ns()}"
    poll_seconds = settings.candidate_task_poll_seconds
    logger.info(
        "worker.started",
        worker_id=worker_id,
        poll_seconds=poll_seconds,
    )
    while True:
        with SessionLocal() as session:
            processed = process_one_task(session, worker_id)
        if not processed:
            time.sleep(poll_seconds)
            

if __name__ == "__main__":
    main()
#Trigger
