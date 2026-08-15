"""Diagnostic: check Sentinel-1 image counts per region/window.

Not part of the pipeline -- one-off debug for the 'Image.divide: 0 bands'
error hit in ingest_satellite_gee.py (empty ImageCollection for one of the
before/after windows).
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

import ee

from flood_watch.geo_reference import get_flood_extent_bbox

ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

REGIONS_AND_PEAKS = {
    "assam": date(2026, 7, 20),
    "gujarat": date(2026, 7, 24),
}


def count(region, start, end):
    min_lon, min_lat, max_lon, max_lat = get_flood_extent_bbox(region)
    geometry = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
    coll = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterDate(start.isoformat(), end.isoformat())
        .filterBounds(geometry)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select("VH")
    )
    dates = coll.aggregate_array("system:time_start").getInfo()
    return len(dates), dates


for region, peak in REGIONS_AND_PEAKS.items():
    print(f"--- {region} (peak {peak}) ---")
    for after_end_offset in (3, 5, 7, 10, 12, 14, 18, 21):
        s = peak
        e = peak + timedelta(days=after_end_offset)
        n, dates = count(region, s, e)
        print(f"  after-window [{s}..{e}] (peak..+{after_end_offset}d): {n} images")
