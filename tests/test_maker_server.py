"""HTTP smoke tests for the local FlatForge Maker interface."""
from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from flatforge_maker.server import MakerHandler


@pytest.fixture
def maker_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MakerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield host, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(maker_server, method, path, body=None, headers=None):
    host, port = maker_server
    connection = HTTPConnection(host, port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.getheader("Content-Type"), response.read()
    finally:
        connection.close()


def test_health_endpoint(maker_server):
    status, content_type, body = request(maker_server, "GET", "/api/health")
    assert status == 200
    assert content_type.startswith("application/json")
    payload = json.loads(body)
    assert payload["ok"] is True
    assert payload["service"] == "flatforge-maker"


def test_home_page_is_served(maker_server):
    status, content_type, body = request(maker_server, "GET", "/")
    assert status == 200
    assert content_type.startswith("text/html")
    assert b"FlatForge Maker" in body


def test_nesting_endpoint_returns_placements(maker_server):
    payload = {
        "parts": [
            {"id": "Panel A", "width": 100, "height": 50},
            {"id": "Panel B", "width": 80, "height": 40},
        ],
        "sheet_width": 300,
        "sheet_height": 200,
        "margin": 5,
        "gap": 3,
        "allow_rotation": True,
    }
    status, content_type, body = request(
        maker_server,
        "POST",
        "/api/nest",
        body=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert status == 200
    assert content_type.startswith("application/json")
    result = json.loads(body)
    assert result["status"] == "ok"
    assert result["placed_count"] == 2
    assert result["unplaced"] == []
    assert len(result["placements"]) == 2


def test_nesting_endpoint_rejects_non_json_content_type(maker_server):
    status, _, body = request(
        maker_server,
        "POST",
        "/api/nest",
        body="parts=[]",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 415
    assert "Content-Type" in json.loads(body)["error"]


def test_unknown_path_returns_404(maker_server):
    status, _, body = request(maker_server, "GET", "/not-a-file")
    assert status == 404
    assert json.loads(body)["error"] == "Not found"



def test_svg_export_endpoint_returns_mm_svg_attachment(maker_server):
    payload = {
        "parts": [{"id": "panel", "width": 100, "height": 50}],
        "sheet_width": 300,
        "sheet_height": 200,
        "margin": 5,
        "gap": 3,
        "allow_rotation": True,
    }
    status, content_type, body = request(
        maker_server,
        "POST",
        "/api/export.svg",
        body=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert status == 200
    assert content_type.startswith("image/svg+xml")
    assert b'width="300mm"' in body
    assert b'height="200mm"' in body
    assert b'fill="none"' in body
    assert b'stroke="#000000"' in body


def test_svg_export_endpoint_rejects_when_no_part_fits(maker_server):
    payload = {
        "parts": [{"id": "too-large", "width": 200, "height": 200}],
        "sheet_width": 100,
        "sheet_height": 100,
        "margin": 0,
        "gap": 0,
        "allow_rotation": False,
    }
    status, content_type, body = request(
        maker_server,
        "POST",
        "/api/export.svg",
        body=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert status == 400
    assert content_type.startswith("application/json")
    assert "no placed parts" in json.loads(body)["error"]
