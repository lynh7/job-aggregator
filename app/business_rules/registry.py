from app.business_rules.base import ProviderBusinessRules, RuleResult
from app.business_rules.passthrough import PassThroughRules
from app.business_rules.providers.itviec import ITViecV1Rules
from app.business_rules.providers.mock import MockV1Rules
from app.business_rules.providers.topcv import TopCVV1Rules
from app.business_rules.providers.vietnamworks import VietnamWorksV1Rules
from app.schemas import RawJobRecord


class BusinessRulesRegistry:
    def __init__(self) -> None:
        self._rules: dict[tuple[str, str], ProviderBusinessRules] = {}

    def register(self, rules: ProviderBusinessRules) -> None:
        key = (rules.provider, rules.api_version)
        if key in self._rules:
            raise ValueError(f"Business rules already registered for {key}")
        self._rules[key] = rules

    def apply(self, raw: RawJobRecord) -> RuleResult:
        key = (raw.provider, raw.api_version)
        rules = self._rules.get(key)
        if rules is None:
            raise ValueError(f"No business rules registered for {raw.provider}/{raw.api_version}")
        return rules.apply(raw)

    def supported_versions(self) -> dict[str, list[str]]:
        supported: dict[str, list[str]] = {}
        for provider, api_version in self._rules:
            supported.setdefault(provider, []).append(api_version)
        return {provider: sorted(versions) for provider, versions in sorted(supported.items())}



def build_business_rules_registry() -> BusinessRulesRegistry:
    registry = BusinessRulesRegistry()

    # These are explicit version slots. They preserve raw JSON today and are the
    # central extension points for future provider-specific standardization.
    registry.register(MockV1Rules())
    registry.register(PassThroughRules("authorized_api", "v1"))
    registry.register(TopCVV1Rules())
    registry.register(VietnamWorksV1Rules())
    registry.register(ITViecV1Rules())
    return registry
