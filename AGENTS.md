# Job Aggregator Agents

Use the repo-local skill at `.codex/skills/job-aggregator-maintainer/` when
working in this repository.

Operational rules:

- Keep `app/` focused on job ingestion, raw provider payload storage, and provider/business-rule boundaries.
- Keep `candidate_service/` focused on CV intake, parsing, matching, and worker execution.
- Preserve `raw_jobs.payload` unchanged in connectors; provider interpretation belongs in `app/business_rules/`.
- Treat `QUEUE_BACKEND=database` as the active production code path unless you are explicitly migrating logic onto NATS.
- When changing runtime topology, keep `docker/`, `compose.yaml`, `k8s/`, and `Helm.Base/` aligned.
- Keep `Helm.Base/templates/` generic and move service-specific differences into values files.

Validation defaults:

- `pytest`
- `ruff check .`
- `helm template` for any touched Helm values/templates
