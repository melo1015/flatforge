"""Threaded TCP JSON-RPC worker; newline-delimited JSON messages."""
import json
import os
import socketserver
from flatforge_proto.jsonrpc import make_error, make_response, parse_message
from flatforge_worker.handlers import dispatch

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            request_id = None
            try:
                message = parse_message(raw)
                request_id = message.get("id")
                if "method" not in message or not isinstance(message["method"], str):
                    response = make_error(request_id, -32600, "Invalid request")
                else:
                    result = dispatch(message["method"], message.get("params"))
                    response = make_response(request_id, result)
            except KeyError as exc:
                response = make_error(request_id, -32601, str(exc))
            except (ValueError, TypeError) as exc:
                response = make_error(request_id, -32600, str(exc))
            except Exception:
                response = make_error(request_id, -32603, "Internal worker error")
            self.wfile.write((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))

def main():
    host = os.getenv("FLATFORGE_HOST", "127.0.0.1")
    port = int(os.getenv("FLATFORGE_PORT", "8765"))
    with socketserver.ThreadingTCPServer((host, port), Handler) as server:
        server.daemon_threads = True
        print(f"FlatForge worker listening on {host}:{port}")
        server.serve_forever()

if __name__ == "__main__":
    main()
