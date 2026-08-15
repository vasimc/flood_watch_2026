"""Bronze/silver/gold: per-district flood extent, using the same Sentinel-1
SAR change-detection method as ingest_satellite_gee.py but clipped to real
district polygons (from ingest_district_boundaries.py) instead of one
approximate bounding box per region.

Reuses every actual GEE computation primitive from ingest_satellite_gee.py
(_find_nonempty_window, resolve_windows, build_bronze_passes,
build_silver_classification, build_gold_summary) unchanged -- resolve_windows
already takes a geometry as a parameter and doesn't care whether it's a
region bbox or a district polygon. Only the per-district orchestration (load
each district's real geometry, loop, land results under district-level table
names) is new here.
"""

from __future__ import annotations

import json
from datetime import date

import ee
import pandas as pd

from .geo_reference import get_districts, get_rainfall_peak_date
from .ingest_satellite_gee import (
    build_bronze_passes,
    build_gold_summary,
    build_silver_classification,
    init,
    resolve_windows,
)
from .warehouse import DATA_DIR, bronze_path, gold_path, silver_path


def _load_district_geometries(region: str) -> dict:
    boundaries_path = DATA_DIR / "reference" / "district_boundaries.geojson"
    if not boundaries_path.exists():
        raise FileNotFoundError(
            f"{boundaries_path} not found -- run ingest_district_boundaries.py first."
        )
    fc = json.loads(boundaries_path.read_text(encoding="utf-8"))
    return {
        feat["properties"]["district"]: ee.Geometry(feat["geometry"])
        for feat in fc["features"]
        if feat["properties"]["region"] == region
    }


def ingest_by_district(project_id: str, regions: tuple = ("assam", "gujarat")) -> pd.DataFrame:
    init(project_id)

    bronze_frames, silver_rows, gold_rows = [], [], []
    for region in regions:
        peak = date.fromisoformat(get_rainfall_peak_date(region))
        geometries = _load_district_geometries(region)

        for district in get_districts(region):
            resolved = resolve_windows(district, geometries[district], peak)

            bronze_df = build_bronze_passes(resolved).rename(columns={"region": "district"})
            bronze_df.insert(0, "region", region)
            bronze_frames.append(bronze_df)

            # build_silver_classification/build_gold_summary both read/carry
            # forward a "region" key -- here that key holds resolved["region"],
            # which resolve_windows set to `district` above. Keep it under its
            # real name (district) and set the actual region explicitly,
            # rather than letting the "region" key drift in meaning downstream.
            silver_row = build_silver_classification(resolved)
            district_name = silver_row.pop("region")
            silver_row = {"region": region, "district": district_name, **silver_row}
            silver_rows.append(silver_row)

            gold_row = build_gold_summary({**silver_row, "region": district_name}, peak)
            gold_row.pop("region")
            gold_row = {"region": region, "district": district_name, **gold_row}
            gold_rows.append(gold_row)

    bronze_df = pd.concat(bronze_frames, ignore_index=True)
    bronze_out = bronze_path("satellite_gee") / "district_passes.parquet"
    bronze_df.to_parquet(bronze_out, index=False)
    print(f"Wrote {len(bronze_df)} rows to {bronze_out}")

    silver_df = pd.DataFrame(silver_rows)
    silver_out = silver_path("flood_extent") / "district_pixel_classification.parquet"
    silver_df.to_parquet(silver_out, index=False)
    print(f"Wrote {len(silver_df)} rows to {silver_out}")

    gold_df = pd.DataFrame(gold_rows)
    gold_out = gold_path("flood_extent") / "flood_extent_by_district.parquet"
    gold_df.to_parquet(gold_out, index=False)
    print(f"Wrote {len(gold_df)} rows to {gold_out}")

    return gold_df


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
    ingest_by_district(project_id)
