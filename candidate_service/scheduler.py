import time

from candidate_service.service import enqueue_due_job_search_tasks
from shared.config import get_settings
from shared.database import Base, SessionLocal, engine
from shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(service_name="candidate-scheduler", level=settings.log_level, json_logs=settings.log_json)
    Base.metadata.create_all(bind=engine)
    poll_seconds = settings.candidate_task_poll_seconds
    logger.info(
        "scheduler.started",
        poll_seconds=poll_seconds,
        crawl_scheduler_enabled=settings.candidate_crawl_scheduler_enabled,
        crawl_interval_hours=settings.candidate_crawl_interval_hours,
    )
    while True:
        if settings.candidate_crawl_scheduler_enabled:
            with SessionLocal() as session:
                enqueued = enqueue_due_job_search_tasks(session, settings)
            if enqueued:
                logger.info("scheduler.tick.enqueued", count=enqueued)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
