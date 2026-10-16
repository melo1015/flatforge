"""Local web interface for FlatForge Maker.

Run from the repository root with:
    python -m flatforge_maker.server

The server deliberately binds to 127.0.0.1. Do not expose it to a network:
it has no TLS, user authentication, or production deployment hardening.
"""
from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from flatforge_worker.engines.nesting import nest_parts
from flatforge_maker.svg_export import render_cut_svg

PACKAGE_DIR = Path(__file__).resolve().parent
MAX_REQUEST_BYTES = 256 * 1024
HOST = "127.0.0.1"
PORT = 8787


class MakerHandler(BaseHTTPRequestHandler):
    server_version = "FlatForgeMaker/0.4"

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(200, {"ok": True, "service": "flatforge-maker", "version": "0.4"})
            return

        allowed_files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/style.css": "style.css",
            "/app.js": "app.js",
        }
        filename = allowed_files.get(path)
        if filename is None:
            self._send_json(404, {"error": "Not found"})
            return

        file_path = PACKAGE_DIR / filename
        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_json(500, {"error": "The Maker interface file could not be read"})
            return
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if content_type == "text/html" or content_type in {"text/css", "text/javascript"}:
            content_type += "; charset=utf-8"
        self._send_bytes(200, body, content_type)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path not in {"/api/nest", "/api/export.svg"}:
            self._send_json(404, {"error": "Not found"})
            return

        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header or "")
        except ValueError:
            self._send_json(411, {"error": "A valid Content-Length header is required"})
            return
        if length < 1:
            self._send_json(400, {"error": "Request body cannot be empty"})
            return
        if length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "Request body exceeds the 256 KiB limit"})
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json"})
            return

        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request JSON must be an object")
            result = nest_parts(payload)
            if path == "/api/export.svg":
                body = render_cut_svg(result)
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Disposition", 'attachment; filename="flatforge-patron.svg"')
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Request body must contain valid UTF-8 JSON"})
            return
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except Exception:
            self.log_error("Unexpected error while calculating a nesting layout")
            self._send_json(500, {"error": "Nesting failed unexpectedly; check the server log"})
            return

        self._send_json(200, result)

    def log_message(self, format: str, *args) -> None:
        # Keep local development logs useful without logging request bodies.
        super().log_message(format, *args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), MakerHandler)
    print(f"FlatForge Maker is running at http://{HOST}:{PORT}")
    print("Local development server only. Do not expose this port to the internet.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping FlatForge Maker...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
