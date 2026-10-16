"""Create a minimal, deterministic SVG from a computed nesting result."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _finite_positive(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"invalid {name} in nesting result")
    return float(value)


def render_cut_svg(result: dict) -> bytes:
    """Return an SVG in millimetres containing only placed rectangular cut outlines."""
    if not isinstance(result, dict) or not isinstance(result.get("sheet"), dict):
        raise ValueError("invalid nesting result")
    sheet = result["sheet"]
    width = _finite_positive(sheet.get("width"), "sheet width")
    height = _finite_positive(sheet.get("height"), "sheet height")
    margin = sheet.get("margin", 0)
    gap = sheet.get("gap", 0)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in (margin, gap)):
        raise ValueError("invalid margin or gap in nesting result")

    placements = result.get("placements")
    if not isinstance(placements, list) or not placements:
        raise ValueError("there are no placed parts to export")

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": f"{width:g}mm",
            "height": f"{height:g}mm",
            "viewBox": f"0 0 {width:g} {height:g}",
            "version": "1.1",
            "role": "img",
            "aria-label": "FlatForge Maker cutting outlines in millimetres",
        },
    )
    for index, part in enumerate(placements):
        if not isinstance(part, dict):
            raise ValueError(f"invalid placement at index {index}")
        x = part.get("x")
        y = part.get("y")
        part_width = _finite_positive(part.get("width"), f"part {index} width")
        part_height = _finite_positive(part.get("height"), f"part {index} height")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (x, y)):
            raise ValueError(f"invalid coordinates for part {index}")
        if x < margin - 1e-6 or y < margin - 1e-6 or x + part_width > width - margin + 1e-6 or y + part_height > height - margin + 1e-6:
            raise ValueError(f"part {index} lies outside the usable sheet")
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}rect",
            {
                "id": f"part-{index + 1}",
                "x": f"{x:g}",
                "y": f"{y:g}",
                "width": f"{part_width:g}",
                "height": f"{part_height:g}",
                "fill": "none",
                "stroke": "#000000",
                "stroke-width": "0.1",
            },
        )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
