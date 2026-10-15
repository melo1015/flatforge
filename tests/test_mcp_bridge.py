from flatforge_mcp.blender_client import BlenderWorkerClient

def test_client_defaults():
    client = BlenderWorkerClient(host="127.0.0.1", port=8765, timeout=1)
    assert client.host == "127.0.0.1"
    assert client.port == 8765
