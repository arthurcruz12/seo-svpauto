# Deploy de producao - SEO Core

Objetivo: transformar o SEO Core numa plataforma comercial segura, multiempresa e operavel.

## Frase de produto

O SEO nao e um dashboard. E um sistema que transforma dados operacionais em decisoes financeiras prioritarias.

## Ambientes

- `development`: SQLite local, MFA demonstrativo permitido.
- `staging`: PostgreSQL, SMTP real, dados de teste.
- `production`: PostgreSQL gerido, HTTPS, SMTP real, backups e monitorizacao.

## PostgreSQL

Subir base local para desenvolvimento:

```cmd
docker compose up -d postgres
```

Variavel esperada:

```text
SEO_DATABASE_URL=postgresql://seo_user:seo_password_change_me@localhost:5432/seo
```

Nota: a aplicacao ja tem estrutura de empresas e dados por `company_id`. A proxima etapa tecnica e migrar `backend/app/store.py` para SQLAlchemy + Alembic.

## Persistencia cloud

A versao atual ja permite persistencia cloud por volume gerido:

```text
SEO_DATABASE_PATH=/data/seo/seo.sqlite3
```

Use um volume persistente do fornecedor cloud para `/data/seo`. O backend guarda inventario, contas, conciliacao, auditoria, snapshots historicos e estado de subscricao nessa base.

Endpoints de historico:

- `POST /reports/snapshots`: cria snapshot `daily`, `weekly`, `monthly`, `quarterly` ou `annual`.
- `GET /reports/snapshots`: lista historico por periodo.
- `GET /reports/compare`: compara os dois snapshots mais recentes do periodo.

## Variaveis obrigatorias em producao

```text
SEO_ENV=production
SEO_JWT_SECRET=<segredo-longo>
SEO_ADMIN_EMAIL=<email-admin>
SEO_ADMIN_PASSWORD=<password-forte>
SEO_EXPOSE_DEV_MFA=0
SEO_SMTP_HOST=<smtp-host>
SEO_SMTP_USERNAME=<smtp-user>
SEO_SMTP_PASSWORD=<smtp-password>
SEO_SMTP_FROM=<remetente>
SEO_DATABASE_PATH=/data/seo/seo.sqlite3
SEO_FRONTEND_URL=https://app.seo.pt
SEO_CORS_ORIGINS=https://app.seo.pt
STRIPE_SECRET_KEY=<stripe-secret-key>
STRIPE_WEBHOOK_SECRET=<stripe-webhook-secret>
STRIPE_PRICE_STARTER=<stripe-price-starter>
STRIPE_PRICE_PROFESSIONAL=<stripe-price-professional>
STRIPE_PRICE_BUSINESS=<stripe-price-business>
```

## Checklist de produto premium

- Centro de Decisao como tela principal.
- Indice SEO Core calculado por dados reais.
- IA ligada a inventario, contas e conciliacao persistidos.
- Relatorio executivo PDF pelo backend.
- Integracoes Ovoko/Recambio catalogadas sem falsa ligacao.
- Multiempresa com isolamento por `company_id`.
- Auditoria persistida.
- Sem dados ficticios na area autenticada apos importacao.

## Proximas entregas

1. SQLAlchemy + Alembic.
2. PostgreSQL real em staging.
3. PDF premium com graficos e branding.
4. Conectores Ovoko e Recambio.
5. Testes automatizados de API e UI.
6. Deploy HTTPS com monitorizacao.
