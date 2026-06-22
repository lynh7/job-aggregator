from typing import Any

import httpx

from app.connectors.base import JobProvider
from app.schemas import RawJobRecord


class AuthorizedApiProvider(JobProvider):
    """Template for a documented API or feed for which the operator has permission."""

    name = "authorized_api"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_version: str = "v1",
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version
        self.timeout = timeout

    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url.rstrip('/')}/jobs",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={
                    "keywords": ",".join(keywords),
                    "location": location,
                    "limit": limit,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return [
            RawJobRecord(
                provider=self.name,
                api_version=self.api_version,
                source_record_id=str(item["id"]),
                payload=item,
            )
            for item in self._items(payload)
        ]

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("jobs"), list):
            return payload["jobs"]
        raise ValueError("Provider response must be a list or contain a 'jobs' list")

