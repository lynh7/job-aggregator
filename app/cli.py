import argparse
import asyncio

from app.business_rules.registry import build_business_rules_registry
from app.config import get_settings
from app.connectors.registry import build_providers
from app.database import Base, SessionLocal, engine
from app.schemas import RawJobResponse
from app.services.collector import apply_business_rules, collect_jobs, store_raw_jobs
from app.services.exporter import export_jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and export job listings")
    subparsers = parser.add_subparsers(dest="command", required=True)
    search = subparsers.add_parser("search")
    search.add_argument("--keywords", required=True, help="Comma-separated keywords")
    search.add_argument("--location")
    search.add_argument("--providers", default=None, help="Comma-separated provider names")
    search.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    settings = get_settings()
    registry = build_providers(settings)
    provider_names = (
        [item.strip() for item in args.providers.split(",")] if args.providers else settings.providers
    )
    missing = [name for name in provider_names if name not in registry]
    if missing:
        parser.error(f"Unavailable providers: {missing}")

    Base.metadata.create_all(bind=engine)
    jobs = asyncio.run(
        collect_jobs(
            [registry[name] for name in provider_names],
            [item.strip() for item in args.keywords.split(",") if item.strip()],
            args.location,
            args.limit,
        )
    )
    with SessionLocal() as session:
        results = apply_business_rules(build_business_rules_registry(), jobs)
        stored = store_raw_jobs(session, results)
        responses = [RawJobResponse.model_validate(job) for job in stored]
    json_path, xlsx_path = export_jobs(responses, settings.export_dir)
    print(f"Fetched: {len(jobs)}")
    print(f"JSON: {json_path}")
    print(f"XLSX: {xlsx_path}")


if __name__ == "__main__":
    main()
