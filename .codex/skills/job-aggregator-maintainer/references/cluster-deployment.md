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

- `job-aggregator` repo owns app code, Dockerfiles, image build logic, Helm chart structure, chart defaults, ports, probes, env variable names, and service topology.
- GitOps repo owns environment-specific values: image tags, replica counts, ingress hosts, secret references, storage class, resource sizing, and rollout objects.

Use raw `k8s/` manifests as reference. Use Helm or the GitOps repo as deployment source of truth.

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

Required image/runtime facts:

- `docker/crawler-api.Dockerfile` installs `crawl4ai` and Playwright Chromium.
- The crawler image is heavier than the core API image.
- Browser workloads need explicit CPU and memory requests in cluster values.

Recommended first-pass requests/limits for crawler:

- requests: `cpu: 500m`, `memory: 1Gi`
- limits: `cpu: 2`, `memory: 2Gi`

Adjust after measuring real crawl volume and browser concurrency.

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
6. Keep Dockerfiles, README, `k8s/`, and Helm values aligned whenever topology changes.

## Validation checklist

When deployment assets change:

- build all touched images
- render Helm templates for each workload variant
- verify service-specific image names and ports
- verify env vars for PostgreSQL, storage, core ingest, and crawler runtime
- verify replica counts do not contradict storage mode or queue assumptions
