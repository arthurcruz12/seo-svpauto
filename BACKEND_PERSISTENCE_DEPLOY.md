# Backend persistence and DuckDNS rollout

This document prepares the backend rollout required by `Assistente IA -> Trabalho` without authorizing or performing a Production deployment.

## Runtime target

The backend container must run:

```text
uvicorn app.main_saft:app --host 0.0.0.0 --port 8000
```

`app.main_saft:app` preserves the existing application/authentication and adds the agent, SAF-T and executable Assistant routers.

## Required environment

Keep the existing secrets and database configuration in a server-side `.env.backend` that is never committed. At minimum the backend needs its existing `DATABASE_URL`, `SECRET_KEY`, host/CORS settings and any currently used service configuration.

The agent persistence rollout additionally requires:

```text
SEO_ARTIFACT_STORAGE_PROVIDER=local
SEO_ARTIFACT_STORAGE_PATH=/var/lib/seo/agent-storage
SNC_WRITE_ENABLED=false
SAFT_INTEGRATION_ENABLED=false
```

The supplied `docker-compose.backend.yml` mounts the named Docker volume `seo_agent_storage` at `/var/lib/seo/agent-storage`, so source/output artifacts survive container recreation.

## Database migration

Before starting the new container, apply the additive migration:

```text
alembic upgrade head
```

The migration creates only:

- `agent_tasks`
- `agent_executions`
- `agent_artifacts`

It does not remove or replace existing tenant, user, company, document or audit tables.

## Guarded deployment helper

Running:

```text
bash scripts/deploy-backend.sh
```

is dry-run only.

An actual host deployment requires both:

```text
SEO_ALLOW_BACKEND_DEPLOY=true
bash scripts/deploy-backend.sh --apply
```

This repository change does not execute those commands on the DuckDNS host.

## Verification gate after an authorized deployment

1. `GET /health` returns 200.
2. `GET /ready` returns 200.
3. `GET /api/v1/assistant/tasks` without a token returns 401 (not 404).
4. The same endpoint with a valid existing SEO JWT returns 200.
5. Execute one billing XLSX through `POST /api/v1/assistant/messages`.
6. Confirm the task is `COMPLETED`, includes DocumentAgent/BillingAgent/AuditAgent executions and has an OUTPUT artifact.
7. Download the OUTPUT artifact.
8. Restart/recreate the backend container.
9. Confirm the task remains queryable and the same artifact remains downloadable.
10. Confirm a JWT from another tenant receives 404 for the task and artifact.
11. Confirm `/api/v1/agents/status` reports `snc_write=false` and `saft_ingestion=false`.

Only after this gate passes should the temporary Preview fallback be removed. Production frontend promotion remains a separate authorization.

## Rollback

If the new backend fails health/readiness checks, restore the previous backend container/image while leaving the additive database tables and persistent artifact volume intact. Do not downgrade the database during an incident unless a separately reviewed rollback explicitly requires it.
