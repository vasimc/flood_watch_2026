import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from flood_watch.ingest_satellite import flood_pixel_stats


def _write_synthetic_geotiff(path, band, pixel_size_deg=0.0025):
    transform = from_origin(90.0, 27.0, pixel_size_deg, pixel_size_deg)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=band.shape[0],
        width=band.shape[1],
        count=1,
        dtype=band.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(band, 1)


def test_flood_pixel_stats_counts_only_flood_values(tmp_path):
    band = np.array(
        [
            [0, 1, 2],
            [3, 0, 1],
            [2, 3, 0],
        ],
        dtype=np.uint8,
    )
    tif_path = tmp_path / "synthetic.tif"
    _write_synthetic_geotiff(tif_path, band)

    stats = flood_pixel_stats(tif_path)

    assert stats["flooded_pixel_count"] == 4  # four cells with value 2 or 3

    with rasterio.open(tif_path) as src:
        expected_pixel_area_km2 = abs(src.res[0] * src.res[1]) / 1_000_000
    assert stats["flooded_area_km2"] == pytest.approx(4 * expected_pixel_area_km2)
