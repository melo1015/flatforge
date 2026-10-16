"""Smoke tests for the reproducible benchmark report."""
from benchmarks.nesting_benchmark import run_benchmarks


def test_benchmark_reports_validated_quality_metrics():
    report = run_benchmarks(iterations=1)
    assert report["benchmark_version"] == 2
    assert len(report["results"]) == 4
    for result in report["results"]:
        assert result["geometry_valid"] is True
        assert result["deterministic"] is True
        assert result["placed"] + len(result["unplaced_ids"]) == result["total"]
        assert 0 <= result["completion_percent"] <= 100
        assert result["placed_part_area"] >= 0
        assert result["checked_pairs"] == result["placed"] * (result["placed"] - 1) // 2
