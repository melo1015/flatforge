# FlatForge

FlatForge is a modular Python prototype for geometry workflows through a newline-delimited JSON-RPC worker and a Model Context Protocol (MCP) bridge.

## Architecture

- **flatforge_proto** — JSON-RPC request validation, shared method names and protocol errors.
- **flatforge_worker** — bounded threaded TCP server and geometry method dispatcher.
- **flatforge_worker/engines** — mesh unfolding, rectangular shelf nesting, and mesh-plane section extraction for rib planning.
- **flatforge_mcp** — MCP tools and an asynchronous TCP client.
- **flatforge_worker/addon** — starter Blender add-on package; Blender lifecycle integration is not yet complete.

## Requirements

Python 3.11 or newer. For tests, install pytest:

```bash
python -m pip install pytest
PYTHONPATH=. python -m pytest -q
```

## Quick start

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install -e ./flatforge_mcp
python -m flatforge_worker.server
```

In a second terminal, start the MCP bridge:

```bash
flatforge-mcp
```

The worker defaults to `127.0.0.1:8765`. Configure it with `FLATFORGE_HOST`, `FLATFORGE_PORT`, `FLATFORGE_READ_TIMEOUT`, and `FLATFORGE_MAX_CONNECTIONS`. The MCP client supports `FLATFORGE_TIMEOUT`.

## Geometry input examples

Unfolding expects `mesh.vertices` as 3D coordinate triples and `mesh.faces` as vertex-index lists. Nesting expects a list of rectangular parts with `id`, `width`, and `height`. Rib planning intersects a mesh with axis-aligned planes and returns section segments.

See [protocol](docs/protocol.md), [MCP tools](docs/mcp_tools.md), [deployment](docs/deployment.md), and [implementation status](docs/implementation-status.md).

## Safety and limitations

This is not a certified CAD/CAM or structural-analysis system. Unfolding does not optimize cuts or detect self-overlap; nesting uses a rectangular shelf heuristic; rib planning returns section segments rather than closed rib solids. Blender integration is incomplete. Do not use outputs for safety-critical fabrication without independent verification.

The worker has no authentication or TLS. Keep it on a trusted private network and do not expose its port directly to the internet. Docker Compose is a development configuration; PostgreSQL is not connected to application code.
