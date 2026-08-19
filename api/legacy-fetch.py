import http.cookiejar
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

ALLOWED_HOST = "seo-svpauto-mayyrprie-arthurcruz12s-projects.vercel.app"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
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
            auth_url = f"https://{ALLOWED_HOST}/?_vercel_share={urllib.parse.quote(token)}"
            opener.open(auth_url, timeout=15).read(32)
            target = f"https://{ALLOWED_HOST}{asset_path}"
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
