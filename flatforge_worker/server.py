"""Bounded threaded TCP worker for newline-delimited JSON-RPC requests."""
from __future__ import annotations

import json
import os
import socket
import socketserver
import threading

from flatforge_proto.jsonrpc import (
    INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST, MAX_MESSAGE_BYTES,
    METHOD_NOT_FOUND, ProtocolError, make_error, make_response, parse_message,
)
from flatforge_worker.handlers import dispatch


class Handler(socketserver.StreamRequestHandler):
    def setup(self):
        self.request.settimeout(float(os.getenv("FLATFORGE_READ_TIMEOUT", "10")))
        super().setup()

    def _send(self, payload: dict) -> None:
        encoded = (json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        if len(encoded) > MAX_MESSAGE_BYTES:
            encoded = (json.dumps(make_error(payload.get("id"), INTERNAL_ERROR, "Response exceeds maximum size")) + "\n").encode()
        self.wfile.write(encoded)
        self.wfile.flush()

    def handle(self):
        while True:
            try:
                raw = self.rfile.readline(MAX_MESSAGE_BYTES + 2)
            except (socket.timeout, OSError):
                return
            if not raw:
                return
            request_id = None
            try:
                if len(raw) > MAX_MESSAGE_BYTES + 1 or (len(raw) == MAX_MESSAGE_BYTES + 1 and not raw.endswith(b"\n")):
                    self._send(make_error(None, INVALID_REQUEST, "Message exceeds maximum size"))
                    return
                if not raw.endswith(b"\n"):
                    self._send(make_error(None, INVALID_REQUEST, "Each request must end with a newline"))
                    return
                message = parse_message(raw.rstrip(b"\r\n"))
                request_id = message.get("id")
                try:
                    result = dispatch(message["method"], message.get("params", {}))
                except KeyError:
                    response = make_error(request_id, METHOD_NOT_FOUND, "Method not found")
                except (ValueError, TypeError) as exc:
                    response = make_error(request_id, INVALID_PARAMS, str(exc))
                except Exception:
                    response = make_error(request_id, INTERNAL_ERROR, "Internal worker error")
                else:
                    response = make_response(request_id, result)
                # JSON-RPC notifications have no id and must not receive a response.
                if "id" in message:
                    self._send(response)
            except ProtocolError as exc:
                self._send(make_error(request_id, exc.code, str(exc)))
            except (ValueError, TypeError):
                self._send(make_error(request_id, INVALID_REQUEST, "Invalid request"))


class BoundedThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, RequestHandlerClass, max_connections=32):
        self._connection_slots = threading.BoundedSemaphore(max_connections)
        super().__init__(server_address, RequestHandlerClass)

    def process_request(self, request, client_address):
        if not self._connection_slots.acquire(blocking=False):
            try:
                request.close()
            finally:
                return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connection_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connection_slots.release()


def main():
    host = os.getenv("FLATFORGE_HOST", "127.0.0.1")
    port = int(os.getenv("FLATFORGE_PORT", "8765"))
    max_connections = int(os.getenv("FLATFORGE_MAX_CONNECTIONS", "32"))
    if not 1 <= port <= 65535:
        raise ValueError("FLATFORGE_PORT must be between 1 and 65535")
    if not 1 <= max_connections <= 1024:
        raise ValueError("FLATFORGE_MAX_CONNECTIONS must be between 1 and 1024")
    with BoundedThreadingTCPServer((host, port), Handler, max_connections) as server:
        print(f"FlatForge worker listening on {host}:{port}")
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            print("FlatForge worker shutting down")


if __name__ == "__main__":
    main()
