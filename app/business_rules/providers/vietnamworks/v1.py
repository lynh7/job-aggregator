from app.business_rules.base import RuleResult
from app.business_rules.normalization import build_standard_job_from_aliases
from app.business_rules.passthrough import PassThroughRules
from app.schemas import RawJobRecord


class VietnamWorksV1Rules(PassThroughRules):
    """VietnamWorks API v1 explicit mapping into the master-data schema."""

    rule_version = "vietnamworks-master-v1"

    def __init__(self) -> None:
        super().__init__(provider="vietnamworks", api_version="v1")

    def apply(self, raw: RawJobRecord) -> RuleResult:
        if (raw.provider, raw.api_version) != (self.provider, self.api_version):
            raise ValueError(
                f"Rules for {self.provider}/{self.api_version} cannot process "
                f"{raw.provider}/{raw.api_version}"
            )
        standard = build_standard_job_from_aliases(
            raw,
            external_id_keys=("jobId", "id", "external_id"),
            title_keys=("position", "title", "job_title"),
            company_keys=("employer", "company", "company_name"),
            location_keys=("work_location", "location", "city"),
            description_keys=("summary", "description", "job_description"),
            employment_type_keys=("type", "employment_type"),
            salary_keys=("salary", "salary_range", "salary_text"),
            url_keys=("link", "url", "job_url", "apply_url"),
            posted_at_keys=("createdAt", "created_at", "published_at"),
        )
        return RuleResult(raw=raw, rule_version=self.rule_version, standard=standard)
