---
name: job-aggregator-maintainer
description: Use this skill when working inside the job-aggregator repository on the job ingestion API, candidate matching service, Docker images, Kubernetes manifests, queue-backed workers, or provider/business-rule integration boundaries.
---

# Job Aggregator Maintainer

## Overview

Use this skill for changes in this repository that affect service boundaries,
runtime topology, data flow, or developer operations. It is specific to the
current repo layout and should be used when modifying APIs, workers, Docker
builds, Kubernetes manifests, Helm base templates, queue topology, matching
logic, or provider integration rules.

## Repository map

- `app/`: job ingestion API, provider connectors, raw job persistence, business rules.
- `candidate_service/`: CV submission API, parsing, matching, task queue worker.
- `tests/`: unit tests for provider flow, export flow, business rules, candidate service.
- `docker/`: service-specific Dockerfiles.
- `k8s/`: per-service Kubernetes manifests.
- `Helm.Base/`: reusable Helm chart and example value overrides.
- `data/`: local SQLite database and export/output directories for development only.
- `.codex/skills/job-aggregator-maintainer/references/cluster-deployment.md`: read when work touches Docker, Helm, Kubernetes, GitOps handoff, runtime topology, or production-readiness decisions.

## Working rules

- Keep `raw_jobs.payload` unchanged. Do not normalize provider JSON in connectors.
- Provider-specific interpretation belongs in `app/business_rules/`.
- Candidate matching reads projected fields from `raw_jobs`; if matching quality must improve, add standardization or improve projection logic deliberately.
- The candidate API should remain stateless. Background work belongs in `candidate_service/worker.py`.
- A standalone NATS app is present for future event-driven workflows, but the live candidate task flow still defaults to `QUEUE_BACKEND=database`.
- For production concurrency assumptions, target PostgreSQL/Supabase, not SQLite.
- All runtime images must support PostgreSQL deployments, not only local SQLite.
- When changing service startup or deployment behavior, update both `compose.yaml` and the relevant files in `k8s/`.
- When changing image layout, update the Dockerfiles in `docker/`, the Makefile build targets, and README build instructions together.
- When changing deployment templates, keep `Helm.Base/templates/` generic and push service-specific differences into values files.
- Prefer `job-aggregator` as the source of truth for app packaging and Helm defaults, and use the separate GitOps repo only for environment-specific deployment values and rollout objects.

## Common tasks

### Run local checks

```bash
make test
.venv/bin/ruff check .
python3 -m compileall -q app candidate_service tests
```

### Run services locally

```bash
make dev
make candidate-dev
make candidate-worker
```

### Build container images

```bash
make build-job-api
make build-candidate-api
make build-candidate-worker
```

### Render Helm manifests

```bash
helm template job-api ./Helm.Base -f ./Helm.Base/examples/job-api.values.yaml
helm template candidate-api ./Helm.Base -f ./Helm.Base/examples/candidate-api.values.yaml
helm template candidate-worker ./Helm.Base -f ./Helm.Base/examples/candidate-worker.values.yaml
helm template nats ./Helm.Base -f ./Helm.Base/examples/nats.values.yaml
```

## Change guidance

### Provider ingestion changes

- Start in `app/connectors/`, `app/business_rules/`, and `app/api/routes.py`.
- Preserve the connector contract: transport/authentication only, raw payload out.
- If a new provider or API version is added, register it explicitly in the business-rules registry.

### Candidate workflow changes

- Start in `candidate_service/routes.py`, `candidate_service/service.py`, `candidate_service/task_queue.py`, and `candidate_service/worker.py`.
- Keep heavy work off the request path.
- Preserve idempotency around `candidate_tasks` and `job_matches`.

### Deployment changes

- Read `references/cluster-deployment.md` before changing Dockerfiles, Helm packaging, `k8s/`, persistence, scaling, database wiring, or GitOps handoff.
- Main job API image: `docker/job-api.Dockerfile`
- Candidate API image: `docker/candidate-api.Dockerfile`
- Candidate worker image: `docker/candidate-worker.Dockerfile`
- Queue app: NATS with JetStream in compose and `k8s/nats.yaml`
- Kubernetes manifests should reference service-specific image names, not one shared tag.
- Current live worker flow is still database-backed, so do not make NATS mandatory unless you are actively migrating queue logic.
- Candidate uploads and exports currently depend on filesystem paths under `/app/data`; treat replica count and PVC mode as part of the runtime contract until storage is redesigned.

## Validation expectations

- Run tests for any touched workflow.
- If queue logic changes, verify task claiming and retry behavior.
- If Docker or K8s files change, verify build commands and image references remain aligned.
- If file paths in docs are changed, keep clickable repo-local paths accurate.
