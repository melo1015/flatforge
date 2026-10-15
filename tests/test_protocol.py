import json
import pytest
from flatforge_proto.jsonrpc import make_request, make_response, parse_message

def test_request_round_trip():
    parsed = parse_message(json.dumps(make_request("system.ping", {}, 7)))
    assert parsed["id"] == 7
    assert parsed["method"] == "system.ping"

def test_response_shape():
    assert make_response(1, {"ok": True})["result"]["ok"] is True

def test_reject_non_jsonrpc():
    with pytest.raises(ValueError):
        parse_message('{"hello":"world"}')
