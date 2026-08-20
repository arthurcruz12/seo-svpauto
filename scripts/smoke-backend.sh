#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
MAX_ATTEMPTS="${SEO_SMOKE_MAX_ATTEMPTS:-30}"
SLEEP_SECONDS="${SEO_SMOKE_SLEEP_SECONDS:-2}"

request_code() {
  local url="$1"
  curl --silent --show-error --output /tmp/seo-smoke-body --write-out '%{http_code}' "$url"
}

wait_for_code() {
  local path="$1"
  local expected="$2"
  local attempt code

  for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
    code="$(request_code "${BASE_URL}${path}" || true)"
    if [[ "$code" == "$expected" ]]; then
      printf 'OK  %s -> %s\n' "$path" "$code"
      return 0
    fi
    sleep "$SLEEP_SECONDS"
  done

  printf 'FAIL %s -> expected %s, got %s\n' "$path" "$expected" "${code:-no-response}" >&2
  if [[ -s /tmp/seo-smoke-body ]]; then
    printf 'Response body: ' >&2
    head -c 500 /tmp/seo-smoke-body >&2 || true
    printf '\n' >&2
  fi
  return 1
}

wait_for_code "/health" "200"
wait_for_code "/ready" "200"
wait_for_code "/api/v1/assistant/tasks" "401"

printf 'Backend smoke gate passed for %s\n' "$BASE_URL"
