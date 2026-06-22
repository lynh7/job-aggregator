from app.business_rules.base import RuleResult
from app.business_rules.normalization import build_standard_job_from_aliases
from app.business_rules.passthrough import PassThroughRules
from app.schemas import RawJobRecord


class ITViecV1Rules(PassThroughRules):
    """ITViec crawler v1 explicit mapping into the master-data schema."""

    rule_version = "itviec-master-v1"

    def __init__(self) -> None:
        super().__init__(provider="itviec", api_version="v1")

    def apply(self, raw: RawJobRecord) -> RuleResult:
        if (raw.provider, raw.api_version) != (self.provider, self.api_version):
            raise ValueError(
                f"Rules for {self.provider}/{self.api_version} cannot process "
                f"{raw.provider}/{raw.api_version}"
            )
        standard = build_standard_job_from_aliases(
            raw,
            external_id_keys=("id", "external_id"),
            title_keys=("title", "job_title"),
            company_keys=("company", "company_name"),
            location_keys=("location", "work_location", "city"),
            description_keys=("description", "descriptions", "summary"),
            employment_type_keys=("employment_type", "mode", "type"),
            salary_keys=("salary", "salary_text"),
            url_keys=("url", "job_url", "apply_url"),
            posted_at_keys=("posted_at", "published_at", "created_at"),
        )
        return RuleResult(raw=raw, rule_version=self.rule_version, standard=standard)
