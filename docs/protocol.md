# Worker protocol

The worker accepts newline-delimited UTF-8 JSON-RPC 2.0 messages over TCP. Requests contain `jsonrpc`, `id`, `method`, and optional object `params`. Responses contain either `result` or `error`.

Methods:
- `system.ping`
- `geometry.unfold` — requires `params.mesh`
- `geometry.nest` — requires `params.parts` as a list
- `geometry.generate_ribs` — requires `params.mesh`

The default bind address is loopback only. Do not expose the port directly to the internet. Add authentication, input limits, and request deadlines before deployment.
