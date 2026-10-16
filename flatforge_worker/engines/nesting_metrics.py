"""Independent, reproducible quality metrics for nesting results.

Metrics describe a returned layout; they do not prove manufacturability or
optimality. Geometry validity should be checked separately.
"""
from __future__ import annotations

import math


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _polygon_area(points, label):
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError(f"{label} must contain at least 3 points")
    normalized = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"{label}[{index}] must be [x, y]")
        normalized.append((
            _finite(point[0], f"{label}[{index}].x"),
            _finite(point[1], f"{label}[{index}].y"),
        ))
    return abs(sum(
        normalized[i][0] * normalized[(i + 1) % len(normalized)][1]
        - normalized[(i + 1) % len(normalized)][0] * normalized[i][1]
        for i in range(len(normalized))
    )) / 2.0


def calculate_nesting_metrics(request, result):
    """Return material-use and completion metrics for a nesting result.

    Material utilization uses full sheet area. Usable-area utilization uses
    sheet area after removing margins. These ratios are separate intentionally.
    """
    if not isinstance(request, dict) or not isinstance(result, dict):
        raise ValueError("request and result must be objects")
    parts = request.get("parts")
    placements = result.get("placements")
    unplaced = result.get("unplaced")
    sheet = result.get("sheet")
    if not isinstance(parts, list) or not isinstance(placements, list) or not isinstance(unplaced, list):
        raise ValueError("parts, placements, and unplaced must be lists")
    if not isinstance(sheet, dict):
        raise ValueError("result.sheet must be an object")

    width = _finite(sheet.get("width"), "sheet.width")
    height = _finite(sheet.get("height"), "sheet.height")
    margin = _finite(sheet.get("margin", 0), "sheet.margin")
    if width <= 0 or height <= 0 or margin < 0 or margin * 2 >= width or margin * 2 >= height:
        raise ValueError("invalid sheet dimensions or margin")

    source = {}
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            raise ValueError(f"parts[{index}] must be an object")
        pid = str(part.get("id", str(index + 1)))
        if pid in source:
            raise ValueError(f"duplicate part id: {pid}")
        if "points" in part:
            area = _polygon_area(part["points"], f"parts[{index}].points")
        else:
            part_width = _finite(part.get("width"), f"parts[{index}].width")
            part_height = _finite(part.get("height"), f"parts[{index}].height")
            if part_width <= 0 or part_height <= 0:
                raise ValueError(f"part {pid} dimensions must be positive")
            area = part_width * part_height
        source[pid] = area

    placed_ids = []
    placed_area = 0.0
    for index, placement in enumerate(placements):
        if not isinstance(placement, dict):
            raise ValueError(f"placements[{index}] must be an object")
        pid = str(placement.get("id"))
        if pid not in source:
            raise ValueError(f"unknown placed part id: {placement.get('id')}")
        if pid in placed_ids:
            raise ValueError(f"duplicate placement id: {placement.get('id')}")
        placed_ids.append(pid)
        placed_area += source[pid]

    unplaced_ids = [str(pid) for pid in unplaced]
    if len(unplaced_ids) != len(set(unplaced_ids)):
        raise ValueError("duplicate IDs in unplaced list")
    if set(placed_ids) & set(unplaced_ids):
        raise ValueError("part is both placed and unplaced")
    if set(placed_ids) | set(unplaced_ids) != set(source):
        raise ValueError("placed/unplaced IDs do not account for every input part")

    sheet_area = width * height
    usable_area = (width - 2 * margin) * (height - 2 * margin)
    total_part_area = sum(source.values())
    return {
        "part_count": len(source),
        "placed_count": len(placed_ids),
        "unplaced_count": len(unplaced_ids),
        "completion_percent": round(100.0 * len(placed_ids) / len(source), 2) if source else 100.0,
        "placed_part_area": round(placed_area, 6),
        "total_part_area": round(total_part_area, 6),
        "sheet_area": round(sheet_area, 6),
        "usable_sheet_area": round(usable_area, 6),
        "material_utilization_percent": round(100.0 * placed_area / sheet_area, 4),
        "usable_area_percent": round(100.0 * placed_area / usable_area, 4),
        "unplaced_ids": list(unplaced),
    }
