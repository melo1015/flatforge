import json

import pytest

from flatforge_proto.jsonrpc import (
    INVALID_PARAMS, PARSE_ERROR, ProtocolError,
    make_request, make_response, parse_message,
)


def test_request_round_trip():
    parsed = parse_message(json.dumps(make_request("system.ping", {}, 7)))
    assert parsed["id"] == 7
    assert parsed["method"] == "system.ping"


def test_response_shape():
    assert make_response(1, {"ok": True})["result"]["ok"] is True


def test_reject_non_jsonrpc():
    with pytest.raises(ProtocolError):
        parse_message('{"hello":"world"}')


def test_reject_non_object_params():
    with pytest.raises(ProtocolError) as exc:
        parse_message('{"jsonrpc":"2.0","method":"system.ping","params":[],"id":1}')
    assert exc.value.code == INVALID_PARAMS


def test_reject_invalid_method_and_boolean_id():
    with pytest.raises(ProtocolError):
        parse_message('{"jsonrpc":"2.0","method":"","id":1}')
    with pytest.raises(ProtocolError):
        parse_message('{"jsonrpc":"2.0","method":"system.ping","id":true}')


def test_reject_duplicate_keys():
    with pytest.raises(ProtocolError) as exc:
        parse_message('{"jsonrpc":"2.0","method":"system.ping","id":1,"id":2}')
    assert exc.value.code == PARSE_ERROR


def test_reject_oversized_message():
    with pytest.raises(ProtocolError):
        parse_message(b" " * 1025, max_bytes=1024)


def test_notification_omits_id():
    assert "id" not in make_request("system.ping", {}, None)
