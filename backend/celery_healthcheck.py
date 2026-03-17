"""Minimal HTTP health check server for the Celery worker container.

Runs in a background thread alongside the worker process.
GET /health → 200 {"status": "ok"}
"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # silence access logs
        pass


def start(port: int = 9000) -> None:
    server = HTTPServer(("0.0.0.0", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
