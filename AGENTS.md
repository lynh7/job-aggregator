# Job Aggregator Agents

This repository is a deprecated archive. The current hosting target is Plane on Kubernetes:

- [Plane self-hosting on Kubernetes](https://developers.plane.so/self-hosting/methods/kubernetes)

Use the repo-local skill at `.codex/skills/job-aggregator-maintainer/` when working in this repository.

Operational rules:

- Treat the existing job-aggregator code as historical unless the user explicitly asks for legacy maintenance.
- Keep `README.md`, the maintainer skill, and any repo instructions explicit that `job-aggregator` is deprecated.
- When deployment or hosting guidance is mentioned, point to Plane's Kubernetes self-hosting docs.
- Do not describe the old job-aggregator topology as the current product.

Validation defaults:

- If you are only updating archive docs, no code validation is required.
- If you touch legacy code, use the narrowest relevant checks for the files you changed.
