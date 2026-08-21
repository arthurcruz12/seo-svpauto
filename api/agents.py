from __future__ import annotations

import json
import os
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from uuid import uuid4

BACKEND_BASE = os.getenv("SEO_BACKEND_URL", "https://sistemaeficienciaoperacional.duckdns.org").rstrip("/")


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def _configured(*names: str) -> bool:
    return any(bool(os.getenv(name)) for name in names)


def _normalize(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )


def _route(message: str, mode: str) -> dict:
    normalized = _normalize(message)
    selected = ["manager"]
    reasons: list[str] = []

    if mode == "code" or any(term in normalized for term in ("codigo", "github", "codex", "bug", "build", "deploy", "vercel", "teste")):
        selected.append("code")
        reasons.append("Tarefa técnica encaminhada ao Agente de Código.")

    if any(term in normalized for term in ("saft", "saf-t", "xml")):
        selected.extend(["saft", "documents", "audit"])
        reasons.append("SAF-T/documentos exigem staging e auditoria.")

    if any(term in normalized for term in ("faturacao", "fatura", "fr ", "ft ", "nota de credito", "nc ", "coimbra", "picoto", "sucata", "salvado", "vendedor", "mapa diario")):
        selected.extend(["billing", "documents", "audit"])
        reasons.append("Pedido operacional de faturação encaminhado ao Agente de Faturação.")

    if any(term in normalized for term in ("snc", "contabil", "debito", "credito", "iva", "lancamento")):
        selected.extend(["accounting", "audit"])
        reasons.append("Pedido contabilístico requer preparação e auditoria.")
        if "snc" in normalized or "lancamento" in normalized:
            selected.append("snc")

    if mode == "integrations" or any(term in normalized for term in ("integracao", "api", "mcp", "atena", "neon", "upstash", "qstash", "sentry", "checkly")):
        reasons.append("Pedido relacionado com integrações/ferramentas externas.")

    if len(selected) == 1:
        selected.append("documents" if any(term in normalized for term in ("ficheiro", "arquivo", "excel", "pdf", "csv")) else "audit")

    selected = list(dict.fromkeys(selected))
    write_stems = ("execut", "lanc", "grav", "alter", "apag", "elimin", "regist")
    explicit_write = ("write", "enviar para o snc", "envie para o snc")
    wants_write = any(stem in normalized for stem in write_stems) or any(phrase in normalized for phrase in explicit_write)
    approval_required = wants_write and any(agent in selected for agent in ("snc", "accounting", "executor"))
    execution_enabled = _flag("AGENT_EXECUTION_ENABLED")

    return {
        "agents": selected,
        "reasons": reasons or ["Roteamento geral pelo SEO Agent Manager."],
        "approval_required": approval_required,
        "execution_enabled": execution_enabled,
        "write_blocked": approval_required and not execution_enabled,
    }


def _agent_registry() -> list[dict]:
    return [
        {"id": "manager", "name": "SEO Agent Manager", "role": "orchestrator", "write_access": False},
        {"id": "billing", "name": "Agente de Faturação", "role": "specialist", "write_access": False},
        {"id": "documents", "name": "Agente de Documentos", "role": "specialist", "write_access": False},
        {"id": "saft", "name": "Agente SAF-T", "role": "specialist", "write_access": False},
        {"id": "accounting", "name": "Agente Contabilístico", "role": "specialist", "write_access": False},
        {"id": "snc", "name": "Agente SNC", "role": "specialist", "write_access": _flag("SNC_INTEGRATION_ENABLED") and _flag("AGENT_EXECUTION_ENABLED")},
        {"id": "audit", "name": "Agente Auditor", "role": "control", "write_access": False},
        {"id": "code", "name": "Agente de Código", "role": "specialist", "write_access": False},
        {"id": "executor", "name": "Agente Executor", "role": "executor", "write_access": _flag("AGENT_EXECUTION_ENABLED")},
    ]


def _integration_catalog() -> list[dict]:
    def item(item_id: str, name: str, category: str, configured: bool, agents: list[str], **extra):
        return {
            "id": item_id,
            "name": name,
            "category": category,
            "configured": configured,
            "status": "CONFIGURADO" if configured else extra.pop("empty_status", "NÃO CONFIGURADO"),
            "agents": agents,
            **extra,
        }

    return [
        item("atena", "Atena", "Sistemas empresariais", _configured("ATENA_API_URL", "ATENA_BASE_URL"), ["manager", "billing", "documents"], permissions=["READ"], note="Fonte confiável de informação; separado do SNC."),
        item("snc", "SNC", "Sistemas empresariais", _flag("SNC_INTEGRATION_ENABLED"), ["accounting", "snc", "audit", "executor"], permissions=["READ", "PREPARE", "VALIDATE"] + (["WRITE"] if _flag("AGENT_EXECUTION_ENABLED") else []), approval_required=True),
        item("saft", "SAF-T", "Sistemas empresariais", _flag("SAFT_INTEGRATION_ENABLED"), ["saft", "documents", "audit"], permissions=["READ", "STAGE", "VALIDATE"], note="Fonte externa imutável; sem escrita direta em documentos financeiros.", empty_status="DESATIVADO"),
        item("neon", "Neon", "Infraestrutura", _configured("POSTGRES_URL", "AI_DATABASE_URL"), ["manager", "saft"]),
        item("redis", "Upstash Redis", "Infraestrutura", _configured("REDIS_URL", "KV_REST_API_URL"), ["manager"]),
        item("vector", "Upstash Vector", "Infraestrutura", _configured("UPSTASH_VECTOR_REST_URL", "UPSTASH_VECTOR_REST_TOKEN"), ["manager", "audit"]),
        item("search", "Upstash Search", "Infraestrutura", _configured("UPSTASH_SEARCH_REST_URL", "UPSTASH_SEARCH_REST_TOKEN"), ["manager", "documents"]),
        item("qstash", "QStash", "Infraestrutura", _configured("upseo_QSTASH_URL", "QSTASH_URL"), ["manager", "executor"]),
        item("sentry", "Sentry", "Observabilidade", _configured("SENTRY_DSN"), ["code"]),
        item("checkly", "Checkly", "Observabilidade", _configured("CHECKLY_ACCOUNT_ID"), ["code"]),
        item("openai", "OpenAI", "IA / Desenvolvimento", _configured("OPENAI_API_KEY"), ["manager", "code", "documents", "accounting"]),
        item("github", "GitHub", "IA / Desenvolvimento", _configured("GITHUB_TOKEN", "GITHUB_APP_ID"), ["code"], empty_status="GERIDO EXTERNAMENTE"),
        item("codex", "Codex", "IA / Desenvolvimento", _configured("OPENAI_API_KEY") or _flag("CODEX_INTEGRATION_ENABLED"), ["code"]),
    ]


class handler(BaseHTTPRequestHandler):
    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _bearer(self) -> str | None:
        value = self.headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            return None
        token = value[7:].strip()
        return token or None

    def _validate_current_session(self, token: str) -> bool:
        req = urllib.request.Request(
            f"{BACKEND_BASE}/dashboard/state",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "seo-agent-manager/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return 200 <= response.status < 300
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False
            raise

    def _audit(self, token: str, task_id: str, mode: str, plan: dict) -> bool:
        details = f"task_id={task_id}; mode={mode}; agents={','.join(plan['agents'])}; approval_required={plan['approval_required']}; write_blocked={plan['write_blocked']}"
        payload = json.dumps({"actor": "SEO Agent Manager", "action": "AGENT_TASK_ROUTED", "details": details}).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_BASE}/audit/events",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "seo-agent-manager/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return 200 <= response.status < 300
        except Exception:
            return False

    def _authorize(self) -> str | None:
        token = self._bearer()
        if not token:
            self._json({"detail": "Authentication required"}, 401)
            return None
        try:
            valid = self._validate_current_session(token)
        except Exception:
            self._json({"detail": "Não foi possível validar a sessão atual."}, 503)
            return None
        if not valid:
            self._json({"detail": "Invalid or expired session"}, 401)
            return None
        return token

    def do_GET(self):
        token = self._authorize()
        if not token:
            return
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        op = (query.get("op") or ["status"])[0]

        if op == "status":
            return self._json({
                "enabled": _flag("AGENT_MANAGER_ENABLED", default=True),
                "manager": "SEO Agent Manager",
                "execution_enabled": _flag("AGENT_EXECUTION_ENABLED"),
                "memory_enabled": _flag("AGENT_MEMORY_ENABLED"),
                "snc_enabled": _flag("SNC_INTEGRATION_ENABLED"),
                "saft_enabled": _flag("SAFT_INTEGRATION_ENABLED"),
                "write_policy": "human_approval_required",
                "assistant_tabs": ["Chat", "Trabalho", "Código", "Integrações"],
                "auth_source": "existing_seo_session",
            })
        if op == "registry":
            return self._json({"agents": _agent_registry()})
        if op == "integrations":
            return self._json({"integrations": _integration_catalog(), "secrets_exposed": False})
        return self._json({"detail": "Unknown operation"}, 404)

    def do_POST(self):
        token = self._authorize()
        if not token:
            return
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        op = (query.get("op") or ["route"])[0]
        if op != "route":
            return self._json({"detail": "Unknown operation"}, 404)

        try:
            length = min(int(self.headers.get("Content-Length", "0")), 10000)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"detail": "Invalid JSON payload"}, 400)

        message = str(payload.get("message") or "").strip()
        mode = str(payload.get("mode") or "chat").strip()
        if not message or len(message) > 8000 or mode not in {"chat", "work", "code", "integrations"}:
            return self._json({"detail": "Invalid agent task"}, 422)

        task_id = str(uuid4())
        plan = _route(message, mode)
        audit_persisted = self._audit(token, task_id, mode, plan)
        return self._json({
            "task_id": task_id,
            "manager": "SEO Agent Manager",
            "mode": mode,
            **plan,
            "audit_persisted": audit_persisted,
            "policy": {
                "homepage_preserved": True,
                "authentication_preserved": True,
                "admin_credentials_unchanged": True,
                "human_approval_for_sensitive_writes": True,
            },
        })
