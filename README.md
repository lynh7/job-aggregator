# Job Aggregator Backend

Backend-only starter for collecting job listings, preserving the raw provider
response, applying versioned business rules, and exporting JSON/XLSX files.

## Scope

- Python 3.12 and FastAPI
- Separate core API and crawler API
- Toggleable crawler backend: lightweight `httpx + BeautifulSoup` or browser `crawl4ai`
- Pluggable provider adapters and business rules
- Unmodified raw provider payloads
- Central business-rules registry by provider and API version
- SQLite for local use
- PostgreSQL/Supabase-compatible `DATABASE_URL` for deployment
- JSON and XLSX exports
- Separate candidate-matching backend service
- Thin `ui-web` SPA for candidate and administrator workflows using `Vite + Preact + TypeScript + Shoelace`
- Lightweight NATS messaging app for future event-driven workflows
- `helm-chart/` for the recommended Kubernetes deployment topology
- Docker-ready

## Code Layout

- `app/`: job API-only code
- `shared/`: shared runtime modules used across services
- `crawler_service/`: crawler-only code
- `candidate_service/`: candidate API and worker code

All service images must include `shared/` in their build context because each
runtime imports config, database, models, schemas, or logging from
`shared.*`.

## Agent Code Map

This section is for follow-up agents. It describes the real ownership
boundaries, not just the top-level folders.

### Runtime entrypoints

- `app/main.py`: `job-api` FastAPI app
- `crawler_service/main.py`: `crawler-api` FastAPI app
- `candidate_service/main.py`: `candidate-api` FastAPI app
- `candidate_service/worker.py`: `candidate-worker` long-running worker loop
- `candidate_service/scheduler.py`: dedicated recurring crawl scheduler loop
- `ui-web/src/main.tsx`: browser SPA entrypoint

### Shared domain layer

- `shared/config.py`: canonical environment settings
- `shared/database.py`: canonical SQLAlchemy engine/session/base
- `shared/models.py`: canonical DB models for `jobs`, `raw_jobs`, candidate entities, tasks, matches, applications
- `shared/schemas.py`: shared Pydantic schemas used across services
- `shared/logging.py`: shared structured logging setup

Notes:

- `app/config.py`, `app/database.py`, and `app/models.py` are thin re-export wrappers over `shared.*`.
- Prefer treating `shared/*` as the source of truth when refactoring.

### Core job-api map

- `app/api/routes.py`: HTTP endpoints for health, list jobs/raw jobs, search, raw ingest, export download
- `app/services/collector.py`: fetch dedupe, apply rules, persist `raw_jobs` and `jobs`, trigger export
- `app/services/exporter.py`: JSON/XLSX export generation
- `app/connectors/`: provider adapters for API-style integrations
- `app/business_rules/`: provider/version normalization into the master-data schema

Main flow:

```text
provider records
  -> RawJobRecord
  -> business rules registry
  -> RuleResult(standard master-data projection)
  -> raw_jobs + jobs persistence
  -> optional JSON/XLSX export
```

### Business-rules extension points

- `app/business_rules/base.py`: base rule contract
- `app/business_rules/registry.py`: central provider/version registry
- `app/business_rules/normalization.py`: generic alias-based mapper into the master schema
- `app/business_rules/providers/<provider>/v1.py`: provider-specific mapping classes

If adding a new provider/version:

1. add or update provider adapter/crawler output so it emits `RawJobRecord`
2. add provider rule class under `app/business_rules/providers/...`
3. register it in `app/business_rules/registry.py`
4. add tests in `tests/test_business_rules.py` and/or `tests/test_master_data.py`

Current design note:

- Provider rule classes are still somewhat repetitive. Most variation is field-alias config.
- If expanding provider count, consider one generic alias-mapping rule class plus provider-specific config data.

### Candidate service map

- `candidate_service/routes.py`: candidate API endpoints
- `candidate_service/service.py`: submission, parsing, matching, rematch, application orchestration
- `candidate_service/parsing.py`: CV text extraction and profile parsing
- `candidate_service/matching.py`: scoring logic
- `candidate_service/job_projection.py`: convert master `Job` rows into candidate matching projection
- `candidate_service/task_queue.py`: DB-backed task queue primitives
- `candidate_service/worker.py`: polling worker that executes queued tasks
- `candidate_service/scheduler.py`: dedicated process that enqueues due recurring crawl tasks
- `candidate_service/crawler_client.py`: talks to `crawler-api`

Main flow:

```text
candidate upload
  -> candidate + candidate_document
  -> candidate_task(parse_and_match)
  -> worker
  -> parsed candidate_profile
  -> job_matches
  -> optional apply_to_job tasks
```

Current design note:

- Recurring candidate crawl scheduling is now split into `candidate_service/scheduler.py` instead of living in the worker loop.
- This removes scheduler side effects from normal task workers.
- For clustered deployment, still prefer a single scheduler replica or a distributed lock/cron design.

### Crawler service map

- `crawler_service/routes.py`: crawl API endpoints
- `crawler_service/service.py`: orchestrates crawl and pushes records to core ingest API
- `crawler_service/crawlers/base.py`: crawler abstraction and backend switching
- `crawler_service/crawlers/common.py`: HTML parsing helpers
- `crawler_service/crawlers/registry.py`: provider registry
- `crawler_service/crawlers/topcv.py`, `itviec.py`, `mock.py`: provider implementations

Backends:

- `CRAWL_BACKEND=http`: lightweight `httpx + BeautifulSoup`
- `CRAWL_BACKEND=crawl4ai`: browser-backed mode

### UI map

- `ui-web/src/app.tsx`: route table
- `ui-web/src/components/`: shell and presentational primitives
- `ui-web/src/pages/`: candidate/admin screens
- `ui-web/src/lib/http.ts`: tiny client-side fetch helper
- `ui-web/src/lib/config.ts`: runtime config loader from `/config.js`
- `ui-web/src/lib/types.ts`: UI-side API response types

Current design note:

- Several UI TSX files currently use `// @ts-nocheck` as a POC workaround for Shoelace + Preact typing friction.
- If the UI becomes long-lived, restore real type-safety instead of extending this pattern.

### Tests

- `tests/test_business_rules.py`: provider master-data mapping checks
- `tests/test_master_data.py`: master schema persistence expectations
- `tests/test_ingest_api.py`: ingest API behavior
- `tests/test_candidate_service.py`: candidate submission, matching, application flow
- `tests/test_exporter.py`: JSON/XLSX export behavior
- `tests/test_mock_provider.py`: mock adapter behavior

### Known refactor hotspots

- `app/services/collector.py`: duplicated dialect-specific upsert logic; good candidate for repository/helper extraction
- `candidate_service/service.py`: multiple commits inside one logical workflow; improve transaction boundaries
- `candidate_service/worker.py`: scheduler and worker concerns are mixed
- `app/config.py`, `app/database.py`, `app/models.py`: wrapper modules; simplify package boundaries later

### Safe change strategy

- For schema or model changes, inspect `shared/models.py`, `shared/schemas.py`, Helm values, and affected API tests together.
- For provider changes, touch crawler/connector output and business rules together.
- For deployment changes, inspect `.github/workflows/`, `cloudbuild.remote.yaml`, `helm-chart/`, and current image-tag automation together.

## Architecture

```text
Crawler API (crawl4ai)
      |
      v
Core Job API ingest endpoint
      |
raw_jobs storage
      |
business-rules registry -> provider/API-version rules
      |
jobs master-data projection
      |
JSON + XLSX exporter
```

Candidate service:

```text
Candidate API
      |
candidate_documents + candidate_tasks
      |
candidate-worker pods
      |
CV text extraction -> candidate_profiles -> job_matches
```

## Core API

The core API owns:

- `raw_jobs`
- `jobs`
- business-rule application
- JSON/XLSX export generation
- candidate matching data

Protected ingest endpoint:

```bash
POST /api/v1/ingest/raw-jobs
X-Ingest-Token: <token>
```

Search endpoint still exists for API-based providers, but the crawler path is now:

```text
crawler-api /api/v1/crawl -> core-api /api/v1/ingest/raw-jobs
```

## Crawler API

The crawler service is a separate deployment.
It can run in two modes:

- lightweight `httpx + BeautifulSoup`
- browser `crawl4ai + Playwright/Chromium`

Both modes send raw provider records to the core API.

Current crawler-backed providers:

- `topcv`
- `itviec`
- `mock`

Local setup:

```bash
cp .env.example .env
make install
make crawler-dev
```

Default local install uses the lightweight backend.
Set `CRAWL_BACKEND=crawl4ai` only when the browser image/runtime is available.

Example crawl:

```bash
curl -X POST http://localhost:8200/api/v1/crawl   -H 'content-type: application/json'   -d '{
    "keywords": ["data engineer", "backend"],
    "providers": ["topcv", "itviec"],
    "limit_per_provider": 10,
    "export": true
  }'
```

Crawler backend options:

- `CRAWL_BACKEND=http`
  - uses `httpx + BeautifulSoup`
  - lighter image and lower memory usage
  - works only when listing/detail pages contain enough server-rendered HTML
- `CRAWL_BACKEND=crawl4ai`
  - uses browser automation through `crawl4ai`
  - heavier image, higher CPU/memory
  - better when pages are JS-rendered or anti-bot behavior blocks plain HTTP fetches

Docker images:

- `docker/crawler-api.Dockerfile` -> lightweight image
- `docker/crawler-api-browser.Dockerfile` -> browser image

## Candidate matching service

This repository contains a second backend service for CV submission and job matching.
It runs as a separate API pod and a separate worker deployment.

Endpoints:

- `POST http://localhost:8100/api/v1/candidates` with multipart file upload
- `POST http://localhost:8100/api/v1/candidates/{id}/job-searches`
- `GET http://localhost:8100/api/v1/candidates`
- `GET http://localhost:8100/api/v1/candidates/{id}`
- `GET http://localhost:8100/api/v1/candidates/{id}/matches`
- `POST http://localhost:8100/api/v1/candidates/{id}/rematch`
- `GET http://localhost:8100/api/v1/tasks`

Candidate job-search automation:

- Candidates can store a keyword list for recurring crawl automation.
- The worker scheduler is enabled by default with `CANDIDATE_CRAWL_SCHEDULER_ENABLED=true`.
- The worker enqueues a crawl task every `CANDIDATE_CRAWL_INTERVAL_HOURS` and defaults to 6 hours.
- Set `CANDIDATE_CRAWL_SCHEDULER_ENABLED=false` to turn the recurring scheduler off entirely.
- Change `CANDIDATE_CRAWL_INTERVAL_HOURS` to retime the default schedule without code changes.
- Successful crawl tasks trigger a rematch so fresh jobs appear in candidate matches.
- Duplicate raw records are filtered before ingest, and database uniqueness on `raw_jobs` and `jobs` still prevents repeated rows.

Candidate submission now also accepts optional `job_keywords` as a comma-separated multipart field if you want to create the first recurring search at upload time.

Logging:

- Shared structured logging is configured across `job-api`, `crawler-api`, `candidate-api`, and `candidate-worker`.
- Request logs include request ID, method, path, status code, and duration.
- Background logs include candidate IDs, task IDs, providers, fetched counts, stored counts, and duplicate-filter counts at the appropriate `INFO`/`WARNING` levels.

## Docker images

Primary image CI/CD path:

- GitHub Actions triggers on `push` to `main` for selected repo paths.
- The checked-in `workflow_dispatch` block in `.github/workflows/build-via-cloud-build.yml` is currently disabled.
- The workflow runs on a private self-hosted runner.
- The Raspberry Pi runner authenticates to Google Cloud and runs `gcloud builds submit`.
- Docker builds happen in Google Cloud Build, not on the Raspberry Pi.
- Cloud Build logs in to GHCR with the `ghcr-token` secret from Google Secret Manager.
- The workflow builds only the images selected by changed-path detection:
  - `app/**` -> `job-api`
  - `shared/**` -> all images
  - `candidate_service/**` -> `candidate-api`, `candidate-worker`
  - `crawler_service/**` -> `crawler-api`, `crawler-api-browser`
- Edits to workflow YAML files do not force image rebuilds by themselves. Use the validation workflow path when testing CI logic changes.

Files:

- workflow: `.github/workflows/build-via-cloud-build.yml`
- validation workflow: `.github/workflows/validation-cases.yml`
- manual chart republish fallback: `.github/workflows/republish-helm-chart.yml`
- build config: `cloudbuild.remote.yaml`
- GCP bootstrap Terraform: `deploy/terraform/gcp-cloud-build-runner/`
- Pi runner compose service: `/home/andy/repositories/home-docker-compose/services/github-actions-runner.yml`

GitHub configuration required:

- secret: `GCP_SERVICE_ACCOUNT_KEY`
- variable: `GCP_PROJECT_ID`

GCP bootstrap creates:

- runner service account for the Raspberry Pi workflow runner
- `roles/cloudbuild.builds.editor` and `roles/serviceusage.serviceUsageConsumer` on that runner service account
- Secret Manager secret `ghcr-token`
- Secret Manager access for the Cloud Build execution service account
- populate the GHCR PAT after `terraform apply` with `gcloud secrets versions add ghcr-token --data-file=-`

Security constraints implemented:

- no `pull_request` trigger
- no public inbound port on the Raspberry Pi runner
- no Docker image build on the Raspberry Pi runner
- Image builds update only the service tags that were rebuilt, and the Helm chart release packages those committed defaults without rewriting them
- Workflow-file edits do not automatically burn Cloud Build minutes by rebuilding every image

Legacy local build agent:

- `scripts/build_agent.py` and `deploy/systemd/job-aggregator-build-agent.service` remain in the repo as older local-build tooling.
- Do not use that path for this Raspberry Pi architecture.

## Helm chart

`helm-chart/` now packages the recommended application topology in one chart:

- `job-api` enabled by default at 2 replicas
- `crawler-api` enabled by default with the `lightweight` image variant
- `candidate-api` enabled by default at 1 replica
- `candidate-worker` enabled by default at 1 replica
- `candidate-scheduler` enabled by default at 1 replica and reuses the `candidate-worker` image with a command override
- `nats` disabled by default because `QUEUE_BACKEND=database` is still the live path
- recurring candidate crawl scheduling is now a separate deployment, not a side effect inside worker pods
- shared `/app/data` persistence made explicit through `sharedData`
- default image tags are pinned per service in `helm-chart/values.yaml`

Render the default chart and the shipped override examples:

```bash
helm template job-aggregator ./helm-chart
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/browser-crawler.values.yaml
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/existing-shared-pvc.values.yaml
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/existing-secret.values.yaml
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/nats.values.yaml
```

Set `crawlerApi.imageVariant=browser` to switch the single `crawler-api` deployment from `ghcr.io/lynh7/job-aggregator-crawler-api` to `ghcr.io/lynh7/job-aggregator-crawler-api-browser`. The default is `lightweight`. When the `browser` variant is selected, the chart also sets `CRAWL_BACKEND=crawl4ai`.

Image versioning behavior:

- `helm-chart/values.yaml` is the source of truth for the chart's default image tags.
- Each service has its own explicit image tag; there is no shared global image tag fallback.
- The build workflow bumps only the tags for services it actually rebuilt and commits those updated defaults back to `main`.
- The chart version is bumped independently, so the chart can move from `0.1.5` to `0.1.6` while service image tags diverge, for example `job-api: 0.1.5` and `crawler-api: 0.1.9`.

Database wiring behavior:

- By default, the chart injects `DATABASE_URL=sqlite:////app/data/jobs.db` for `job-api`, `candidate-api`, and `candidate-worker`.
- The default SQLite path uses the shared volume mount at `/app/data`.
- `crawler-api` does not get `DATABASE_URL` because it pushes raw records to `job-api` and does not persist directly.
- If you want PostgreSQL or Supabase, enable `database.connection.enabled=true` and set `database.connection.secretName` to a Secret containing the connection string at the configured key.
- `helm-chart/examples/existing-secret.values.yaml` shows the intended secret-backed database configuration.

If your cluster injects runtime configuration from an existing Secret, set `global.envFrom` or use `helm-chart/examples/existing-secret.values.yaml`. The chart no longer assumes a `job-aggregator-env` Secret exists by default.

Chart releases are published directly from `.github/workflows/build-via-cloud-build.yml` after successful image builds, chart-state sync, and reusable validation checks. The workflow packages the chart exactly as committed, including the per-service image tags already written to `helm-chart/values.yaml`, then pushes the chart package to GHCR as an OCI artifact.

`.github/workflows/republish-helm-chart.yml` remains available as a manual fallback if you need to republish the current chart state without rebuilding images.

- `helm-chart/Chart.yaml` `version`
- `helm-chart/Chart.yaml` `appVersion`
- `helm-chart/values.yaml` per-service `image.tag` defaults

Recommended GitOps split:

- this repo owns chart structure, defaults, and release automation
- your GitOps repo owns environment-specific overrides such as secrets, ingress, storage class, replica tuning, and immutable image pinning when you want SHA-based rollouts

## Roadmap

- Add a dedicated UI service for both candidates and administrators.
- Keep the frontend as UI-only: no business logic, no authz source of truth, client-side rendering only.
- UI stack: `Vite + Preact + TypeScript + Shoelace`.
- Authentication service/pod: `Authentik` or `Keycloak` via OIDC.
- Authorization service/pod: `OPA` for centralized policy decisions enforced by backend APIs.
