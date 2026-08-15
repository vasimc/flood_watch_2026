"""Bronze/gold ingestion: Sentinel-1 SAR flood extent via Google Earth Engine.

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

Requires a Google Cloud project with the Earth Engine API enabled (see
README.md setup steps -- this is a one-time thing you do yourself, not
something this script can do for you). First run of ee.Authenticate() opens
a browser OAuth prompt; after that, credentials are cached and later runs
are headless.
"""

from __future__ import annotations

from datetime import date, timedelta

import ee
import pandas as pd

from .geo_reference import get_flood_extent_bbox
from .warehouse import gold_path

SPECKLE_FILTER_RADIUS_M = 50
FLOOD_RATIO_THRESHOLD = 1.25
SCALE_M = 10


def init(project_id: str) -> None:
    ee.Authenticate()
    ee.Initialize(project=project_id)


def pixels_to_km2(pixel_count: int, scale_m: int = SCALE_M) -> float:
    return pixel_count * (scale_m * scale_m) / 1_000_000


WIDEN_STEP_DAYS = 7
WIDEN_MAX_DAYS = 30


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
) -> tuple[date, date, int]:
    """Sentinel-1's revisit interval (~12 days for the single operational
    satellite) means a narrow date window can have zero passes over a given
    region -- Gujarat's post-peak window is a real example of this, not a
    bug in the filter. Widen outward (earlier for the 'before' window, later
    for the 'after' window) until a pass is found, capped at WIDEN_MAX_DAYS,
    and report back the actual window + image count used so callers can
    flag when a result relied on widening."""
    widened = 0
    while widened <= WIDEN_MAX_DAYS:
        n = _s1_collection(geometry, start, end).size().getInfo()
        if n > 0:
            return start, end, n
        widened += WIDEN_STEP_DAYS
        if widen_earlier:
            start -= timedelta(days=WIDEN_STEP_DAYS)
        else:
            end += timedelta(days=WIDEN_STEP_DAYS)
    raise RuntimeError(
        f"No Sentinel-1 VH images found for window [{start}..{end}] even "
        f"after widening by {WIDEN_MAX_DAYS} days."
    )


def compute_flood_extent(
    region: str,
    peak_date: date,
    before_days=(30, 15),
    after_days=(-3, 3),
) -> dict:
    """Returns a dict with flooded_pixel_count, flooded_area_km2, the
    actual before/after date windows used (for the record), and an
    image_count/widened flag per window so a thin result is visible rather
    than silently trusted."""
    min_lon, min_lat, max_lon, max_lat = get_flood_extent_bbox(region)
    geometry = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])

    req_before_start = peak_date - timedelta(days=before_days[0])
    req_before_end = peak_date - timedelta(days=before_days[1])
    req_after_start = peak_date + timedelta(days=after_days[0])
    req_after_end = peak_date + timedelta(days=after_days[1])

    before_start, before_end, before_n = _find_nonempty_window(
        geometry, req_before_start, req_before_end, widen_earlier=True
    )
    after_start, after_end, after_n = _find_nonempty_window(
        geometry, req_after_start, req_after_end, widen_earlier=False
    )

    before_img = _s1_collection(geometry, before_start, before_end).mosaic().focal_mean(
        SPECKLE_FILTER_RADIUS_M, "circle", "meters"
    )
    after_img = _s1_collection(geometry, after_start, after_end).mosaic().focal_mean(
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

    flooded_pixel_count = stats.get("flooded", 0) or 0
    return {
        "region": region,
        "peak_date": peak_date.isoformat(),
        "before_window": f"{before_start.isoformat()}_{before_end.isoformat()}",
        "after_window": f"{after_start.isoformat()}_{after_end.isoformat()}",
        "before_image_count": before_n,
        "after_image_count": after_n,
        "before_window_widened": (before_start, before_end) != (req_before_start, req_before_end),
        "after_window_widened": (after_start, after_end) != (req_after_start, req_after_end),
        "flooded_pixel_count": flooded_pixel_count,
        "flooded_area_km2": pixels_to_km2(flooded_pixel_count),
    }


def ingest(project_id: str, regions_and_peaks: dict) -> pd.DataFrame:
    """regions_and_peaks: {"assam": date(2026,7,20), "gujarat": date(2026,7,24)}"""
    init(project_id)
    rows = [compute_flood_extent(region, peak) for region, peak in regions_and_peaks.items()]
    df = pd.DataFrame(rows)
    out_path = gold_path("flood_extent") / "flood_extent_gee.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


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
    ingest(
        project_id,
        {
            "assam": date(2026, 7, 20),
            "gujarat": date(2026, 7, 24),
        },
    )
