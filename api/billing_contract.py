from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

from app.billing_contract import BILLING_AGENT_CONTRACT

BACKEND_BASE = os.getenv("SEO_BACKEND_URL", "https://sistemaeficienciaoperacional.duckdns.org").rstrip("/")


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

    def _authorize(self):
        token = self._bearer()
        if not token:
            self._json({"detail": "Authentication required"}, 401)
            return None
        req = urllib.request.Request(
            f"{BACKEND_BASE}/dashboard/state",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "seo-billing-contract/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                if 200 <= response.status < 300:
                    return token
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                self._json({"detail": "Invalid or expired session"}, 401)
                return None
        except Exception:
            self._json({"detail": "Não foi possível validar a sessão atual."}, 503)
            return None
        self._json({"detail": "Authentication failed"}, 401)
        return None

    def do_GET(self):
        if not self._authorize():
            return
        return self._json({
            "mandatory": True,
            "contract": BILLING_AGENT_CONTRACT,
            "validation_source": "server_side_audit_agent",
        })

    def do_POST(self):
        if not self._authorize():
            return
        return self._json(
            {
                "status": "NEEDS_REVIEW",
                "deprecated": True,
                "detail": "Client-supplied audit booleans are not accepted. Execute billing through /api/v1/assistant/messages so AuditAgent inspects the generated workbook server-side.",
            },
            410,
        )
