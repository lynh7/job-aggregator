#!/bin/sh
set -eu

cat > /usr/share/nginx/html/config.js <<CONFIG
window.__JOB_AGGREGATOR_CONFIG__ = {
  jobApiBaseUrl: "${UI_JOB_API_BASE_URL:-/job-api/api/v1}",
  candidateApiBaseUrl: "${UI_CANDIDATE_API_BASE_URL:-/candidate-api/api/v1}",
  environment: "${UI_ENVIRONMENT:-runtime}"
};
CONFIG
