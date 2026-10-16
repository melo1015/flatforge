"""End-to-end smoke test for the real FlatForge TCP worker process.

Run from the repository root with: python scripts/smoke_test_worker.py
Uses only the Python standard library and never binds outside loopback.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _rpc(port: int, method: str, params: dict | None = None, request_id: int = 1) -> dict:
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }
    with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
        conn.settimeout(3)
        conn.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
        with conn.makefile("rb") as stream:
            line = stream.readline()
    if not line:
        raise RuntimeError(f"worker closed connection without a response to {method}")
    response = json.loads(line.decode("utf-8"))
    if response.get("jsonrpc") != "2.0" or response.get("id") != request_id:
        raise RuntimeError(f"invalid JSON-RPC response for {method}: {response!r}")
    return response


def main() -> int:
    port = _free_loopback_port()
    env = os.environ.copy()
    env.update({
        "FLATFORGE_HOST": "127.0.0.1",
        "FLATFORGE_PORT": str(port),
    })
    # Keep this smoke test deterministic and independent of developer credentials.
    env.pop("FLATFORGE_TOKEN", None)
    process = subprocess.Popen(
        [sys.executable, "-m", "flatforge_worker.server"],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        last_error = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
                raise RuntimeError(f"worker exited during startup (code {process.returncode}): {stderr}")
            try:
                ping = _rpc(port, "system.ping", request_id=1)
                break
            except (OSError, RuntimeError, json.JSONDecodeError) as exc:
                last_error = exc
                time.sleep(0.1)
        else:
            raise RuntimeError(f"worker did not become ready within 10 seconds: {last_error}")

        if ping.get("result", {}).get("ok") is not True:
            raise RuntimeError(f"system.ping failed: {ping!r}")
        print("PASS system.ping: worker process is reachable")

        nesting = _rpc(port, "geometry.nest", {
            "sheet_width": 100,
            "sheet_height": 80,
            "margin": 2,
            "gap": 1,
            "allow_rotation": True,
            "parts": [
                {"id": "smoke-a", "width": 20, "height": 10},
                {"id": "smoke-b", "width": 15, "height": 12},
            ],
        }, request_id=2)
        result = nesting.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(f"geometry.nest returned an error: {nesting!r}")
        placements = result.get("placements")
        if result.get("status") != "ok" or not isinstance(placements, list) or len(placements) != 2:
            raise RuntimeError(f"unexpected nesting result: {result!r}")
        if result.get("unplaced") != []:
            raise RuntimeError(f"smoke-test parts unexpectedly unplaced: {result!r}")
        print("PASS geometry.nest: two parts placed on a test sheet")

        unknown = _rpc(port, "smoke.unknown_method", request_id=3)
        if unknown.get("error", {}).get("code") != -32601:
            raise RuntimeError(f"unknown method did not return JSON-RPC -32601: {unknown!r}")
        print("PASS JSON-RPC error handling: unknown method returns -32601")
        print("FlatForge worker smoke test passed.")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.stderr:
            process.stderr.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FlatForge worker smoke test FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
