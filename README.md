# SEO — Sistema de Eficiência Operacional com IA

Backend MVP funcional para o aplicativo **SEO — Sistema de Eficiência Operacional**, um SaaS mobile/empresarial focado em automação contabilística, financeira e administrativa com IA.

## Arquitetura oficial do backend

O backend oficial do projeto está exclusivamente na pasta:

```text
app/
```

O ponto de entrada oficial da API é:

```bash
app.main:app
```

Todas as importações internas devem usar:

```python
from app.nome_do_modulo import ...
```

A estrutura antiga `backend/app` foi descontinuada e não deve ser usada em CI, Docker, testes ou deploy.

## Objetivo

O SEO funciona como um AI Backoffice para empresas: interpreta documentos, classifica despesas, gera alertas, mantém logs de auditoria e prepara dados para controlo financeiro e contabilístico.

## Funcionalidades deste MVP

- API FastAPI funcional
- Registo de empresas
- Registo de documentos financeiros
- Classificação automática de despesas
- Dashboard financeiro básico
- Logs de auditoria
- Estrutura preparada para OCR real, IA e integrações bancárias

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite no MVP
- Pydantic
- Uvicorn
- Pytest
- Docker
- Alembic

## Como correr localmente

```bash
python -m venv .venv
```

### Windows PowerShell

```bash
.venv\Scripts\Activate.ps1
```

### Instalar dependências

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Iniciar a API

```bash
python -m uvicorn app.main:app --reload
```

### Executar testes

```bash
python -m pytest -q
```

### Docker

```bash
docker compose up --build
```

## Endpoints principais

### Health check
GET /health

### Criar empresa
POST /companies

### Criar documento financeiro
POST /documents

### Processar documento
POST /documents/{document_id}/process

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

- API versionada em `/api/v1`
- JWT Authentication
- OCR real
- IA financeira
- Integrações bancárias
- Dashboard mobile
- Compliance engine
- Chat IA empresarial
