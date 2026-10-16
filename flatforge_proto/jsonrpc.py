"""Strict helpers for the newline-delimited JSON-RPC 2.0 worker protocol."""
from __future__ import annotations

import json
from typing import Any

MAX_MESSAGE_BYTES = 1_048_576
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ProtocolError(ValueError):
    """A malformed JSON-RPC message with a protocol error code."""

    def __init__(self, message: str, code: int = INVALID_REQUEST):
        super().__init__(message)
        self.code = code


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"Duplicate JSON object key: {key}", PARSE_ERROR)
        result[key] = value
    return result


def make_request(method: str, params: dict | None = None, request_id: str | int | None = 1) -> dict:
    if not isinstance(method, str) or not method.strip():
        raise ValueError("method must be a non-empty string")
    if params is not None and not isinstance(params, dict):
        raise ValueError("params must be an object")
    message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if request_id is not None:
        if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
            raise ValueError("request_id must be a string, integer, or None")
        message["id"] = request_id
    return message


def make_response(request_id: str | int | None, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def make_error(request_id: str | int | None, code: int, message: str, data: Any = None) -> dict:
    error = {"code": int(code), "message": str(message)}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def validate_request(message: Any) -> dict:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        raise ProtocolError("Expected a JSON-RPC 2.0 object")
    method = message.get("method")
    if not isinstance(method, str) or not method.strip():
        raise ProtocolError("method must be a non-empty string")
    if "params" in message and not isinstance(message["params"], dict):
        raise ProtocolError("params must be an object", INVALID_PARAMS)
    if "id" in message:
        request_id = message["id"]
        if request_id is not None and (isinstance(request_id, bool) or not isinstance(request_id, (str, int))):
            raise ProtocolError("id must be a string, integer, or null")
    allowed = {"jsonrpc", "method", "params", "id"}
    if set(message) - allowed:
        raise ProtocolError("Request contains unsupported fields")
    return message


def parse_message(raw: str | bytes, *, max_bytes: int = MAX_MESSAGE_BYTES) -> dict:
    if isinstance(raw, bytes):
        if len(raw) > max_bytes:
            raise ProtocolError("Message exceeds maximum size", INVALID_REQUEST)
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("Message must be UTF-8", PARSE_ERROR) from exc
    elif isinstance(raw, str):
        if len(raw.encode("utf-8")) > max_bytes:
            raise ProtocolError("Message exceeds maximum size", INVALID_REQUEST)
    else:
        raise ProtocolError("Message must be text or bytes", PARSE_ERROR)
    try:
        message = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except ProtocolError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProtocolError("Invalid JSON payload", PARSE_ERROR) from exc
    return validate_request(message)
