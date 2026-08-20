#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.backend.yml"
MODE="${1:-dry-run}"

commands=(
  "docker compose -f ${COMPOSE_FILE} build seo-backend"
  "docker compose -f ${COMPOSE_FILE} run --rm seo-backend alembic upgrade head"
  "docker compose -f ${COMPOSE_FILE} up -d seo-backend"
  "docker compose -f ${COMPOSE_FILE} ps seo-backend"
)

if [[ "$MODE" != "--apply" ]]; then
  echo "DRY RUN ONLY — no deployment was performed."
  echo "Required server-side file: .env.backend (not committed)."
  echo "Planned commands:"
  printf '  %s\n' "${commands[@]}"
  echo
  echo "To execute on the authorized backend host, set SEO_ALLOW_BACKEND_DEPLOY=true and pass --apply."
  exit 0
fi

if [[ "${SEO_ALLOW_BACKEND_DEPLOY:-false}" != "true" ]]; then
  echo "BLOCKED: SEO_ALLOW_BACKEND_DEPLOY=true is required for an actual deployment." >&2
  exit 2
fi

if [[ ! -f .env.backend ]]; then
  echo "BLOCKED: .env.backend is required and must contain the existing backend secrets/configuration." >&2
  exit 2
fi

for command in "${commands[@]}"; do
  echo "+ $command"
  bash -lc "$command"
done

echo "Backend container updated. Verify /health, /ready and authenticated /api/v1/assistant/tasks before changing frontend fallback policy."
