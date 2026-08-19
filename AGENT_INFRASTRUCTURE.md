# Infraestrutura Agentic do SEO

Esta camada é aditiva. O banco operacional continua configurado por `DATABASE_URL` e não deve ser substituído por Neon.

## 1. Banco AI / SAF-T (Neon)

No runtime do backend configure, sem colocar valores no repositório:

```text
AI_DATABASE_URL=<valor equivalente ao POSTGRES_URL do recurso Neon>
AI_DATABASE_URL_NON_POOLING=<valor equivalente ao POSTGRES_URL_NON_POOLING>
```

Para criar apenas as tabelas da camada AI/SAF-T, execute uma vez:

```bash
python scripts/init_ai_db.py
```

O script usa a conexão non-pooling quando disponível e nunca usa `DATABASE_URL` para criar o schema AI.

Em produção mantenha:

```text
AI_AUTO_CREATE_SCHEMA=false
```

## 2. SAF-T

Comece com:

```text
SAFT_INTEGRATION_ENABLED=false
```

Depois de o schema Neon estar criado e o endpoint `/api/v1/saft/status` confirmar a infraestrutura, habilite de forma controlada:

```text
SAFT_INTEGRATION_ENABLED=true
```

O SAF-T grava apenas nas tabelas AI isoladas e não cria registos em `financial_documents`.

## 3. Upstash Redis / KV

Variáveis suportadas:

```text
REDIS_URL
KV_URL
```

Usar para cache, sessões temporárias, locks e estado de jobs. Dados contabilísticos oficiais não devem depender exclusivamente do Redis.

## 4. Upstash Vector

```text
UPSTASH_VECTOR_REST_URL
UPSTASH_VECTOR_REST_TOKEN
```

Usar para memória semântica e padrões aprovados. Todo item deve conter `tenant_id` e as pesquisas devem ser filtradas pelo tenant.

## 5. Upstash Search

```text
UPSTASH_SEARCH_REST_URL
UPSTASH_SEARCH_REST_TOKEN
```

Integração disponível para pesquisa. Não é fonte oficial de verdade contabilística.

## 6. QStash

Este projeto usa prefixo `upseo_` no recurso instalado no Vercel:

```text
upseo_QSTASH_URL
upseo_QSTASH_TOKEN
upseo_QSTASH_CURRENT_SIGNING_KEY
upseo_QSTASH_NEXT_SIGNING_KEY
```

O código também aceita nomes QStash sem prefixo como fallback. Tokens e signing keys são apenas de backend.

Usar QStash para lembretes, jobs e processamento assíncrono. Callbacks devem validar assinatura antes de executar qualquer ação.

## 7. Sentry

```text
SENTRY_DSN
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.0
```

`app.observability` remove body, cookies, cabeçalhos de autenticação e extras com dados financeiros antes do envio.

`SENTRY_AUTH_TOKEN` é de build/administração e não deve ser exposto à aplicação cliente.

## 8. Checkly

`CHECKLY_ACCOUNT_ID` pode ser disponibilizado ao backend, mas os monitores são geridos externamente. Os checks recomendados são:

- `/health`
- `/ready`
- login/autenticação
- `/api/v1/saft/status`
- importação SAF-T de teste em preview
- isolamento por tenant

## 9. Segurança

Nunca colocar no Git:

- URLs PostgreSQL completas;
- passwords;
- tokens Upstash/QStash;
- signing keys;
- Sentry auth token;
- ficheiros SAF-T reais.

Nunca enviar secrets ao frontend.

## 10. SNC

A infraestrutura deste documento não habilita lançamentos SNC. O futuro SNC Adapter deve seguir:

```text
proposta -> validação -> ApprovalRequest -> autorização explícita -> execução -> AuditLog
```

Aprendizagem/Vector pode melhorar a proposta, mas nunca remover a aprovação obrigatória para lançamento definitivo.
