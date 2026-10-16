"""Geometry invariants for the rectangular nesting engine."""
from flatforge_worker.engines.nesting import nest_parts


def _assert_no_overlap_and_inside_sheet(result, sheet_width, sheet_height, margin, gap):
    parts = result["placements"]
    for part in parts:
        assert part["x"] >= margin - 1e-6
        assert part["y"] >= margin - 1e-6
        assert part["x"] + part["width"] <= sheet_width - margin + 1e-6
        assert part["y"] + part["height"] <= sheet_height - margin + 1e-6

    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            separated = (
                a["x"] + a["width"] + gap <= b["x"] + 1e-6
                or b["x"] + b["width"] + gap <= a["x"] + 1e-6
                or a["y"] + a["height"] + gap <= b["y"] + 1e-6
                or b["y"] + b["height"] + gap <= a["y"] + 1e-6
            )
            assert separated, f"parts overlap or violate the gap: {a['id']} and {b['id']}"


def test_rotates_a_part_when_only_rotated_orientation_fits():
    result = nest_parts({
        "sheet_width": 50,
        "sheet_height": 80,
        "margin": 2,
        "allow_rotation": True,
        "parts": [{"id": "tall", "width": 70, "height": 40}],
    })
    assert result["status"] == "ok"
    assert result["placements"][0]["rotated_90"] is True
    assert result["placements"][0]["width"] == 40
    assert result["placements"][0]["height"] == 70


def test_spacing_and_margins_are_respected_for_many_parts():
    request = {
        "sheet_width": 320,
        "sheet_height": 240,
        "margin": 7,
        "gap": 4,
        "allow_rotation": True,
        "parts": [
            {"id": f"p{i}", "width": 30 + (i % 3) * 7, "height": 18 + (i % 4) * 5}
            for i in range(20)
        ],
    }
    result = nest_parts(request)
    _assert_no_overlap_and_inside_sheet(
        result, request["sheet_width"], request["sheet_height"], request["margin"], request["gap"]
    )
    assert result["placed_count"] + len(result["unplaced"]) == len(request["parts"])


def test_layout_is_deterministic_for_same_request():
    request = {
        "sheet_width": 200,
        "sheet_height": 150,
        "gap": 3,
        "parts": [
            {"id": "A", "width": 70, "height": 40},
            {"id": "B", "width": 50, "height": 50},
            {"id": "C", "width": 60, "height": 20},
        ],
    }
    assert nest_parts(request) == nest_parts(request)


def test_rejects_more_than_500_parts():
    import pytest
    with pytest.raises(ValueError, match="500 parts"):
        nest_parts({"parts": [{"id": str(i), "width": 1, "height": 1} for i in range(501)]})
