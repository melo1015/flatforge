"""Run inside Blender with the FlatForge worker already listening on 127.0.0.1:8765.

Example:
  blender --background --factory-startup --python scripts/blender_smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    import bpy
    from flatforge_worker import addon

    registered = False
    try:
        addon.register()
        registered = True

        ping_result = bpy.ops.flatforge.ping_worker()
        if "FINISHED" not in ping_result:
            raise RuntimeError(f"Blender worker ping operator failed: {ping_result!r}")
        print("PASS Blender add-on worker connection")

        # Use a cube to exercise face triangulation, JSON-RPC, result parsing,
        # and creation of a new Blender mesh object.
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
        source = bpy.context.active_object
        source_name = source.name

        unfold_result = bpy.ops.flatforge.unfold_selected_mesh()
        if "FINISHED" not in unfold_result:
            raise RuntimeError(f"Blender unfold operator failed: {unfold_result!r}")

        unfolded_name = f"{source_name}_Unfolded"
        unfolded = bpy.data.objects.get(unfolded_name)
        if unfolded is None or unfolded.type != "MESH":
            raise RuntimeError(f"Expected generated mesh object {unfolded_name!r}")
        if len(unfolded.data.vertices) != 36 or len(unfolded.data.polygons) != 12:
            raise RuntimeError(
                "Unexpected unfolded cube topology: "
                f"{len(unfolded.data.vertices)} vertices, {len(unfolded.data.polygons)} faces"
            )
        if any(abs(vertex.co.z) > 1e-7 for vertex in unfolded.data.vertices):
            raise RuntimeError("Unfolded mesh is not planar on Z=0")

        print(
            "PASS Blender geometry generation: "
            f"{len(unfolded.data.vertices)} 2D vertices, "
            f"{len(unfolded.data.polygons)} triangles"
        )
        print("FlatForge Blender smoke test passed.")
        return 0
    finally:
        if registered:
            addon.unregister()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FlatForge Blender smoke test FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
