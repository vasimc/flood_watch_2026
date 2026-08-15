"""Tier B: structured extraction of human-impact/causation figures.

Not an API pull -- these rows are hand-transcribed from cited public
reporting (news, Wikipedia), because no open real-time government feed
exists for casualty/damage figures (see README.md's "Honest data-pipeline
note"). Every row carries region, metric, as_of_date, source_org, source_url
so a claim can always be traced back to where it came from.

Three layers, honestly scoped: BRONZE is the literal transcription --
`raw_value_text` (the exact phrase as reported, e.g. "over 3 lakh") plus
`value` (the analyst's numeric read of that phrase, recorded at the same
time as the quote itself -- there's no separate automated text-to-number
parser here, and pretending "over 3 lakh" gets programmatically parsed
into 300000 via a `lakh`-aware regex would be fake rigor; a human read the
source and captured both the quote and its value in one step, same as any
manual transcription). SILVER adds one real derived column,
`is_estimate`, computed from `raw_value_text` by an actual function
(`parse_estimate_flag`), not hand-typed. GOLD validates uniqueness and
drops the working `raw_value_text` column for the final display shape
(the underlying quote is still visible in `context_note` where it adds
real information beyond the number).

Gathered 2026-08-14. Re-check dates before trusting these as current --
flood situations change quickly and some of these are already a couple of
weeks stale relative to "today."
"""

from __future__ import annotations

import pandas as pd

from .warehouse import bronze_path, gold_path, silver_path

ROWS = [
    # --- Assam, as of 2026-07-30 (The Week) ---
    {
        "region": "assam", "metric": "deaths", "raw_value_text": "78", "value": 78, "unit": "people",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "",
    },
    {
        "region": "assam", "metric": "people_affected", "raw_value_text": "over 3 lakh", "value": 300000, "unit": "people",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "",
    },
    {
        "region": "assam", "metric": "relief_camps", "raw_value_text": "71", "value": 71, "unit": "camps",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "sheltering 16,500+ displaced people",
    },
    {
        "region": "assam", "metric": "relief_distribution_centers", "raw_value_text": "30", "value": 30, "unit": "centers",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "assisting 72,000+ people",
    },
    {
        "region": "assam", "metric": "crop_damage_hectares", "raw_value_text": "more than 21,500", "value": 21500, "unit": "hectares",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "",
    },
    {
        "region": "assam", "metric": "livestock_washed_away", "raw_value_text": "11,000", "value": 11000, "unit": "animals",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "17,000 additional head of livestock affected (non-fatal)",
    },
    {
        "region": "assam", "metric": "worst_hit_district_population_affected", "raw_value_text": "137,561", "value": 137561, "unit": "people",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "context_note": "Charaideo district",
    },
    # --- Assam, as of 2026-08-04 (Wikipedia) -- later snapshot, shows recovery in affected count ---
    {
        "region": "assam", "metric": "deaths", "raw_value_text": "85", "value": 85, "unit": "people",
        "as_of_date": "2026-08-04", "source_org": "Wikipedia (2026 Assam floods)",
        "source_url": "https://en.wikipedia.org/wiki/2026_Assam_floods",
        "context_note": "",
    },
    {
        "region": "assam", "metric": "people_affected_remaining", "raw_value_text": "more than 1 lakh", "value": 100000, "unit": "people",
        "as_of_date": "2026-08-04", "source_org": "Wikipedia (2026 Assam floods)",
        "source_url": "https://en.wikipedia.org/wiki/2026_Assam_floods",
        "context_note": "distinct metric from the 2026-07-30 cumulative people_affected figure, not directly comparable",
    },
    # --- Gujarat, as of 2026-07-24 (ThePrint / ANI) ---
    {
        "region": "gujarat", "metric": "deaths", "raw_value_text": "5", "value": 5, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ThePrint",
        "source_url": "https://theprint.in/india/gujarat-rains-see-massive-relief-ops-from-ndrf-army-and-icg-40k-shifted-2637-rescued-5-dead/2996022/",
        "context_note": "rain-related deaths across Tapi, Valsad, Anand, Mehsana, Panchmahal districts",
    },
    {
        "region": "gujarat", "metric": "evacuated", "raw_value_text": "40,500+", "value": 40500, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ThePrint",
        "source_url": "https://theprint.in/india/gujarat-rains-see-massive-relief-ops-from-ndrf-army-and-icg-40k-shifted-2637-rescued-5-dead/2996022/",
        "context_note": "",
    },
    {
        "region": "gujarat", "metric": "rescued", "raw_value_text": "2,637", "value": 2637, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ThePrint",
        "source_url": "https://theprint.in/india/gujarat-rains-see-massive-relief-ops-from-ndrf-army-and-icg-40k-shifted-2637-rescued-5-dead/2996022/",
        "context_note": "",
    },
    {
        "region": "gujarat", "metric": "rescued_single_village", "raw_value_text": "67", "value": 67, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ANI News",
        "source_url": "https://www.aninews.in/news/national/general-news/ndrf-rescues-67-people-from-floodwaters-in-gujarats-navsari-operation-underway20260724093308/",
        "context_note": "NDRF rescue from Sarikhurad village, Navsari district -- illustrative single-village figure, not a district/state total",
    },
]

# known gaps as of 2026-08-14 -- deliberately not filled with guesses:
#   - Gujarat: no relief-camp count or crop/hectare damage figure found yet
#   - Assam: no confirmed embankment-breach or dam-release causation figure
#     with a citation yet (see README "why" section, which currently draws
#     only on the Down To Earth natural/human-factors summary, not a specific
#     breach event)

ESTIMATE_MARKERS = ("over", "more than", "+")


def parse_estimate_flag(raw_value_text: str) -> bool:
    """True when the raw reported text itself signals the figure is a
    floor/approximation rather than an exact count (e.g. 'over 3 lakh',
    '40,500+') -- a real check against the actual wording, not a guess."""
    text = raw_value_text.lower()
    return any(marker in text for marker in ESTIMATE_MARKERS if marker != "+") or "+" in raw_value_text


def compute_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    """Pure transform: adds `is_estimate`, derived from the raw text."""
    df = bronze_df.copy()
    df["is_estimate"] = df["raw_value_text"].apply(parse_estimate_flag)
    return df


def compute_gold(silver_df: pd.DataFrame) -> pd.DataFrame:
    """Pure transform: validates (no duplicate region+metric+as_of_date
    rows) and shapes for display -- drops the working raw_value_text
    column, keeps everything else including the new is_estimate flag."""
    dupes = silver_df.duplicated(subset=["region", "metric", "as_of_date"])
    if dupes.any():
        raise ValueError(f"Duplicate (region, metric, as_of_date) rows found:\n{silver_df[dupes]}")
    return silver_df.drop(columns=["raw_value_text"]).rename(columns={"context_note": "note"})


def build_bronze() -> pd.DataFrame:
    """BRONZE: the literal hand-transcribed rows, exactly as extracted."""
    df = pd.DataFrame(ROWS)
    out_path = bronze_path("impact_reports") / "impact_reports_raw.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def build_silver(bronze_df: pd.DataFrame) -> pd.DataFrame:
    df = compute_silver(bronze_df)
    out_path = silver_path("impact_summary") / "impact_summary_typed.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def build_gold(silver_df: pd.DataFrame) -> pd.DataFrame:
    df = compute_gold(silver_df)
    out_path = gold_path("impact_summary") / "impact_summary.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


def build_impact_summary() -> pd.DataFrame:
    bronze_df = build_bronze()
    silver_df = build_silver(bronze_df)
    return build_gold(silver_df)


if __name__ == "__main__":
    build_impact_summary()
