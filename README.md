# FlatForge

FlatForge is a modular Python prototype for geometry workflows through a newline-delimited JSON-RPC worker and a Model Context Protocol (MCP) bridge.

## Architecture

- **flatforge_proto** — JSON-RPC request validation, shared method names and protocol errors.
- **flatforge_worker** — bounded threaded TCP server and geometry method dispatcher.
- **flatforge_worker/engines** — mesh unfolding, rectangular shelf nesting, and mesh-plane section extraction for rib planning.
- **flatforge_mcp** — MCP tools and an asynchronous TCP client.
- **flatforge_worker/addon** — Blender add-on with registration, worker health check, and selected-mesh unfolding operator; Blender-version integration still needs in-Blender verification.

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

The worker defaults to `127.0.0.1:8765`. Configure it with `FLATFORGE_HOST`, `FLATFORGE_PORT`, `FLATFORGE_READ_TIMEOUT`, `FLATFORGE_MAX_CONNECTIONS`, and optionally `FLATFORGE_TOKEN`. When a token is set, the MCP client and Blender add-on send it automatically from their process environment. The MCP client also supports `FLATFORGE_TIMEOUT`.

## FlatForge Maker (early web prototype)

A local visual interface is available for the rectangular nesting engine. It supports sheet dimensions, margins, spacing, 90-degree rotation, preview of placements, a utilization estimate, unplaced-part warnings, and SVG export in millimetres.

Run it from the repository root:

```bash
python -m flatforge_maker.server
```

Then open http://127.0.0.1:8787. See [FlatForge Maker documentation](flatforge_maker/README.md) for setup and limitations. The app is a local prototype; it is not a certified manufacturing workflow and must not be exposed directly to a network.

## Geometry input examples

Unfolding expects `mesh.vertices` as 3D coordinate triples and `mesh.faces` as vertex-index lists. Nesting expects a list of rectangular parts with `id`, `width`, and `height`. Rib planning intersects a mesh with axis-aligned planes and returns section segments.

See [protocol](docs/protocol.md), [MCP tools](docs/mcp_tools.md), [deployment](docs/deployment.md), and [implementation status](docs/implementation-status.md).

## Safety and limitations

This is not a certified CAD/CAM or structural-analysis system. Unfolding does not optimize cuts or detect self-overlap; nesting uses a rectangular shelf heuristic; rib planning returns section segments rather than closed rib solids. Blender integration is incomplete. Do not use outputs for safety-critical fabrication without independent verification.

The worker supports optional shared-token authentication through `FLATFORGE_TOKEN`, but the TCP transport has no TLS. Keep it on a trusted private network and do not expose its port directly to the internet; use a TLS-capable private proxy or secure tunnel for remote access. Docker Compose contains only the worker and MCP bridge. PostgreSQL was removed until durable persistence is actually implemented.
