# SEO — Sistema de Eficiência Operacional com IA

Backend MVP funcional para o aplicativo **SEO — Sistema de Eficiência Operacional**, um SaaS mobile/empresarial focado em automação contabilística, financeira e administrativa com IA.

## Objetivo

O SEO funciona como um AI Backoffice para empresas: interpreta documentos, classifica despesas, gera alertas, mantém logs de auditoria e prepara dados para controlo financeiro e contabilístico.

## Funcionalidades deste MVP

- API FastAPI funcional
- Registo de empresas
- Registo de documentos financeiros
- Simulação de OCR/extração de dados
- Classificação automática de despesas
- Dashboard financeiro básico
- Logs de auditoria
- Alertas operacionais
- Estrutura preparada para OCR real, IA e integrações bancárias

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite no MVP
- Pydantic
- Uvicorn

## Como correr localmente

```bash
python -m venv .venv
```

### Windows PowerShell

```bash
.venv\\Scripts\\Activate.ps1
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Iniciar a API

```bash
python -m uvicorn app.main:app --reload
```

## Endpoints principais

### Health check
GET /health

### Criar empresa
POST /companies

### Criar documento financeiro
POST /documents

### Processar documento
POST /documents/{id}/process

### Dashboard
GET /dashboard/{company_id}

### Logs
GET /audit-logs

## Compliance

Toda automação deve ser:

- rastreável
- auditável
- reversível
- documentada
- compatível com auditorias

## Roadmap

- OCR real
- IA financeira
- Integrações bancárias
- Dashboard mobile
- Compliance engine
- Chat IA empresarial
