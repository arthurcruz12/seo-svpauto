from __future__ import annotations

import base64
import cgi
import hashlib
import json
import os
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from uuid import uuid4

from app.agents.manager import AgentManager

BACKEND_BASE = os.getenv("SEO_BACKEND_URL", "https://sistemaeficienciaoperacional.duckdns.org").rstrip("/")
MAX_UPLOAD_BYTES = int(os.getenv("SEO_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MANAGER = AgentManager()

# Preview-only fallback. Durable task/artifact persistence belongs to
# app.assistant_api in the FastAPI backend. This cache is deliberately scoped
# by bearer-token fingerprint and may disappear when a serverless instance is
# recycled; it exists only so a Preview can exercise the real agent chain
# before the external backend is promoted.
_TASKS: dict[str, list[dict]] = defaultdict(list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _safe_filename(name: str | None) -> str:
    value = (name or "faturacao.xlsx").replace("\\", "/").split("/")[-1].strip()
    if not value:
        return "faturacao.xlsx"
    return value[:180]


def _preview_only() -> bool:
    return os.getenv("VERCEL_ENV", "development").lower() != "production"


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
        return value[7:].strip() or None

    def _validate_session(self, token: str) -> bool:
        request = urllib.request.Request(
            f"{BACKEND_BASE}/dashboard/state",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "seo-preview-assistant/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                return 200 <= response.status < 300
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False
            raise

    def _authorize(self) -> str | None:
        token = self._bearer()
        if not token:
            self._json({"detail": "Authentication required"}, 401)
            return None
        try:
            if not self._validate_session(token):
                self._json({"detail": "Invalid or expired session"}, 401)
                return None
        except Exception:
            self._json({"detail": "Não foi possível validar a sessão atual."}, 503)
            return None
        return token

    def _audit(self, token: str, task_id: str, status: str, source_sha256: str, output_sha256: str | None) -> bool:
        payload = json.dumps({
            "actor": "SEO Preview Agent Manager",
            "action": "AGENT_BILLING_PREVIEW_EXECUTED",
            "details": f"task_id={task_id}; status={status}; source_sha256={source_sha256}; output_sha256={output_sha256 or 'none'}; durable_storage=false",
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{BACKEND_BASE}/audit/events",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "seo-preview-assistant/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                return 200 <= response.status < 300
        except Exception:
            return False

    def _parse_upload(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            raise ValueError("Empty request body")
        if length > MAX_UPLOAD_BYTES + (1024 * 1024):
            raise OverflowError("Billing workbook exceeds upload limit")
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise TypeError("multipart/form-data required")

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": str(length),
            },
            keep_blank_values=True,
        )
        message = str(form.getfirst("message", "")).strip()
        if "file" not in form:
            raise ValueError("Billing source file required")
        file_item = form["file"]
        if isinstance(file_item, list):
            file_item = file_item[0]
        filename = _safe_filename(getattr(file_item, "filename", None))
        if not filename.lower().endswith((".xlsx", ".xlsm")):
            raise TypeError("Billing source must be XLSX/XLSM")
        content = file_item.file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise OverflowError("Billing workbook exceeds upload limit")
        if not content:
            raise ValueError("Billing source file is empty")
        return message, filename, content

    def do_GET(self):
        if not _preview_only():
            return self._json({"detail": "Not Found"}, 404)
        token = self._authorize()
        if not token:
            return
        if "op=tasks" not in self.path:
            return self._json({"detail": "Unknown operation"}, 404)
        tasks = _TASKS.get(_session_key(token), [])[:20]
        return self._json({
            "tasks": tasks,
            "persistence": "ephemeral_preview",
            "durable_backend_required_for_production": True,
        })

    def do_POST(self):
        if not _preview_only():
            return self._json({"detail": "Not Found"}, 404)
        token = self._authorize()
        if not token:
            return
        if "op=execute" not in self.path:
            return self._json({"detail": "Unknown operation"}, 404)

        try:
            message, filename, content = self._parse_upload()
        except OverflowError as exc:
            return self._json({"detail": str(exc)}, 413)
        except TypeError as exc:
            return self._json({"detail": str(exc)}, 415)
        except ValueError as exc:
            return self._json({"detail": str(exc)}, 422)
        except Exception:
            return self._json({"detail": "Invalid upload payload"}, 400)

        if not any(term in message.casefold() for term in ("fatur", "mapa diário", "mapa diario")):
            return self._json({
                "answer": "O executor Preview está limitado à faturação diária nesta fase.",
                "task_id": None,
                "status": "NEEDS_REVIEW",
                "agents_used": ["SEO Agent Manager"],
                "artifacts": [],
                "audit": None,
                "confidence": 0.0,
                "errors": ["unsupported_execution_intent"],
                "preview_bridge": True,
            })

        started_at = _now()
        try:
            result = MANAGER.execute_billing(content, filename)
        except ValueError as exc:
            return self._json({
                "answer": "Não foi possível processar o Excel de faturação.",
                "task_id": None,
                "status": "FAILED",
                "agents_used": ["SEO Agent Manager", "DocumentAgent"],
                "artifacts": [],
                "audit": None,
                "confidence": 0.0,
                "errors": [str(exc)],
                "preview_bridge": True,
            })

        artifacts: list[dict] = []
        if result.get("output_content") and result.get("status") == "COMPLETED":
            output_content = result["output_content"]
            artifacts.append({
                "file_id": str(uuid4()),
                "filename": result["output_filename"],
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "size": len(output_content),
                "sha256": result["output_sha256"],
                "inline_base64": base64.b64encode(output_content).decode("ascii"),
            })

        task = {
            "task_id": result["task_id"],
            "agent": "billing",
            "created_at": started_at,
            "started_at": started_at,
            "finished_at": _now(),
            "status": result["status"],
            "progress": 100,
            "source_file": {"filename": filename, "size": len(content)},
            "output_files": artifacts,
            "errors": result["errors"],
            "audit": result["audit"],
            "agents_used": result["agents_used"],
            "records_processed": result["records_processed"],
            "records_rejected": result["records_rejected"],
            "preview_bridge": True,
            "durable_storage": False,
        }
        key = _session_key(token)
        _TASKS[key].insert(0, task)
        del _TASKS[key][20:]

        audit_persisted = self._audit(
            token,
            result["task_id"],
            result["status"],
            result["source_sha256"],
            result.get("output_sha256"),
        )

        return self._json({
            "answer": (
                "Faturação concluída e auditada no Preview. O Excel pode ser descarregado agora."
                if result["status"] == "COMPLETED"
                else "A faturação foi processada, mas o auditor rejeitou o resultado."
            ),
            "task_id": result["task_id"],
            "status": result["status"],
            "agents_used": result["agents_used"],
            "artifacts": artifacts,
            "audit": result["audit"],
            "confidence": result["confidence"],
            "errors": result["errors"],
            "preview_bridge": True,
            "persistence": "ephemeral_preview",
            "audit_persisted": audit_persisted,
        })
