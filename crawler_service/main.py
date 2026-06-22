from fastapi import FastAPI

from crawler_service.routes import router

app = FastAPI(
    title="Job Aggregator Crawler",
    version="0.1.0",
)
app.include_router(router, prefix="/api/v1")
