"""Deterministic shelf nesting for rectangular 2D parts.

This is a practical first-pass layout engine, not an optimal polygon nest.
Input part records use {id, width, height}; optional sheet_width, sheet_height,
margin, gap, and allow_rotation control the layout.
"""
from __future__ import annotations

import math


def _positive_number(value, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0 if allow_zero else value <= 0:
        raise ValueError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return float(value)


def nest_parts(params: dict) -> dict:
    parts = params.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("'parts' must be a non-empty list")
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

    normalized.sort(key=lambda p: (-max(p["width"], p["height"]), -(p["width"] * p["height"]), str(p["id"])))
    usable_w, usable_h = sheet_width - 2 * margin, sheet_height - 2 * margin
    x = y = row_height = 0.0
    placements, unplaced = [], []
    for part in normalized:
        options = [(part["width"], part["height"], False)]
        if allow_rotation and part["width"] != part["height"]:
            options.append((part["height"], part["width"], True))
        placed = None
        for width, height, rotated in options:
            if width > usable_w or height > usable_h:
                continue
            if x + width > usable_w + 1e-9 or y + height > usable_h + 1e-9:
                continue
            placed = (width, height, rotated, x, y)
            break
        if placed is None:
            new_y = y + row_height + gap if placements else 0.0
            for width, height, rotated in options:
                if width <= usable_w and height <= usable_h and new_y + height <= usable_h + 1e-9:
                    placed = (width, height, rotated, 0.0, new_y)
                    x, y, row_height = 0.0, new_y, 0.0
                    break
        if placed is None:
            unplaced.append(part["id"])
            continue
        width, height, rotated, px, py = placed
        placements.append({
            "id": part["id"], "x": round(margin + px, 6), "y": round(margin + py, 6),
            "width": width, "height": height, "rotated_90": rotated,
        })
        x, y = px + width + gap, py
        row_height = max(row_height, height)

    placed_ids = {str(p["id"]) for p in placements}
    placed_area = sum(p["width"] * p["height"] for p in normalized if str(p["id"]) in placed_ids)
    return {
        "status": "partial" if unplaced else "ok",
        "algorithm": "rectangular_shelf_heuristic",
        "sheet": {"width": sheet_width, "height": sheet_height, "margin": margin, "gap": gap},
        "placements": placements,
        "unplaced": unplaced,
        "utilization": round(placed_area / (sheet_width * sheet_height), 6),
        "placed_count": len(placements),
        "part_count": len(normalized),
        "warning": "Rectangular shelf heuristic; not an optimal polygon nesting algorithm.",
    }
