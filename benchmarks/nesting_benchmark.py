"""Reproducible, dependency-free nesting quality benchmark.

Run from the repository root:
    python benchmarks/nesting_benchmark.py --iterations 5
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flatforge_worker.engines.nesting import nest_parts
from flatforge_worker.engines.polygon_nesting import nest_polygon_parts
from flatforge_worker.engines.geometry_validation import validate_nesting_result
from flatforge_worker.engines.nesting_metrics import calculate_nesting_metrics


CASES = [
    {
        "name": "rectangles_mixed",
        "request": {
            "sheet_width": 100, "sheet_height": 70, "margin": 2, "gap": 1,
            "parts": [
                {"id": "a", "width": 30, "height": 20},
                {"id": "b", "width": 25, "height": 18},
                {"id": "c", "width": 22, "height": 16},
                {"id": "d", "width": 18, "height": 14},
                {"id": "e", "width": 12, "height": 28},
                {"id": "f", "width": 15, "height": 10},
                {"id": "g", "width": 11, "height": 9},
                {"id": "h", "width": 8, "height": 8},
            ],
        },
    },
    {
        "name": "rectangles_tight_fit",
        "request": {
            "sheet_width": 60, "sheet_height": 40, "margin": 1, "gap": 1,
            "parts": [
                {"id": "a", "width": 28, "height": 18},
                {"id": "b", "width": 28, "height": 18},
                {"id": "c", "width": 18, "height": 10},
                {"id": "d", "width": 18, "height": 10},
                {"id": "e", "width": 10, "height": 10},
            ],
        },
    },
    {
        "name": "polygons_mixed",
        "request": {
            "sheet_width": 100, "sheet_height": 70, "margin": 2, "gap": 1,
            "parts": [
                {"id": "tri_a", "points": [[0, 0], [24, 0], [12, 16]]},
                {"id": "tri_b", "points": [[0, 0], [24, 0], [12, 16]]},
                {"id": "rect_a", "width": 20, "height": 12},
                {"id": "concave", "points": [[0, 0], [18, 0], [18, 5], [6, 5], [6, 14], [0, 14]]},
                {"id": "small", "points": [[0, 0], [10, 0], [5, 8]]},
            ],
        },
    },
]


def run_benchmarks(iterations: int = 5) -> dict:
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be an integer >= 1")
    results = []
    for case in CASES:
        modes = ("compact_envelope", "bottom_left") if case["name"] == "polygons_mixed" else (None,)
        for mode in modes:
            samples = []
            reference = None
            for _ in range(iterations):
                started = time.perf_counter()
                result = (
                    nest_polygon_parts(case["request"], scoring=mode)
                    if mode is not None else nest_parts(case["request"])
                )
                samples.append((time.perf_counter() - started) * 1000)
                # Never report quality metrics for a geometrically invalid layout.
                validation = validate_nesting_result(case["request"], result)
                metrics = calculate_nesting_metrics(case["request"], result)
                stable = {
                    "status": result["status"],
                    "placements": result["placements"],
                    "unplaced": result["unplaced"],
                    "utilization": result["utilization"],
                }
                if reference is not None and stable != reference:
                    raise AssertionError(
                        f"non-deterministic result for {case['name']} ({mode or 'default'})"
                    )
                reference = stable
            results.append({
                "case": case["name"],
                "comparison": mode or "default",
                "algorithm": result["algorithm"],
                "iterations": iterations,
                "median_ms": round(statistics.median(samples), 3),
                "min_ms": round(min(samples), 3),
                "placed": result["placed_count"],
                "total": result["part_count"],
                "unplaced": result["unplaced"],
                "utilization_percent": round(result["utilization"] * 100, 2),
                "deterministic": True,
                "geometry_valid": validation["valid"],
                "checked_pairs": validation["checked_pairs"],
                "completion_percent": metrics["completion_percent"],
                "placed_part_area": metrics["placed_part_area"],
                "usable_area_percent": metrics["usable_area_percent"],
                "unplaced_ids": metrics["unplaced_ids"],
            })
    return {
        "benchmark_version": 2,
        "note": (
            "Runtime is machine-dependent. The polygon case compares the current compact-envelope "
            "score with the pre-0.7 bottom-left score on identical input; this is a heuristic "
            "comparison, not proof of global optimality."
        ),
        "results": results,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5, help="repetitions per scenario (default: 5)")
    args = parser.parse_args()
    print(json.dumps(run_benchmarks(args.iterations), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
