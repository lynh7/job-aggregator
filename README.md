# Job Aggregator Backend

Backend-only starter for collecting job listings, preserving the raw provider
response, applying versioned business rules, and exporting JSON/XLSX files.

## Scope

- Python 3.12 and FastAPI
- Separate core API and crawler API
- Crawl4AI-backed browser crawling for TopCV and ITViec
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

The crawler service is a separate deployment and image.
It uses `crawl4ai` with Playwright/Chromium, then sends raw provider records to the core API.

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

Example crawl:

```bash
curl -X POST http://localhost:8200/api/v1/crawl   -H 'content-type: application/json'   -d '{
    "keywords": ["data engineer", "backend"],
    "providers": ["topcv", "itviec"],
    "limit_per_provider": 10,
    "export": true
  }'
```

Important runtime note:

- `crawl4ai` requires Playwright browser binaries
- the crawler Docker image installs Chromium during build
- local dev install now uses `.[dev,crawler]`

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

- `docker/job-api.Dockerfile` -> `job-aggregator-api:latest`
- `docker/candidate-api.Dockerfile` -> `job-aggregator-candidate-api:latest`
- `docker/candidate-worker.Dockerfile` -> `job-aggregator-candidate-worker:latest`
- `docker/crawler-api.Dockerfile` -> `job-aggregator-crawler-api:latest`

Build commands:

```bash
make build-job-api
make build-candidate-api
make build-candidate-worker
make build-crawler-api
```

## Helm examples

Render each workload from the shared chart:

```bash
helm template job-api ./Helm.Base -f ./Helm.Base/examples/job-api.values.yaml
helm template crawler-api ./Helm.Base -f ./Helm.Base/examples/crawler-api.values.yaml
helm template candidate-api ./Helm.Base -f ./Helm.Base/examples/candidate-api.values.yaml
helm template candidate-worker ./Helm.Base -f ./Helm.Base/examples/candidate-worker.values.yaml
```

Recommended GitOps split:

- this repo owns chart structure and example workload values
- `home-server/applications` owns environment-specific overrides such as image tags, secrets, replicas, ingress, and storage class
