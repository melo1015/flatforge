"""Async TCP client for the FlatForge JSON-RPC worker."""
from __future__ import annotations

import asyncio
import itertools
import json
import os
from typing import Any

from flatforge_proto.jsonrpc import MAX_MESSAGE_BYTES, make_request


class WorkerProtocolError(RuntimeError):
    """The worker returned a malformed or mismatched response."""


class WorkerRemoteError(RuntimeError):
    """The worker returned a JSON-RPC error response."""

    def __init__(self, code: int, message: str):
        super().__init__(f"Worker error {code}: {message}")
        self.code = code
        self.message = message


class BlenderWorkerClient:
    def __init__(self, host=None, port=None, timeout=None, max_message_bytes=MAX_MESSAGE_BYTES):
        self.host = host if host is not None else os.getenv("FLATFORGE_HOST", "127.0.0.1")
        self.port = int(port if port is not None else os.getenv("FLATFORGE_PORT", "8765"))
        self.timeout = float(timeout if timeout is not None else os.getenv("FLATFORGE_TIMEOUT", "30"))
        self.max_message_bytes = int(max_message_bytes)
        if not self.host:
            raise ValueError("host must not be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if not 128 <= self.max_message_bytes <= MAX_MESSAGE_BYTES:
            raise ValueError("max_message_bytes must be between 128 and the protocol maximum")
        self._ids = itertools.count(1)

    async def call(self, method: str, params: dict | None = None, request_id: str | int | None = None) -> dict:
        if params is not None and not isinstance(params, dict):
            raise ValueError("params must be an object")
        request_id = next(self._ids) if request_id is None else request_id
        request_params = dict(params or {})
        token = os.getenv("FLATFORGE_TOKEN")
        if token:
            request_params["_auth"] = token
        request = make_request(method, request_params, request_id)
        payload = (json.dumps(request, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        if len(payload) > self.max_message_bytes:
            raise ValueError("Request exceeds maximum message size")

        async def _exchange():
            reader, writer = await asyncio.open_connection(self.host, self.port, limit=self.max_message_bytes + 1)
            try:
                writer.write(payload)
                await writer.drain()
                line = await reader.readline()
                if not line:
                    raise ConnectionError("Worker closed connection without a response")
                if len(line) > self.max_message_bytes:
                    raise WorkerProtocolError("Worker response exceeds maximum message size")
                try:
                    response: Any = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise WorkerProtocolError("Worker returned invalid JSON") from exc
                if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
                    raise WorkerProtocolError("Worker returned an invalid JSON-RPC response")
                if response.get("id") != request_id:
                    raise WorkerProtocolError("Worker response id does not match request")
                has_result, has_error = "result" in response, "error" in response
                if has_result == has_error:
                    raise WorkerProtocolError("Response must contain exactly one of result or error")
                if has_error:
                    error = response["error"]
                    if not isinstance(error, dict) or not isinstance(error.get("code"), int) or not isinstance(error.get("message"), str):
                        raise WorkerProtocolError("Worker returned a malformed error")
                    raise WorkerRemoteError(error["code"], error["message"])
                if not isinstance(response["result"], dict):
                    raise WorkerProtocolError("Worker result must be an object")
                return response["result"]
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except (ConnectionError, OSError):
                    pass

        return await asyncio.wait_for(_exchange(), timeout=self.timeout)
