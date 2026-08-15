"""Silver/gold: multi-year monsoon-season rainfall-extremity trend.

A proxy for "is this getting worse," not a verified flood-event count --
CWC/WRIS gauge history isn't open (see README), so this uses rainfall
extremity as a stand-in. Monsoon season here is June-September inclusive,
the standard Indian Southwest Monsoon window.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MONSOON_MONTHS = {6, 7, 8, 9}


def _monsoon_only(daily_means: pd.DataFrame) -> pd.DataFrame:
    df = daily_means.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    return df[df["date"].dt.month.isin(MONSOON_MONTHS)]


def compute_extremity_threshold(monsoon_daily_means: pd.DataFrame) -> float:
    """2x the all-years monsoon daily mean, per the plan's own definition."""
    return 2 * monsoon_daily_means["mean_rainfall_mm"].mean()


def compute_yearly_trend(regional_daily_means: pd.DataFrame) -> pd.DataFrame:
    """regional_daily_means: region, date, mean_rainfall_mm (output of
    compute_regional_daily_mean on a multi-year bronze frame). Returns one
    row per (region, year): total monsoon rainfall, max daily rainfall,
    and a count of days exceeding 2x the region's all-years monsoon mean."""
    rows = []
    for region, group in regional_daily_means.groupby("region"):
        monsoon = _monsoon_only(group)
        threshold = compute_extremity_threshold(monsoon)
        for year, yr_group in monsoon.groupby("year"):
            rows.append(
                {
                    "region": region,
                    "year": int(year),
                    "total_monsoon_mm": yr_group["mean_rainfall_mm"].sum(),
                    "max_daily_mm": yr_group["mean_rainfall_mm"].max(),
                    "extreme_day_count": int((yr_group["mean_rainfall_mm"] > threshold).sum()),
                    "extremity_threshold_mm": threshold,
                }
            )
    return pd.DataFrame(rows).sort_values(["region", "year"]).reset_index(drop=True)


def linear_trend(yearly_trend: pd.DataFrame, region: str, metric: str) -> tuple[float, float]:
    """Least-squares (slope, intercept) of `metric` vs. year, for one
    region -- positive slope means increasing over the period covered."""
    sub = yearly_trend[yearly_trend["region"] == region]
    slope, intercept = np.polyfit(sub["year"], sub[metric], 1)
    return float(slope), float(intercept)


def linear_trend_slope(yearly_trend: pd.DataFrame, region: str, metric: str) -> float:
    """Simple least-squares slope of `metric` vs. year, for one region --
    positive means increasing over the period covered."""
    slope, _intercept = linear_trend(yearly_trend, region, metric)
    return slope
