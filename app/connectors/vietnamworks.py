from app.connectors.authorized_api import AuthorizedApiProvider
from app.connectors.base import ProviderApplicationRequest, ProviderApplicationResult


class VietnamWorksProvider(AuthorizedApiProvider):
    name = "vietnamworks"

    async def apply(self, request: ProviderApplicationRequest) -> ProviderApplicationResult:
        result = await super().apply(request)
        payload = dict(result.request_payload)
        payload["jobId"] = request.job_source_record_id
        response = dict(result.response_payload)
        external_id = result.external_application_id or f"vietnamworks-{request.job_source_record_id}-{request.candidate_id}"
        return ProviderApplicationResult(
            status=result.status,
            external_application_id=external_id,
            request_payload=payload,
            response_payload=response,
        )
