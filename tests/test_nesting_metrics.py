"""Independent nesting quality metric tests."""
import pytest

from flatforge_worker.engines.nesting_metrics import calculate_nesting_metrics
from flatforge_worker.engines.nesting import nest_parts


def test_metrics_report_sheet_and_margin_adjusted_utilization():
    request = {
        "sheet_width": 100, "sheet_height": 50, "margin": 5,
        "parts": [
            {"id": "rect", "width": 20, "height": 10},
            {"id": "triangle", "points": [[0, 0], [10, 0], [0, 10]]},
        ],
    }
    result = nest_parts(request)
    metrics = calculate_nesting_metrics(request, result)
    assert metrics["part_count"] == 2
    assert metrics["placed_count"] == result["placed_count"]
    assert metrics["unplaced_count"] == len(result["unplaced"])
    assert metrics["total_part_area"] == pytest.approx(250)
    assert metrics["sheet_area"] == pytest.approx(5000)
    assert metrics["usable_sheet_area"] == pytest.approx(3600)
    assert metrics["material_utilization_percent"] == pytest.approx(5)
    assert metrics["usable_area_percent"] == pytest.approx(250 / 3600 * 100, abs=5e-5)
    assert metrics["completion_percent"] == 100


def test_metrics_account_for_unplaced_parts():
    request = {
        "sheet_width": 10, "sheet_height": 10,
        "parts": [{"id": "fits", "width": 5, "height": 5}, {"id": "too-big", "width": 20, "height": 20}],
    }
    result = nest_parts(request)
    metrics = calculate_nesting_metrics(request, result)
    assert metrics["placed_count"] == 1
    assert metrics["unplaced_count"] == 1
    assert metrics["unplaced_ids"] == result["unplaced"]
    assert metrics["completion_percent"] == 50


def test_metrics_reject_incomplete_part_accounting():
    request = {"sheet_width": 20, "sheet_height": 20, "parts": [{"id": "a", "width": 2, "height": 2}]}
    result = nest_parts(request)
    result["unplaced"] = []
    result["placements"] = []
    with pytest.raises(ValueError, match="do not account"):
        calculate_nesting_metrics(request, result)
