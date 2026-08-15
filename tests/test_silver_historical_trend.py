import pandas as pd
import pytest

from flood_watch.silver_historical_trend import compute_yearly_trend, linear_trend_slope


def test_compute_yearly_trend_counts_extreme_days_and_totals():
    # two monsoon years, region "x": year 1 mild, year 2 has one big spike
    rows = []
    for day in range(1, 31):
        rows.append({"region": "x", "date": f"2020-07-{day:02d}", "mean_rainfall_mm": 5.0})
    for day in range(1, 30):
        rows.append({"region": "x", "date": f"2021-07-{day:02d}", "mean_rainfall_mm": 5.0})
    rows.append({"region": "x", "date": "2021-07-30", "mean_rainfall_mm": 200.0})
    df = pd.DataFrame(rows)

    trend = compute_yearly_trend(df)

    y2020 = trend[trend["year"] == 2020].iloc[0]
    y2021 = trend[trend["year"] == 2021].iloc[0]

    assert y2020["extreme_day_count"] == 0
    assert y2021["extreme_day_count"] == 1
    assert y2021["max_daily_mm"] == 200.0
    assert y2021["total_monsoon_mm"] > y2020["total_monsoon_mm"]


def test_linear_trend_slope_positive_for_increasing_series():
    trend = pd.DataFrame(
        {
            "region": ["x"] * 5,
            "year": [2016, 2017, 2018, 2019, 2020],
            "total_monsoon_mm": [100, 120, 140, 160, 180],
        }
    )
    slope = linear_trend_slope(trend, "x", "total_monsoon_mm")
    assert slope == pytest.approx(20.0)
