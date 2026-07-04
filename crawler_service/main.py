from contextlib import asynccontextmanager

from fastapi import FastAPI

from crawler_service.config import get_settings
from crawler_service.routes import router
from shared.logging import configure_logging, log_request_middleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(service_name="crawler-api", level=settings.log_level, json_logs=settings.log_json)
    yield


app = FastAPI(
    title="Job Aggregator Crawler",
    version="0.1.0",
    lifespan=lifespan,
)
app.middleware("http")(log_request_middleware)
app.include_router(router, prefix="/api/v1")
