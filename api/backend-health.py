import http.cookiejar
import json
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

TARGETS = [
    "https://sistemaeficienciaoperacional.duckdns.org/health",
    "https://sistemaeficienciaoperacional.duckdns.org/ready",
    "https://sistemaeficienciaoperacional.duckdns.org/",
]
LEGACY_HOST = "seo-svpauto-mayyrprie-arthurcruz12s-projects.vercel.app"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        if (query.get("mode") or [""])[0] == "legacy":
            return self._legacy(query)
        return self._health()

    def _legacy(self, query):
        token = (query.get("token") or [""])[0]
        asset_path = (query.get("path") or ["/"])[0]
        if not token or not asset_path.startswith("/"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"missing token or invalid path")
            return

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        try:
            auth_url = f"https://{LEGACY_HOST}/?_vercel_share={urllib.parse.quote(token)}"
            opener.open(auth_url, timeout=15).read(64)
            target = f"https://{LEGACY_HOST}{asset_path}"
            with opener.open(target, timeout=20) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = f"{type(exc).__name__}: {exc}".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

    def _health(self):
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
