import pandas as pd
import pytest

from flood_watch.silver_gdelt import compute_coverage_peak_lag, compute_rolling_average


def test_compute_rolling_average_smooths_within_region_only():
    df = pd.DataFrame(
        {
            "region": ["x", "x", "x", "y", "y", "y"],
            "date": ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-01", "2026-07-02", "2026-07-03"],
            "article_count": [10, 20, 30, 100, 200, 300],
        }
    )
    out = compute_rolling_average(df, window=3)

    x_mid = out[(out.region == "x") & (out.date == "2026-07-02")]["rolling_avg_3d"].iloc[0]
    assert x_mid == pytest.approx(20.0)
    # region y's smoothing must not leak into region x's window
    y_mid = out[(out.region == "y") & (out.date == "2026-07-02")]["rolling_avg_3d"].iloc[0]
    assert y_mid == pytest.approx(200.0)


def test_compute_coverage_peak_lag_negative_means_coverage_anticipated_event():
    df = pd.DataFrame(
        {
            "region": ["gujarat"] * 3,
            "date": ["2026-07-22", "2026-07-23", "2026-07-24"],
            "article_count": [6, 41, 26],
        }
    )
    result = compute_coverage_peak_lag(df, "gujarat", "2026-07-24")

    assert result["peak_date"] == "2026-07-23"
    assert result["peak_article_count"] == 41
    assert result["lag_days"] == -1


def test_compute_coverage_peak_lag_positive_means_coverage_lagged_event():
    df = pd.DataFrame(
        {
            "region": ["assam"] * 3,
            "date": ["2026-07-20", "2026-07-27", "2026-08-03"],
            "article_count": [34, 37, 87],
        }
    )
    result = compute_coverage_peak_lag(df, "assam", "2026-07-20")

    assert result["peak_date"] == "2026-08-03"
    assert result["lag_days"] == 14
