from datetime import date
from unittest.mock import patch

from flood_watch.ingest_gdelt import fetch_timeline

SAMPLE_PAYLOAD = {
    "query_details": {"title": "Assam flood", "date_resolution": "day"},
    "timeline": [
        {
            "series": "Article Count",
            "data": [
                {"date": "20260720T000000Z", "value": 34, "norm": 129669},
                {"date": "20260721T000000Z", "value": 28, "norm": 184866},
            ],
        }
    ],
}


def test_fetch_timeline_parses_gdelt_payload_into_a_clean_frame():
    with patch("flood_watch.ingest_gdelt._get_with_retry", return_value=SAMPLE_PAYLOAD):
        df = fetch_timeline("Assam flood", date(2026, 7, 20), date(2026, 7, 21))

    assert list(df["date"]) == ["2026-07-20", "2026-07-21"]
    assert list(df["article_count"]) == [34, 28]
    assert list(df["total_monitored_articles"]) == [129669, 184866]
