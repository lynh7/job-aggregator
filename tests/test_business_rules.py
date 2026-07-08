from app.business_rules.registry import build_business_rules_registry
from shared.schemas import RawJobRecord


def test_topcv_rule_preserves_raw_payload_and_maps_master_record():
    payload = {
        "job_id": "topcv-1",
        "job_title": "Platform Engineer",
        "company_name": "Top Company",
        "city": "Hanoi",
        "job_description": "Kubernetes and Python",
        "job_type": "Full-time",
        "salary_range": "$1000-$2000",
        "apply_url": "https://topcv.example/jobs/topcv-1",
        "published_at": "2026-06-22T10:00:00Z",
    }
    raw = RawJobRecord(provider="topcv", api_version="v1", source_record_id="topcv-1", payload=payload)

    result = build_business_rules_registry().apply(raw)

    assert result.raw.payload == payload
    assert result.standard is not None
    assert result.standard.external_id == "topcv-1"
    assert result.standard.title == "Platform Engineer"
    assert result.standard.company == "Top Company"
    assert result.rule_version == "topcv-master-v1"


def test_vietnamworks_rule_preserves_raw_payload_and_maps_master_record():
    payload = {
        "jobId": "vw-1",
        "position": "Backend Engineer",
        "employer": "VW Company",
        "work_location": "HCMC",
        "summary": "FastAPI and PostgreSQL",
        "type": "Hybrid",
        "salary": "$2000",
        "link": "https://vw.example/jobs/vw-1",
        "createdAt": "2026-06-21T10:00:00Z",
    }
    raw = RawJobRecord(provider="vietnamworks", api_version="v1", source_record_id="vw-1", payload=payload)

    result = build_business_rules_registry().apply(raw)

    assert result.raw.payload == payload
    assert result.standard is not None
    assert result.standard.external_id == "vw-1"
    assert result.standard.title == "Backend Engineer"
    assert result.standard.company == "VW Company"
    assert result.rule_version == "vietnamworks-master-v1"


def test_registry_reports_provider_api_versions():
    supported = build_business_rules_registry().supported_versions()

    assert supported["topcv"] == ["v1"]
    assert supported["vietnamworks"] == ["v1"]
