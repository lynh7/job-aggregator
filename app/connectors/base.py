from abc import ABC, abstractmethod

from app.schemas import RawJobRecord


class JobProvider(ABC):
    name: str
    api_version: str

    @abstractmethod
    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        """Return source records without changing their payloads."""
