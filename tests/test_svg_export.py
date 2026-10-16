"""Regression tests for the backend-generated cutting SVG."""
import xml.etree.ElementTree as ET

import pytest

from flatforge_maker.svg_export import SVG_NS, render_cut_svg


def test_export_has_mm_dimensions_and_only_unfilled_black_cut_outlines():
    svg = render_cut_svg({
        "sheet": {"width": 300, "height": 200, "margin": 5, "gap": 3},
        "placements": [
            {"id": "panel-a", "x": 5, "y": 5, "width": 100, "height": 50},
            {"id": "panel-b", "x": 108, "y": 5, "width": 80, "height": 40},
        ],
    })
    root = ET.fromstring(svg)
    assert root.tag == f"{{{SVG_NS}}}svg"
    assert root.attrib["width"] == "300mm"
    assert root.attrib["height"] == "200mm"
    assert root.attrib["viewBox"] == "0 0 300 200"
    rectangles = root.findall(f"{{{SVG_NS}}}rect")
    assert len(rectangles) == 2
    assert all(rect.attrib["fill"] == "none" for rect in rectangles)
    assert all(rect.attrib["stroke"] == "#000000" for rect in rectangles)
    assert all(rect.attrib["stroke-width"] == "0.1" for rect in rectangles)


def test_export_rejects_placements_outside_usable_sheet():
    with pytest.raises(ValueError, match="outside the usable sheet"):
        render_cut_svg({
            "sheet": {"width": 100, "height": 100, "margin": 5, "gap": 2},
            "placements": [
                {"x": 4, "y": 5, "width": 10, "height": 10},
            ],
        })


def test_export_rejects_empty_placements():
    with pytest.raises(ValueError, match="no placed parts"):
        render_cut_svg({
            "sheet": {"width": 100, "height": 100, "margin": 0, "gap": 0},
            "placements": [],
        })


def test_export_rejects_non_finite_coordinates():
    with pytest.raises(ValueError, match="coordinates"):
        render_cut_svg({
            "sheet": {"width": 100, "height": 100, "margin": 0, "gap": 0},
            "placements": [
                {"x": float("nan"), "y": 0, "width": 10, "height": 10},
            ],
        })


def test_export_preserves_polygon_cut_contour():
    from flatforge_maker.svg_export import render_cut_svg
    import xml.etree.ElementTree as ET

    result = {
        "sheet": {"width": 100, "height": 80, "margin": 2, "gap": 1},
        "placements": [{
            "id": "triangle", "x": 10, "y": 10, "width": 30, "height": 20,
            "points": [[10, 10], [40, 10], [25, 30]],
        }],
    }
    root = ET.fromstring(render_cut_svg(result))
    polygon = root.find("{http://www.w3.org/2000/svg}polygon")
    assert polygon is not None
    assert polygon.attrib["points"] == "10,10 40,10 25,30"
    assert polygon.attrib["fill"] == "none"
    assert polygon.attrib["stroke"] == "#000000"
