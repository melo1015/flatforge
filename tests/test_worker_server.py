import json
import socket
import threading

from flatforge_worker.server import BoundedThreadingTCPServer, Handler


def _request(port, params):
    payload = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "system.ping",
        "params": params,
    }
    with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
        conn.sendall((json.dumps(payload) + "\\n").encode())
        with conn.makefile("rb") as stream:
            return json.loads(stream.readline())


def test_worker_requires_shared_token_when_configured(monkeypatch):
    monkeypatch.setenv("FLATFORGE_TOKEN", "test-secret")
    server = BoundedThreadingTCPServer(("127.0.0.1", 0), Handler, max_connections=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        denied = _request(port, {})
        assert denied["error"]["code"] == -32001
        allowed = _request(port, {"_auth": "test-secret"})
        assert allowed["result"]["ok"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_worker_maps_unknown_method_to_jsonrpc_error(monkeypatch):
    monkeypatch.delenv("FLATFORGE_TOKEN", raising=False)
    server = BoundedThreadingTCPServer(("127.0.0.1", 0), Handler, max_connections=2)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = {"jsonrpc": "2.0", "id": 2, "method": "no.such.method", "params": {}}
        with socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=2) as conn:
            conn.sendall((json.dumps(payload) + "\\n").encode())
            with conn.makefile("rb") as stream:
                response = json.loads(stream.readline())
        assert response["error"]["code"] == -32601
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
