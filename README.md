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

- `docker/job-api.Dockerfile` -> `job-aggregator-api:latest`
- `docker/candidate-api.Dockerfile` -> `job-aggregator-candidate-api:latest`
- `docker/candidate-worker.Dockerfile` -> `job-aggregator-candidate-worker:latest`
- `docker/crawler-api.Dockerfile` -> `job-aggregator-crawler-api:latest`
- `docker/crawler-api-browser.Dockerfile` -> `job-aggregator-crawler-api-browser:latest`

Build commands:

```bash
make build-job-api
make build-candidate-api
make build-candidate-worker
make build-crawler-api
make build-crawler-api-browser
```

## Build agent

The local build agent lives in [scripts/build_agent.py](/home/andy/repositories/job-aggregator/scripts/build_agent.py).

What it watches and builds:

- target repository: `/home/andy/repositories/job-aggregator`
- remote branch watched by default: `origin/main`
- build source: a temporary detached git worktree from the watched commit
- versioning: patch-only semantic bump from `pyproject.toml`

Current default image set built by the agent:

- `job-aggregator-api`
- `job-aggregator-candidate-api`
- `job-aggregator-candidate-worker`

Run once:

```bash
make build-agent
```

Run continuously in the foreground:

```bash
python3 scripts/build_agent.py --mode daemon --poll-seconds 60
```

Run with custom repository or registry:

```bash
BUILD_AGENT_REGISTRY=ghcr.io/<org> BUILD_AGENT_PUSH=true python3 scripts/build_agent.py --mode once
```

```bash
python3 scripts/build_agent.py   --mode once   --repo-dir /home/andy/repositories/job-aggregator   --remote origin   --branch main
```

State file:

- default: `/home/andy/repositories/job-aggregator/.codex/build-agent/state.json`
- stores `last_built_sha` and `last_version`

Environment variables:

- `BUILD_AGENT_POLL_SECONDS`
- `BUILD_AGENT_REMOTE`
- `BUILD_AGENT_BRANCH`
- `BUILD_AGENT_REGISTRY`
- `BUILD_AGENT_PUSH`
- `BUILD_AGENT_STATE_FILE`

Systemd units:

- [deploy/systemd/job-aggregator-build-agent.service](/home/andy/repositories/job-aggregator/deploy/systemd/job-aggregator-build-agent.service)
- [deploy/systemd/job-aggregator-build-agent.timer](/home/andy/repositories/job-aggregator/deploy/systemd/job-aggregator-build-agent.timer)

Install them on this machine with paths unchanged only if the repo stays at `/home/andy/repositories/job-aggregator`.

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
