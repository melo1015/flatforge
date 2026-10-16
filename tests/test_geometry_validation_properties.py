"""Deterministic property-style tests for the independent geometry validator."""
import copy
import random

import pytest

from flatforge_worker.engines.geometry_validation import validate_nesting_result
from flatforge_worker.engines.nesting import nest_parts


@pytest.mark.parametrize("seed", range(12))
def test_validator_accepts_seeded_rectangular_layouts(seed):
    rng = random.Random(seed)
    request = {
        "sheet_width": 140,
        "sheet_height": 100,
        "margin": 2,
        "gap": 1 + (seed % 3),
        "allow_rotation": bool(seed % 2),
        "parts": [
            {
                "id": f"s{seed}-p{i}",
                "width": rng.randint(4, 36),
                "height": rng.randint(4, 28),
            }
            for i in range(18)
        ],
    }
    result = nest_parts(request)
    report = validate_nesting_result(request, result)
    assert report["valid"] is True
    assert report["placed"] == result["placed_count"]
    assert report["unplaced"] == len(result["unplaced"])
    assert report["placed"] + report["unplaced"] == len(request["parts"])


def test_validator_accepts_deterministic_mixed_polygon_layout():
    request = {
        "sheet_width": 160,
        "sheet_height": 120,
        "margin": 3,
        "gap": 2,
        "parts": [
            {"id": "triangle", "points": [[0, 0], [24, 0], [12, 17]]},
            {"id": "concave", "points": [[0, 0], [22, 0], [22, 6], [8, 6], [8, 18], [0, 18]]},
            {"id": "rect", "width": 19, "height": 13},
            {"id": "small-triangle", "points": [[0, 0], [9, 0], [4, 7]]},
            {"id": "wide-rect", "width": 37, "height": 11},
        ],
    }
    first = nest_parts(request)
    second = nest_parts(request)
    assert first == second
    assert validate_nesting_result(request, first)["valid"] is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda result: result["placements"][0].update(x=float("nan")), "finite number"),
        (lambda result: result.update(status="ok" if result["unplaced"] else "partial"), "status does not match"),
        (lambda result: result.update(placed_count=result["placed_count"] + 1), "counts are inconsistent"),
        (lambda result: result["placements"][0].update(id="not-in-request"), "unknown placed part id"),
    ],
)
def test_validator_rejects_corrupted_result_metadata(mutation, message):
    request = {
        "sheet_width": 80,
        "sheet_height": 60,
        "parts": [
            {"id": "a", "width": 12, "height": 9},
            {"id": "b", "width": 15, "height": 11},
        ],
    }
    result = copy.deepcopy(nest_parts(request))
    mutation(result)
    with pytest.raises(ValueError, match=message):
        validate_nesting_result(request, result)
