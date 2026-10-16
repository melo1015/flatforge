"""Independent geometry checks for nesting results.

This module deliberately does not call or reuse the placement algorithms. It
validates their output against the original request before results are shown or
exported. It is a consistency/safety check, not a manufacturing certification.
"""
from __future__ import annotations

import math

EPS = 1e-5


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"geometry validation: {label} must be a finite number")
    return float(value)


def _points(part, label):
    points = part.get("points")
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError(f"geometry validation: {label} must have at least 3 contour points")
    output = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"geometry validation: {label}[{index}] must be [x, y]")
        output.append((_finite(point[0], f"{label}[{index}].x"), _finite(point[1], f"{label}[{index}].y")))
    return output


def _area(points):
    return abs(sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )) / 2.0


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p):
    return abs(_cross(a, b, p)) <= EPS and min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS


def _segments_intersect(a, b, c, d):
    ab_c, ab_d = _cross(a, b, c), _cross(a, b, d)
    cd_a, cd_b = _cross(c, d, a), _cross(c, d, b)
    if ((ab_c > EPS and ab_d < -EPS) or (ab_c < -EPS and ab_d > EPS)) and ((cd_a > EPS and cd_b < -EPS) or (cd_a < -EPS and cd_b > EPS)):
        return True
    return any((
        abs(ab_c) <= EPS and _on_segment(a, b, c),
        abs(ab_d) <= EPS and _on_segment(a, b, d),
        abs(cd_a) <= EPS and _on_segment(c, d, a),
        abs(cd_b) <= EPS and _on_segment(c, d, b),
    ))


def _proper_intersection(a, b, c, d):
    ab_c, ab_d = _cross(a, b, c), _cross(a, b, d)
    cd_a, cd_b = _cross(c, d, a), _cross(c, d, b)
    return ((ab_c > EPS and ab_d < -EPS) or (ab_c < -EPS and ab_d > EPS)) and ((cd_a > EPS and cd_b < -EPS) or (cd_a < -EPS and cd_b > EPS))


def _inside(point, polygon):
    x, y = point
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if _on_segment(a, b, point):
            return False
        if (a[1] > y) != (b[1] > y):
            cross_x = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < cross_x:
                inside = not inside
    return inside


def _point_segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    t = 0.0 if den <= EPS * EPS else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / den))
    return math.hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy))


def _edge_distance(a, b, c, d):
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(_point_segment_distance(a, c, d), _point_segment_distance(b, c, d),
               _point_segment_distance(c, a, b), _point_segment_distance(d, a, b))


def _vertex_on_boundary(point, polygon):
    return any(_on_segment(polygon[i], polygon[(i + 1) % len(polygon)], point) for i in range(len(polygon)))


def _polygons_conflict(a, b, gap):
    if any(_proper_intersection(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)])
           for i in range(len(a)) for j in range(len(b))):
        return True
    if _inside(a[0], b) or _inside(b[0], a):
        return True
    # Coincident contours have no proper crossings and all vertices lie on
    # the opposite boundary, but they occupy exactly the same area.
    if all(_vertex_on_boundary(point, b) for point in a) and all(_vertex_on_boundary(point, a) for point in b):
        return True
    if gap > EPS:
        return any(_edge_distance(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)]) < gap - EPS
                   for i in range(len(a)) for j in range(len(b)))
    return False


def _same_contour_shape(source, contour):
    """Compare ordered edge vectors, ignoring translation and 90-degree rotation."""
    if len(source) != len(contour):
        return False

    def edges(points):
        return [
            (points[(i + 1) % len(points)][0] - points[i][0],
             points[(i + 1) % len(points)][1] - points[i][1])
            for i in range(len(points))
        ]

    source_edges = edges(source)
    contour_edges = edges(contour)
    variants = [
        source_edges,
        [(dy, -dx) for dx, dy in source_edges],
    ]
    for expected in variants:
        for offset in range(len(expected)):
            shifted = expected[offset:] + expected[:offset]
            if all(abs(a[0] - b[0]) <= EPS and abs(a[1] - b[1]) <= EPS
                   for a, b in zip(shifted, contour_edges)):
                return True
    return False


def _rect_polygon(placement):
    x, y = placement["x"], placement["y"]
    w, h = placement["width"], placement["height"]
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def validate_nesting_result(request, result):
    """Raise ValueError if a computed layout violates request geometry invariants.

    Returns a small report on success. The function never changes the result.
    """
    if not isinstance(request, dict) or not isinstance(result, dict):
        raise ValueError("geometry validation: request and result must be objects")
    sheet = result.get("sheet")
    if not isinstance(sheet, dict):
        raise ValueError("geometry validation: result is missing sheet dimensions")
    sw = _finite(sheet.get("width"), "sheet.width")
    sh = _finite(sheet.get("height"), "sheet.height")
    margin = _finite(sheet.get("margin", 0), "sheet.margin")
    gap = _finite(sheet.get("gap", 0), "sheet.gap")
    if sw <= 0 or sh <= 0 or margin < 0 or gap < 0 or margin * 2 >= sw or margin * 2 >= sh:
        raise ValueError("geometry validation: invalid sheet dimensions, margin, or gap")

    input_parts = request.get("parts")
    placements = result.get("placements")
    unplaced = result.get("unplaced")
    if not isinstance(input_parts, list) or not isinstance(placements, list) or not isinstance(unplaced, list):
        raise ValueError("geometry validation: parts, placements, and unplaced must be lists")

    source_by_id = {}
    for index, part in enumerate(input_parts):
        if not isinstance(part, dict):
            raise ValueError(f"geometry validation: parts[{index}] must be an object")
        pid = part.get("id", str(index + 1))
        key = str(pid)
        if key in source_by_id:
            raise ValueError(f"geometry validation: duplicate input part id {pid}")
        if "points" in part:
            source_points = _points(part, f"parts[{index}].points")
            source_by_id[key] = {"id": pid, "points": source_points, "area": _area(source_points)}
        else:
            w = _finite(part.get("width"), f"parts[{index}].width")
            h = _finite(part.get("height"), f"parts[{index}].height")
            if w <= 0 or h <= 0:
                raise ValueError(f"geometry validation: part {pid} dimensions must be positive")
            source_by_id[key] = {"id": pid, "width": w, "height": h, "area": w * h}

    placed_keys = []
    geometry = []
    for index, placement in enumerate(placements):
        if not isinstance(placement, dict):
            raise ValueError(f"geometry validation: placements[{index}] must be an object")
        key = str(placement.get("id"))
        if key not in source_by_id:
            raise ValueError(f"geometry validation: unknown placed part id {placement.get('id')}")
        if key in placed_keys:
            raise ValueError(f"geometry validation: duplicate placement for part {placement.get('id')}")
        placed_keys.append(key)
        x = _finite(placement.get("x"), f"placements[{index}].x")
        y = _finite(placement.get("y"), f"placements[{index}].y")
        w = _finite(placement.get("width"), f"placements[{index}].width")
        h = _finite(placement.get("height"), f"placements[{index}].height")
        if w <= 0 or h <= 0:
            raise ValueError(f"geometry validation: placement {placement.get('id')} has non-positive bounds")
        if x < margin - EPS or y < margin - EPS or x + w > sw - margin + EPS or y + h > sh - margin + EPS:
            raise ValueError(f"geometry validation: part {placement.get('id')} exceeds sheet usable bounds")

        source = source_by_id[key]
        if "points" in source:
            contour = _points(placement, f"placements[{index}].points")
            if len(contour) != len(source["points"]):
                raise ValueError(f"geometry validation: contour vertex count changed for part {placement.get('id')}")
            if abs(_area(contour) - source["area"]) > max(EPS, source["area"] * 1e-5):
                raise ValueError(f"geometry validation: contour area changed for part {placement.get('id')}")
            if not _same_contour_shape(source["points"], contour):
                raise ValueError(f"geometry validation: contour shape changed for part {placement.get('id')}")
            min_x, min_y = min(p[0] for p in contour), min(p[1] for p in contour)
            max_x, max_y = max(p[0] for p in contour), max(p[1] for p in contour)
            if abs(min_x - x) > EPS or abs(min_y - y) > EPS or abs(max_x - min_x - w) > EPS or abs(max_y - min_y - h) > EPS:
                raise ValueError(f"geometry validation: contour bounds disagree with placement for part {placement.get('id')}")
            polygon = contour
        else:
            expected_w, expected_h = source["width"], source["height"]
            rotated = placement.get("rotated_90", False)
            if not isinstance(rotated, bool):
                raise ValueError(f"geometry validation: invalid rotation flag for part {placement.get('id')}")
            expected = (expected_h, expected_w) if rotated else (expected_w, expected_h)
            if abs(w - expected[0]) > EPS or abs(h - expected[1]) > EPS:
                raise ValueError(f"geometry validation: dimensions/rotation disagree for part {placement.get('id')}")
            polygon = _rect_polygon({"x": x, "y": y, "width": w, "height": h})
        geometry.append((placement.get("id"), polygon))

    unplaced_keys = [str(pid) for pid in unplaced]
    if len(unplaced_keys) != len(set(unplaced_keys)):
        raise ValueError("geometry validation: duplicate IDs in unplaced list")
    if set(placed_keys) & set(unplaced_keys):
        raise ValueError("geometry validation: a part is both placed and unplaced")
    if set(placed_keys) | set(unplaced_keys) != set(source_by_id):
        raise ValueError("geometry validation: placed/unplaced IDs do not account for every input part")

    for i, (aid, a) in enumerate(geometry):
        for bid, b in geometry[i + 1:]:
            if _polygons_conflict(a, b, gap):
                raise ValueError(f"geometry validation: parts {aid} and {bid} overlap or violate gap {gap:g}")

    expected_status = "partial" if unplaced else "ok"
    if result.get("status") != expected_status:
        raise ValueError("geometry validation: status does not match placed/unplaced parts")
    if result.get("placed_count") != len(placements) or result.get("part_count") != len(source_by_id):
        raise ValueError("geometry validation: result counts are inconsistent")

    return {"valid": True, "placed": len(placements), "unplaced": len(unplaced), "checked_pairs": len(placements) * (len(placements) - 1) // 2}
