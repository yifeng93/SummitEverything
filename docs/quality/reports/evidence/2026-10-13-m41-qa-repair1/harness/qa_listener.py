from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

mode = sys.argv[1]
log_path = Path(sys.argv[2])

class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(self.path + "\n")
        if mode == "wrong-identity" and self.path == "/api/v1/health":
            body = json.dumps({
                "service": "ready", "run_id": "not-the-app-run",
                "source_sha": "0000000000000000000000000000000000000000",
                "dirty": False, "build_id": "synthetic-wrong-build",
                "app_version": "0.1.0", "frontend_sha256": "wrong",
                "dependencies_sha256": "wrong",
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = b"synthetic unrelated loopback server\n"
        self.send_response(200 if self.path == "/" else 404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return

server = ThreadingHTTPServer(("127.0.0.1", 18793), Handler)
server.serve_forever()
