# Job Aggregator Backend

Backend-only starter for collecting job listings by keywords from authorized
platform APIs or feeds, preserving the raw provider response, applying
versioned business rules, and exporting JSON and XLSX files.

## Scope

- Python 3.12 and FastAPI
- Keyword and location searches
- Pluggable provider adapters
- Unmodified raw provider payloads
- Central business-rules registry by provider and API version
- SQLite for local use
- PostgreSQL/Supabase-compatible `DATABASE_URL` for deployment
- JSON and XLSX exports
- CLI and HTTP API
- Separate candidate-matching backend service
- Docker-ready

The repository intentionally does not scrape Indeed, TopCV, or bypass anti-bot
controls. Add a platform connector only when you have an official API/feed or
written permission that allows collection and storage.

## Architecture

```text
CLI / REST API
      |
provider registry -> authorized provider adapters
      |
RawJobRecord (provider payload unchanged)
      |
business-rules registry -> provider/API-version rules
      |
raw_jobs storage
      |
JSON + XLSX exporter

Future rule implementations can additionally emit the standard `JobRecord`
schema and populate the `jobs` table without changing the connector contract.
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

## Raw data and business rules

Connectors only handle transport, authentication, source API parameters, and
extracting records from the provider response. The `payload` saved for each
record is the original JSON object returned by that provider.

Business rules are selected using:

```text
(provider, api_version)
```

The central registry is in `app/business_rules/registry.py`. Provider-specific
rule slots are separated by API version:

```text
app/business_rules/providers/
├── mock/v1.py
├── topcv/v1.py
└── vietnamworks/v1.py
```

These rules are currently pass-through. They record `rule_version=raw-v1` and
do not create or correct standardized job fields.

List configured rule versions:

```bash
curl http://localhost:8000/api/v1/business-rules
```

Inspect stored raw records:

```bash
curl http://localhost:8000/api/v1/raw-jobs
```

## Local setup

```bash
cp .env.example .env
make install
make test
make dev
```

API documentation is available at `http://localhost:8000/docs`.

Run a local mock search:

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H 'content-type: application/json' \
  -d '{
    "keywords": ["python", "backend"],
    "location": "Remote",
    "providers": ["mock"]
  }'
```

Or use the CLI:

```bash
.venv/bin/job-aggregator search \
  --keywords "python,backend" \
  --location "Remote"
```

Generated files are written to `data/exports/`.

## Candidate matching service

This repository now contains a second backend service for CV submission and job
matching. It runs as a separate API pod and a separate worker deployment.

Endpoints:

- `POST http://localhost:8100/api/v1/candidates` with multipart file upload
- `GET http://localhost:8100/api/v1/candidates`
- `GET http://localhost:8100/api/v1/candidates/{id}`
- `GET http://localhost:8100/api/v1/candidates/{id}/matches`
- `POST http://localhost:8100/api/v1/candidates/{id}/rematch`
- `GET http://localhost:8100/api/v1/tasks`

Local commands:

```bash
make candidate-dev
make candidate-worker
```

Example submission:

```bash
curl -X POST http://localhost:8100/api/v1/candidates \
  -F "file=@./sample-cv.txt" \
  -F "full_name=Alex Example" \
  -F "location=Remote"
```

The candidate service currently supports `txt`, `pdf`, and `docx` uploads. It
stores the original document, extracts text, derives a minimal candidate
profile, and ranks matches against projected fields from `raw_jobs`.

## Parallel pod scaling

The candidate API is stateless and can scale horizontally behind a Kubernetes
Service.

Worker pods can also scale horizontally, with one important constraint:

- PostgreSQL/Supabase is the intended production database.
- Worker task claiming uses `FOR UPDATE SKIP LOCKED` outside SQLite.
- That allows multiple worker pods to claim different pending tasks safely.
- SQLite remains suitable for local development only and does not provide the
  same concurrency guarantees.

Candidate processing is idempotent at the task boundary:

- tasks are persisted in `candidate_tasks`
- job matches are regenerated per candidate using `candidate-match-v1`
- match rows are deduplicated by `(candidate_id, job_key, rule_version)`

Reference manifests are included in:

- [candidate-api.yaml](/home/tlta17/job-aggregator-backend/k8s/candidate-api.yaml)
- [candidate-worker.yaml](/home/tlta17/job-aggregator-backend/k8s/candidate-worker.yaml)

## Supabase/PostgreSQL

Install the PostgreSQL driver:

```bash
.venv/bin/pip install -e ".[postgres]"
```

Set `DATABASE_URL` to the Supabase PostgreSQL connection string. Prefer the
transaction pooler URL for a containerized API, enable TLS as required by the
provider, and keep credentials in environment variables or a secret manager.

For production, replace automatic table creation with Alembic migrations.

## Adding a provider

1. Obtain authorized API/feed access and review its storage and redistribution terms.
2. Implement `JobProvider` in `app/connectors/`.
3. Return each untouched source object as `RawJobRecord.payload`.
4. Register the adapter in `app/connectors/registry.py`.
5. Add a provider/API-version rule class under `app/business_rules/providers/`.
6. Register that rule in `app/business_rules/registry.py`.
7. Add contract tests using saved, sanitized API fixtures.

`AuthorizedApiProvider` is only a template; its endpoint and field mapping must
be adapted to the actual provider documentation. It does not standardize fields.

## Suggested next milestones

1. Confirm which official provider integrations are available.
2. Define the canonical `JobRecord` schema and provider-specific mappings.
3. Add Alembic migrations and PostgreSQL integration tests.
4. Add scheduled searches, retry/backoff, and per-provider rate limits.
5. Add search-run/audit tables and structured logging.
6. Add authentication before exposing the API outside localhost.
