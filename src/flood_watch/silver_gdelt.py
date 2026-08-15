"""Silver/gold: smoothed GDELT coverage, and its lag against the rainfall peak.

GDELT's raw daily counts are noisy day to day (see the bronze data --
Assam swings from 4 to 87 articles between adjacent days). A 3-day
centered rolling average is the silver-layer smoothing; the gold-layer
question this whole section exists to answer -- "did coverage track the
event, or lag it?" -- was previously only answered in prose on the site.
This makes it a real, re-derivable number instead.
"""

from __future__ import annotations

import pandas as pd

ROLLING_WINDOW_DAYS = 3


def compute_rolling_average(bronze_df: pd.DataFrame, window: int = ROLLING_WINDOW_DAYS) -> pd.DataFrame:
    """bronze_df: region, date, article_count (+ whatever else ingest_gdelt.py
    produced). Adds a `rolling_avg_Nd` column, centered, per region."""
    df = bronze_df.sort_values(["region", "date"]).reset_index(drop=True)
    df[f"rolling_avg_{window}d"] = df.groupby("region")["article_count"].transform(
        lambda s: s.rolling(window, min_periods=1, center=True).mean()
    )
    return df


def compute_coverage_peak_lag(silver_df: pd.DataFrame, region: str, rainfall_peak_date: str) -> dict:
    """Peak-coverage day (by raw article_count, not the smoothed average --
    the actual attention spike, not a smoothed approximation of it) and its
    lag in days against the independently-computed rainfall peak. Negative
    lag_days means news coverage peaked *before* the rainfall peak
    (anticipatory, e.g. red-alert coverage); positive means it lagged."""
    sub = silver_df[silver_df["region"] == region]
    peak_row = sub.loc[sub["article_count"].idxmax()]
    peak_date = pd.Timestamp(peak_row["date"])
    rainfall_peak = pd.Timestamp(rainfall_peak_date)
    return {
        "region": region,
        "peak_date": peak_date.strftime("%Y-%m-%d"),
        "peak_article_count": int(peak_row["article_count"]),
        "rainfall_peak_date": rainfall_peak.strftime("%Y-%m-%d"),
        "lag_days": int((peak_date - rainfall_peak).days),
    }
