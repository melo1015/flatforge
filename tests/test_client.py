import asyncio
import json

import pytest

from flatforge_mcp.blender_client import (
    BlenderWorkerClient,
    WorkerProtocolError,
    WorkerRemoteError,
)


def test_client_round_trip_and_unique_request_ids():
    async def scenario():
        received = []

        async def handler(reader, writer):
            line = await reader.readline()
            request = json.loads(line)
            received.append(request)
            writer.write((json.dumps({
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"ok": True},
            }) + "\\n").encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            client = BlenderWorkerClient(port=port, timeout=2)
            assert await client.call("system.ping", {}) == {"ok": True}
            assert await client.call("system.ping", {}) == {"ok": True}
            assert received[0]["id"] != received[1]["id"]
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())


def test_client_rejects_mismatched_response_id():
    async def scenario():
        async def handler(reader, writer):
            await reader.readline()
            writer.write(b'{"jsonrpc":"2.0","id":999,"result":{}}\\n')
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            client = BlenderWorkerClient(port=port, timeout=2)
            with pytest.raises(WorkerProtocolError):
                await client.call("system.ping", {})
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())


def test_client_surfaces_remote_error():
    async def scenario():
        async def handler(reader, writer):
            request = json.loads(await reader.readline())
            response = {"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "Method not found"}}
            writer.write((json.dumps(response) + "\\n").encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            client = BlenderWorkerClient(port=port, timeout=2)
            with pytest.raises(WorkerRemoteError) as exc:
                await client.call("unknown.method", {})
            assert exc.value.code == -32601
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())
