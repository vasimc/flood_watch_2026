from flood_watch.extract_impact import ROWS


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
