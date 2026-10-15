"""Starter operator registration; import bpy only inside Blender."""
try:
    import bpy
except ImportError:
    bpy = None

def register():
    if bpy is None:
        raise RuntimeError("This module must be registered inside Blender")

def unregister():
    if bpy is None:
        return
