import json
import urllib.request
from http.server import BaseHTTPRequestHandler

TARGETS = [
    "https://sistemaeficienciaoperacional.duckdns.org/health",
    "https://sistemaeficienciaoperacional.duckdns.org/ready",
    "https://sistemaeficienciaoperacional.duckdns.org/",
]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        results = []
        for url in TARGETS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "seo-vercel-diagnostic/1.0"})
                with urllib.request.urlopen(req, timeout=8) as response:
                    body = response.read(500).decode("utf-8", errors="replace")
                    results.append({"url": url, "status": response.status, "body": body})
            except Exception as exc:
                results.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

        payload = json.dumps({"results": results}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
