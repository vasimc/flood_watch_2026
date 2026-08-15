"""Export gold-layer Parquet into the static JSON files site/index.html reads.

The prototype (site/index_prototype.html) embeds every number inline in a
<script> block -- fine for a fast Artifact draft, but the durable site is
supposed to read real files per the project plan, so nothing on the page
is hand-typed. This script is the one place that turns gold Parquet into
site/data/*.json; re-run it any time upstream data changes and the site
picks it up on next load, no HTML edits needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .silver_historical_trend import linear_trend
from .warehouse import DATA_DIR, PROJECT_ROOT

SITE_DATA_DIR = PROJECT_ROOT / "site" / "data"

REGIONS = ("assam", "gujarat")


def export_rainfall() -> dict:
    out = {}
    for region in REGIONS:
        df = pd.read_parquet(DATA_DIR / "gold" / f"{region}_rainfall_anomaly_timeline.parquet")
        df = df.sort_values("date")
        out[region] = [
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "actual": round(float(row.mean_rainfall_mm), 1),
                "normal": round(float(row.normal_mm), 1),
                "dep": round(float(row.pct_departure), 1),
            }
            for row in df.itertuples()
        ]
    return out


def export_trend() -> dict:
    df = pd.read_parquet(DATA_DIR / "gold" / "historical_frequency.parquet")
    out = {}
    for region in REGIONS:
        sub = df[df["region"] == region].sort_values("year")
        slope, intercept = linear_trend(df, region, "extreme_day_count")
        total_slope, _total_intercept = linear_trend(df, region, "total_monsoon_mm")
        out[region] = {
            "slope": round(slope, 4),
            "intercept": round(intercept, 2),
            "total_mm_slope": round(total_slope, 2),
            "years": [[int(r.year), int(r.extreme_day_count)] for r in sub.itertuples()],
        }
    return out


def export_news() -> dict:
    out = {}
    for region in REGIONS:
        files = sorted((DATA_DIR / "bronze" / "gdelt_news").glob(f"{region}_*.parquet"))
        if not files:
            out[region] = []
            continue
        df = pd.read_parquet(files[-1]).sort_values("date")
        out[region] = [
            [pd.Timestamp(row.date).strftime("%m-%d"), int(row.article_count)]
            for row in df.itertuples()
        ]
    return out


def export_flood_extent() -> list:
    df = pd.read_parquet(DATA_DIR / "gold" / "flood_extent" / "flood_extent_gee.parquet")
    return [
        {
            "region": row.region,
            "peak_date": row.peak_date,
            "before_window": row.before_window,
            "after_window": row.after_window,
            "before_image_count": int(row.before_image_count),
            "after_image_count": int(row.after_image_count),
            "before_window_widened": bool(row.before_window_widened),
            "after_window_widened": bool(row.after_window_widened),
            "flooded_area_km2": round(float(row.flooded_area_km2), 1),
        }
        for row in df.itertuples()
    ]


def export_impact() -> list:
    df = pd.read_parquet(DATA_DIR / "gold" / "impact_summary" / "impact_summary.parquet")
    return [
        {
            "region": row.region,
            "metric": row.metric,
            "value": int(row.value),
            "unit": row.unit,
            "as_of_date": row.as_of_date,
            "source_org": row.source_org,
            "source_url": row.source_url,
            "note": row.note or "",
            "is_estimate": bool(row.is_estimate),
        }
        for row in df.itertuples()
    ]


def export_news_attention() -> list:
    df = pd.read_parquet(DATA_DIR / "gold" / "news_attention.parquet")
    return [
        {
            "region": row.region,
            "peak_date": row.peak_date,
            "peak_article_count": int(row.peak_article_count),
            "rainfall_peak_date": row.rainfall_peak_date,
            "lag_days": int(row.lag_days),
        }
        for row in df.itertuples()
    ]


def export_all() -> None:
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    exports = {
        "rainfall.json": export_rainfall(),
        "trend.json": export_trend(),
        "news.json": export_news(),
        "news_attention.json": export_news_attention(),
        "flood_extent.json": export_flood_extent(),
        "impact.json": export_impact(),
    }
    for filename, payload in exports.items():
        path = SITE_DATA_DIR / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {path} ({len(json.dumps(payload))} bytes)")


if __name__ == "__main__":
    export_all()
