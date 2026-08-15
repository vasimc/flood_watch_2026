"""Runner: bronze GDELT -> persisted silver (smoothed) -> gold (coverage-lag).

Previously GDELT was the one automated source with no gold table at all --
`export_site_data.py` read straight from bronze because there was nothing
to compute. This script adds a real silver smoothing step and a gold
table that formalizes the "did coverage track the event" question the
site already asks in prose, as an actual re-derivable number.
"""

from __future__ import annotations

import pandas as pd

from .geo_reference import get_rainfall_peak_date
from .silver_gdelt import compute_coverage_peak_lag, compute_rolling_average
from .warehouse import DATA_DIR, silver_path

REGIONS = ("assam", "gujarat")


def _read_bronze(region: str) -> pd.DataFrame:
    matches = sorted((DATA_DIR / "bronze" / "gdelt_news").glob(f"{region}_*.parquet"))
    if not matches:
        raise FileNotFoundError(f"No GDELT bronze file for {region!r} -- run ingest_gdelt.py first.")
    return pd.read_parquet(matches[-1])


def build_all(regions=REGIONS) -> tuple[pd.DataFrame, pd.DataFrame]:
    bronze = pd.concat([_read_bronze(r) for r in regions], ignore_index=True)

    silver = compute_rolling_average(bronze)
    silver_out = silver_path("gdelt_news") / "article_volume_smoothed.parquet"
    silver.to_parquet(silver_out, index=False)
    print(f"Wrote {len(silver)} rows to {silver_out}")

    gold_rows = [
        compute_coverage_peak_lag(silver, region, get_rainfall_peak_date(region))
        for region in regions
    ]
    gold = pd.DataFrame(gold_rows)
    gold_dir = DATA_DIR / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold_out = gold_dir / "news_attention.parquet"
    gold.to_parquet(gold_out, index=False)
    print(f"Wrote {len(gold)} rows to {gold_out}")

    return silver, gold


if __name__ == "__main__":
    build_all()
