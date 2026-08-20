# Backend persistence and DuckDNS rollout

This document defines the Production backend rollout required by `Assistente IA -> Trabalho`. It describes the deployment contract; executing it still requires access to the DuckDNS host.

## Runtime target

The backend container runs:

```text
uvicorn app.main_saft:app --host 0.0.0.0 --port 8000
```

`app.main_saft:app` preserves the existing application/authentication and adds the agent, isolated SAF-T and executable Assistant routers.

## Required server-side environment

Copy the repository template:

```text
.env.backend.example -> .env.backend
```

The real `.env.backend` must remain only on the backend host and is ignored by Git.

The guarded deploy requires, at minimum:

```text
ENVIRONMENT=production
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

Production deployment is intentionally blocked when `DATABASE_URL` is not PostgreSQL.

The runtime also keeps these safety controls:

```text
SEO_ARTIFACT_STORAGE_PROVIDER=local
SEO_ARTIFACT_STORAGE_PATH=/var/lib/seo/agent-storage
SNC_WRITE_ENABLED=false
SAFT_INTEGRATION_ENABLED=false
```

`docker-compose.backend.yml` mounts the named Docker volume `seo_agent_storage` at `/var/lib/seo/agent-storage`, so SOURCE/OUTPUT artifacts survive container recreation.

## Database migration

Deployment runs the additive migration before starting the new container:

```text
alembic upgrade head
```

Migration `0003_agent_task_persistence` creates:

- `agent_tasks`
- `agent_executions`
- `agent_artifacts`

It does not remove or replace the existing tenant, user, company, document or audit tables.

## Guarded deployment helper

A dry-run is always safe:

```text
bash scripts/deploy-backend.sh
```

It prints the commands but does not modify the host.

An actual host deployment requires both:

```text
SEO_ALLOW_BACKEND_DEPLOY=true bash scripts/deploy-backend.sh --apply
```

Before changing the container the script validates:

- `.env.backend` exists;
- Docker is installed;
- Docker Compose is available;
- `ENVIRONMENT=production`;
- `SECRET_KEY` is present;
- `DATABASE_URL` points to PostgreSQL;
- the Compose file is valid.

The deployment sequence is:

1. `docker compose ... config -q`
2. build `seo-backend`
3. `alembic upgrade head`
4. `docker compose ... up -d seo-backend`
5. display container state
6. execute `scripts/smoke-backend.sh`

If any command fails, the script exits non-zero and prints the latest backend container logs.

## Automated smoke gate

`scripts/smoke-backend.sh` waits for and requires:

```text
GET /health                          -> 200
GET /ready                           -> 200
GET /api/v1/assistant/tasks          -> 401 without authentication
```

The `401` requirement is deliberate: it proves the new Assistant route exists while remaining protected. A `404` means the new backend was not actually deployed.

Default local target:

```text
http://127.0.0.1:8000
```

It can be overridden with `SEO_LOCAL_BACKEND_URL` or by passing a base URL directly to the smoke script.

## Live rollout gate after host deployment

After the local smoke gate passes:

1. `GET https://sistemaeficienciaoperacional.duckdns.org/health` returns 200.
2. `GET https://sistemaeficienciaoperacional.duckdns.org/ready` returns 200.
3. unauthenticated `GET /api/v1/assistant/tasks` returns 401, not 404.
4. the same endpoint with a valid existing SEO JWT returns 200.
5. execute one real billing XLSX through `POST /api/v1/assistant/messages`.
6. confirm the Task reaches `COMPLETED` only after DocumentAgent, BillingAgent and AuditAgent complete.
7. confirm an OUTPUT artifact exists and can be downloaded.
8. restart/recreate the backend container.
9. confirm the Task remains queryable.
10. confirm the same OUTPUT remains downloadable after restart.
11. confirm a JWT from another tenant receives 404 for the Task and artifact.
12. confirm `/api/v1/agents/status` reports `snc_write=false` and `saft_ingestion=false`.

Only after this live gate passes should the temporary Preview fallback be removed.

## CI deployment-contract gate

The PR CI additionally validates:

- shell syntax for `deploy-backend.sh` and `smoke-backend.sh`;
- deploy helper remains dry-run by default;
- `docker-compose.backend.yml` parses with a safe temporary Production-shaped environment;
- Alembic migrations;
- backend tests/coverage;
- protected frontend build;
- Docker image build.

## Rollback

If the new backend fails the live health/readiness gate, restore the previous backend container/image while leaving the additive database tables and persistent artifact volume intact. Do not downgrade the database during an incident unless a separately reviewed rollback explicitly requires it.
