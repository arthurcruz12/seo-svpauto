#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.backend.yml"
MODE="${1:-dry-run}"
LOCAL_BASE_URL="${SEO_LOCAL_BACKEND_URL:-http://127.0.0.1:8000}"

commands=(
  "docker compose -f ${COMPOSE_FILE} config -q"
  "docker compose -f ${COMPOSE_FILE} build seo-backend"
  "docker compose -f ${COMPOSE_FILE} run --rm seo-backend alembic upgrade head"
  "docker compose -f ${COMPOSE_FILE} up -d seo-backend"
  "docker compose -f ${COMPOSE_FILE} ps seo-backend"
  "bash scripts/smoke-backend.sh ${LOCAL_BASE_URL}"
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

if ! command -v docker >/dev/null 2>&1; then
  echo "BLOCKED: docker is not installed on this host." >&2
  exit 2
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "BLOCKED: docker compose is not available on this host." >&2
  exit 2
fi

if ! grep -Eq '^ENVIRONMENT=["'"']?production["'"']?$' .env.backend; then
  echo "BLOCKED: .env.backend must set ENVIRONMENT=production." >&2
  exit 2
fi

if ! grep -Eq '^SECRET_KEY=.+$' .env.backend; then
  echo "BLOCKED: .env.backend must contain SECRET_KEY." >&2
  exit 2
fi

DATABASE_VALUE="$(grep -E '^DATABASE_URL=' .env.backend | tail -n 1 | cut -d= -f2- | sed -e 's/^["'"']//; s/["'"']$//' || true)"
case "$DATABASE_VALUE" in
  postgresql://*|postgres://*) ;;
  *)
    echo "BLOCKED: Production DATABASE_URL must point to PostgreSQL." >&2
    exit 2
    ;;
esac

echo "Deploying backend commit: $(git rev-parse HEAD 2>/dev/null || echo unknown)"

for command in "${commands[@]}"; do
  echo "+ $command"
  if ! bash -lc "$command"; then
    echo "DEPLOY FAILED while running: $command" >&2
    docker compose -f "$COMPOSE_FILE" logs --tail=120 seo-backend >&2 || true
    exit 1
  fi
done

echo "Backend container updated and smoke gate passed."
echo "Verify the public DuckDNS URL and an authenticated billing task before removing the Preview fallback."
