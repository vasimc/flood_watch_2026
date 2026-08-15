import pandas as pd

from flood_watch.silver_rainfall import (
    compute_anomaly,
    compute_monthly_normal,
    compute_regional_daily_mean,
)


def test_compute_regional_daily_mean_averages_across_grid_cells():
    bronze = pd.DataFrame(
        {
            "region": ["assam", "assam", "assam"],
            "date": ["2026-07-20", "2026-07-20", "2026-07-20"],
            "lat": [26.0, 26.25, 26.5],
            "lon": [92.0, 92.0, 92.0],
            "rainfall_mm": [10.0, 20.0, 30.0],
        }
    )
    out = compute_regional_daily_mean(bronze)
    assert len(out) == 1
    assert out.iloc[0]["mean_rainfall_mm"] == 20.0


def test_compute_anomaly_flags_above_normal_rainfall():
    historical = pd.DataFrame(
        {
            "region": ["assam"] * 4,
            "date": ["2020-07-15", "2021-07-15", "2022-07-15", "2023-07-15"],
            "mean_rainfall_mm": [20.0, 22.0, 18.0, 20.0],
        }
    )
    normal = compute_monthly_normal(historical)
    assert normal.iloc[0]["normal_mm"] == 20.0

    actual = pd.DataFrame(
        {"region": ["assam"], "date": ["2026-07-20"], "mean_rainfall_mm": [45.0]}
    )
    result = compute_anomaly(actual, normal)

    assert result.iloc[0]["normal_mm"] == 20.0
    assert result.iloc[0]["pct_departure"] == 125.0  # 45 vs 20 normal = +125%
