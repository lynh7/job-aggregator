from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import Base, engine
from candidate_service.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.candidate_storage_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Candidate Matching Service", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")

