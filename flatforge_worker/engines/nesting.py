"""Deterministic MaxRects-style nesting for rectangular 2D parts.

This engine handles rectangles only. It uses a best-short-side-fit heuristic,
not an optimal solver or a polygon nesting algorithm.
"""
from __future__ import annotations

import math

from flatforge_worker.engines.polygon_nesting import nest_polygon_parts


_EPSILON = 1e-9


def _positive_number(value, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0 if allow_zero else value <= 0:
        raise ValueError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return float(value)


def _intersects(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"] + _EPSILON
        or b["x"] + b["width"] <= a["x"] + _EPSILON
        or a["y"] + a["height"] <= b["y"] + _EPSILON
        or b["y"] + b["height"] <= a["y"] + _EPSILON
    )


def _contains(outer: dict, inner: dict) -> bool:
    return (
        inner["x"] >= outer["x"] - _EPSILON
        and inner["y"] >= outer["y"] - _EPSILON
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + _EPSILON
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + _EPSILON
    )


def _split_free_rectangles(free_rectangles: list[dict], used: dict) -> list[dict]:
    """Split every intersecting free rectangle around a newly occupied rectangle."""
    result = []
    for free in free_rectangles:
        if not _intersects(free, used):
            result.append(free)
            continue

        if used["x"] > free["x"] + _EPSILON:
            result.append({
                "x": free["x"], "y": free["y"],
                "width": used["x"] - free["x"], "height": free["height"],
            })
        if used["x"] + used["width"] < free["x"] + free["width"] - _EPSILON:
            result.append({
                "x": used["x"] + used["width"], "y": free["y"],
                "width": free["x"] + free["width"] - (used["x"] + used["width"]),
                "height": free["height"],
            })
        if used["y"] > free["y"] + _EPSILON:
            result.append({
                "x": free["x"], "y": free["y"],
                "width": free["width"], "height": used["y"] - free["y"],
            })
        if used["y"] + used["height"] < free["y"] + free["height"] - _EPSILON:
            result.append({
                "x": free["x"], "y": used["y"] + used["height"],
                "width": free["width"],
                "height": free["y"] + free["height"] - (used["y"] + used["height"]),
            })

    result = [r for r in result if r["width"] > _EPSILON and r["height"] > _EPSILON]
    pruned = []
    for i, rect in enumerate(result):
        rect_area = rect["width"] * rect["height"]
        contained = False
        for j, other in enumerate(result):
            if i == j or not _contains(other, rect):
                continue
            other_area = other["width"] * other["height"]
            if other_area > rect_area + _EPSILON or (
                math.isclose(other_area, rect_area, abs_tol=_EPSILON) and j < i
            ):
                contained = True
                break
        if contained:
            continue
        if not any(
            math.isclose(rect["x"], other["x"], abs_tol=_EPSILON)
            and math.isclose(rect["y"], other["y"], abs_tol=_EPSILON)
            and math.isclose(rect["width"], other["width"], abs_tol=_EPSILON)
            and math.isclose(rect["height"], other["height"], abs_tol=_EPSILON)
            for other in pruned
        ):
            pruned.append(rect)
    return pruned


def nest_parts(params: dict) -> dict:
    if not isinstance(params, dict):
        raise ValueError("request must be an object")
    parts = params.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("'parts' must be a non-empty list")
    if len(parts) > 500:
        raise ValueError("at most 500 parts are supported per nesting request")
    if any(isinstance(part, dict) and "points" in part for part in parts):
        return nest_polygon_parts(params)

    sheet_width = _positive_number(params.get("sheet_width", 1000), "sheet_width")
    sheet_height = _positive_number(params.get("sheet_height", 1000), "sheet_height")
    margin = _positive_number(params.get("margin", 0), "margin", allow_zero=True)
    gap = _positive_number(params.get("gap", 0), "gap", allow_zero=True)
    allow_rotation = params.get("allow_rotation", True)
    if not isinstance(allow_rotation, bool):
        raise ValueError("allow_rotation must be a boolean")
    if margin * 2 >= sheet_width or margin * 2 >= sheet_height:
        raise ValueError("margin leaves no usable sheet area")

    normalized = []
    seen = set()
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            raise ValueError(f"parts[{index}] must be an object")
        part_id = part.get("id", str(index + 1))
        if not isinstance(part_id, (str, int)) or isinstance(part_id, bool):
            raise ValueError(f"parts[{index}].id must be a string or integer")
        if str(part_id) in seen:
            raise ValueError(f"duplicate part id: {part_id}")
        seen.add(str(part_id))
        width = _positive_number(part.get("width"), f"parts[{index}].width")
        height = _positive_number(part.get("height"), f"parts[{index}].height")
        normalized.append({"id": part_id, "width": width, "height": height})

    normalized.sort(
        key=lambda p: (-max(p["width"], p["height"]), -(p["width"] * p["height"]), str(p["id"]))
    )
    usable_w = sheet_width - 2 * margin
    usable_h = sheet_height - 2 * margin
    # One gap is added to occupied rectangles and to the usable rectangle. This
    # enforces spacing between parts without imposing a gap at the sheet edge.
    free_rectangles = [{
        "x": margin, "y": margin,
        "width": usable_w + gap, "height": usable_h + gap,
    }]
    placements, unplaced = [], []

    for part in normalized:
        orientations = [(part["width"], part["height"], False)]
        if allow_rotation and not math.isclose(part["width"], part["height"], abs_tol=_EPSILON):
            orientations.append((part["height"], part["width"], True))

        best = None
        for width, height, rotated in orientations:
            padded_w, padded_h = width + gap, height + gap
            if width > usable_w + _EPSILON or height > usable_h + _EPSILON:
                continue
            for free_index, free in enumerate(free_rectangles):
                if padded_w > free["width"] + _EPSILON or padded_h > free["height"] + _EPSILON:
                    continue
                leftover_h = free["height"] - padded_h
                leftover_w = free["width"] - padded_w
                score = (
                    min(leftover_w, leftover_h),
                    max(leftover_w, leftover_h),
                    free["y"], free["x"], rotated, free_index,
                )
                if best is None or score < best[0]:
                    best = (score, free, width, height, rotated, padded_w, padded_h)

        if best is None:
            unplaced.append(part["id"])
            continue

        _, free, width, height, rotated, padded_w, padded_h = best
        used = {"x": free["x"], "y": free["y"], "width": padded_w, "height": padded_h}
        placements.append({
            "id": part["id"], "x": round(used["x"], 6), "y": round(used["y"], 6),
            "width": width, "height": height, "rotated_90": rotated,
        })
        free_rectangles = _split_free_rectangles(free_rectangles, used)

    placed_ids = {str(p["id"]) for p in placements}
    placed_area = sum(
        p["width"] * p["height"] for p in normalized if str(p["id"]) in placed_ids
    )
    return {
        "status": "partial" if unplaced else "ok",
        "algorithm": "rectangular_maxrects_best_short_side_fit",
        "sheet": {"width": sheet_width, "height": sheet_height, "margin": margin, "gap": gap},
        "placements": placements,
        "unplaced": unplaced,
        "utilization": round(placed_area / (sheet_width * sheet_height), 6),
        "placed_count": len(placements),
        "part_count": len(normalized),
        "warning": (
            "Rectangular MaxRects-style heuristic; not an optimal polygon nesting algorithm. "
            "Verify clearances and exported scale before fabrication."
        ),
    }
