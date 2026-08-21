from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

BACKEND_BASE = os.getenv("SEO_BACKEND_URL", "https://sistemaeficienciaoperacional.duckdns.org").rstrip("/")
VALID_DECISIONS = {"approve", "reject", "request_change"}


class handler(BaseHTTPRequestHandler):
    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _bearer(self):
        value = self.headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            return None
        return value[7:].strip() or None

    def _validate(self, token: str) -> bool:
        req = urllib.request.Request(
            f"{BACKEND_BASE}/dashboard/state",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "seo-agent-approval/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return 200 <= response.status < 300
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False
            raise

    def _audit(self, token: str, task_id: str, decision: str, note: str) -> bool:
        safe_note = " ".join(note.replace("\n", " ").split())[:300]
        details = f"task_id={task_id}; decision={decision}; note={safe_note or 'none'}; executed=false"
        payload = json.dumps({
            "actor": "SEO Human Approval",
            "action": f"AGENT_APPROVAL_{decision.upper()}",
            "details": details,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_BASE}/audit/events",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "seo-agent-approval/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return 200 <= response.status < 300
        except Exception:
            return False

    def do_POST(self):
        token = self._bearer()
        if not token:
            return self._json({"detail": "Authentication required"}, 401)
        try:
            if not self._validate(token):
                return self._json({"detail": "Invalid or expired session"}, 401)
        except Exception:
            return self._json({"detail": "Não foi possível validar a sessão atual."}, 503)

        try:
            length = min(int(self.headers.get("Content-Length", "0")), 4000)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"detail": "Invalid JSON payload"}, 400)

        task_id = str(payload.get("task_id") or "").strip()
        decision = str(payload.get("decision") or "").strip()
        note = str(payload.get("note") or "").strip()
        if not task_id or len(task_id) > 100 or decision not in VALID_DECISIONS:
            return self._json({"detail": "Invalid approval decision"}, 422)

        persisted = self._audit(token, task_id, decision, note)
        if decision == "approve":
            state = "APPROVED_EXECUTION_DISABLED" if os.getenv("AGENT_EXECUTION_ENABLED", "false").lower() not in {"1", "true", "yes", "on"} else "APPROVED_PENDING_EXECUTOR"
        elif decision == "reject":
            state = "REJECTED"
        else:
            state = "REVISION_REQUESTED"

        return self._json({
            "task_id": task_id,
            "decision": decision,
            "state": state,
            "audit_persisted": persisted,
            "executed": False,
            "message": "Decisão registada. Nenhuma ação foi executada automaticamente.",
        })
