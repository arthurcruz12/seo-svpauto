import base64
import json
import os
import re
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
        mode = (query.get("mode") or [""])[0]
        if mode.startswith("legacy"):
            return self._legacy(query, mode)
        return self._health()

    def _fetch_legacy(self, asset_path):
        bypass = os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET")
        headers = {"User-Agent": "seo-legacy-recovery/1.0"}
        if bypass:
            headers["x-vercel-protection-bypass"] = bypass
        target = f"https://{LEGACY_HOST}{asset_path}"
        req = urllib.request.Request(target, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read(), response.headers.get("Content-Type", "application/octet-stream"), bool(bypass)

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _legacy(self, query, mode):
        asset_path = (query.get("path") or ["/"])[0]
        if not asset_path.startswith("/"):
            return self._json({"error": "invalid path"}, 400)
        try:
            body, content_type, bypass_available = self._fetch_legacy(asset_path)

            if mode == "legacy-meta":
                text = body.decode("utf-8", errors="replace")
                assets = sorted(set(re.findall(r'(?:src|href)=[\"\']([^\"\']+)[\"\']', text)))
                return self._json({"path": asset_path, "length": len(body), "assets": assets, "bypass_available": bypass_available})

            if mode == "legacy-search":
                needle = (query.get("needle") or [""])[0]
                if not needle:
                    return self._json({"error": "missing needle"}, 400)
                text = body.decode("utf-8", errors="replace")
                matches = []
                start = 0
                while len(matches) < 20:
                    pos = text.lower().find(needle.lower(), start)
                    if pos < 0:
                        break
                    lo, hi = max(0, pos - 450), min(len(text), pos + len(needle) + 450)
                    matches.append({"position": pos, "snippet": text[lo:hi]})
                    start = pos + max(1, len(needle))
                return self._json({"path": asset_path, "length": len(body), "needle": needle, "matches": matches, "bypass_available": bypass_available})

            if mode == "legacy-chunk":
                offset = max(0, int((query.get("offset") or ["0"])[0]))
                length = min(200000, max(1, int((query.get("length") or ["50000"])[0])))
                chunk = body[offset:offset + length]
                return self._json({
                    "path": asset_path,
                    "content_type": content_type,
                    "total_length": len(body),
                    "offset": offset,
                    "length": len(chunk),
                    "data_base64": base64.b64encode(chunk).decode("ascii"),
                    "bypass_available": bypass_available,
                })

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            return self._json({
                "error": f"{type(exc).__name__}: {exc}",
                "bypass_available": bool(os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET")),
            }, 502)

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
        return self._json({"results": results, "vercel_automation_bypass_available": bool(os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET"))})
