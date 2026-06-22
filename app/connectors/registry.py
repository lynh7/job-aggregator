from app.config import Settings
from app.connectors.authorized_api import AuthorizedApiProvider
from app.connectors.base import JobProvider
from app.connectors.mock import MockProvider
from app.connectors.topcv import TopCVProvider
from app.connectors.vietnamworks import VietnamWorksProvider


def build_providers(settings: Settings) -> dict[str, JobProvider]:
    providers: dict[str, JobProvider] = {"mock": MockProvider()}
    if settings.provider_base_url and settings.provider_api_key:
        providers["authorized_api"] = AuthorizedApiProvider(
            base_url=settings.provider_base_url,
            api_key=settings.provider_api_key,
            api_version=settings.provider_api_version,
            timeout=settings.request_timeout_seconds,
        )
    if settings.topcv_base_url and settings.topcv_api_key:
        providers["topcv"] = TopCVProvider(
            base_url=settings.topcv_base_url,
            api_key=settings.topcv_api_key,
            api_version=settings.topcv_api_version,
            timeout=settings.request_timeout_seconds,
            search_path=settings.topcv_search_path,
            apply_path=settings.topcv_apply_path,
        )
    if settings.vietnamworks_base_url and settings.vietnamworks_api_key:
        providers["vietnamworks"] = VietnamWorksProvider(
            base_url=settings.vietnamworks_base_url,
            api_key=settings.vietnamworks_api_key,
            api_version=settings.vietnamworks_api_version,
            timeout=settings.request_timeout_seconds,
            search_path=settings.vietnamworks_search_path,
            apply_path=settings.vietnamworks_apply_path,
        )
    return providers
