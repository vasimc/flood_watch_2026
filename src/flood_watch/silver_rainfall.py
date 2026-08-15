"""Silver: regional daily rainfall means and anomaly vs. historical normal."""

from __future__ import annotations

import pandas as pd


def compute_regional_daily_mean(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse a bronze rainfall frame (region, date, lat, lon, rainfall_mm)
    to one region-mean-mm-per-day row."""
    out = bronze_df.groupby(["region", "date"], as_index=False)["rainfall_mm"].mean()
    return out.rename(columns={"rainfall_mm": "mean_rainfall_mm"})


def compute_monthly_normal(yearly_daily_means: pd.DataFrame) -> pd.DataFrame:
    """Historical monthly-mean rainfall per region from multiple years of
    regional daily means (output of compute_regional_daily_mean on a
    multi-year ingest_yearly bronze frame)."""
    df = yearly_daily_means.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    normal = df.groupby(["region", "month"], as_index=False)["mean_rainfall_mm"].mean()
    return normal.rename(columns={"mean_rainfall_mm": "normal_mm"})


def compute_anomaly(actual_daily: pd.DataFrame, normal_monthly: pd.DataFrame) -> pd.DataFrame:
    """actual_daily: region, date, mean_rainfall_mm (one or more single dates).
    normal_monthly: region, month, normal_mm (output of compute_monthly_normal).
    Returns actual_daily with normal_mm and pct_departure columns added."""
    df = actual_daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    merged = df.merge(normal_monthly, on=["region", "month"], how="left")
    merged["pct_departure"] = (
        (merged["mean_rainfall_mm"] - merged["normal_mm"]) / merged["normal_mm"] * 100
    )
    return merged.drop(columns=["month"])
