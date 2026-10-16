"""MCP server exposing FlatForge worker operations."""
from mcp.server.fastmcp import FastMCP
from flatforge_proto.methods import GENERATE_RIBS, NEST, PING, UNFOLD
from .session import get_client
mcp = FastMCP("flatforge")

@mcp.tool()
async def flatforge_ping() -> dict:
    """Check whether the FlatForge worker is reachable."""
    return await get_client().call(PING, {})

@mcp.tool()
async def unfold_mesh(mesh: dict) -> dict:
    """Unfold a triangle mesh into 2D coordinates; output is not overlap-checked."""
    return await get_client().call(UNFOLD, {"mesh": mesh})

@mcp.tool()
async def nest_parts(parts: list[dict], sheet_width: float | None = None, sheet_height: float | None = None) -> dict:
    """Nest rectangular or supported simple-polygon parts on a sheet using a deterministic heuristic."""
    return await get_client().call(NEST, {"parts": parts, "sheet_width": sheet_width, "sheet_height": sheet_height})

@mcp.tool()
async def generate_ribs(mesh: dict) -> dict:
    """Extract mesh cross-section segments at regular axis-aligned plane offsets; does not create rib solids."""
    return await get_client().call(GENERATE_RIBS, {"mesh": mesh})

if __name__ == "__main__":
    mcp.run()
