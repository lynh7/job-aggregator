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
- Lightweight NATS messaging app for future event-driven workflows
- Reusable `Helm.Base/` chart for service deployments
- Docker-ready

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
- `GET http://localhost:8100/api/v1/candidates`
- `GET http://localhost:8100/api/v1/candidates/{id}`
- `GET http://localhost:8100/api/v1/candidates/{id}/matches`
- `POST http://localhost:8100/api/v1/candidates/{id}/rematch`
- `GET http://localhost:8100/api/v1/tasks`

## Docker images

Primary CI/CD path:

- GitHub Actions triggers on `push` to `main` and `workflow_dispatch` only.
- The workflow runs on a private self-hosted runner labeled `self-hosted,raspberry-pi`.
- The Raspberry Pi runner authenticates to Google Cloud and runs `gcloud builds submit`.
- Docker builds happen in Google Cloud Build, not on the Raspberry Pi.
- Cloud Build logs in to GHCR with the `ghcr-token` secret from Google Secret Manager.
- The default build target in this repo is `docker/job-api.Dockerfile` -> `ghcr.io/trthienan17/my-app:${GITHUB_SHA}` and `ghcr.io/trthienan17/my-app:latest`.

Files:

- workflow: `.github/workflows/build-via-cloud-build.yml`
- build config: `cloudbuild.yaml`
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
- Kubernetes and Helm examples use immutable `replace-with-git-sha` tags instead of `latest`

Legacy local build agent:

- `scripts/build_agent.py` and `deploy/systemd/job-aggregator-build-agent.service` remain in the repo as older local-build tooling.
- Do not use that path for this Raspberry Pi architecture.

## Helm examples

Render each workload from the shared chart:

```bash
helm template job-api ./Helm.Base -f ./Helm.Base/examples/job-api.values.yaml
helm template crawler-api ./Helm.Base -f ./Helm.Base/examples/crawler-api.values.yaml
helm template crawler-api ./Helm.Base -f ./Helm.Base/examples/crawler-api-browser.values.yaml
helm template candidate-api ./Helm.Base -f ./Helm.Base/examples/candidate-api.values.yaml
helm template candidate-worker ./Helm.Base -f ./Helm.Base/examples/candidate-worker.values.yaml
```

Recommended GitOps split:

- this repo owns chart structure and example workload values
- `home-server/applications` owns environment-specific overrides such as image tags, secrets, replicas, ingress, and storage class

