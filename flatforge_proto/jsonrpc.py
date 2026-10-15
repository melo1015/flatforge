"""Small JSON-RPC 2.0 helpers."""
import json
from typing import Any

def make_request(method: str, params: dict | None = None, request_id: str | int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}

def make_response(request_id: str | int | None, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def make_error(request_id: str | int | None, code: int, message: str, data: Any = None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}

def parse_message(raw: str | bytes) -> dict:
    try:
        message = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid JSON payload") from exc
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        raise ValueError("Expected a JSON-RPC 2.0 object")
    return message
