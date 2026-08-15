import pytest

from flood_watch.ingest_district_boundaries import _clean_geometry


def test_clean_geometry_passes_through_plain_polygon():
    geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
    assert _clean_geometry(geom) == geom


def test_clean_geometry_strips_linestring_artifacts_from_geometry_collection():
    # observed on Surat: simplify() padded a GeometryCollection with
    # degenerate 2-point LineString slivers alongside the real polygon
    geom = {
        "type": "GeometryCollection",
        "geometries": [
            {"type": "LineString", "coordinates": [[0, 0], [0, 0.0001]]},
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        ],
    }
    cleaned = _clean_geometry(geom)
    assert cleaned == {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}


def test_clean_geometry_collapses_multiple_polygons_to_multipolygon():
    poly_a = [[[0, 0], [1, 0], [1, 1], [0, 0]]]
    poly_b = [[[5, 5], [6, 5], [6, 6], [5, 5]]]
    geom = {
        "type": "GeometryCollection",
        "geometries": [
            {"type": "Polygon", "coordinates": poly_a},
            {"type": "Polygon", "coordinates": poly_b},
        ],
    }
    cleaned = _clean_geometry(geom)
    assert cleaned == {"type": "MultiPolygon", "coordinates": [poly_a, poly_b]}


def test_clean_geometry_raises_if_no_polygon_survives():
    geom = {
        "type": "GeometryCollection",
        "geometries": [{"type": "LineString", "coordinates": [[0, 0], [0, 1]]}],
    }
    with pytest.raises(ValueError):
        _clean_geometry(geom)
