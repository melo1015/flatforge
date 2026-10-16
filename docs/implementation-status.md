# Implementation status

This document distinguishes implemented algorithms from work that still requires integration or domain validation.

## Worker protocol

- JSON-RPC 2.0 request validation, duplicate-key rejection, UTF-8 checking and message-size limits are implemented in `flatforge_proto/jsonrpc.py`.
- The TCP worker applies bounded connection concurrency, per-connection read timeouts and protocol error mapping.
- The MCP TCP client validates response shape and request IDs and distinguishes remote errors from malformed responses.
- The worker supports optional shared-token authentication via `FLATFORGE_TOKEN`; the MCP client and Blender add-on read the same environment variable. The transport has no TLS, so keep it on a trusted private network and do not expose it directly to the internet.

## Geometry engines

### Mesh unfolding

`geometry.unfold` accepts a mesh with `vertices: [[x,y,z], ...]` and `faces: [[vertex_index, ...], ...]`. Polygon faces are fan-triangulated, then a breadth-first spanning forest is unfolded while preserving triangle edge lengths.

Limitations: this is not a cut optimizer, does not detect 2D self-overlap, and assumes fan triangulation is appropriate for polygon faces. Results require independent geometric validation before fabrication.

### Rectangular nesting

`geometry.nest` accepts rectangular parts with `id`, `width`, and `height`; optional sheet dimensions, margin, gap and rotation are supported. It uses a deterministic shelf heuristic, not an optimal polygon nesting algorithm. Parts that cannot be placed are returned in `unplaced`.

### Mesh sections for rib planning

`geometry.generate_ribs` intersects mesh triangles with regularly spaced axis-aligned planes and returns section segments. It does not stitch contours, create thickness-aware rib solids, or certify structural suitability.

## Not yet production-ready

- Blender add-on operators and registration are implemented; Blender-version-specific runtime and end-to-end integration tests are still required.
- Polygon nesting with collision detection and optimization.
- Robust contour stitching and actual rib-solid generation.
- Authentication, TLS, job queueing, durable job state, and resource isolation for untrusted workloads.
- Structural analysis validated against a qualified solver and physical test data.

A successful protocol response is not proof that a geometric result is manufacturable or structurally safe.
