# CURRENT ARCHITECTURE — SEO

Date: 2026-08-20
Branch: `feature/agent-manager-assistant-integration`

## Purpose

This file records the architecture actually observed in the repository and deployment configuration before further agent implementation. It is descriptive, not a migration plan.

## 1. Protected public frontend

The public SEO interface is not served from `frontend/App.js`.

The Vercel build on `main` serves the preserved frontend under `legacy/`. The agent branch rebuilds the original Vite source from the immutable commit `20e92f6ecea51b8ae0afba88391ae03e53e68e93` and applies narrowly scoped patches only inside the existing Assistant IA.

Protected flow:

`Homepage pública -> Entrar -> Login existente -> autenticação existente -> SEO interno -> Assistente IA`

Protected areas that must not be replaced by agent work:

- public homepage and navigation;
- Entrar button;
- login form;
- MFA flow;
- registration flow;
- administrator identity/credentials;
- existing authenticated shell.

The agent-enabled Assistant IA order is:

`Chat | Trabalho | Código | Integrações`

## 2. Vercel routing

Vercel serves the frontend and provides small authenticated bridge endpoints under `/api/*` for agent-related capabilities.

Requests under `/seo-api/:path*` are rewritten to the external backend:

`https://sistemaeficienciaoperacional.duckdns.org/:path*`

All other frontend paths fall back to `/index.html`.

Production and preview must remain separate. Changes in this branch must not be promoted to Production automatically.

## 3. Backend repository structure

The canonical Python application code is under:

`app/`

Core application:

`app.main:app`

Agent/SAF-T additive entrypoint used by the container:

`app.main_saft:app`

`app.main_saft` imports the existing `app.main:app` and adds isolated routers. It must not replace authentication, users, tenants, companies, roles or existing financial data.

## 4. Authentication and tenancy

Existing authentication is JWT-based and resolves the current user from the existing `users` table.

Relevant identity context:

- `current_user`;
- `tenant_id`;
- user role / RBAC permissions;
- company ownership scoped to the current tenant.

New agent endpoints must reuse this identity. No parallel authentication provider is allowed for the MVP.

## 5. Operational database

The existing operational database is configured through `DATABASE_URL`.

Current operational models include:

- Tenant;
- User;
- Company;
- FinancialDocument;
- AuditLog.

Schema changes for agent tasks, stored artifacts and richer execution metadata must be additive only.

## 6. AI / SAF-T isolated infrastructure

The repository contains a separate AI/SAF-T infrastructure path configured through `AI_DATABASE_URL` / `AI_DATABASE_URL_NON_POOLING` when available.

SAF-T is not part of the MVP execution input yet.

Required state for this phase:

- `SAFT_INTEGRATION_ENABLED=false`;
- no real company SAF-T ingestion;
- no direct write from SAF-T into official financial documents.

## 7. SNC

SNC is distinct from Atena and from SAF-T.

For the current phase SNC is preparation-only:

`READ | CLASSIFY | PREPARE | VALIDATE`

Direct SNC write must remain disabled. Human approval records a decision but does not execute an SNC posting in this phase.

A dedicated `SNC_WRITE_ENABLED=false` guard must be treated as mandatory before any future adapter can expose write behavior.

## 8. Atena

Atena is a trusted information source. It is not the SNC and must not be represented as the SNC.

The SEO may use Atena data for treatment, reconciliation, organization, analysis and decision support when a real integration is configured. No simulated Atena connection is considered functional.

## 9. Current Agent Manager state before this implementation

The existing agent layer performs authenticated intent routing and can show the selected agents, integration status and approval requirement.

It does not yet constitute successful business execution merely by returning agent names.

The target billing execution is:

`message -> task -> DocumentAgent -> BillingAgent -> AuditAgent -> XLSX artifact -> persisted task/audit -> response`

`COMPLETED` is valid only when the real output artifact exists and the autonomous auditor passes all mandatory checks.

## 10. Billing source contract observed

Raw daily billing workbooks use header names rather than fixed column indexes. The supported canonical fields are:

- ID;
- Documento;
- Data Doc.;
- Entidade;
- Total;
- Total liquido / Total líquido;
- Total IVA;
- Estado;
- Doc. Fornecedor;
- Nº Enc. / Req. Ext.;
- Canal de Anúncios;
- Vendedor;
- F. Liquidação / Forma de Liquidação.

Document type and series can be derived from `Documento` when not supplied explicitly, e.g. `FR CUSA/667`.

Supported series:

- Coimbra: CUSA, CNOV;
- Picoto: PUSA, PNOV, POFI.

Supported billing documents:

- FR;
- FT;
- NC.

NC monetary values are normalized to `-ABS(value)` and are separated by `Liquidado` / `Pendente`.

Sucatas and Salvados must be separate. A Sucata is only classified when there is an explicit marker (currently a known operational marker is an entity containing `SUCATAS DE RAMIL`). Salvados must not be invented when no explicit marker exists.

## 11. Storage

The original source file must never be overwritten.

Agent execution must retain metadata including:

- file id;
- tenant/company/user scope;
- filename;
- content type;
- size;
- SHA-256;
- source/output role;
- storage reference;
- creation time.

The storage backend may be configurable, but the API contract must not expose filesystem paths, secrets or connection strings to the client.

## 12. Jobs

`app/tasks.py` currently contains a Celery placeholder returning `processed_async`. It is legacy behavior and must not be treated as a real job implementation.

A future asynchronous architecture must use one real job mechanism and perform real work. Until then, the billing MVP may execute synchronously while persisting task state transitions.

## 13. CI and validation

Existing Backend CI covers Python lint, Alembic migrations, pytest/coverage and Docker build.

The complete MVP gate additionally requires:

- frontend protected-marker regression checks;
- frontend typecheck/build;
- billing workbook integration tests;
- negative auditor test with a deliberately corrupted workbook;
- authentication/tenant tests;
- E2E homepage/login/Assistant tests;
- visual regression check;
- Vercel Preview validation.

## 14. Canonical safety rules

No implementation in this branch may:

- remove or replace the homepage;
- replace login/authentication;
- change administrator credentials;
- perform destructive schema migration;
- overwrite originals;
- push or merge directly to `main`;
- promote a deployment to Production;
- enable SAF-T real ingestion;
- execute an SNC posting.

If any requested change would require one of those actions, that part is `BLOCKED_BY_SAFETY` while safe work continues.