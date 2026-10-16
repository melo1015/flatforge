"""Strict, dependency-free importer for simple SVG part outlines.

Supported: rect, polygon, and explicitly closed polyline elements directly inside
the root SVG. SVG transforms, styles, paths, references, and nested groups are
rejected rather than silently misinterpreted.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
MAX_SVG_BYTES = 256 * 1024
_NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _number(value: str | None, label: str, default: float | None = None) -> float:
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"{label} is required")
    if not _NUMBER.fullmatch(value.strip()):
        raise ValueError(f"{label} must be a plain finite number; units and expressions are unsupported")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _points(value: str, label: str) -> list[tuple[float, float]]:
    numbers = [float(item) for item in _NUMBER.findall(value)]
    residue = _NUMBER.sub("", value)
    if residue.strip(" ,\t\r\n") or len(numbers) < 6 or len(numbers) % 2:
        raise ValueError(f"{label} must contain at least three x,y points")
    if not all(math.isfinite(item) for item in numbers):
        raise ValueError(f"{label} coordinates must be finite")
    points = list(zip(numbers[::2], numbers[1::2]))
    if points[0] == points[-1]:
        points.pop()
    if len(set(points)) < 3:
        raise ValueError(f"{label} must have at least three distinct points")
    return points


def import_svg_outlines(source: str) -> dict:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("SVG content is required")
    encoded = source.encode("utf-8")
    if len(encoded) > MAX_SVG_BYTES:
        raise ValueError("SVG exceeds the 256 KiB import limit")
    lowered = source.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise ValueError("DOCTYPE and entity declarations are not allowed")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise ValueError("The uploaded file is not valid XML/SVG") from exc
    if root.tag != f"{{{SVG_NS}}}svg":
        raise ValueError("The document root must be an SVG element")
    if len(root) == 0:
        raise ValueError("SVG contains no supported part outlines")

    outlines = []
    for index, element in enumerate(list(root), start=1):
        tag = element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""
        if tag not in {"rect", "polygon", "polyline"} or element.tag != f"{{{SVG_NS}}}{tag}":
            raise ValueError(f"Element {index} ({tag or 'unknown'}) is unsupported; use rect, polygon, or closed polyline")
        if list(element):
            raise ValueError("Nested SVG elements are not supported")
        for attribute in element.attrib:
            local = attribute.rsplit("}", 1)[-1].lower()
            if local.startswith("on") or local in {"transform", "style", "href", "class"}:
                raise ValueError(f"Attribute '{local}' is unsupported for safe geometry import")

        if tag == "rect":
            x = _number(element.get("x"), f"rect {index} x", 0)
            y = _number(element.get("y"), f"rect {index} y", 0)
            width = _number(element.get("width"), f"rect {index} width")
            height = _number(element.get("height"), f"rect {index} height")
            if width <= 0 or height <= 0:
                raise ValueError(f"rect {index} width and height must be positive")
            points = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
        else:
            points = _points(element.get("points", ""), f"{tag} {index}")
            if tag == "polyline":
                raw_points = _points_allow_closed(element.get("points", ""), f"polyline {index}")
                if not raw_points[0] == raw_points[-1]:
                    raise ValueError(f"polyline {index} must be closed (first point equals last point)")
                points = raw_points[:-1]

        min_x = min(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_x = max(p[0] for p in points)
        max_y = max(p[1] for p in points)
        width, height = max_x - min_x, max_y - min_y
        if width <= 0 or height <= 0:
            raise ValueError(f"Shape {index} has zero width or height")
        normalized = [[round(x - min_x, 6), round(y - min_y, 6)] for x, y in points]
        outlines.append({
            "id": element.get("id") or f"SVG {index}",
            "shape": tag,
            "width": round(width, 6),
            "height": round(height, 6),
            "points": normalized,
            "source_bounds": {"x": min_x, "y": min_y, "width": width, "height": height},
        })
    return {
        "count": len(outlines),
        "outlines": outlines,
        "warning": "Los contornos se conservan en la importación, pero el anidado y la exportación actuales usan cajas rectangulares envolventes. No fabricar como geometría final hasta implementar anidado poligonal.",
    }


def _points_allow_closed(value: str, label: str) -> list[tuple[float, float]]:
    numbers = [float(item) for item in _NUMBER.findall(value)]
    residue = _NUMBER.sub("", value)
    if residue.strip(" ,\t\r\n") or len(numbers) < 8 or len(numbers) % 2:
        raise ValueError(f"{label} must contain at least three points and repeat the first point at the end")
    if not all(math.isfinite(item) for item in numbers):
        raise ValueError(f"{label} coordinates must be finite")
    return list(zip(numbers[::2], numbers[1::2]))
