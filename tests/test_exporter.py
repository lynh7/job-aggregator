import json
from datetime import UTC, datetime

from openpyxl import load_workbook

from app.schemas import RawJobResponse
from app.services.exporter import export_jobs


def test_export_jobs_creates_json_and_xlsx(tmp_path):
    job = RawJobResponse(
        id=1,
        provider="mock",
        api_version="v1",
        source_record_id="abc",
        rule_version="raw-v1",
        payload={"title": "Python Engineer", "provider_field": "unchanged"},
        fetched_at=datetime.now(UTC),
    )

    json_path, xlsx_path = export_jobs([job], tmp_path)

    assert json.loads(json_path.read_text())[0]["payload"]["title"] == "Python Engineer"
    sheet = load_workbook(xlsx_path).active
    assert json.loads(sheet["G2"].value)["provider_field"] == "unchanged"

