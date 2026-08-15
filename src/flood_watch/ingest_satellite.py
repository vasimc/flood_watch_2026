"""Bronze ingestion: NASA LANCE/LAADS MODIS-VIIRS near-real-time flood product.

Product: MCDWD_L3_NRT (MODIS/VIIRS Water/Flood, Level 3, Near Real Time),
served from NASA's LAADS DAAC archive. Pulls one date's tile(s) covering a
region, computes a flooded-pixel count from the GeoTIFF, and lands the
result as bronze Parquet.

VERIFICATION NEEDED BEFORE FIRST REAL RUN (this has not been run against the
live API yet -- do this the first time you run it, not blindly trust it):

1. MODIS sinusoidal tile IDs below (TILE_IDS_BY_REGION) are a best-effort
   guess for Assam/Gujarat, not verified against a live tile grid lookup.
   Cross-check against the MODIS Sinusoidal Tile Grid
   (https://modis-land.gsfc.nasa.gov/MODLAND_grid.html) or by browsing
   https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61/MCDWD_L3_NRT/
   for a known flood date and seeing which tiles actually cover India.
2. The directory-listing-as-JSON URL pattern
   (append ".json" to an archive directory URL) is a long-standing LAADS
   DAAC convention but confirm it still returns what's expected once you
   have a real token -- print the raw response before trusting the parse.
3. FLOOD_PIXEL_VALUES below (which raster values count as "flooded") is
   from memory of the product's general Water/Flood value scheme, not
   re-verified against the current MCDWD Product User Guide. Check the
   guide (linked from the LAADS DAAC product page) before trusting
   flooded_pixel_count numbers in an analysis.

None of this is hard to fix -- it just needs a human with real API access
and real output in front of them, which is why this hasn't been run yet.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from dotenv import load_dotenv

from .warehouse import bronze_path

load_dotenv()

LAADS_TOKEN = os.environ.get("NASA_EARTHDATA_TOKEN", "")
LAADS_BASE = "https://ladsweb.modaps.eosdis.nasa.gov"
PRODUCT = "MCDWD_L3_NRT"
COLLECTION = "61"

# best-effort guess, see module docstring point 1 -- verify before relying on it
TILE_IDS_BY_REGION = {
    "assam": ["h25v06", "h26v06"],
    "gujarat": ["h24v06", "h24v07"],
}

# best-effort guess, see module docstring point 3 -- verify before relying on it
FLOOD_PIXEL_VALUES = {2, 3}  # 2 = flood, 3 = recurring flood


def _session() -> requests.Session:
    if not LAADS_TOKEN:
        raise RuntimeError(
            "NASA_EARTHDATA_TOKEN not set. Copy .env.example to .env and fill in "
            "a token from https://ladsweb.modaps.eosdis.nasa.gov/profile/#generate-token"
        )
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {LAADS_TOKEN}"})
    return session


def list_granules(target_date: date, session: requests.Session) -> list[dict]:
    """List available granule files for a given date via the LAADS archive JSON listing."""
    day_of_year = target_date.timetuple().tm_yday
    url = f"{LAADS_BASE}/archive/allData/{COLLECTION}/{PRODUCT}/{target_date.year}/{day_of_year:03d}.json"
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def download_granule(granule: dict, session: requests.Session, dest_dir: Path) -> Path:
    dest = dest_dir / granule["name"]
    if dest.exists():
        return dest
    file_url = f"{LAADS_BASE}/archive/allData/{COLLECTION}/{PRODUCT}/{granule['downloadsLink'].split('/allData/' + COLLECTION + '/' + PRODUCT + '/')[-1]}"
    with session.get(file_url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest


def flood_pixel_stats(geotiff_path: Path) -> dict:
    with rasterio.open(geotiff_path) as src:
        band = src.read(1)
        pixel_area_km2 = abs(src.res[0] * src.res[1]) / 1_000_000
    flooded_mask = np.isin(band, list(FLOOD_PIXEL_VALUES))
    flooded_pixel_count = int(flooded_mask.sum())
    return {
        "flooded_pixel_count": flooded_pixel_count,
        "flooded_area_km2": flooded_pixel_count * pixel_area_km2,
    }


def ingest(region: str, target_date: date) -> pd.DataFrame:
    session = _session()
    dest_dir = bronze_path("satellite_lance") / region
    dest_dir.mkdir(parents=True, exist_ok=True)

    granules = list_granules(target_date, session)
    tile_ids = TILE_IDS_BY_REGION[region]
    relevant = [g for g in granules if any(tile in g["name"] for tile in tile_ids)]

    if not relevant:
        raise RuntimeError(
            f"No granules found for {region} on {target_date} matching tile IDs "
            f"{tile_ids}. Check the raw `granules` list printed above -- the tile "
            f"IDs guessed in TILE_IDS_BY_REGION are likely wrong. See module docstring."
        )

    rows = []
    for granule in relevant:
        path = download_granule(granule, session, dest_dir)
        stats = flood_pixel_stats(path)
        rows.append(
            {
                "region": region,
                "date": target_date.isoformat(),
                "tile_name": granule["name"],
                "source_file": str(path),
                **stats,
            }
        )

    df = pd.DataFrame(rows)
    out_path = bronze_path("satellite_lance") / f"{region}_{target_date.isoformat()}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


if __name__ == "__main__":
    # Phase 1 target: one region, one recent date. Adjust the date below to a
    # known flood-affected day from the ReliefWeb sitreps before running.
    ingest(region="assam", target_date=date(2026, 7, 20))
