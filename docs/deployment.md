# Deployment notes

1. Use Python 3.11+ and install the bridge package.
2. Start the worker with `python -m flatforge_worker.server`.
3. Start the MCP bridge with `python -m flatforge_mcp.bridge`.
4. Configure host, port, and timeout using environment variables.
5. Keep the worker on a private network. Set `FLATFORGE_TOKEN` to enable shared-token authentication. Add TLS via a private proxy/tunnel, observability, resource limits, and Blender-version-specific integration before production.

Docker Compose is a development configuration for the worker and MCP bridge only; it does not start the FlatForge Maker web UI and no database is provisioned until persistence is implemented. In Compose, the worker is bound to the container network and the host port is published only on `127.0.0.1`. Authentication is optional: set a strong `FLATFORGE_TOKEN` in the environment before starting Compose; an empty value disables token authentication. The TCP protocol has no TLS.
