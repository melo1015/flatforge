"""Async newline-delimited JSON TCP client."""
import asyncio
import json
import os
from flatforge_proto.jsonrpc import make_request

class BlenderWorkerClient:
    def __init__(self, host=None, port=None, timeout=None):
        self.host = host or os.getenv("FLATFORGE_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("FLATFORGE_PORT", "8765"))
        self.timeout = float(timeout or os.getenv("FLATFORGE_TIMEOUT", "30"))

    async def call(self, method: str, params: dict | None = None, request_id: int = 1) -> dict:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=self.timeout)
        try:
            payload = json.dumps(make_request(method, params, request_id), separators=(",", ":"))
            writer.write((payload + "\\n").encode("utf-8"))
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
            if not line:
                raise ConnectionError("Worker closed connection without a response")
            response = json.loads(line)
            if "error" in response:
                err = response["error"]
                raise RuntimeError(f"Worker error {err.get('code')}: {err.get('message')}")
            return response.get("result", {})
        finally:
            writer.close()
            await writer.wait_closed()
