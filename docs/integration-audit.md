# FlatForge integration audit

Audit date: 2026-10-16  
Audited revision: `main` at `5cbd7cc6e5e6137c0e41ae9406f5146b81b30778`

## Scope and evidence

This is a repository/code review plus the repository's GitHub Actions result. It is not a live deployment test. The CI workflow compiles the Python packages and runs pytest on Python 3.11 and 3.12. The reviewed run passed both jobs.

## Confirmed integration

- The `main` tree contains the Maker UI, SVG importer/exporter, polygon nesting, independent geometry validation, nesting metrics and benchmark.
- The JSON-RPC worker dispatches unfolding, nesting, rib-section extraction and ping operations.
- The TCP worker limits message size, concurrent connections and per-connection read time; optional shared-token authentication is supported.
- The MCP bridge calls the worker using the shared async client.
- Docker Compose includes the worker and MCP bridge; it does not include the Maker web interface or persistent storage.
- The Maker server binds to `127.0.0.1:8787` and documents that it is not hardened for network exposure.

## Documentation inconsistencies corrected in this branch

- The root README now describes polygon nesting and independent validation instead of describing Maker as rectangular-only.
- MCP tool docstrings no longer say that the geometry engines are placeholders.
- Implementation status now distinguishes the implemented polygon heuristic from the remaining quality and production-readiness work.
- Deployment notes now state that Compose does not launch Maker, and that a blank `FLATFORGE_TOKEN` disables token authentication.

## Risks and follow-up work

1. **Blender runtime remains unverified.** CI does not launch Blender or exercise the add-on inside Blender. Validate against the exact Blender version used by the operator.
2. **Docker images are not built in CI.** Add a CI job that builds both Dockerfiles and validates the Compose configuration.
3. **Maker has no browser-driven end-to-end tests.** Unit tests cover geometry and benchmark smoke paths, but not the UI-to-HTTP-to-SVG workflow in a real browser.
4. **Authentication and transport security are different controls.** The shared token is optional and TCP has no TLS. Keep the worker on a trusted private network; do not expose it directly to the internet.
5. **Geometry output is not manufacturing certification.** Polygon nesting is heuristic; unfolding does not detect 2D self-overlap; rib generation returns section segments rather than closed, thickness-aware solids. Verify output in the target CAM workflow.
6. **No persistence or job queue.** Current Compose is a development arrangement, not a multi-user production service.

## Recommended next validation gate

Before deployment, add CI coverage for Docker builds and Compose configuration, then run a smoke test that starts the worker, checks `system.ping`, calls each geometry method with a small valid fixture, and verifies malformed/oversized requests are rejected. Separately run Maker in a browser and verify import → nest → validation → SVG export, including invalid SVG and unplaced-part cases.

## Conclusion

The current automated test suite is green on Python 3.11 and 3.12. The repository is suitable for controlled developer/server testing, subject to the limitations above; this audit does not certify production readiness or fabrication safety.
