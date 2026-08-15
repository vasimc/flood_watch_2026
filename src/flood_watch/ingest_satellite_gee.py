"""Bronze/silver/gold: Sentinel-1 SAR flood extent via Google Earth Engine.

Chosen over NASA LANCE MODIS/VIIRS (see ingest_satellite.py, still in this
repo but deprioritized) for two reasons: GEE signup is same-day self-service
rather than an open-ended Earthdata Login wait, and Sentinel-1 is radar --
it sees through the monsoon cloud cover that would obstruct MODIS/VIIRS
optical imagery during exactly the events this project cares about.

Method: the UN-SPIDER "Flood Mapping and Damage Assessment Using Sentinel-1
SAR Data in Google Earth Engine" recommended practice (change detection, not
a fixed single-date threshold):
  https://un-spider.org/advisory-support/recommended-practices/recommended-practice-google-earth-engine-flood-mapping
1. Build a pre-flood reference mosaic and a flood-date mosaic from
   COPERNICUS/S1_GRD, VH polarization (more sensitive to land-surface change
   than VV, per the recommended practice).
2. Apply a speckle-reduction smoothing filter (~50m focal mean) to both.
3. Compute the ratio image: after / before.
4. Classify flooded = ratio > 1.25 (the recipe's documented threshold).
5. Sum flooded pixels within the region via reduceRegion, convert to km2.

Three real, persisted layers rather than one shot straight to gold: bronze
is which actual Sentinel-1 passes were found and used (one row per pass);
silver is the pixel-classification result (flooded pixel count, before the
km2 conversion); gold is the final area summary. There's no bronze "raw
imagery" layer -- downloading raw Sentinel-1 scenes defeats the point of
using GEE's server-side compute, so the rawest fact this pipeline can
capture and persist is which passes existed and got used.

Requires a Google Cloud project with the Earth Engine API enabled (see
README.md setup steps -- this is a one-time thing you do yourself, not
something this script can do for you). First run of ee.Authenticate() opens
a browser OAuth prompt; after that, credentials are cached and later runs
are headless.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import ee
import pandas as pd

from .geo_reference import get_flood_extent_bbox
from .warehouse import bronze_path, gold_path, silver_path

SPECKLE_FILTER_RADIUS_M = 50
FLOOD_RATIO_THRESHOLD = 1.25
SCALE_M = 10
WIDEN_STEP_DAYS = 7
WIDEN_MAX_DAYS = 30


def init(project_id: str) -> None:
    ee.Authenticate()
    ee.Initialize(project=project_id)


def pixels_to_km2(pixel_count: int, scale_m: int = SCALE_M) -> float:
    return pixel_count * (scale_m * scale_m) / 1_000_000


def _s1_collection(geometry: "ee.Geometry", start: date, end: date) -> "ee.ImageCollection":
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterDate(start.isoformat(), end.isoformat())
        .filterBounds(geometry)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select("VH")
    )


def _find_nonempty_window(
    geometry: "ee.Geometry", start: date, end: date, widen_earlier: bool
) -> tuple[date, date, list[str]]:
    """Sentinel-1's revisit interval (~12 days for the single operational
    satellite) means a narrow date window can have zero passes over a given
    region -- Gujarat's post-peak window is a real example of this, not a
    bug in the filter. Widen outward (earlier for the 'before' window, later
    for the 'after' window) until a pass is found, capped at WIDEN_MAX_DAYS,
    and return the actual pass dates found (the bronze fact) alongside the
    window used."""
    widened = 0
    while widened <= WIDEN_MAX_DAYS:
        collection = _s1_collection(geometry, start, end)
        pass_dates_ms = collection.aggregate_array("system:time_start").getInfo()
        if pass_dates_ms:
            pass_dates = [
                datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()
                for ms in pass_dates_ms
            ]
            return start, end, pass_dates
        widened += WIDEN_STEP_DAYS
        if widen_earlier:
            start -= timedelta(days=WIDEN_STEP_DAYS)
        else:
            end += timedelta(days=WIDEN_STEP_DAYS)
    raise RuntimeError(
        f"No Sentinel-1 VH images found for window [{start}..{end}] even "
        f"after widening by {WIDEN_MAX_DAYS} days."
    )


def resolve_windows(
    row_id: str, geometry: "ee.Geometry", peak_date: date, before_days=(30, 15), after_days=(-3, 3)
) -> dict:
    """Resolves the before/after date windows (auto-widening as needed) and
    the real Sentinel-1 passes found in each -- the fact-finding step that
    both the bronze and silver layers below are built from.

    Takes the geometry directly rather than deriving it from a region name,
    so this same function serves both region-level (bbox) and district-level
    (real polygon, see ingest_flood_extent_district.py) ingestion. `row_id`
    just labels the output row -- a region name or a district name."""
    req_before = (peak_date - timedelta(days=before_days[0]), peak_date - timedelta(days=before_days[1]))
    req_after = (peak_date + timedelta(days=after_days[0]), peak_date + timedelta(days=after_days[1]))

    before_start, before_end, before_dates = _find_nonempty_window(geometry, *req_before, widen_earlier=True)
    after_start, after_end, after_dates = _find_nonempty_window(geometry, *req_after, widen_earlier=False)

    return {
        "region": row_id,
        "geometry": geometry,
        "before_start": before_start,
        "before_end": before_end,
        "before_dates": before_dates,
        "before_widened": (before_start, before_end) != req_before,
        "after_start": after_start,
        "after_end": after_end,
        "after_dates": after_dates,
        "after_widened": (after_start, after_end) != req_after,
    }


def build_bronze_passes(resolved: dict) -> pd.DataFrame:
    """BRONZE: one row per real Sentinel-1 pass actually used, in either
    window. The rawest fact this pipeline persists for satellite data."""
    rows = [
        {
            "region": resolved["region"],
            "window_role": role,
            "window_start": resolved[f"{role}_start"].isoformat(),
            "window_end": resolved[f"{role}_end"].isoformat(),
            "window_widened": resolved[f"{role}_widened"],
            "pass_date": pass_date,
        }
        for role in ("before", "after")
        for pass_date in resolved[f"{role}_dates"]
    ]
    return pd.DataFrame(rows)


def build_silver_classification(resolved: dict) -> dict:
    """SILVER: the pixel-classification result (flooded pixel count) --
    cleaned/derived from the raw passes, but not yet the final story-ready
    area figure."""
    geometry = resolved["geometry"]
    before_img = _s1_collection(geometry, resolved["before_start"], resolved["before_end"]).mosaic().focal_mean(
        SPECKLE_FILTER_RADIUS_M, "circle", "meters"
    )
    after_img = _s1_collection(geometry, resolved["after_start"], resolved["after_end"]).mosaic().focal_mean(
        SPECKLE_FILTER_RADIUS_M, "circle", "meters"
    )
    ratio = after_img.divide(before_img)
    flooded = ratio.gt(FLOOD_RATIO_THRESHOLD).rename("flooded")

    stats = flooded.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=SCALE_M,
        maxPixels=1e9,
        bestEffort=True,
    ).getInfo()

    return {
        "region": resolved["region"],
        "before_window": f"{resolved['before_start'].isoformat()}_{resolved['before_end'].isoformat()}",
        "after_window": f"{resolved['after_start'].isoformat()}_{resolved['after_end'].isoformat()}",
        "before_image_count": len(resolved["before_dates"]),
        "after_image_count": len(resolved["after_dates"]),
        "before_window_widened": resolved["before_widened"],
        "after_window_widened": resolved["after_widened"],
        "flood_ratio_threshold": FLOOD_RATIO_THRESHOLD,
        "scale_m": SCALE_M,
        "flooded_pixel_count": stats.get("flooded", 0) or 0,
    }


def build_gold_summary(silver_row: dict, peak_date: date) -> dict:
    """GOLD: the story-ready row -- pixel count converted to km2, nothing
    else new computed here."""
    return {
        "region": silver_row["region"],
        "peak_date": peak_date.isoformat(),
        "before_window": silver_row["before_window"],
        "after_window": silver_row["after_window"],
        "before_image_count": silver_row["before_image_count"],
        "after_image_count": silver_row["after_image_count"],
        "before_window_widened": silver_row["before_window_widened"],
        "after_window_widened": silver_row["after_window_widened"],
        "flooded_area_km2": pixels_to_km2(silver_row["flooded_pixel_count"]),
    }


def ingest(project_id: str, regions_and_peaks: dict) -> pd.DataFrame:
    """regions_and_peaks: {"assam": date(2026,7,20), "gujarat": date(2026,7,24)}"""
    init(project_id)

    bronze_frames, silver_rows, gold_rows = [], [], []
    for region, peak in regions_and_peaks.items():
        min_lon, min_lat, max_lon, max_lat = get_flood_extent_bbox(region)
        geometry = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
        resolved = resolve_windows(region, geometry, peak)
        bronze_frames.append(build_bronze_passes(resolved))
        silver_row = build_silver_classification(resolved)
        silver_rows.append(silver_row)
        gold_rows.append(build_gold_summary(silver_row, peak))

    bronze_df = pd.concat(bronze_frames, ignore_index=True)
    bronze_out = bronze_path("satellite_gee") / "passes.parquet"
    bronze_df.to_parquet(bronze_out, index=False)
    print(f"Wrote {len(bronze_df)} rows to {bronze_out}")

    silver_df = pd.DataFrame(silver_rows)
    silver_out = silver_path("flood_extent") / "pixel_classification.parquet"
    silver_df.to_parquet(silver_out, index=False)
    print(f"Wrote {len(silver_df)} rows to {silver_out}")

    gold_df = pd.DataFrame(gold_rows)
    gold_out = gold_path("flood_extent") / "flood_extent_gee.parquet"
    gold_df.to_parquet(gold_out, index=False)
    print(f"Wrote {len(gold_df)} rows to {gold_out}")

    return gold_df


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    from .geo_reference import get_rainfall_peak_date

    load_dotenv()
    project_id = os.environ.get("GEE_PROJECT_ID", "")
    if not project_id:
        raise RuntimeError(
            "GEE_PROJECT_ID not set. Copy .env.example to .env and fill in "
            "the Google Cloud project ID you registered for Earth Engine."
        )
    ingest(
        project_id,
        {
            region: date.fromisoformat(get_rainfall_peak_date(region))
            for region in ("assam", "gujarat")
        },
    )
