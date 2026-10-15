"""Minimal client holder; each TCP call opens a fresh connection."""
from .blender_client import BlenderWorkerClient
_client = BlenderWorkerClient()
def get_client() -> BlenderWorkerClient:
    return _client
