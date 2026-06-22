from typing import Any

import httpx

from app.connectors.base import JobProvider, ProviderApplicationRequest, ProviderApplicationResult
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
        search_path: str = "/jobs",
        apply_path: str = "/applications",
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.api_version = api_version
        self.timeout = timeout
        self.search_path = search_path
        self.apply_path = apply_path

    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url.rstrip('/')}{self.search_path}",
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
                source_record_id=str(item.get("id") or item.get("job_id") or item.get("jobId")),
                payload=item,
            )
            for item in self._items(payload)
        ]

    async def apply(self, request: ProviderApplicationRequest) -> ProviderApplicationResult:
        data = {
            "candidate_id": str(request.candidate_id),
            "job_source_record_id": request.job_source_record_id,
            "full_name": request.full_name or "",
            "email": request.email or "",
            "phone": request.phone or "",
            "location": request.location or "",
            "cv_text": request.cv_text or "",
            "job_url": request.job_url or "",
        }
        files = {
            "cv": (request.cv_filename, request.cv_bytes, request.cv_content_type),
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}{self.apply_path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=data,
                files=files,
            )
            response.raise_for_status()
            payload = response.json() if response.content else {"status": "submitted"}
        return ProviderApplicationResult(
            status=str(payload.get("status") or "submitted"),
            external_application_id=str(payload.get("application_id") or payload.get("id") or ""),
            request_payload=data | {"cv_filename": request.cv_filename},
            response_payload=payload,
        )

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("jobs", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
                if isinstance(value, dict) and isinstance(value.get("jobs"), list):
                    return value["jobs"]
        raise ValueError("Provider response must be a list or contain a jobs list")
