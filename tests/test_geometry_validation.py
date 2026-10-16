"""Independent validation tests for computed nesting layouts."""
import copy

import pytest

from flatforge_worker.engines.geometry_validation import validate_nesting_result
from flatforge_worker.engines.nesting import nest_parts


def test_validates_rectangular_layout_and_reports_checked_pairs():
    request = {
        "sheet_width": 100, "sheet_height": 70, "margin": 2, "gap": 2,
        "parts": [
            {"id": "a", "width": 30, "height": 20},
            {"id": "b", "width": 25, "height": 18},
            {"id": "c", "width": 15, "height": 10},
        ],
    }
    result = nest_parts(request)
    report = validate_nesting_result(request, result)
    assert report["valid"] is True
    assert report["placed"] == result["placed_count"]
    assert report["checked_pairs"] == report["placed"] * (report["placed"] - 1) // 2


def test_validates_polygon_layout_with_concave_contour():
    request = {
        "sheet_width": 100, "sheet_height": 70, "margin": 2, "gap": 1,
        "parts": [
            {"id": "triangle", "points": [[0, 0], [20, 0], [10, 12]]},
            {"id": "concave", "points": [[0, 0], [12, 0], [12, 4], [4, 4], [4, 12], [0, 12]]},
        ],
    }
    result = nest_parts(request)
    report = validate_nesting_result(request, result)
    assert report["valid"] is True
    assert report["placed"] + report["unplaced"] == len(request["parts"])


def test_rejects_out_of_bounds_placement():
    request = {"sheet_width": 30, "sheet_height": 30, "parts": [{"id": "a", "width": 5, "height": 5}]}
    result = nest_parts(request)
    broken = copy.deepcopy(result)
    broken["placements"][0]["x"] = 28
    with pytest.raises(ValueError, match="exceeds sheet"):
        validate_nesting_result(request, broken)


def test_rejects_overlapping_rectangles_even_if_result_claims_success():
    request = {
        "sheet_width": 50, "sheet_height": 50, "gap": 0,
        "parts": [{"id": "a", "width": 10, "height": 10}, {"id": "b", "width": 10, "height": 10}],
    }
    result = nest_parts(request)
    broken = copy.deepcopy(result)
    broken["placements"][1]["x"] = broken["placements"][0]["x"]
    broken["placements"][1]["y"] = broken["placements"][0]["y"]
    with pytest.raises(ValueError, match="overlap or violate gap"):
        validate_nesting_result(request, broken)


def test_rejects_contour_area_mutation():
    request = {
        "sheet_width": 50, "sheet_height": 50,
        "parts": [{"id": "tri", "points": [[0, 0], [10, 0], [5, 8]]}],
    }
    result = nest_parts(request)
    broken = copy.deepcopy(result)
    broken["placements"][0]["points"][1][0] += 3
    with pytest.raises(ValueError, match="contour area changed"):
        validate_nesting_result(request, broken)


def test_rejects_missing_part_accounting():
    request = {"sheet_width": 30, "sheet_height": 30, "parts": [{"id": "a", "width": 5, "height": 5}]}
    result = nest_parts(request)
    broken = copy.deepcopy(result)
    broken["unplaced"] = []
    broken["placements"] = []
    with pytest.raises(ValueError, match="do not account"):
        validate_nesting_result(request, broken)
