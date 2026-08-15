from datetime import date

import numpy as np

from flood_watch.ingest_rainfall import GRID_LAT, GRID_LON, daily_grid_to_frame


def test_daily_grid_to_frame_clips_to_region_and_drops_missing(tmp_path):
    grid = np.full((len(GRID_LAT), len(GRID_LON)), -999.0, dtype="<f4")

    # Assam bbox is roughly lon 89.7-96.0, lat 24.1-28.2 -- pick one cell inside it
    lon_i = np.argmin(np.abs(GRID_LON - 92.0))
    lat_i = np.argmin(np.abs(GRID_LAT - 26.0))
    grid[lat_i, lon_i] = 45.5

    # and one cell clearly outside Assam (southern India) that must be excluded
    lon_j = np.argmin(np.abs(GRID_LON - 77.0))
    lat_j = np.argmin(np.abs(GRID_LAT - 12.0))
    grid[lat_j, lon_j] = 999.9

    grd_path = tmp_path / "synthetic.grd"
    grid.tofile(grd_path)

    df = daily_grid_to_frame(grd_path, date(2026, 7, 20), "assam")

    assert len(df) == 1
    row = df.iloc[0]
    assert row["rainfall_mm"] == 45.5
    assert 89.7 <= row["lon"] <= 96.0
    assert 24.1 <= row["lat"] <= 28.2
