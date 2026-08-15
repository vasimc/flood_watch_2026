import pandas as pd
import pytest

from flood_watch.extract_impact import ROWS, compute_gold, compute_silver, parse_estimate_flag


def test_every_row_has_a_traceable_citation():
    required = {"region", "metric", "value", "as_of_date", "source_org", "source_url"}
    for row in ROWS:
        assert required.issubset(row.keys())
        assert row["source_url"].startswith("http")
        assert row["source_org"]
        assert row["as_of_date"]


def test_no_duplicate_region_metric_as_of_rows():
    seen = set()
    for row in ROWS:
        key = (row["region"], row["metric"], row["as_of_date"])
        assert key not in seen, f"duplicate row: {key}"
        seen.add(key)


@pytest.mark.parametrize(
    "raw_text,expected",
    [
        ("78", False),
        ("137,561", False),
        ("over 3 lakh", True),
        ("more than 21,500", True),
        ("40,500+", True),
        ("11,000", False),
    ],
)
def test_parse_estimate_flag_reads_the_actual_wording(raw_text, expected):
    assert parse_estimate_flag(raw_text) is expected


def test_build_silver_adds_is_estimate_without_changing_row_count():
    bronze = pd.DataFrame(
        [
            {"region": "x", "metric": "a", "raw_value_text": "over 100", "value": 100, "as_of_date": "2026-01-01"},
            {"region": "x", "metric": "b", "raw_value_text": "5", "value": 5, "as_of_date": "2026-01-01"},
        ]
    )
    silver = compute_silver(bronze)
    assert len(silver) == len(bronze)
    assert list(silver["is_estimate"]) == [True, False]


def test_build_gold_rejects_duplicate_region_metric_as_of_date():
    silver = pd.DataFrame(
        [
            {"region": "x", "metric": "a", "raw_value_text": "5", "value": 5, "as_of_date": "2026-01-01", "is_estimate": False, "context_note": ""},
            {"region": "x", "metric": "a", "raw_value_text": "6", "value": 6, "as_of_date": "2026-01-01", "is_estimate": False, "context_note": ""},
        ]
    )
    with pytest.raises(ValueError):
        compute_gold(silver)
