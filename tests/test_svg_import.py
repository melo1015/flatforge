"""Tests for safe SVG outline import."""
import pytest

from flatforge_maker.svg_import import import_svg_outlines


def test_imports_rect_and_polygon_preserving_normalized_contours():
    result = import_svg_outlines('''<svg xmlns="http://www.w3.org/2000/svg">
      <rect id="box" x="10" y="20" width="30" height="40"/>
      <polygon id="tri" points="50,10 70,10 60,30"/>
    </svg>''')
    assert result["count"] == 2
    assert result["outlines"][0]["id"] == "box"
    assert result["outlines"][0]["width"] == 30
    assert result["outlines"][0]["points"] == [[0, 0], [30, 0], [30, 40], [0, 40]]
    assert result["outlines"][1]["points"] == [[0, 0], [20, 0], [10, 20]]
    assert "cajas rectangulares" in result["warning"]


def test_imports_only_closed_polyline():
    result = import_svg_outlines('<svg xmlns="http://www.w3.org/2000/svg"><polyline points="0,0 20,0 10,10 0,0"/></svg>')
    assert result["outlines"][0]["points"] == [[0, 0], [20, 0], [10, 10]]


@pytest.mark.parametrize("source", [
    '<!DOCTYPE svg [<!ENTITY x "bad">]><svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2" onload="alert(1)"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2" transform="rotate(30)"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><polyline points="0,0 10,0 10,10"/></svg>',
])
def test_rejects_unsafe_or_unsupported_svg(source):
    with pytest.raises(ValueError):
        import_svg_outlines(source)


def test_rejects_malformed_svg():
    with pytest.raises(ValueError, match="valid XML/SVG"):
        import_svg_outlines("<svg")


def test_rejects_non_svg_root():
    with pytest.raises(ValueError, match="root must be an SVG"):
        import_svg_outlines("<html/>")
