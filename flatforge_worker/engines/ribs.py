"""Extract cross-section polylines from a triangle mesh at regular plane offsets.

This returns section curves suitable as input to a downstream rib fabrication
step. It does not generate closed, thickness-aware rib solids.
"""
from __future__ import annotations

import math


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def generate_ribs(params: dict) -> dict:
    mesh = params.get("mesh")
    if not isinstance(mesh, dict):
        raise ValueError("'mesh' must be an object")
    vertices, faces = mesh.get("vertices"), mesh.get("faces")
    if not isinstance(vertices, list) or not vertices or not isinstance(faces, list) or not faces:
        raise ValueError("mesh must contain non-empty vertices and faces")
    points = []
    for i, point in enumerate(vertices):
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            raise ValueError(f"vertices[{i}] must have three coordinates")
        points.append(tuple(_number(v, f"vertices[{i}]") for v in point))
    axis = params.get("axis", "z")
    axis_index = {"x": 0, "y": 1, "z": 2}.get(axis)
    if axis_index is None:
        raise ValueError("axis must be x, y, or z")
    spacing = _number(params.get("spacing", 10), "spacing")
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    start = _number(params.get("start", min(p[axis_index] for p in points)), "start")
    end = _number(params.get("end", max(p[axis_index] for p in points)), "end")
    if end < start:
        raise ValueError("end must be greater than or equal to start")
    if len(faces) > 100000 or len(points) > 200000:
        raise ValueError("mesh exceeds the supported size limit")

    planes = []
    count = int(math.floor((end - start) / spacing + 1e-9)) + 1
    if count > 10000:
        raise ValueError("requested more than 10000 section planes")
    for plane_i in range(count):
        offset = start + plane_i * spacing
        segments = []
        for fi, face in enumerate(faces):
            if not isinstance(face, list) or len(face) < 3:
                raise ValueError(f"faces[{fi}] must contain at least three indices")
            if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(points) for i in face):
                raise ValueError(f"faces[{fi}] contains an invalid vertex index")
            # Triangulate polygon faces as a fan for section extraction.
            for j in range(1, len(face) - 1):
                tri = (face[0], face[j], face[j + 1])
                intersections = []
                for ia, ib in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                    a, b = points[ia], points[ib]
                    da, db = a[axis_index] - offset, b[axis_index] - offset
                    if abs(da) <= 1e-9 and abs(db) <= 1e-9:
                        continue
                    if da * db > 0:
                        continue
                    denominator = b[axis_index] - a[axis_index]
                    if abs(denominator) <= 1e-12:
                        continue
                    t = (offset - a[axis_index]) / denominator
                    if -1e-9 <= t <= 1 + 1e-9:
                        point = tuple(a[k] + max(0.0, min(1.0, t)) * (b[k] - a[k]) for k in range(3))
                        projected = tuple(round(point[k], 8) for k in range(3) if k != axis_index)
                        if projected not in intersections:
                            intersections.append(projected)
                if len(intersections) == 2 and intersections[0] != intersections[1]:
                    segments.append([list(intersections[0]), list(intersections[1])])
        planes.append({"offset": round(offset, 8), "segments": segments, "segment_count": len(segments)})
    return {
        "status": "ok",
        "operation": "mesh_plane_sections",
        "axis": axis,
        "spacing": spacing,
        "planes": planes,
        "warning": "Outputs section segments, not closed rib solids; contour stitching and thickness generation are separate steps.",
    }
