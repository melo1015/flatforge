import pytest

from flatforge_worker.engines.nesting import nest_parts
from flatforge_worker.engines.ribs import generate_ribs
from flatforge_worker.engines.unfold import unfold_mesh


def test_nesting_places_rectangles_without_overlap_on_simple_shelf():
    result = nest_parts({
        "sheet_width": 100,
        "sheet_height": 100,
        "gap": 2,
        "parts": [
            {"id": "a", "width": 30, "height": 20},
            {"id": "b", "width": 30, "height": 20},
        ],
    })
    assert result["status"] == "ok"
    assert result["placed_count"] == 2
    first, second = result["placements"]
    assert first["x"] != second["x"] or first["y"] != second["y"]
    assert result["algorithm"] == "rectangular_shelf_heuristic"


def test_nesting_reports_unplaced_parts():
    result = nest_parts({
        "sheet_width": 10,
        "sheet_height": 10,
        "allow_rotation": False,
        "parts": [{"id": "large", "width": 20, "height": 20}],
    })
    assert result["status"] == "partial"
    assert result["unplaced"] == ["large"]


def test_nesting_rejects_non_finite_dimensions():
    with pytest.raises(ValueError):
        nest_parts({"parts": [{"width": float("nan"), "height": 2}]})


def test_unfold_triangle_preserves_edge_lengths():
    result = unfold_mesh({
        "mesh": {
            "vertices": [[0, 0, 0], [3, 0, 0], [0, 4, 0]],
            "faces": [[0, 1, 2]],
        }
    })
    assert result["status"] == "ok"
    points = {v["index"]: (v["x"], v["y"]) for v in result["vertices_2d"]}
    import math
    assert math.isclose(math.dist(points[0], points[1]), 3, abs_tol=1e-6)
    assert math.isclose(math.dist(points[0], points[2]), 4, abs_tol=1e-6)
    assert math.isclose(math.dist(points[1], points[2]), 5, abs_tol=1e-6)


def test_unfold_rejects_invalid_vertex_index():
    with pytest.raises(ValueError):
        unfold_mesh({"mesh": {"vertices": [[0, 0, 0]] * 3, "faces": [[0, 1, 4]]}})


def test_ribs_returns_mesh_plane_intersection_segments():
    result = generate_ribs({
        "mesh": {
            "vertices": [[0, 0, 0], [1, 0, 1], [0, 1, 1]],
            "faces": [[0, 1, 2]],
        },
        "axis": "z",
        "spacing": 0.5,
        "start": 0.25,
        "end": 0.75,
    })
    assert result["status"] == "ok"
    assert len(result["planes"]) == 2
    assert result["planes"][0]["segment_count"] >= 1


def test_ribs_rejects_invalid_axis():
    with pytest.raises(ValueError):
        generate_ribs({"mesh": {"vertices": [[0, 0, 0]], "faces": [[0, 0, 0]]}, "axis": "q"})


def test_unfold_duplicates_corners_across_faces_to_preserve_cut_seams():
    result = unfold_mesh({
        "mesh": {
            "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, -1, 0]],
            "faces": [[0, 1, 2], [1, 0, 3]],
        }
    })
    assert len(result["vertices_2d"]) == 6
    assert len(result["triangles_2d"]) == 2
    points = result["vertices_2d"]
    first_edge = {v["source_vertex"]: (v["x"], v["y"]) for v in points[:3] if v["source_vertex"] in (0, 1)}
    second_edge = {v["source_vertex"]: (v["x"], v["y"]) for v in points[3:] if v["source_vertex"] in (0, 1)}
    assert first_edge == second_edge
