#!/usr/bin/env sh
set -eu

base_url="${API_URL:-http://localhost:8000}"

curl --fail --silent --show-error "$base_url/api/v1/health"
printf '\n'
curl --fail --silent --show-error \
  -X POST "$base_url/api/v1/sync-runs" \
  -H 'Content-Type: application/json' \
  -d '{"source":"fixtures"}'
printf '\n'
curl --fail --silent --show-error "$base_url/api/v1/risk-signals"
printf '\n'

