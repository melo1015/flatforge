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

### Rectangular and polygon nesting

`geometry.nest` accepts rectangular parts with `id`, `width`, and `height`, and simple, hole-free polygon parts with `id` and `points`. Rectangular parts use a deterministic MaxRects-style heuristic; polygon parts use a vertex-alignment heuristic with compact-envelope scoring. Neither is an optimal solver. Polygon mode has documented part and vertex limits. FlatForge Maker additionally validates returned layouts independently before displaying or exporting them. Parts that cannot be placed are returned in `unplaced`.

### Mesh sections for rib planning

`geometry.generate_ribs` intersects mesh triangles with regularly spaced axis-aligned planes and returns section segments. It does not stitch contours, create thickness-aware rib solids, or certify structural suitability.

## Not yet production-ready

- Blender add-on operators and registration are implemented; Blender-version-specific runtime and end-to-end integration tests are still required.
- Polygon nesting is implemented for simple, hole-free contours, but further algorithmic quality testing is needed; optimal packing is not guaranteed.
- Robust contour stitching and actual rib-solid generation.
- TLS, job queueing, durable job state, and resource isolation for untrusted workloads. Shared-token authentication is optional and does not encrypt traffic.
- Structural analysis validated against a qualified solver and physical test data.

A successful protocol response is not proof that a geometric result is manufacturable or structurally safe.
