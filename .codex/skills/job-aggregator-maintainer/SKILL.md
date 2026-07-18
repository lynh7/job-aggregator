---
name: job-aggregator-maintainer
description: Use this skill when updating the deprecated job-aggregator archive docs or any remaining references in this repo.
---

# Job Aggregator Maintainer

This repository is deprecated. Treat the existing job-aggregator implementation as historical unless the user explicitly asks for legacy maintenance.

Current hosting target: Plane self-hosting on Kubernetes.
Official guide: https://developers.plane.so/self-hosting/methods/kubernetes

## What to do

- Keep README and any repo instructions explicit that `job-aggregator` is deprecated.
- Replace old "active product" wording with archive or legacy wording.
- When deployment guidance is mentioned, point to Plane's Kubernetes self-hosting docs.
- Avoid expanding the legacy stack docs unless the user is maintaining archived behavior on purpose.

## What not to do

- Do not describe the old job-aggregator topology as the current product.
- Do not add new guidance that assumes the deprecated stack is still the target.
