"""Serveur HTTP sans framework. L'index est calculé une seule fois au démarrage."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from engine import Atlas, ROOT

ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8")}


def make_handler(atlas: Atlas):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, value, status=200, mime="application/json; charset=utf-8"):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store" if mime.startswith("application/json") else "public, max-age=3600")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlsplit(self.path)
            args = parse_qs(route.query)
            first = lambda key, default="": args.get(key, [default])[0]
            try:
                if route.path in ASSETS:
                    filename, mime = ASSETS[route.path]
                    return self.reply((ROOT / "web" / filename).read_bytes(), mime=mime)
                if route.path == "/api/overview":
                    return self.reply(atlas.overview())
                if route.path == "/api/map":
                    return self.reply({"points": atlas.points})
                if route.path == "/api/search":
                    year = int(first("year")) if first("year") else None
                    cluster = int(first("cluster")) if first("cluster") else None
                    return self.reply(atlas.search(first("q"), first("researcher"), year, cluster, first("limit", "30")))
                if route.path == "/api/paper":
                    paper = atlas.by_id.get(first("id"))
                    return self.reply(paper if paper else {"error": "Publication introuvable"}, 200 if paper else 404)
                return self.reply({"error": "Page introuvable"}, 404)
            except (ValueError, TypeError) as exc:
                return self.reply({"error": f"Paramètre invalide : {exc}"}, 400)

    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atlas des publications scientifiques FSBM")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "fsbm_dataset.json")
    opts = parser.parse_args()
    print("Construction de l'index sémantique…", flush=True)
    atlas = Atlas(opts.data)
    server = ThreadingHTTPServer((opts.host, opts.port), make_handler(atlas))
    print(f"{len(atlas.papers)} publications disponibles : http://{opts.host}:{opts.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
