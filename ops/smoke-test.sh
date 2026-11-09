#!/usr/bin/env bash
set -euo pipefail
base="http://localhost:5173"
if [ "$#" -gt 0 ]; then base="$1"; fi
curl --fail --silent --show-error --max-time 15 "$base/healthz" | grep -q '"status":"ok"'
curl --fail --silent --show-error --max-time 15 "$base/readyz" | grep -q '"status":"ready"'
curl --fail --silent --show-error --max-time 15 "$base/api/v1/public/landing-content" | grep -q UGX
echo "Basic health, database readiness and public API smoke checks passed."
