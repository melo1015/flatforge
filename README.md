# FlatForge

FlatForge is a modular prototype for driving Blender geometry workflows through a JSON-RPC worker and a Model Context Protocol (MCP) bridge.

## Architecture
- **flatforge_worker** — TCP JSON-RPC server and dispatcher; geometry engines are pure-Python placeholders and do not import `bpy`.
- **flatforge_mcp** — MCP server and asynchronous TCP client.
- **flatforge_proto** — protocol envelopes, errors, and method names.
- **flatforge_llm** — optional LLM helpers and prompt examples.
- **flatforge_worker/addon** — starter Blender add-on package.

## Quick start
Requires Python 3.11+.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -e ./flatforge_mcp
python -m flatforge_worker.server
```

In a second terminal run `flatforge-mcp`. The worker defaults to `127.0.0.1:8765`; configure with `FLATFORGE_HOST` and `FLATFORGE_PORT`.

## Important status
This is a scaffold, not production-ready Blender automation. Geometry algorithms are placeholders; the Blender add-on lifecycle is incomplete; Docker Compose is a development starting point; Postgres is provisioned but not connected to application code. Test in a safe environment before use and do not expose the worker port to untrusted networks.

See [protocol](docs/protocol.md), [MCP tools](docs/mcp_tools.md), and [deployment](docs/deployment.md).
