import json
from datetime import UTC, datetime

from openpyxl import load_workbook

from shared.schemas import JobResponse
from app.services.exporter import export_jobs


def test_export_jobs_creates_json_and_xlsx(tmp_path):
    job = JobResponse(
        id=1,
        provider="mock",
        api_version="v1",
        source_record_id="abc",
        raw_job_id=10,
        external_id="abc",
        title="Python Engineer",
        company="Example Co",
        location="Remote",
        description="Build APIs",
        employment_type="Full-time",
        salary_text=None,
        url="https://example.com/jobs/abc",
        posted_at=None,
        rule_version="master-v1",
        normalization_status="normalized",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )

    json_path, xlsx_path = export_jobs([job], tmp_path)

    assert json.loads(json_path.read_text())[0]["title"] == "Python Engineer"
    sheet = load_workbook(xlsx_path).active
    assert sheet["F2"].value == "Python Engineer"
    assert sheet["N2"].value == "master-v1"
