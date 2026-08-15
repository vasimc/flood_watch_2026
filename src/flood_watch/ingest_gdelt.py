"""Bronze ingestion: GDELT news-attention timeline.

GDELT DOC 2.0 API (api.gdeltproject.org), no auth needed, verified live
2026-08-15: `mode=timelinevolraw` returns a real daily article-count series
for a text query. GDELT's own terms require attribution + a link on any use
or redistribution of the data (see README.md's licensing section) -- this
is stricter than the other Tier A sources, where attribution is a request
not a requirement.

Rate limit observed in practice: the documented "one request per 5 seconds"
undercounts what's actually needed on a shared egress IP (this ran from a
cloud dev environment) -- back-to-back requests 5-10s apart still got
rate-limited with a text response instead of JSON, while a ~20s gap worked
reliably. `_get_with_retry` below backs off accordingly; increase
MIN_GAP_SECONDS further if you see the rate-limit message again.
"""

from __future__ import annotations

import time
from datetime import date

import pandas as pd
import requests

from .warehouse import bronze_path

API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
MIN_GAP_SECONDS = 30
MAX_ATTEMPTS = 5

QUERIES_BY_REGION = {
    "assam": "Assam flood",
    "gujarat": "Gujarat flood",
}

_last_request_ts = 0.0


def _get_with_retry(params: dict) -> dict:
    global _last_request_ts
    for attempt in range(1, MAX_ATTEMPTS + 1):
        elapsed = time.monotonic() - _last_request_ts
        if elapsed < MIN_GAP_SECONDS:
            time.sleep(MIN_GAP_SECONDS - elapsed)
        resp = requests.get(API_URL, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=40)
        _last_request_ts = time.monotonic()

        if resp.status_code == 429 or (resp.ok and not resp.text.lstrip().startswith("{")):
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"GDELT rate-limited us {MAX_ATTEMPTS} times in a row -- "
                    f"last response ({resp.status_code}): {resp.text[:200]!r}. "
                    f"Try again later, or raise MIN_GAP_SECONDS further."
                )
            backoff = MIN_GAP_SECONDS * attempt
            print(f"GDELT rate-limited (attempt {attempt}/{MAX_ATTEMPTS}), waiting {backoff}s...")
            time.sleep(backoff)
            continue

        resp.raise_for_status()
        return resp.json()
    raise AssertionError("unreachable")


def fetch_timeline(query: str, start_date: date, end_date: date) -> pd.DataFrame:
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": start_date.strftime("%Y%m%d") + "000000",
        "enddatetime": end_date.strftime("%Y%m%d") + "235959",
    }
    payload = _get_with_retry(params)
    points = payload["timeline"][0]["data"]
    df = pd.DataFrame(points)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df.rename(columns={"value": "article_count", "norm": "total_monitored_articles"})[
        ["date", "article_count", "total_monitored_articles"]
    ]


def ingest_region(region: str, start_date: date, end_date: date) -> pd.DataFrame:
    query = QUERIES_BY_REGION[region]
    df = fetch_timeline(query, start_date, end_date)
    df["region"] = region
    df["query"] = query
    out_path = bronze_path("gdelt_news") / f"{region}_{start_date.isoformat()}_{end_date.isoformat()}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


if __name__ == "__main__":
    from .geo_reference import get_event_window

    for region in ("assam", "gujarat"):
        start_s, end_s = get_event_window(region)
        ingest_region(region, date.fromisoformat(start_s), date.fromisoformat(end_s))
