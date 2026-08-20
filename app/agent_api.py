from __future__ import annotations

import os
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations import infrastructure_status
from app.main import get_current_user, write_audit_log
from app.models import User
from app.security import require_permission

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def _configured(*names: str) -> bool:
    return any(bool(os.getenv(name)) for name in names)


AGENTS = [
    {
        "id": "manager",
        "name": "SEO Agent Manager",
        "role": "orchestrator",
        "capabilities": ["intent-routing", "task-planning", "agent-selection", "approval-routing", "result-consolidation"],
        "write_access": False,
    },
    {
        "id": "billing",
        "name": "Agente de Faturação",
        "role": "specialist",
        "capabilities": ["FR", "FT", "NC", "POFI", "Coimbra/Picoto", "Novo/Usado", "Sucatas/Salvados", "NC liquidado/pendente", "resumo vendedores", "mapa diário"],
        "write_access": False,
    },
    {
        "id": "documents",
        "name": "Agente de Documentos",
        "role": "specialist",
        "capabilities": ["Excel", "CSV", "PDF", "OCR/IDP", "classificação", "normalização", "validação"],
        "write_access": False,
    },
    {
        "id": "saft",
        "name": "Agente SAF-T",
        "role": "specialist",
        "capabilities": ["importação", "SHA-256", "staging", "anomalias", "normalização"],
        "write_access": False,
    },
    {
        "id": "accounting",
        "name": "Agente Contabilístico",
        "role": "specialist",
        "capabilities": ["SNC", "débito/crédito", "IVA", "centros de custo", "reconciliação", "propostas contabilísticas"],
        "write_access": False,
    },
    {
        "id": "snc",
        "name": "Agente SNC",
        "role": "specialist",
        "capabilities": ["READ", "PREPARE", "VALIDATE", "WRITE"],
        "write_access": _flag("AGENT_EXECUTION_ENABLED") and _flag("SNC_INTEGRATION_ENABLED"),
    },
    {
        "id": "audit",
        "name": "Agente Auditor",
        "role": "control",
        "capabilities": ["cálculos", "duplicados", "permissões", "políticas", "risco", "aprovação/revisão/bloqueio"],
        "write_access": False,
    },
    {
        "id": "code",
        "name": "Agente de Código",
        "role": "specialist",
        "capabilities": ["Codex", "GitHub", "testes", "CI/CD", "diagnóstico", "patches"],
        "write_access": False,
    },
    {
        "id": "executor",
        "name": "Agente Executor",
        "role": "executor",
        "capabilities": ["operações autorizadas", "idempotência", "confirmação", "auditoria"],
        "write_access": _flag("AGENT_EXECUTION_ENABLED"),
    },
]


class RouteRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    mode: str = Field(default="chat", pattern="^(chat|work|code|integrations)$")
    company_id: int | None = None


def _route(message: str, mode: str) -> dict:
    text = message.casefold()
    selected = ["manager"]
    reasons: list[str] = []

    if mode == "code" or any(word in text for word in ("código", "codigo", "github", "codex", "bug", "erro de build", "deploy", "vercel", "teste")):
        selected.append("code")
        reasons.append("Tarefa técnica ou de engenharia de software.")

    if any(word in text for word in ("saft", "saf-t", "xml")):
        selected.extend(["saft", "documents", "audit"])
        reasons.append("Pedido relacionado com SAF-T/documentos requer staging e validação.")

    if any(word in text for word in ("faturação", "faturacao", "fatura", "fr ", "ft ", "nota de crédito", "nota de credito", "nc ", "coimbra", "picoto", "sucata", "salvado", "vendedor", "mapa diário", "mapa diario")):
        selected.extend(["billing", "documents", "audit"])
        reasons.append("Pedido de faturação ou mapa operacional.")

    accounting_terms = ("snc", "contabil", "contábil", "débito", "debito", "crédito", "credito", "iva", "lançamento", "lancamento")
    if any(word in text for word in accounting_terms):
        selected.extend(["accounting", "audit"])
        reasons.append("Pedido contabilístico requer preparação e auditoria.")
        if "snc" in text or "lançamento" in text or "lancamento" in text:
            selected.append("snc")

    if mode == "integrations" or any(word in text for word in ("integração", "integracao", "api", "mcp", "atena", "neon", "upstash", "qstash", "sentry", "checkly")):
        reasons.append("Pedido relacionado com integrações e ferramentas externas.")

    if len(selected) == 1:
        selected.append("documents" if any(word in text for word in ("ficheiro", "arquivo", "excel", "pdf", "csv")) else "audit")

    selected = list(dict.fromkeys(selected))
    write_terms = ("executar", "lançar", "lancar", "gravar", "alterar", "apagar", "eliminar", "write", "enviar para o snc")
    wants_write = any(word in text for word in write_terms)
    approval_required = wants_write and any(agent in selected for agent in ("snc", "executor", "accounting"))
    execution_enabled = _flag("AGENT_EXECUTION_ENABLED")

    return {
        "agents": selected,
        "reasons": reasons or ["Roteamento geral pelo Agent Manager."],
        "approval_required": approval_required,
        "execution_enabled": execution_enabled,
        "write_blocked": approval_required and not execution_enabled,
    }


def _integration_catalog() -> list[dict]:
    infra = infrastructure_status()
    return [
        {"id": "atena", "name": "Atena", "category": "Sistemas empresariais", "configured": _configured("ATENA_API_URL", "ATENA_BASE_URL"), "status": "CONFIGURADO" if _configured("ATENA_API_URL", "ATENA_BASE_URL") else "NÃO CONFIGURADO", "permissions": ["READ"], "agents": ["manager", "billing", "documents"], "note": "Fonte confiável de informação; separado do SNC."},
        {"id": "snc", "name": "SNC", "category": "Sistemas empresariais", "configured": _flag("SNC_INTEGRATION_ENABLED"), "status": "CONFIGURADO" if _flag("SNC_INTEGRATION_ENABLED") else "NÃO CONFIGURADO", "permissions": ["READ", "PREPARE", "VALIDATE"] + (["WRITE"] if _flag("AGENT_EXECUTION_ENABLED") else []), "agents": ["accounting", "snc", "audit", "executor"], "approval_required": True},
        {"id": "saft", "name": "SAF-T", "category": "Sistemas empresariais", "configured": _flag("SAFT_INTEGRATION_ENABLED"), "status": "CONFIGURADO" if _flag("SAFT_INTEGRATION_ENABLED") else "DESATIVADO", "permissions": ["READ", "STAGE", "VALIDATE"], "agents": ["saft", "documents", "audit"], "note": "Fonte externa imutável; sem escrita direta em documentos financeiros."},
        {"id": "neon", "name": "Neon", "category": "Infraestrutura", "configured": bool(infra.get("neon", {}).get("configured")), "status": "CONFIGURADO" if infra.get("neon", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["manager", "saft"]},
        {"id": "redis", "name": "Upstash Redis", "category": "Infraestrutura", "configured": bool(infra.get("redis", {}).get("configured")), "status": "CONFIGURADO" if infra.get("redis", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["manager"]},
        {"id": "vector", "name": "Upstash Vector", "category": "Infraestrutura", "configured": bool(infra.get("vector", {}).get("configured")), "status": "CONFIGURADO" if infra.get("vector", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["manager", "audit"], "feature_flag": "AGENT_MEMORY_ENABLED"},
        {"id": "search", "name": "Upstash Search", "category": "Infraestrutura", "configured": bool(infra.get("search", {}).get("configured")), "status": "CONFIGURADO" if infra.get("search", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["manager", "documents"]},
        {"id": "qstash", "name": "QStash", "category": "Infraestrutura", "configured": bool(infra.get("qstash", {}).get("configured")), "status": "CONFIGURADO" if infra.get("qstash", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["manager", "executor"]},
        {"id": "sentry", "name": "Sentry", "category": "Observabilidade", "configured": bool(infra.get("sentry", {}).get("configured")), "status": "CONFIGURADO" if infra.get("sentry", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["code"]},
        {"id": "checkly", "name": "Checkly", "category": "Observabilidade", "configured": bool(infra.get("checkly", {}).get("configured")), "status": "CONFIGURADO" if infra.get("checkly", {}).get("configured") else "NÃO CONFIGURADO", "agents": ["code"]},
        {"id": "openai", "name": "OpenAI", "category": "IA / Desenvolvimento", "configured": _configured("OPENAI_API_KEY"), "status": "CONFIGURADO" if _configured("OPENAI_API_KEY") else "NÃO CONFIGURADO", "agents": ["manager", "code", "documents", "accounting"]},
        {"id": "github", "name": "GitHub", "category": "IA / Desenvolvimento", "configured": _configured("GITHUB_TOKEN", "GITHUB_APP_ID") or _flag("GITHUB_INTEGRATION_ENABLED"), "status": "CONFIGURADO" if (_configured("GITHUB_TOKEN", "GITHUB_APP_ID") or _flag("GITHUB_INTEGRATION_ENABLED")) else "GERIDO EXTERNAMENTE", "agents": ["code"]},
        {"id": "codex", "name": "Codex", "category": "IA / Desenvolvimento", "configured": _configured("OPENAI_API_KEY") or _flag("CODEX_INTEGRATION_ENABLED"), "status": "DISPONÍVEL" if (_configured("OPENAI_API_KEY") or _flag("CODEX_INTEGRATION_ENABLED")) else "NÃO CONFIGURADO", "agents": ["code"]},
    ]


@router.get("/status")
def agent_status(current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    return {
        "enabled": _flag("AGENT_MANAGER_ENABLED", default=True),
        "manager": "SEO Agent Manager",
        "execution_enabled": _flag("AGENT_EXECUTION_ENABLED"),
        "memory_enabled": _flag("AGENT_MEMORY_ENABLED"),
        "snc_enabled": _flag("SNC_INTEGRATION_ENABLED"),
        "saft_enabled": _flag("SAFT_INTEGRATION_ENABLED"),
        "write_policy": "human_approval_required",
        "assistant_tabs": ["Chat", "Trabalho", "Código", "Integrações"],
    }


@router.get("/registry")
def agent_registry(current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    return {"agents": AGENTS}


@router.get("/integrations")
def integrations(current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    return {"integrations": _integration_catalog(), "secrets_exposed": False}


@router.post("/route")
def route_task(payload: RouteRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_permission(current_user, "dashboard:read")
    task_id = str(uuid4())
    plan = _route(payload.message, payload.mode)
    write_audit_log(
        db,
        current_user.tenant_id,
        "agent_task_routed",
        "agent_task",
        None,
        f"task_id={task_id}; user={current_user.email}; mode={payload.mode}; agents={','.join(plan['agents'])}; approval_required={plan['approval_required']}",
    )
    db.commit()
    return {
        "task_id": task_id,
        "manager": "SEO Agent Manager",
        "mode": payload.mode,
        **plan,
        "policy": {
            "homepage_preserved": True,
            "authentication_preserved": True,
            "admin_credentials_unchanged": True,
            "human_approval_for_sensitive_writes": True,
        },
    }
