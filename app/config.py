from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/jobs.db"
    export_dir: Path = Path("./data/exports")
    enabled_providers: str = "mock"
    provider_api_key: str | None = None
    provider_base_url: str | None = None
    provider_api_version: str = "v1"
    topcv_api_key: str | None = None
    topcv_base_url: str | None = None
    topcv_api_version: str = "v1"
    topcv_search_path: str = "/jobs"
    topcv_apply_path: str = "/applications"
    vietnamworks_api_key: str | None = None
    vietnamworks_base_url: str | None = None
    vietnamworks_api_version: str = "v1"
    vietnamworks_search_path: str = "/jobs"
    vietnamworks_apply_path: str = "/applications"
    request_timeout_seconds: float = 20.0
    candidate_storage_dir: Path = Path("./data/candidates")
    candidate_task_poll_seconds: float = 2.0
    candidate_match_limit: int = 50
    queue_backend: str = "database"
    nats_url: str = "nats://nats:4222"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def providers(self) -> list[str]:
        return [item.strip() for item in self.enabled_providers.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
