from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

from app.billing_contract import BILLING_AGENT_CONTRACT, validate_billing_delivery

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
        })

    def do_POST(self):
        if not self._authorize():
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 20000)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._json({"detail": "Invalid JSON payload"}, 400)

        sheet_names = payload.get("sheet_names") or []
        checks = payload.get("checks") or {}
        if not isinstance(sheet_names, list) or not isinstance(checks, dict):
            return self._json({"detail": "Invalid billing delivery manifest"}, 422)

        result = validate_billing_delivery(sheet_names, checks)
        http_status = 200 if result["valid"] else 422
        return self._json({
            **result,
            "mandatory": True,
            "message": (
                "Faturação aprovada pelo contrato obrigatório."
                if result["valid"]
                else "Faturação rejeitada: a tarefa não pode ser marcada como concluída."
            ),
        }, http_status)
