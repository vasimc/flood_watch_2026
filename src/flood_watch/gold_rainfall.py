"""Runner: bronze rainfall -> persisted silver daily-means -> gold tables.

Closes a real gap: `silver_rainfall.py` and `silver_historical_trend.py`
have always held the actual transform logic (regional daily mean, monthly
normal, anomaly, yearly trend) as pure functions, but until now nothing
committed to the repo actually called them and wrote the result back to
disk -- the two rainfall gold tables on disk were produced by interactive
one-off code in an earlier session, not by anything re-runnable. This
script is that missing, re-runnable step, and it persists the silver
layer too (previously computed in-memory and thrown away), not just gold.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .silver_historical_trend import compute_yearly_trend
from .silver_rainfall import compute_anomaly, compute_monthly_normal, compute_regional_daily_mean
from .warehouse import DATA_DIR, silver_path


def _gold_root() -> Path:
    path = DATA_DIR / "gold"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_bronze(path_glob: str) -> pd.DataFrame:
    matches = sorted((DATA_DIR / "bronze" / "rainfall_imd").glob(path_glob))
    if not matches:
        raise FileNotFoundError(f"No bronze file matching {path_glob!r} -- run ingest_rainfall.py first.")
    return pd.read_parquet(matches[-1])


def build_silver_daily_mean(region: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (event_window_daily_mean, normal_baseline_1016_25_daily_mean,
    trend_baseline_2000_25_daily_mean), all persisted to
    silver/rainfall_daily_mean/.

    Two different historical windows on purpose, not a shortcut: the
    published "+226.6% / +540.9% vs. normal" figures are pinned to the
    2016-2025 normal used since the first session this was computed and
    quoted throughout the site/README -- silently widening that baseline
    to the later-added 2000-2025 archive would shift the published
    percentages without anyone asking for that. The 26-year archive is
    only for the separate "is this getting worse" trend table."""
    event_bronze = _read_bronze(f"{region}_daily_range_*.parquet")
    normal_bronze = _read_bronze(f"{region}_yearly_2016_2025.parquet")
    trend_bronze = _read_bronze(f"{region}_yearly_2000_2025.parquet")

    event_silver = compute_regional_daily_mean(event_bronze)
    normal_silver = compute_regional_daily_mean(normal_bronze)
    trend_silver = compute_regional_daily_mean(trend_bronze)

    out_dir = silver_path("rainfall_daily_mean")
    event_silver.to_parquet(out_dir / f"{region}_event.parquet", index=False)
    normal_silver.to_parquet(out_dir / f"{region}_normal_2016_2025.parquet", index=False)
    trend_silver.to_parquet(out_dir / f"{region}_trend_2000_2025.parquet", index=False)
    print(
        f"Wrote silver daily-mean tables for {region} "
        f"({len(event_silver)} event rows, {len(normal_silver)} normal-baseline rows, "
        f"{len(trend_silver)} trend-baseline rows)"
    )
    return event_silver, normal_silver, trend_silver


def build_gold_for_region(region: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (rainfall_anomaly_timeline, historical_frequency_for_region)."""
    event_silver, normal_silver, trend_silver = build_silver_daily_mean(region)

    normal = compute_monthly_normal(normal_silver)
    anomaly = compute_anomaly(event_silver, normal)
    anomaly_path = _gold_root() / f"{region}_rainfall_anomaly_timeline.parquet"
    anomaly.to_parquet(anomaly_path, index=False)
    print(f"Wrote {len(anomaly)} rows to {anomaly_path}")

    trend = compute_yearly_trend(trend_silver)
    return anomaly, trend


def build_all(regions=("assam", "gujarat")) -> None:
    trends = []
    for region in regions:
        _, trend = build_gold_for_region(region)
        trends.append(trend)

    trend_df = pd.concat(trends, ignore_index=True)
    trend_path = _gold_root() / "historical_frequency.parquet"
    trend_df.to_parquet(trend_path, index=False)
    print(f"Wrote {len(trend_df)} rows to {trend_path}")


if __name__ == "__main__":
    build_all()
