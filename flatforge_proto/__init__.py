"""Shared FlatForge protocol primitives."""
from .errors import ProtocolError
from .jsonrpc import make_error, make_request, make_response, parse_message
__all__ = ["ProtocolError", "make_error", "make_request", "make_response", "parse_message"]
