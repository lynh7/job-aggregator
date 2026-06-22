from app.config import Settings
from app.connectors.authorized_api import AuthorizedApiProvider
from app.connectors.base import JobProvider
from app.connectors.mock import MockProvider


def build_providers(settings: Settings) -> dict[str, JobProvider]:
    providers: dict[str, JobProvider] = {"mock": MockProvider()}
    if settings.provider_base_url and settings.provider_api_key:
        providers["authorized_api"] = AuthorizedApiProvider(
            base_url=settings.provider_base_url,
            api_key=settings.provider_api_key,
            api_version=settings.provider_api_version,
            timeout=settings.request_timeout_seconds,
        )
    return providers
