"""Triangle-mesh unfolding into 2D using a breadth-first face traversal.

Each triangle receives its own 2D corner vertices so cut seams can duplicate
original mesh vertices. Edge lengths are preserved per triangle. This is not
a cut optimizer and does not detect self-overlap.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque


def _vec3(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain exactly three coordinates")
    result = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise ValueError(f"{label} coordinates must be finite numbers")
        result.append(float(item))
    return tuple(result)


def _distance(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _distance2(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unfold_mesh(params: dict) -> dict:
    mesh = params.get("mesh")
    if not isinstance(mesh, dict):
        raise ValueError("'mesh' must be an object")
    vertices_raw, faces_raw = mesh.get("vertices"), mesh.get("faces")
    if not isinstance(vertices_raw, list) or len(vertices_raw) < 3:
        raise ValueError("mesh.vertices must contain at least three vertices")
    if not isinstance(faces_raw, list) or not faces_raw:
        raise ValueError("mesh.faces must contain at least one face")
    if len(vertices_raw) > 200000 or len(faces_raw) > 100000:
        raise ValueError("mesh exceeds the supported size limit")
    vertices = [_vec3(v, f"vertices[{i}]") for i, v in enumerate(vertices_raw)]
    triangles = []
    for fi, face in enumerate(faces_raw):
        if not isinstance(face, list) or len(face) < 3:
            raise ValueError(f"faces[{fi}] must contain at least three vertex indices")
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(vertices) for i in face):
            raise ValueError(f"faces[{fi}] contains an invalid vertex index")
        if len(set(face)) != len(face):
            raise ValueError(f"faces[{fi}] repeats a vertex index")
        # Fan triangulation is deterministic; concave polygons should be triangulated upstream.
        triangles.extend((face[0], face[i], face[i + 1]) for i in range(1, len(face) - 1))

    edge_faces = defaultdict(list)
    for ti, tri in enumerate(triangles):
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edge_faces[tuple(sorted((a, b)))].append(ti)
    if any(len(adj) > 2 for adj in edge_faces.values()):
        raise ValueError("mesh is non-manifold: an edge belongs to more than two triangles")

    adjacency = defaultdict(list)
    for edge, adjacent in edge_faces.items():
        if len(adjacent) == 2:
            a, b = adjacent
            adjacency[a].append((b, edge))
            adjacency[b].append((a, edge))

    face_coords = {}
    placed_faces = set()
    component_roots = []
    cut_edges = []
    component_offset = 0.0
    for root, tri in enumerate(triangles):
        if root in placed_faces:
            continue
        a, b, c = tri
        ab = _distance(vertices[a], vertices[b])
        ac = _distance(vertices[a], vertices[c])
        bc = _distance(vertices[b], vertices[c])
        if ab <= 1e-12:
            raise ValueError(f"triangle {root} has a zero-length edge")
        cx = (ac * ac + ab * ab - bc * bc) / (2 * ab)
        cy_sq = ac * ac - cx * cx
        if cy_sq < -1e-8:
            raise ValueError(f"triangle {root} violates triangle inequality")
        face_coords[root] = {
            a: (component_offset, 0.0),
            b: (component_offset + ab, 0.0),
            c: (component_offset + cx, math.sqrt(max(0.0, cy_sq))),
        }
        placed_faces.add(root)
        component_roots.append(root)
        component_faces = {root}
        queue = deque([root])
        while queue:
            current = queue.popleft()
            parent = triangles[current]
            parent_coords = face_coords[current]
            for neighbor, edge in adjacency[current]:
                if neighbor in placed_faces:
                    # This adjacency closes a cycle; it becomes a cut in the 2D net.
                    cut_edges.append({"faces": [current, neighbor], "edge": list(edge)})
                    continue
                u, v = edge
                w = next(index for index in triangles[neighbor] if index not in edge)
                pu, pv = parent_coords[u], parent_coords[v]
                length = _distance2(pu, pv)
                duw = _distance(vertices[u], vertices[w])
                dvw = _distance(vertices[v], vertices[w])
                if length <= 1e-12:
                    raise ValueError("Cannot unfold a zero-length shared edge")
                along = (duw * duw - dvw * dvw + length * length) / (2 * length)
                height_sq = duw * duw - along * along
                if height_sq < -1e-7:
                    raise ValueError("Inconsistent edge lengths while unfolding mesh")
                height = math.sqrt(max(0.0, height_sq))
                dx, dy = (pv[0] - pu[0]) / length, (pv[1] - pu[1]) / length
                candidates = [
                    (pu[0] + dx * along - dy * height, pu[1] + dy * along + dx * height),
                    (pu[0] + dx * along + dy * height, pu[1] + dy * along - dx * height),
                ]
                parent_third = next(index for index in parent if index not in edge)
                pp = parent_coords[parent_third]
                cross_parent = (pv[0] - pu[0]) * (pp[1] - pu[1]) - (pv[1] - pu[1]) * (pp[0] - pu[0])
                cross_candidates = [
                    (pv[0] - pu[0]) * (point[1] - pu[1]) - (pv[1] - pu[1]) * (point[0] - pu[0])
                    for point in candidates
                ]
                chosen = candidates[0] if cross_parent * cross_candidates[0] < 0 else candidates[1]
                face_coords[neighbor] = {u: pu, v: pv, w: chosen}
                placed_faces.add(neighbor)
                component_faces.add(neighbor)
                queue.append(neighbor)
        component_points = [point for face_i in component_faces for point in face_coords[face_i].values()]
        component_offset = max(point[0] for point in component_points) + 1.0

    all_points = [point for values in face_coords.values() for point in values.values()]
    min_x = min(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    vertices_2d, triangles_2d = [], []
    for face_i, tri in enumerate(triangles):
        out_face = []
        for corner_i, original_index in enumerate(tri):
            x, y = face_coords[face_i][original_index]
            out_face.append(len(vertices_2d))
            vertices_2d.append({
                "index": len(vertices_2d), "face_index": face_i,
                "corner_index": corner_i, "source_vertex": original_index,
                "x": round(x - min_x, 8), "y": round(y - min_y, 8),
            })
        triangles_2d.append(out_face)
    unique_cut_edges = []
    seen_cut_edges = set()
    for item in cut_edges:
        key = (min(item["faces"]), max(item["faces"]), tuple(item["edge"]))
        if key not in seen_cut_edges:
            seen_cut_edges.add(key)
            unique_cut_edges.append(item)
    return {
        "status": "ok",
        "algorithm": "triangle_bfs_edge_length_unfold",
        "vertices_2d": vertices_2d,
        "triangles_2d": triangles_2d,
        "component_count": len(component_roots),
        "cut_edges": unique_cut_edges,
        "warnings": [
            "Face traversal chooses a spanning forest; cut optimization is not performed.",
            "Self-overlap detection is not performed.",
            "Concave polygon faces must be triangulated upstream.",
        ],
    }
