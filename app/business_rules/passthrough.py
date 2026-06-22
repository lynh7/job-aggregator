from app.business_rules.base import ProviderBusinessRules, RuleResult
from app.schemas import RawJobRecord


class PassThroughRules(ProviderBusinessRules):
    rule_version = "raw-v1"

    def __init__(self, provider: str, api_version: str) -> None:
        self.provider = provider
        self.api_version = api_version

    def apply(self, raw: RawJobRecord) -> RuleResult:
        if (raw.provider, raw.api_version) != (self.provider, self.api_version):
            raise ValueError(
                f"Rules for {self.provider}/{self.api_version} cannot process "
                f"{raw.provider}/{raw.api_version}"
            )
        return RuleResult(raw=raw, rule_version=self.rule_version)

