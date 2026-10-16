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
