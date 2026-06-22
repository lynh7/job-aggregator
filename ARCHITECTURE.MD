# Architecture

This repository contains two application domains:

- `app/`: job ingestion API, provider connectors, raw payload storage, and business-rule projection
- `candidate_service/`: CV intake API, parsing, matching, and background worker execution

The live queue path for candidate work is database-backed with `QUEUE_BACKEND=database`.
NATS is deployed for future event-driven workflows, but it is not the primary task transport today.

## Runtime Diagram

```text
Clients
  Operators / CLI --------------------------> Job API
  Frontend or API consumers ----------------> Candidate API
  Authorized job providers <---------------> Job API

Services
  Job API (FastAPI, app/)
    -> fetches raw provider records
    -> stores untouched payloads in raw_jobs
    -> applies business rules
    -> writes normalized projections to jobs
    -> writes export files to /app/data

  Candidate API (FastAPI, candidate_service/)
    -> creates candidates
    -> stores candidate document metadata
    -> saves uploaded CV files to /app/data
    -> enqueues parse, rematch, and apply tasks in candidate_tasks

  Candidate Worker (candidate_service/worker.py)
    -> claims pending tasks from candidate_tasks
    -> reads CV files from /app/data
    -> parses CVs into candidate_profiles
    -> reads projected jobs
    -> writes job_matches
    -> persists job_applications

  NATS + JetStream
    -> present for future event-driven workflows
    -> not the active transport for candidate tasks today

Persistence
  Shared database (PostgreSQL in production, SQLite for local development)
    -> raw_jobs
    -> jobs
    -> candidates
    -> candidate_documents
    -> candidate_profiles
    -> candidate_tasks
    -> job_matches
    -> job_applications

  Shared /app/data volume
    -> exports
    -> uploaded candidate documents
```

## Main Flows

### 1. Job ingestion

```text
CLI / REST client
  -> sends search request to Job API

Job API
  -> calls authorized provider APIs
  -> receives raw provider payloads
  -> stores raw_jobs.payload unchanged
  -> applies business rules using (provider, api_version)
  -> optionally writes normalized job projections to jobs
  -> writes JSON/XLSX exports to /app/data
  -> returns search results and export references to the client
```

### 2. Candidate submission and matching

```text
Candidate user / client
  -> uploads CV and metadata to Candidate API

Candidate API
  -> saves the original file under /app/data
  -> inserts candidates and candidate_documents
  -> inserts candidate_tasks
  -> returns an accepted response with a task id

Candidate Worker
  -> claims a pending task from candidate_tasks
  -> reads the CV file from /app/data
  -> extracts text and stores candidate_profiles
  -> reads projected jobs from jobs
  -> writes ranked results to job_matches
  -> marks the task as completed
```

## Deployment Shape

- Kubernetes manifests split the workloads into separate deployments under `k8s/`
- All services share the same `DATABASE_URL`
- `candidate-api` and `candidate-worker` also share `/app/data` for uploaded documents
- In production, PostgreSQL is the intended backend; SQLite is mainly for local development

## Current Constraints

- Tables are created at startup with SQLAlchemy `create_all`, not migrations
- Candidate task coordination is safe for multi-worker production when using PostgreSQL because the worker claim path uses `FOR UPDATE SKIP LOCKED`
- NATS exists in the repo, but the active candidate workflow still runs through `candidate_tasks` in the database
