"""Serveur web local uniquement, sans dependance externe."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from generator import generate, validate
import json
import re

ROOT = Path(__file__).parent
STATIC = {
    "/": (ROOT / "ui" / "index.html", "text/html; charset=utf-8"),
    "/css/app.css": (ROOT / "ui" / "css" / "app.css", "text/css; charset=utf-8"),
    "/js/app.js": (ROOT / "ui" / "js" / "app.js", "text/javascript; charset=utf-8"),
}
LOCAL_HOST = re.compile(r"^(?:127\.0\.0\.1|localhost)(?::[0-9]{1,5})?$")


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, content, media="text/plain; charset=utf-8", download=None):
        self.send_response(code)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; style-src 'self'; script-src 'self'; connect-src 'self'")
        if download:
            self.send_header("Content-Disposition", 'attachment; filename="' + download + '"')
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        resource = STATIC.get(self.path)
        if resource is None:
            return self.reply(404, b"Not found")
        path, media = resource
        self.reply(200, path.read_bytes(), media)

    def do_POST(self):
        if self.path != "/generate":
            return self.reply(404, b"Not found")
        try:
            if not LOCAL_HOST.fullmatch(self.headers.get("Host", "")):
                return self.reply(403, b"Hote interdit")
            media = self.headers.get_content_type()
            if media != "application/json":
                return self.reply(415, b"Content-Type application/json requis")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16384:
                raise ValueError("Taille de requete invalide")
            params = json.loads(self.rfile.read(size))
            config = validate(params)
            result = generate(config)
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            return self.reply(400, str(exc).encode("utf-8"))
        self.reply(200, result, "application/zip", config["name"] + ".zip")

if __name__ == "__main__":
    print("http://127.0.0.1:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
