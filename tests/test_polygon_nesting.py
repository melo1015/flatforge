import pytest
from flatforge_worker.engines.polygon_nesting import nest_polygon_parts, _conflict


def test_places_triangle_and_preserves_absolute_contour():
    result=nest_polygon_parts({"sheet_width":100,"sheet_height":100,"margin":5,"gap":2,"parts":[{"id":"tri","points":[[0,0],[30,0],[15,20]]}]})
    assert result["status"]=="ok"
    assert result["placements"][0]["points"]==[[5.0,5.0],[35.0,5.0],[20.0,25.0]]
    assert result["placements"][0]["area"]==300


def test_two_triangles_respect_gap():
    result=nest_polygon_parts({"sheet_width":100,"sheet_height":50,"margin":2,"gap":3,"allow_rotation":False,"parts":[{"id":"a","points":[[0,0],[20,0],[10,10]]},{"id":"b","points":[[0,0],[20,0],[10,10]]}]})
    assert result["placed_count"]==2
    a,b=result["placements"]
    assert not _conflict([tuple(p) for p in a["points"]],[tuple(p) for p in b["points"]],3)


def test_rejects_self_intersection():
    with pytest.raises(ValueError,match="simple polygon"):
        nest_polygon_parts({"parts":[{"id":"bow","points":[[0,0],[10,10],[0,10],[10,0]]}]})


def test_rejects_negative_point():
    with pytest.raises(ValueError,match="non-negative"):
        nest_polygon_parts({"parts":[{"id":"bad","points":[[0,0],[10,0],[-1,4]]}]})


def test_polygon_part_limit():
    with pytest.raises(ValueError,match="at most 100"):
        nest_polygon_parts({"parts":[{"id":str(i),"points":[[0,0],[1,0],[0,1]]} for i in range(101)]})


def test_identical_polygons_cannot_occupy_the_same_space():
    result = nest_polygon_parts({
        "sheet_width": 30, "sheet_height": 30, "margin": 0, "gap": 0,
        "allow_rotation": False,
        "parts": [
            {"id": "one", "points": [[0, 0], [10, 0], [5, 8]]},
            {"id": "two", "points": [[0, 0], [10, 0], [5, 8]]},
        ],
    })
    assert result["placed_count"] == 2
    a, b = result["placements"]
    assert a["points"] != b["points"]

def test_concave_polygon_is_accepted_and_area_is_preserved():
    result = nest_polygon_parts({
        "sheet_width": 30, "sheet_height": 30, "margin": 2,
        "parts": [{"id": "concave", "points": [
            [0, 0], [10, 0], [10, 4], [4, 4], [4, 10], [0, 10]
        ]}],
    })
    assert result["status"] == "ok"
    assert result["placements"][0]["area"] == 64


def test_rotation_allows_part_to_fit_tight_sheet():
    result = nest_polygon_parts({
        "sheet_width": 12, "sheet_height": 22, "margin": 1,
        "allow_rotation": True,
        "parts": [{"id": "long", "points": [[0, 0], [20, 0], [20, 10], [0, 10]]}],
    })
    assert result["placed_count"] == 1
    placement = result["placements"][0]
    assert placement["rotated_90"] is True
    assert placement["x"] >= 1 and placement["y"] >= 1
    assert placement["x"] + placement["width"] <= 11
    assert placement["y"] + placement["height"] <= 21


def test_polygon_layout_is_deterministic_and_reports_compact_scoring():
    request = {
        "sheet_width": 80, "sheet_height": 60, "margin": 2, "gap": 1,
        "parts": [
            {"id": "wide", "points": [[0, 0], [24, 0], [24, 8], [0, 8]]},
            {"id": "tall", "points": [[0, 0], [8, 0], [8, 18], [0, 18]]},
            {"id": "triangle", "points": [[0, 0], [12, 0], [6, 8]]},
        ],
    }
    first = nest_polygon_parts(request)
    second = nest_polygon_parts(request)
    assert first == second
    assert first["algorithm"] == "polygon_vertex_alignment_compact_envelope"
    assert first["placed_count"] == 3

