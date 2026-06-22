from app.business_rules.base import RuleResult
from app.business_rules.normalization import build_standard_job_from_aliases
from app.business_rules.passthrough import PassThroughRules
from app.schemas import RawJobRecord


class TopCVV1Rules(PassThroughRules):
    """TopCV API v1 explicit mapping into the master-data schema."""

    rule_version = "topcv-master-v1"

    def __init__(self) -> None:
        super().__init__(provider="topcv", api_version="v1")

    def apply(self, raw: RawJobRecord) -> RuleResult:
        if (raw.provider, raw.api_version) != (self.provider, self.api_version):
            raise ValueError(
                f"Rules for {self.provider}/{self.api_version} cannot process "
                f"{raw.provider}/{raw.api_version}"
            )
        standard = build_standard_job_from_aliases(
            raw,
            external_id_keys=("job_id", "id", "external_id"),
            title_keys=("job_title", "title", "position_name"),
            company_keys=("company_name", "company", "employer"),
            location_keys=("city", "location", "work_location"),
            description_keys=("job_description", "description", "summary"),
            employment_type_keys=("job_type", "employment_type", "type"),
            salary_keys=("salary_range", "salary_text", "salary"),
            url_keys=("apply_url", "job_url", "url", "link"),
            posted_at_keys=("published_at", "posted_at", "created_at"),
        )
        return RuleResult(raw=raw, rule_version=self.rule_version, standard=standard)
