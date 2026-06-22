import json
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook

from app.schemas import JobResponse


HEADERS = [
    "id",
    "provider",
    "api_version",
    "source_record_id",
    "external_id",
    "title",
    "company",
    "location",
    "description",
    "employment_type",
    "salary_text",
    "url",
    "posted_at",
    "rule_version",
    "normalization_status",
    "raw_job_id",
    "last_seen_at",
]


def export_jobs(jobs: list[JobResponse], export_dir: Path) -> tuple[Path, Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = export_dir / f"jobs-{stamp}.json"
    xlsx_path = export_dir / f"jobs-{stamp}.xlsx"

    payload = [job.model_dump(mode="json") for job in jobs]
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "MasterJobs"
    sheet.append(HEADERS)
    for item in payload:
        sheet.append(
            [
                item["id"],
                item["provider"],
                item["api_version"],
                item["source_record_id"],
                item["external_id"],
                item["title"],
                item.get("company"),
                item.get("location"),
                item.get("description"),
                item.get("employment_type"),
                item.get("salary_text"),
                item["url"],
                item.get("posted_at"),
                item["rule_version"],
                item["normalization_status"],
                item.get("raw_job_id"),
                item["last_seen_at"],
            ]
        )
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    workbook.save(xlsx_path)
    return json_path, xlsx_path
