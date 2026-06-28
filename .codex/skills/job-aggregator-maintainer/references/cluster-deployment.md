# Cluster deployment reference

Read this file when work touches:

- Docker image packaging
- Helm chart shape or values
- Kubernetes manifests
- replica counts, probes, resources, or persistence
- database choice, queue backend, crawler topology, or runtime topology
- handoff between this repo and a separate GitOps repo

## Current runtime facts

- The core job API owns normalization, master-data persistence, and JSON/XLSX export generation.
- The crawler is now a separate service. It crawls provider pages and posts raw records to `/api/v1/ingest/raw-jobs` on the core API.
- The ingest path can be protected by `INGEST_API_TOKEN`. The crawler and core API must share the same token.
- The active production candidate queue path is still database-backed with `QUEUE_BACKEND=database`.
- NATS exists for future event-driven work, but current candidate processing does not require it.
- Production concurrency assumes PostgreSQL-compatible locking. The worker uses `FOR UPDATE SKIP LOCKED` when the dialect is not SQLite.
- Candidate uploads are written to local disk under `CANDIDATE_STORAGE_DIR`.
- Job exports are written to local disk under `EXPORT_DIR`.
- All app entrypoints still use startup `create_all(...)`; this is convenient for development and weak for production migrations.

## Deployment ownership split

Recommended split:

- `job-aggregator` repo owns app code, Dockerfiles, Cloud Build config, GitHub workflow logic, Helm chart structure, chart defaults, ports, probes, env variable names, and service topology.
- GitOps repo owns environment-specific values: immutable image tags, replica counts, ingress hosts, secret references, storage class, resource sizing, and rollout objects.

Use `helm-chart/` or the GitOps repo as the deployment source of truth.

## Current CI/CD path

- GitHub Actions triggers on `push` to `main` when image-producing paths change and on `workflow_dispatch`.
- `workflow_dispatch` builds every service image.
- Repo release version source of truth is git tags starting at `v0.1.0`. CI bumps only the patch digit and computes one new version per workflow run.
- `push` builds only the affected images:
  - `app/**` or `docker/job-api.Dockerfile` -> `job-api`
  - `candidate_service/**`, `docker/candidate-api.Dockerfile`, or `docker/candidate-worker.Dockerfile` -> `candidate-api` and `candidate-worker`
  - `crawler_service/**`, `docker/crawler-api.Dockerfile`, or `docker/crawler-api-browser.Dockerfile` -> `crawler-api` and `crawler-api-browser`
  - shared packaging files such as `pyproject.toml`, `.dockerignore`, `cloudbuild.remote.yaml`, or the workflow itself -> build all images
- Workflow runner target: private self-hosted runner with label `self-hosted`.
- The Raspberry Pi runner must not build Docker images locally. It only authenticates to GCP and runs `gcloud builds submit`.
- Google Cloud Build performs the Docker build and pushes GHCR tags.
- `cloudbuild.remote.yaml` logs in to GHCR using Secret Manager secret `ghcr-token`.
- After all selected image builds pass, the workflow creates and pushes the new repo git tag.
- Published GHCR repositories:
  - `ghcr.io/lynh7/job-aggregator-job-api`
  - `ghcr.io/lynh7/job-aggregator-candidate-api`
  - `ghcr.io/lynh7/job-aggregator-candidate-worker`
  - `ghcr.io/lynh7/job-aggregator-crawler-api`
  - `ghcr.io/lynh7/job-aggregator-crawler-api-browser`
- GHCR package visibility is separate from GitHub repository visibility. Public repo status does not automatically make these package pulls anonymous.
- Image tags pushed per selected image: `<semver>`, `<full git sha>`, `<short sha>`, and `latest`.
- Selective-build mode means some later semver tags may exist only for the images changed in that release.
- Kubernetes-facing values should pin immutable Git SHA tags, not rely on `latest`.
- Helm chart publication is triggered by the `Release Helm Chart` workflow via `workflow_run` after the image build workflow succeeds, not by the tag push event directly.

## Recommended crawler topology

Default first cluster shape:

- `job-api`: 2 replicas
- `crawler-api`: 1 replica
- `candidate-api`: 1 replica
- `candidate-worker`: 1 replica
- `nats`: disabled unless queue migration is active
- PostgreSQL: required for real multi-worker scaling

Reasoning:

- `job-api` is mostly stateless and can scale horizontally.
- `crawler-api` is compute/browser heavy and should start at 1 replica until selector stability and resource usage are known.
- `candidate-api` and `candidate-worker` still depend on shared document storage assumptions.

## Crawler deployment contract

Required env wiring for crawler:

- `CORE_API_BASE_URL=http://job-api:8000`
- `CORE_API_INGEST_PATH=/api/v1/ingest/raw-jobs`
- `INGEST_API_TOKEN=<shared token>` if enabled
- `CRAWLER_ENABLED_PROVIDERS=topcv,itviec`

Crawler image/runtime options:

- lightweight image: `docker/crawler-api.Dockerfile`
  - backend: `CRAWL_BACKEND=http`
  - lower CPU and memory
  - preferred first POC deploy when pages are server-rendered enough
- browser image: `docker/crawler-api-browser.Dockerfile`
  - backend: `CRAWL_BACKEND=crawl4ai`
  - installs Playwright Chromium
  - use when lightweight fetches miss data or sites require browser execution

Recommended first-pass requests/limits:

- lightweight crawler
  - requests: `cpu: 250m`, `memory: 256Mi`
  - limits: `cpu: 1`, `memory: 512Mi`
- browser crawler
  - requests: `cpu: 500m`, `memory: 1Gi`
  - limits: `cpu: 2`, `memory: 2Gi`

Adjust after measuring real crawl volume and selector stability.

## Persistence and scaling constraints

- The current app still assumes shared access to `/app/data` for candidate documents and exports.
- A single `ReadWriteOnce` PVC is a poor default for multi-pod candidate components.
- Safer first deploy options:
  - keep `candidate-api` and `candidate-worker` at one replica each
  - use `ReadWriteMany` storage if supported
  - or redesign storage to use S3-compatible object storage

## Helm packaging guidance

Preferred chart direction:

- one app chart in this repo packaging:
  - `job-api`
  - `crawler-api`
  - `candidate-api`
  - `candidate-worker`
- feature flags such as:
  - `jobApi.enabled`
  - `crawlerApi.enabled`
  - `candidateApi.enabled`
  - `candidateWorker.enabled`
  - `nats.enabled` with default `false`

Keep generic logic in templates. Push service-specific and environment-specific values into values files.

## Production-readiness gaps

Prioritize these before relying on the cluster deploy:

1. Install PostgreSQL runtime deps in deployed images that need them.
2. Replace startup `create_all()` with migrations or a bootstrap job.
3. Add or verify readiness/liveness probes, requests/limits, and ingress/auth decisions.
4. Make storage behavior explicit in chart values.
5. Make crawler scheduling explicit: manual API trigger, CronJob, or external scheduler.
6. Keep Dockerfiles, README, Helm values, and release workflows aligned whenever topology changes.

## Validation checklist

When deployment assets change:

- build all touched images
- render Helm templates for each workload variant
- verify service-specific image names and ports
- verify env vars for PostgreSQL, storage, core ingest, and crawler runtime
- verify replica counts do not contradict storage mode or queue assumptions
