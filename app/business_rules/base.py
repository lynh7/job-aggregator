from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas import JobRecord, RawJobRecord


@dataclass(frozen=True)
class RuleResult:
    raw: RawJobRecord
    rule_version: str
    standard: JobRecord | None = None


class ProviderBusinessRules(ABC):
    provider: str
    api_version: str
    rule_version: str

    @abstractmethod
    def apply(self, raw: RawJobRecord) -> RuleResult:
        """Apply provider/version rules without modifying the raw payload."""

