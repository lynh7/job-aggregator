from app.business_rules.registry import build_business_rules_registry
from app.schemas import RawJobRecord


def test_pass_through_rule_preserves_raw_payload_identity():
    payload = {"unexpected": {"provider": ["shape", 1]}}
    raw = RawJobRecord(
        provider="topcv",
        api_version="v1",
        source_record_id="topcv-1",
        payload=payload,
    )

    result = build_business_rules_registry().apply(raw)

    assert result.raw.payload == payload
    assert result.standard is None
    assert result.rule_version == "raw-v1"


def test_registry_reports_provider_api_versions():
    supported = build_business_rules_registry().supported_versions()

    assert supported["topcv"] == ["v1"]
    assert supported["vietnamworks"] == ["v1"]
