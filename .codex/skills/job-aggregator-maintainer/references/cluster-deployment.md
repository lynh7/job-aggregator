# Cluster deployment reference

Read this file when work touches:

- Docker image packaging
- Helm chart shape or values
- Kubernetes manifests
- replica counts, probes, resources, or persistence
- database choice, queue backend, or runtime topology
- handoff between this repo and a separate GitOps repo

## Current runtime facts

- The active production queue path is database-backed. `QUEUE_BACKEND=database` is the default in `.env.example`, and worker claiming logic lives in `candidate_service/task_queue.py`.
- NATS exists for future event-driven work, but current candidate processing does not require it.
- Production concurrency assumes PostgreSQL-compatible locking. The worker uses `FOR UPDATE SKIP LOCKED` when the dialect is not SQLite.
- Candidate uploads are written to local disk under `CANDIDATE_STORAGE_DIR`, and `CandidateDocument.storage_path` stores filesystem paths in the database.
- Job exports are written to local disk under `EXPORT_DIR`.
- All app entrypoints currently call `Base.metadata.create_all(...)` at startup. This is convenient for development but weak for production migrations.
- Current Dockerfiles install `pip install .`, not `pip install '.[postgres]'`, so PostgreSQL deployments need image changes or equivalent dependency handling.

## Deployment ownership split

Recommended split:

- `job-aggregator` repo owns app code, Dockerfiles, image build logic, Helm chart structure, chart defaults, ports, probes, commands, env variable names, and service topology.
- GitOps repo owns environment-specific values: image tags, replica counts, ingress hosts, secret references, storage class, resource sizing, and rollout objects.

Do not treat `k8s/` as the long-term source of truth if Helm is the packaged deployment artifact. Keep raw manifests aligned, but drive real deployments through the chart.

## Recommended cluster topology

Default first production shape:

- PostgreSQL via CNPG or another managed PostgreSQL offering
- `job-api`: 2 replicas
- `candidate-api`: 1 replica initially
- `candidate-worker`: 1 replica initially
- `nats`: disabled unless queue migration is in progress

Reasoning:

- `job-api` is stateless enough to scale horizontally.
- `candidate-api` accepts uploads that land on local/shared storage, so scaling safely depends on storage design.
- `candidate-worker` can scale horizontally only when PostgreSQL is in use and the document storage path is reachable from every worker pod.

## Persistence and scaling constraints

- The current app assumes shared access to `/app/data` for candidate documents and exports.
- A single shared PVC with `ReadWriteOnce` is a bad default for multi-pod deployments.
- Safer first deploy options:
  - keep `candidate-api` and `candidate-worker` at one replica each
  - use `ReadWriteMany` storage if the cluster supports it
  - or redesign storage to use S3-compatible object storage and store object keys instead of pod-local file paths

If scaling candidate components, verify both of these:

- PostgreSQL is the active database
- uploaded document paths are accessible from every worker pod that may claim the task

## Helm packaging guidance

Preferred chart direction:

- one app chart in this repo packaging:
  - `job-api`
  - `candidate-api`
  - `candidate-worker`
- feature flags such as:
  - `jobApi.enabled`
  - `candidateApi.enabled`
  - `candidateWorker.enabled`
  - `nats.enabled` with default `false`

Chart defaults should describe the application contract, not one cluster's staging values.

Keep generic template logic in templates and push service-specific or environment-specific values into values files.

## Production-readiness gaps

Before relying on this repo for cluster deployment, prioritize:

1. Install PostgreSQL runtime dependencies in all deployed images.
2. Replace startup `create_all()` with migrations or a controlled bootstrap job.
3. Add or verify readiness/liveness probes, requests/limits, and ingress/auth decisions.
4. Make storage behavior explicit in chart values.
5. Keep Dockerfiles, README, `k8s/`, and Helm values aligned whenever topology changes.

## Validation checklist

When deployment assets change:

- build all touched images
- render Helm templates for each workload variant
- verify image names and tags remain service-specific
- verify env vars required for PostgreSQL and storage are still wired
- verify replica counts do not contradict storage mode or queue backend assumptions
