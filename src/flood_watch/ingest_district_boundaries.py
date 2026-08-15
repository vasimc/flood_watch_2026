"""Reference data: real district (ADM2) and state (ADM1) boundary polygons,
not a fact table -- this is dimension/reference data (the same role as
geo_reference.py's hand-typed bboxes), just sourced from a real external
dataset instead of typed in, so it doesn't get its own bronze/silver/gold
treatment. Fetched once and re-fetched only if the district/state list
changes.

Source: geoBoundaries' India ADM1 (state) and ADM2 (district) layers,
available directly in Google Earth Engine's public data catalog as
`WM/geoLab/geoBoundaries/600/ADM1` and `.../ADM2` -- no download/hosting of
the full national files needed, just the 7 districts + 2 states this
project actually uses. Verified live 2026-08-15: all 7 target districts
present by exact name, including Charaideo (Assam's newest district,
created Aug 2015 -- a good sign this isn't a stale pre-2015 list); both
states present, though Gujarat's ADM1 `shapeName` has a real upstream
encoding glitch (literally "Gujar?t", a raw '?' byte) -- matched by
substring instead of exact name to sidestep it. Underlying data traces to
India's own Local Government Directory (lgdirectory.gov.in), licensed
ODbL 1.0.

Licensing note (checked against the actual ODbL 1.0 text, not assumed):
derived *statistics* computed from this data (e.g. flooded_area_km2 per
district) only need a simple attribution notice under ODbL section 4.3.
But republishing the boundary *geometries themselves*, as this script does,
counts as extracting a substantial part of the source database (section
4.2/4.4) -- so the geometry file this writes carries its own ODbL notice,
separate from (and stricter than) the simple-attribution sources elsewhere
in this project. See README's licensing table.
"""

from __future__ import annotations

import json

import ee

from .geo_reference import district_region_map
from .ingest_satellite_gee import init
from .warehouse import DATA_DIR

GEOBOUNDARIES_ADM2_ASSET = "WM/geoLab/geoBoundaries/600/ADM2"
GEOBOUNDARIES_ADM1_ASSET = "WM/geoLab/geoBoundaries/600/ADM1"
SIMPLIFY_TOLERANCE_M = 100
STATE_SIMPLIFY_TOLERANCE_M = 1000  # states are background context, not analysis precision
ATTRIBUTION = (
    "Contains information from geoBoundaries ({asset}), made available under "
    "the Open Database License (ODbL) v1.0 "
    "(https://opendatacommons.org/licenses/odbl/1-0/). Source: India Local "
    "Government Directory (lgdirectory.gov.in) via geoBoundaries."
)

# geoBoundaries' ADM1 shapeName field has a real encoding glitch for Gujarat
# in this dataset -- verified live 2026-08-15, its shapeName is literally
# "Gujar?t" (a raw '?' byte where a diacritic should be), not a display
# artifact. Matching by substring instead of exact name sidesteps it and is
# robust either way.
STATE_NAME_SEARCH = {"assam": "Assam", "gujarat": "Gujar"}


def _clean_geometry(geometry: dict) -> dict:
    """GEE's .simplify() on complex/coastal district shapes can return a
    GeometryCollection padded with degenerate 2-point LineString slivers
    alongside the real polygon(s) -- observed on Surat. Drop anything that
    isn't a Polygon and collapse to a single Polygon/MultiPolygon."""
    if geometry["type"] != "GeometryCollection":
        return geometry

    polygons = [g["coordinates"] for g in geometry["geometries"] if g["type"] == "Polygon"]
    if not polygons:
        raise ValueError(f"No Polygon geometry survived cleanup: {geometry}")
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def fetch_district_boundaries(project_id: str) -> dict:
    init(project_id)
    mapping = district_region_map()

    fc = (
        ee.FeatureCollection(GEOBOUNDARIES_ADM2_ASSET)
        .filter(ee.Filter.eq("shapeGroup", "IND"))
        .filter(ee.Filter.inList("shapeName", list(mapping.keys())))
        .map(lambda f: f.simplify(SIMPLIFY_TOLERANCE_M))
    )
    raw = fc.getInfo()

    features = []
    for feat in raw["features"]:
        district = feat["properties"]["shapeName"]
        features.append(
            {
                "type": "Feature",
                "properties": {"district": district, "region": mapping[district]},
                "geometry": _clean_geometry(feat["geometry"]),
            }
        )

    if len(features) != len(mapping):
        missing = set(mapping) - {f["properties"]["district"] for f in features}
        raise RuntimeError(f"Expected {len(mapping)} districts, got {len(features)}. Missing: {missing}")

    out = {
        "type": "FeatureCollection",
        "license": "ODbL-1.0",
        "attribution": ATTRIBUTION.format(asset=f"{GEOBOUNDARIES_ADM2_ASSET}, India ADM2"),
        "features": features,
    }

    out_dir = DATA_DIR / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "district_boundaries.geojson"
    out_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"Wrote {len(features)} district boundaries to {out_path}")
    return out


def fetch_state_boundaries(project_id: str) -> dict:
    """Full state outlines (Assam, Gujarat) -- background context for the
    district map so the reader can see where the flood-tracked district
    cluster actually sits within the whole state, not just the cluster in
    isolation."""
    init(project_id)

    fc = ee.FeatureCollection(GEOBOUNDARIES_ADM1_ASSET).filter(ee.Filter.eq("shapeGroup", "IND"))

    features = []
    for region, name_search in STATE_NAME_SEARCH.items():
        feat = fc.filter(ee.Filter.stringContains("shapeName", name_search)).first()
        info = feat.geometry().simplify(STATE_SIMPLIFY_TOLERANCE_M).getInfo()
        features.append(
            {
                "type": "Feature",
                "properties": {"region": region},
                "geometry": _clean_geometry(info),
            }
        )

    out = {
        "type": "FeatureCollection",
        "license": "ODbL-1.0",
        "attribution": ATTRIBUTION.format(asset=f"{GEOBOUNDARIES_ADM1_ASSET}, India ADM1"),
        "features": features,
    }

    out_dir = DATA_DIR / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "state_boundaries.geojson"
    out_path.write_text(json.dumps(out), encoding="utf-8")
    print(f"Wrote {len(features)} state boundaries to {out_path}")
    return out


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    project_id = os.environ.get("GEE_PROJECT_ID", "")
    if not project_id:
        raise RuntimeError(
            "GEE_PROJECT_ID not set. Copy .env.example to .env and fill in "
            "the Google Cloud project ID you registered for Earth Engine."
        )
    fetch_district_boundaries(project_id)
    fetch_state_boundaries(project_id)
