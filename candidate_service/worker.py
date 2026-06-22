import socket
import time

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Candidate
from candidate_service.service import process_candidate_submission, rematch_candidate
from candidate_service.task_queue import claim_candidate_task, complete_candidate_task, fail_candidate_task


def process_one_task(session: Session, worker_id: str) -> bool:
    task = claim_candidate_task(session, worker_id=worker_id)
    if task is None:
        return False

    settings = get_settings()
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
        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")
        complete_candidate_task(session, task)
        return True
    except Exception as exc:
        session.rollback()
        managed = session.get(type(task), task.id)
        if managed is not None:
            fail_candidate_task(session, managed, str(exc))
        return True


def main() -> None:
    Base.metadata.create_all(bind=engine)
    worker_id = f"{socket.gethostname()}:{time.time_ns()}"
    poll_seconds = get_settings().candidate_task_poll_seconds
    while True:
        with SessionLocal() as session:
            processed = process_one_task(session, worker_id)
        if not processed:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
