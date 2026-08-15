"""Bronze ingestion: IMD Pune gridded rainfall (0.25x0.25 degree).

Two data endpoints on imdpune.gov.in, both no-auth, both verified live on
2026-08-14 (unlike ingest_satellite.py, nothing here is a guess):

- RF25.php: yearly archive, one NetCDF file per year (`RAINFALL` variable,
  dims TIME/LATITUDE/LONGITUDE, missing = NaN), years available up to 2025 as
  of 2026-08-14 -- used for the historical "normal" baseline.
- rain.php: single-day realtime grid, raw binary (135x129 float32,
  little-endian, row-major latitude-then-longitude, missing = -999.0), date
  posted as `ddmmyyyy`. This *does* have real 2026 event dates -- confirmed
  by pulling 2026-07-20 for the Assam bbox (mean ~45mm, max ~355mm in a
  single cell across the region, consistent with a flood-triggering day).
  Cross-checked: the set of non-missing (land) grid cells in the binary pull
  for Assam matched exactly the non-NaN cell count from the yearly NetCDF's
  own Assam clip for the same day-of-year in a different year (290 of 416
  cells both times), which is strong evidence the binary layout/orientation
  used below is correct, not just plausible-looking.

Grid: 135 columns (longitude, 66.5 to 100.0 step 0.25), 129 rows (latitude,
6.5 to 38.5 step 0.25), covering all of India.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

from .geo_reference import get_bbox
from .warehouse import bronze_path

YEARLY_URL = "https://www.imdpune.gov.in/cmpg/Griddata/RF25.php"
DAILY_URL = "https://www.imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php"

GRID_LON = 66.5 + np.arange(135) * 0.25
GRID_LAT = 6.5 + np.arange(129) * 0.25
MISSING_VALUE = -999.0


def _clip_indices(region: str) -> tuple[np.ndarray, np.ndarray]:
    min_lon, min_lat, max_lon, max_lat = get_bbox(region)
    lon_idx = np.where((GRID_LON >= min_lon) & (GRID_LON <= max_lon))[0]
    lat_idx = np.where((GRID_LAT >= min_lat) & (GRID_LAT <= max_lat))[0]
    return lat_idx, lon_idx


def download_yearly_archive(year: int, dest_dir: Path) -> Path:
    dest = dest_dir / f"ind{year}_rfp25.nc"
    if dest.exists():
        return dest
    resp = requests.post(YEARLY_URL, data={"RF25": str(year)}, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def download_daily_realtime(target_date: date, dest_dir: Path) -> Path:
    dest = dest_dir / f"rain_{target_date.isoformat()}.grd"
    if dest.exists():
        return dest
    resp = requests.post(
        DAILY_URL, data={"rain": target_date.strftime("%d%m%Y")}, timeout=60
    )
    resp.raise_for_status()
    expected_bytes = len(GRID_LAT) * len(GRID_LON) * 4
    if len(resp.content) != expected_bytes:
        raise RuntimeError(
            f"Unexpected daily grid size ({len(resp.content)} bytes, expected "
            f"{expected_bytes}) for {target_date} -- IMD may not have "
            f"published this date yet, or the response format changed."
        )
    dest.write_bytes(resp.content)
    return dest


def yearly_archive_to_frame(nc_path: Path, region: str) -> pd.DataFrame:
    ds = xr.open_dataset(nc_path)
    lat_idx, lon_idx = _clip_indices(region)
    clipped = ds["RAINFALL"].isel(LATITUDE=lat_idx, LONGITUDE=lon_idx)
    df = clipped.to_dataframe().reset_index()
    df = df.rename(
        columns={
            "TIME": "date",
            "LATITUDE": "lat",
            "LONGITUDE": "lon",
            "RAINFALL": "rainfall_mm",
        }
    )
    df["region"] = region
    return df.dropna(subset=["rainfall_mm"])


def daily_grid_to_frame(grd_path: Path, target_date: date, region: str) -> pd.DataFrame:
    grid = np.fromfile(grd_path, dtype="<f4").reshape(len(GRID_LAT), len(GRID_LON))
    lat_idx, lon_idx = _clip_indices(region)
    sub = grid[np.ix_(lat_idx, lon_idx)]
    lon_mesh, lat_mesh = np.meshgrid(GRID_LON[lon_idx], GRID_LAT[lat_idx])
    mask = sub > (MISSING_VALUE + 1)
    return pd.DataFrame(
        {
            "date": target_date.isoformat(),
            "lat": lat_mesh[mask],
            "lon": lon_mesh[mask],
            "rainfall_mm": sub[mask],
            "region": region,
        }
    )


def ingest_yearly(region: str, years: list[int]) -> pd.DataFrame:
    dest_dir = bronze_path("rainfall_imd") / "yearly_raw"
    dest_dir.mkdir(parents=True, exist_ok=True)
    frames = [
        yearly_archive_to_frame(download_yearly_archive(year, dest_dir), region)
        for year in years
    ]
    df = pd.concat(frames, ignore_index=True)
    out_path = bronze_path("rainfall_imd") / f"{region}_yearly_{min(years)}_{max(years)}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def ingest_daily(region: str, target_date: date) -> pd.DataFrame:
    dest_dir = bronze_path("rainfall_imd") / "daily_raw"
    dest_dir.mkdir(parents=True, exist_ok=True)
    grd_path = download_daily_realtime(target_date, dest_dir)
    df = daily_grid_to_frame(grd_path, target_date, region)
    out_path = bronze_path("rainfall_imd") / f"{region}_daily_{target_date.isoformat()}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def ingest_daily_range(region: str, start_date: date, end_date: date, pause_s: float = 0.5) -> pd.DataFrame:
    """Ingest each day in [start_date, end_date] via the realtime endpoint and
    land the whole window as one bronze Parquet (a timeline, not a snapshot).
    pause_s is a small politeness delay between requests to IMD's server."""
    dest_dir = bronze_path("rainfall_imd") / "daily_raw"
    dest_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    day = start_date
    while day <= end_date:
        grd_path = download_daily_realtime(day, dest_dir)
        frames.append(daily_grid_to_frame(grd_path, day, region))
        day += timedelta(days=1)
        time.sleep(pause_s)

    df = pd.concat(frames, ignore_index=True)
    out_path = (
        bronze_path("rainfall_imd")
        / f"{region}_daily_range_{start_date.isoformat()}_{end_date.isoformat()}.parquet"
    )
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows ({start_date} to {end_date}) to {out_path}")
    return df


if __name__ == "__main__":
    from .geo_reference import get_event_window

    for region in ("assam", "gujarat"):
        start_s, end_s = get_event_window(region)
        start = date.fromisoformat(start_s)
        end = date.fromisoformat(end_s)
        ingest_daily_range(region=region, start_date=start, end_date=end)
        ingest_yearly(region=region, years=list(range(2016, 2026)))
