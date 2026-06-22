from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas import RawJobRecord


@dataclass(frozen=True)
class ProviderApplicationRequest:
    candidate_id: int
    full_name: str | None
    email: str | None
    phone: str | None
    location: str | None
    cv_text: str | None
    cv_filename: str
    cv_content_type: str
    cv_bytes: bytes
    job_source_record_id: str
    job_url: str | None


@dataclass(frozen=True)
class ProviderApplicationResult:
    status: str
    external_application_id: str | None
    request_payload: dict
    response_payload: dict


class JobProvider(ABC):
    name: str
    api_version: str

    @abstractmethod
    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        """Return source records without changing their payloads."""

    @abstractmethod
    async def apply(self, request: ProviderApplicationRequest) -> ProviderApplicationResult:
        """Submit a candidate application to the provider API."""
