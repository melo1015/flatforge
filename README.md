# FlatForge

FlatForge is a modular Python prototype for geometry workflows through a newline-delimited JSON-RPC worker and a Model Context Protocol (MCP) bridge.

## Architecture

- **flatforge_proto** — JSON-RPC request validation, shared method names and protocol errors.
- **flatforge_worker** — bounded threaded TCP server and geometry method dispatcher.
- **flatforge_worker/engines** — mesh unfolding, rectangular and simple-polygon nesting, independent layout validation, quality metrics, and mesh-plane section extraction for rib planning.
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

A local-only visual interface supports rectangular parts and simple, hole-free polygon contours imported from SVG. It includes sheet dimensions, margins, spacing, 90-degree rotation, placement preview, utilization estimates, unplaced-part warnings, independent server-side geometry validation, and SVG export in millimetres.

Run it from the repository root:

```bash
python -m flatforge_maker.server
```

Then open http://127.0.0.1:8787. See [FlatForge Maker documentation](flatforge_maker/README.md) for setup and limitations. The app is a local prototype; it is not a certified manufacturing workflow and must not be exposed directly to a network.

## Geometry input examples

Unfolding expects `mesh.vertices` as 3D coordinate triples and `mesh.faces` as vertex-index lists. Nesting accepts rectangular parts with `id`, `width`, and `height`, or simple polygon parts with `id` and `points` (a list of `[x, y]` coordinates). Polygon nesting is heuristic and supports no holes. Rib planning intersects a mesh with axis-aligned planes and returns section segments.

Start with the [integration and user guide](docs/integration-user-guide.md) for setup instructions and five implementation cases. Also see [protocol](docs/protocol.md), [MCP tools](docs/mcp_tools.md), [deployment](docs/deployment.md), [implementation status](docs/implementation-status.md), and the [integration audit](docs/integration-audit.md).

## Safety and limitations

This is not a certified CAD/CAM or structural-analysis system. Unfolding does not optimize cuts or detect self-overlap; rectangular nesting uses a MaxRects-style heuristic and polygon nesting uses a separate vertex-alignment heuristic; neither is optimal; rib planning returns section segments rather than closed rib solids. Blender integration is incomplete. Do not use outputs for safety-critical fabrication without independent verification.

The worker supports optional shared-token authentication through `FLATFORGE_TOKEN`, but the TCP transport has no TLS. Keep it on a trusted private network and do not expose its port directly to the internet; use a TLS-capable private proxy or secure tunnel for remote access. Docker Compose contains only the worker and MCP bridge. PostgreSQL was removed until durable persistence is actually implemented.
