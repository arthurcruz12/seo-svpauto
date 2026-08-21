# CURRENT ARCHITECTURE — SEO

Date: 2026-08-20
Branch: `feature/agent-manager-assistant-integration`

## Purpose

This file records the architecture currently implemented on the agent integration branch. It is descriptive of branch state and does not authorize merge to `main` or Production deployment.

## 1. Protected public frontend

The public SEO interface is preserved from the immutable frontend source commit `20e92f6ecea51b8ae0afba88391ae03e53e68e93`. The branch rebuilds that frontend and applies narrowly scoped patches only inside the existing Assistente IA.

Protected flow:

`Homepage pública -> Entrar -> Login existente -> MFA/autenticação existente -> SEO interno -> Assistente IA`

Protected areas that agent work must not replace or redesign:

- homepage and public navigation;
- Entrar/login forms;
- MFA and registration;
- administrator identity/credentials;
- authenticated shell.

Assistente IA order remains:

`Chat | Trabalho | Código | Integrações`

`Trabalho` now has its own task-execution interface and does not replace the existing Chat flow.

## 2. Vercel routing and Preview compatibility

Vercel serves the protected frontend. Requests under `/seo-api/:path*` are rewritten to:

`https://sistemaeficienciaoperacional.duckdns.org/:path*`

The Trabalho UI first calls the persistent backend endpoints under `/api/v1/assistant/*` through that rewrite.

Because the currently deployed DuckDNS backend has not yet been updated with this branch, Preview retains a temporary `/api/assistant` execution fallback. That fallback is a compatibility layer only and is blocked in Production. It must be removed only after the persistent DuckDNS backend passes the rollout/restart gate.

No branch change is promoted to Production automatically.

## 3. Backend application

Canonical core application:

`app.main:app`

Additive container entrypoint:

`app.main_saft:app`

`app.main_saft` imports the existing core app and adds:

- agent router;
- assistant execution router;
- isolated SAF-T router.

Authentication, tenants, users, companies and existing financial models are reused rather than replaced.

## 4. Authentication, RBAC and tenancy

The backend uses the existing JWT authentication and existing `users` table.

All Assistant execution endpoints reuse:

- `current_user`;
- `tenant_id`;
- existing RBAC permissions;
- existing company ownership.

`company_id`, task detail and artifact download are tenant-scoped. A different tenant receives 404 rather than visibility into another tenant's resources.

## 5. Persistent task database

`DATABASE_URL` remains the operational database source.

Existing core models remain intact:

- Tenant;
- User;
- Company;
- FinancialDocument;
- AuditLog.

Additive migration `0003_agent_task_persistence` creates:

### AgentTask

Persistent task lifecycle and metadata, including:

- tenant/user/company scope;
- agent/task type;
- PENDING/RUNNING/NEEDS_REVIEW/COMPLETED/FAILED/CANCELLED-compatible status field;
- progress;
- instruction/source filename;
- processed/rejected counts;
- confidence/approval;
- audit JSON;
- error code/message;
- timestamps.

### AgentExecution

One trace per participating agent with:

- agent name;
- status;
- start/finish timestamps;
- input/output summary;
- confidence;
- error.

Current billing execution records:

`DocumentAgent -> BillingAgent -> AuditAgent`

### AgentArtifact

Persistent artifact metadata with:

- task/tenant/user scope;
- filename/content type/size;
- SHA-256;
- SOURCE / OUTPUT / AUDIT_REPORT role;
- storage provider/reference;
- creation time.

The API never exposes `storage_reference`.

## 6. Artifact storage

Agents no longer depend directly on a task JSON folder.

`ArtifactStorage` is the storage interface with:

- `save()`;
- `open()`;
- `exists()`;
- `delete()`.

Current provider:

`LocalPersistentStorage`

Configuration:

`SEO_ARTIFACT_STORAGE_PROVIDER=local`

`SEO_ARTIFACT_STORAGE_PATH=/var/lib/seo/agent-storage`

The supplied backend Compose configuration mounts a persistent Docker named volume at that path. Storage references are opaque relative references and path traversal outside the configured root is rejected.

The abstraction permits future S3/R2/Blob/MinIO providers without changing DocumentAgent/BillingAgent/AuditAgent.

## 7. Original/output integrity

Original uploads and generated results are different artifacts and different storage references.

Each has an independent SHA-256.

The source upload is preserved byte-for-byte and is never overwritten by the BillingAgent output.

Only an OUTPUT artifact can be downloaded through the public Assistant artifact endpoint.

## 8. Agent Manager execution lifecycle

The executable billing path is:

`POST /api/v1/assistant/messages`

`-> AgentTask PENDING`

`-> RUNNING`

`-> SOURCE artifact persisted`

`-> DocumentAgent`

`-> BillingAgent`

`-> AuditAgent`

`-> AUDIT_REPORT persisted`

`-> OUTPUT persisted only if audit passes`

`-> AgentTask COMPLETED or FAILED`

Routing alone is never completion.

`COMPLETED` requires a real generated workbook and a passing autonomous AuditAgent result.

If a stage raises, partial AgentExecution traces are preserved with the actual failing agent.

## 9. Assistant API

Persistent endpoints:

- `POST /api/v1/assistant/messages`
- `GET /api/v1/assistant/tasks`
- `GET /api/v1/assistant/tasks/{task_id}`
- `GET /api/v1/assistant/artifacts/{file_id}`

Task listing supports:

- `limit` (1–100);
- `offset`;
- `status`;
- `agent_type`;
- `date_from`;
- `date_to`.

Default ordering is newest task first.

All endpoints use existing authentication/RBAC and tenant isolation.

## 10. Trabalho interface

`Assistente IA -> Trabalho` supports:

- XLSX/XLSM source selection;
- execution instruction;
- execution through Agent Manager;
- status/result card;
- DocumentAgent/BillingAgent/AuditAgent status display;
- autonomous audit detail;
- OUTPUT download;
- persisted task history from `/tasks`.

The existing Chat interface remains separate.

## 11. Billing contract

Raw workbooks are located by header names rather than hard-coded column positions.

Supported billing series:

- Coimbra: CUSA, CNOV;
- Picoto: PUSA, PNOV, POFI.

Supported billing documents:

- FR;
- FT;
- NC.

GT/PF and cancelled documents are excluded. NC values are normalized negative and separated by Liquidado/Pendente. Seller summary uses `Total líquido`. Sucatas and Salvados remain separate and Salvado is never invented without an explicit marker.

Required workbook output remains exactly:

1. `Faturação Separada`
2. `Resumo Vendedores`
3. `Mapa Diário`

The legacy serverless billing contract POST no longer accepts client-declared audit booleans. Server-side AuditAgent inspection is authoritative.

## 12. Autonomous audit

AuditAgent opens the generated workbook itself and validates the output against normalized source records.

The negative corruption test remains mandatory: after deliberate workbook value modification the auditor must return FAILED.

A FAILED audit does not create/expose an OUTPUT artifact.

## 13. SNC safety

SNC is distinct from Atena and SAF-T.

Current SNC capability remains:

`READ | CLASSIFY | PREPARE | VALIDATE`

SNC write requires all three flags to be true:

- `AGENT_EXECUTION_ENABLED`;
- `SNC_INTEGRATION_ENABLED`;
- `SNC_WRITE_ENABLED`.

For this phase the deployment configuration pins:

`SNC_WRITE_ENABLED=false`

Human approval alone cannot bypass that gate.

## 14. SAF-T safety

SAF-T real ingestion remains disabled for this phase:

`SAFT_INTEGRATION_ENABLED=false`

No SAF-T path is allowed to write directly into official financial documents in this phase.

## 15. Atena

Atena remains a distinct trusted information source. SEO may consume Atena data for treatment, reconciliation, organization, analysis and decision support when a real integration is configured. SEO does not replace or “correct” Atena and Atena must not be represented as SNC.

## 16. Legacy fake completion paths

The legacy Celery placeholder no longer claims `processed_async` success.

Fake DocumentAI values were removed.

Client-provided `checks=true` style billing audit assertions are deprecated and cannot mark a task complete.

## 17. Backend rollout preparation

`docker-compose.backend.yml` defines the persistent backend runtime and artifact volume.

`scripts/deploy-backend.sh` is dry-run by default. An actual server deployment requires both explicit `--apply` and `SEO_ALLOW_BACKEND_DEPLOY=true`, plus the server-side `.env.backend`.

`BACKEND_PERSISTENCE_DEPLOY.md` documents the migration, deployment and rollback procedure.

This branch preparation does **not** constitute a Production deployment.

## 18. Required live rollout gate

After a separately authorized DuckDNS backend deployment, verify:

1. `/health` = 200;
2. `/ready` = 200;
3. unauthenticated `/api/v1/assistant/tasks` = 401, not 404;
4. authenticated `/api/v1/assistant/tasks` = 200;
5. real billing upload reaches COMPLETED only after audit passes;
6. task and artifact survive backend/container restart;
7. same OUTPUT remains downloadable after restart;
8. another tenant gets 404 for task/artifact;
9. `snc_write=false`;
10. `saft_ingestion=false`.

Only after this live gate passes should the temporary Preview fallback be removed.

## 19. CI gate

The branch CI validates:

- Ruff;
- Alembic migrations;
- pytest + coverage;
- billing integration tests;
- negative auditor test;
- persistent task/artifact tests;
- tenant isolation;
- protected frontend marker tests;
- TypeScript/Vite protected frontend build;
- Docker build.

## 20. Canonical safety rules

This branch must not:

- replace homepage/login/MFA/authentication;
- change administrator credentials;
- destructively migrate existing data;
- overwrite source uploads;
- merge directly to `main`;
- promote to Production;
- enable real SAF-T ingestion;
- execute SNC write while the explicit gate is false.

If a requested step requires Production deployment or another permission outside the current branch authorization, that step remains blocked while branch-safe implementation and validation continue.
