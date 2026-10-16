# Deployment notes

1. Use Python 3.11+ and install the bridge package.
2. Start the worker with `python -m flatforge_worker.server`.
3. Start the MCP bridge with `python -m flatforge_mcp.bridge`.
4. Configure host, port, and timeout using environment variables.
5. Keep the worker on a private network. Set `FLATFORGE_TOKEN` to enable shared-token authentication. Add TLS via a private proxy/tunnel, observability, resource limits, and Blender-version-specific integration before production.

Docker Compose is an illustrative development configuration. The Postgres service is not yet connected to application code.
