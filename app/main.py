from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Job Aggregator Backend",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router, prefix="/api/v1")

