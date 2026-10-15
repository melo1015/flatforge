"""JSON-RPC method dispatcher."""
from flatforge_proto.methods import GENERATE_RIBS, NEST, PING, UNFOLD
from flatforge_worker.engines import generate_ribs, nest_parts, unfold_mesh

def dispatch(method: str, params: dict | None = None) -> dict:
    params = params or {}
    if method == PING:
        return {"ok": True, "service": "flatforge-worker"}
    if method == UNFOLD:
        return unfold_mesh(params)
    if method == NEST:
        return nest_parts(params)
    if method == GENERATE_RIBS:
        return generate_ribs(params)
    raise KeyError(f"Unknown method: {method}")
