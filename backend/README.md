# SEO API

Camada backend do SEO para transformar o prototipo num produto seguro, multiempresa e comercializavel.

Inclui:

- autenticacao com duas etapas;
- emissao de token JWT;
- upload e leitura segura de Excel/CSV no servidor;
- base SQLite persistente com isolamento por empresa;
- snapshots historicos para comparacao diaria, semanal, mensal, trimestral e anual;
- checkout de subscricao via Stripe;
- registo de auditoria;
- endpoint de saude em `/health`.
- OCR local de fotografias e PDFs digitalizados, sem envio dos documentos para fornecedores externos.

## Execucao local

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Na primeira leitura de uma fotografia ou PDF digitalizado, o RapidOCR carrega os modelos locais. O processamento seguinte reutiliza o mesmo motor em memória.

O limite de upload é 50 MB por defeito e pode ser ajustado sem alterar código:

```text
SEO_MAX_UPLOAD_MB=50
```

Os ficheiros são validados por extensão, tamanho e assinatura antes do processamento. Excel, PDF e OCR são executados fora do ciclo principal da API para não bloquear outros utilizadores.

Credenciais locais:

- email: `admin@seo.local`
- palavra-passe: `Seo-Admin-2026`

## Nuvem e historico

Por defeito a API usa `backend/storage/seo.sqlite3`. Em producao, aponte `SEO_DATABASE_PATH` para um volume persistente do fornecedor cloud:

```text
SEO_DATABASE_PATH=/data/seo/seo.sqlite3
```

Sempre que um ficheiro operacional e analisado, o sistema cria um snapshot diario. Tambem pode criar snapshots manualmente em `/reports/snapshots` para os periodos `daily`, `weekly`, `monthly`, `quarterly` e `annual`.

## Pagamentos

Configuracao minima para Stripe:

```text
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PROFESSIONAL=price_...
STRIPE_PRICE_BUSINESS=price_...
SEO_FRONTEND_URL=https://app.seo.pt
```

Antes de producao, usar `SEO_ENV=production`, substituir `SEO_JWT_SECRET`, definir uma palavra-passe admin forte, configurar SMTP real e manter `SEO_EXPOSE_DEV_MFA=0`.
