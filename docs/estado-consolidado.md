# Estado consolidado do SEO

O SEO deixou de ser apenas um prototipo visual. A base atual inclui backend, autenticacao, permissoes, persistencia e auditoria.

## Componentes consolidados

- Frontend React com build de producao.
- Backend FastAPI.
- Base SQLite local em `backend/storage/seo.sqlite3`.
- Preparacao de configuracao `SEO_DATABASE_URL` para evoluir para PostgreSQL.
- Estrutura multiempresa com `company_id` em utilizadores e dados operacionais.
- Centro de Decisao como tela principal da plataforma.
- Indice SEO Core calculado por margem, pendencias, saldos e stock parado.
- Contas persistidas.
- Auditoria persistida.
- Autenticacao com JWT.
- Segunda verificacao por codigo temporario em ambiente local.
- MFA por email via SMTP quando configurado.
- Relatorio executivo PDF gerado pelo backend.
- Endpoint de catalogo para integracoes de marketplaces e ERP.
- Leitura `.xlsx` no backend com `openpyxl`.
- Permissoes por perfil.
- Bloqueio de configuracoes inseguras quando `SEO_ENV=production`.
- Documentacao de privacidade, conformidade e checklist legal.

## Execucao local

```cmd
scripts\start-local.cmd
```

URL:

```text
http://127.0.0.1:5173/
```

Conta admin local:

```text
admin@seo.local
Seo-Admin-2026
```

## Variaveis de producao

Copie `backend/.env.example` e defina valores reais:

```text
SEO_ENV=production
SEO_JWT_SECRET=<segredo-longo-e-aleatorio>
SEO_ADMIN_EMAIL=<email-real>
SEO_ADMIN_PASSWORD=<password-forte>
SEO_EXPOSE_DEV_MFA=0
SEO_SMTP_HOST=<smtp-host>
SEO_SMTP_USERNAME=<smtp-user>
SEO_SMTP_PASSWORD=<smtp-password>
SEO_SMTP_FROM=<email-remetente>
```

## Ainda pendente para produto comercial

- Migracao efetiva para PostgreSQL gerido.
- App autenticadora TOTP como alternativa ao email.
- Integracoes reais com Ovoko, Recambio, WooCommerce, Shopify, Moloni e Primavera.
- Motor profissional de PDF com branding completo, graficos e assinatura visual.
- Encriptacao da base de dados em repouso.
- Deploy HTTPS.
- Multiempresa com isolamento forte em PostgreSQL e politicas de backup por empresa.
- Endpoints backend para alterar inventario, pagamentos e conciliacao.
- Testes automatizados.
- Revisao juridica e contabilistica.
