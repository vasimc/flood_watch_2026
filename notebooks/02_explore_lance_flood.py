"""Thin interactive check: run the LANCE satellite ingestion for one date and
plot the flood-extent raster of the first matching tile.

Run from the project root:
    python notebooks/02_explore_lance_flood.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import matplotlib.pyplot as plt
import numpy as np
import rasterio

from flood_watch.ingest_satellite import FLOOD_PIXEL_VALUES, ingest

REGION = "assam"
TARGET_DATE = date(2026, 7, 20)  # adjust to a known flood-affected day first


def main() -> None:
    df = ingest(region=REGION, target_date=TARGET_DATE)
    print(df)

    first_row = df.iloc[0]
    with rasterio.open(first_row["source_file"]) as src:
        band = src.read(1)

    flooded_mask = np.isin(band, list(FLOOD_PIXEL_VALUES))

    plt.figure(figsize=(8, 8))
    plt.imshow(flooded_mask, cmap="Blues")
    plt.title(f"{REGION} flood extent — {TARGET_DATE.isoformat()} — {first_row['tile_name']}")
    plt.colorbar(label="flooded (1) / not flooded (0)")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
