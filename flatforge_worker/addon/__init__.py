"""FlatForge Blender add-on: worker health check and mesh unfolding."""
from __future__ import annotations

import json
import socket

import bpy
from bpy.types import Operator, Panel

bl_info = {
    "name": "FlatForge",
    "author": "FlatForge contributors",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > FlatForge",
    "description": "Connect to the FlatForge worker and unfold selected meshes",
    "category": "Object",
}

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_MESSAGE_BYTES = 1_048_576


def _worker_call(method: str, params: dict, timeout: float = 30.0) -> dict:
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    payload = (json.dumps(request, separators=(",", ":")) + "\\n").encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("Request exceeds FlatForge's message size limit")
    with socket.create_connection((DEFAULT_HOST, DEFAULT_PORT), timeout=timeout) as connection:
        connection.settimeout(timeout)
        connection.sendall(payload)
        with connection.makefile("rb") as stream:
            line = stream.readline(MAX_MESSAGE_BYTES + 1)
    if not line:
        raise ConnectionError("FlatForge worker closed the connection without a response")
    if len(line) > MAX_MESSAGE_BYTES or not line.endswith(b"\\n"):
        raise ValueError("FlatForge worker returned an oversized or incomplete response")
    response = json.loads(line)
    if not isinstance(response, dict) or response.get("jsonrpc") != "2.0" or response.get("id") != 1:
        raise ValueError("FlatForge worker returned an invalid JSON-RPC response")
    if "error" in response:
        error = response["error"]
        raise RuntimeError(f"Worker error {error.get('code')}: {error.get('message')}")
    if "result" not in response or not isinstance(response["result"], dict):
        raise ValueError("FlatForge worker response is missing an object result")
    return response["result"]


class FLATFORGE_OT_ping_worker(Operator):
    bl_idname = "flatforge.ping_worker"
    bl_label = "Test Worker Connection"
    bl_description = "Check whether the local FlatForge worker is reachable"

    def execute(self, context):
        try:
            result = _worker_call("system.ping", {}, timeout=3.0)
        except Exception as exc:
            self.report({"ERROR"}, f"FlatForge worker unavailable: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"FlatForge worker reachable: {result.get('service', 'ok')}")
        return {"FINISHED"}


class FLATFORGE_OT_unfold_selected_mesh(Operator):
    bl_idname = "flatforge.unfold_selected_mesh"
    bl_label = "Unfold Selected Mesh"
    bl_description = "Send the active mesh to FlatForge and create a 2D triangle mesh"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        obj = context.active_object
        if len(obj.data.vertices) > 200000 or len(obj.data.polygons) > 100000:
            self.report({"ERROR"}, "Mesh exceeds FlatForge's current size limit")
            return {"CANCELLED"}
        mesh_payload = {
            "vertices": [[float(c) for c in vertex.co] for vertex in obj.data.vertices],
            "faces": [list(poly.vertices) for poly in obj.data.polygons],
        }
        try:
            result = _worker_call("geometry.unfold", {"mesh": mesh_payload})
            vertices_2d = result.get("vertices_2d")
            triangles_2d = result.get("triangles_2d")
            if not isinstance(vertices_2d, list) or not isinstance(triangles_2d, list):
                raise ValueError("Worker result does not contain unfolded vertices and triangles")
            coordinates = [(float(v["x"]), float(v["y"]), 0.0) for v in vertices_2d]
            if any(not isinstance(face, list) or len(face) != 3 for face in triangles_2d):
                raise ValueError("Worker returned an invalid triangle list")
            new_mesh = bpy.data.meshes.new(f"{obj.name}_FlatForge_2D")
            new_mesh.from_pydata(coordinates, [], triangles_2d)
            new_mesh.update()
            new_obj = bpy.data.objects.new(f"{obj.name}_Unfolded", new_mesh)
            context.collection.objects.link(new_obj)
            new_obj.location = obj.location
            self.report({"INFO"}, f"Created 2D mesh with {len(triangles_2d)} triangles")
            if result.get("warnings"):
                self.report({"WARNING"}, "Unfolding is not overlap-checked; inspect before fabrication")
        except Exception as exc:
            self.report({"ERROR"}, f"Unfolding failed: {exc}")
            return {"CANCELLED"}
        return {"FINISHED"}


class FLATFORGE_PT_sidebar(Panel):
    bl_label = "FlatForge"
    bl_idname = "FLATFORGE_PT_sidebar"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FlatForge"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Worker")
        layout.operator("flatforge.ping_worker", icon="URL")
        layout.separator()
        layout.label(text="Geometry")
        layout.operator("flatforge.unfold_selected_mesh", icon="MOD_TRIANGULATE")


_CLASSES = (
    FLATFORGE_OT_ping_worker,
    FLATFORGE_OT_unfold_selected_mesh,
    FLATFORGE_PT_sidebar,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            # Make repeated unregister calls safe during add-on reloads.
            pass
