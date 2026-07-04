---
name: job-aggregator-maintainer
description: Use this skill when working inside the job-aggregator repository on the core job API, crawler API, candidate matching service, Docker images, Kubernetes manifests, queue-backed workers, or provider/business-rule integration boundaries.
---

# Job Aggregator Maintainer

Use this skill for repo-specific work that changes service boundaries, data flow,
deployment packaging, or operational behavior.

## Repo map

- `app/`: core job API, ingest endpoint, raw job persistence, master-data projection, business rules.
- `crawler_service/`: crawl4ai-backed crawler API for TopCV, ITViec, and future site adapters.
- `candidate_service/`: CV intake API, parsing, matching, task queue worker.
- `docker/`: service-specific Dockerfiles.
- `helm-chart/`: Helm chart packaging the recommended application topology.
- `tests/`: API, business-rule, export, and candidate workflow tests.
- `references/cluster-deployment.md`: read when work touches Docker, Helm, Kubernetes, storage, scaling, GitOps handoff, or CI/CD build flow.

## Runtime rules

- Keep `raw_jobs.payload` unchanged. Provider interpretation belongs in `app/business_rules/`.
- The crawler is a separate service. It should crawl source pages and send raw records to `POST /api/v1/ingest/raw-jobs` on the core API.
- The crawler backend is deployment-selectable: lightweight `http` or browser `crawl4ai`.
- Keep the core API authoritative for normalization, master-data persistence, and JSON/XLSX export generation.
- Provider-specific crawling belongs in `crawler_service/crawlers/`.
- Provider-specific normalization belongs in `app/business_rules/providers/`.
- The candidate API should remain stateless. Heavy work belongs in `candidate_service/worker.py`.
- The live candidate queue path still defaults to `QUEUE_BACKEND=database`.
- Target PostgreSQL-compatible production behavior, not SQLite assumptions.
- When topology or build flow changes, update Dockerfiles, `helm-chart/`, CI workflows, README, and this skill together.
- The preferred image build path is GitHub Actions on a private self-hosted Raspberry Pi runner submitting to Google Cloud Build.
- Push service images separately:
  - `ghcr.io/lynh7/job-aggregator-job-api`
  - `ghcr.io/lynh7/job-aggregator-candidate-api`
  - `ghcr.io/lynh7/job-aggregator-candidate-worker`
  - `ghcr.io/lynh7/job-aggregator-crawler-api`
  - `ghcr.io/lynh7/job-aggregator-crawler-api-browser`
- GHCR package visibility is managed separately from repo visibility. A public GitHub repo can still publish private GHCR packages unless each package is explicitly made public or pulled with auth.
- Image versions are tracked per service in `helm-chart/values.yaml`.
- CI only bumps the patch digit for services that were actually rebuilt and commits those new default image tags back to `main`.
- Chart versioning is independent from service image versions; the Helm chart patch can advance even when only one service image tag changes.
- Use immutable Git SHA image tags in Kubernetes-facing examples and environment values; `latest` is convenience only.

## Common tasks

### Local checks

```bash
make test
.venv/bin/ruff check .
python3 -m compileall -q app crawler_service candidate_service tests
```

### Run services locally

```bash
make dev
make crawler-dev
make candidate-dev
make candidate-worker
```

### Build images

```bash
make build-job-api
make build-candidate-api
make build-candidate-worker
make build-crawler-api
make build-crawler-api-browser
```

### CI/CD files

```bash
sed -n '1,260p' .github/workflows/build-via-cloud-build.yml
sed -n '1,260p' .github/workflows/release-helm-chart.yml
sed -n '1,220p' cloudbuild.remote.yaml
find deploy/terraform/gcp-cloud-build-runner -maxdepth 2 -type f
```

### Render Helm workloads

```bash
helm template job-aggregator ./helm-chart
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/browser-crawler.values.yaml
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/existing-shared-pvc.values.yaml
helm template job-aggregator ./helm-chart -f ./helm-chart/examples/nats.values.yaml
```

## Change guidance

### Crawler changes

- Start in `crawler_service/crawlers/`, `crawler_service/service.py`, and crawler env settings.
- Keep site selectors and fetch timing inside crawler adapters.
- Preserve provider names and API versions expected by `app/business_rules/registry.py`.
- If a new source is added, add both:
  - crawler adapter
  - matching business-rule registration

### Core ingestion changes

- Start in `app/api/routes.py`, `app/services/collector.py`, `app/models.py`, and `app/business_rules/`.
- Preserve the ingest contract: raw source records in, raw payload unchanged, master-data projection out.
- Keep export generation inside the core API.

### Candidate workflow changes

- Start in `candidate_service/routes.py`, `candidate_service/service.py`, `candidate_service/task_queue.py`, and `candidate_service/worker.py`.
- Keep heavy work off the request path.
- Preserve idempotency around `candidate_tasks`, `job_matches`, and `job_applications`.

### Deployment changes

- Read `references/cluster-deployment.md` first.
- Main images:
  - `docker/job-api.Dockerfile`
  - `docker/crawler-api.Dockerfile`
  - `docker/crawler-api-browser.Dockerfile`
  - `docker/candidate-api.Dockerfile`
  - `docker/candidate-worker.Dockerfile`
- Keep service-specific image names, immutable tags, and ports aligned across Cloud Build and Helm values.
- Keep Helm release automation aligned with the image build workflow. The build workflow commits updated per-service image tags and the next chart patch version into `helm-chart/`, and the chart release packages that committed chart state on `push` to `main`.
- Treat `/app/data` storage, PostgreSQL wiring, and ingest token wiring as deployment contract.

## Validation expectations

- Run tests for touched workflows.
- If crawler logic changes, verify at least one real provider selector path or document why runtime verification was not possible.
- If Docker or K8s files change, verify build commands and image references stay aligned.
- If skill instructions change, keep `agents/openai.yaml` consistent with the skill scope.
