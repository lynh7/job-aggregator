import json
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook

from app.schemas import RawJobResponse


HEADERS = [
    "id",
    "provider",
    "api_version",
    "source_record_id",
    "rule_version",
    "fetched_at",
    "raw_payload",
]


def export_jobs(jobs: list[RawJobResponse], export_dir: Path) -> tuple[Path, Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = export_dir / f"jobs-{stamp}.json"
    xlsx_path = export_dir / f"jobs-{stamp}.xlsx"

    payload = [job.model_dump(mode="json") for job in jobs]
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Jobs"
    sheet.append(HEADERS)
    for item in payload:
        sheet.append(
            [
                item["id"],
                item["provider"],
                item["api_version"],
                item["source_record_id"],
                item["rule_version"],
                item["fetched_at"],
                json.dumps(item["payload"], ensure_ascii=False),
            ]
        )
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(xlsx_path)
    return json_path, xlsx_path
