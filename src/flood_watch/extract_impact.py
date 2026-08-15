"""Tier B: structured extraction of human-impact/causation figures.

Not an API pull -- these rows are hand-transcribed from cited public
reporting (news, Wikipedia), because no open real-time government feed
exists for casualty/damage figures (see README.md's "Honest data-pipeline
note"). Every row carries region, metric, value, as_of_date, source_org,
source_url so a claim can always be traced back to where it came from.

Gathered 2026-08-14. Re-check dates before trusting these as current --
flood situations change quickly and some of these are already a couple of
weeks stale relative to "today."
"""

from __future__ import annotations

import pandas as pd

from .warehouse import gold_path

ROWS = [
    # --- Assam, as of 2026-07-30 (The Week) ---
    {
        "region": "assam", "metric": "deaths", "value": 78, "unit": "people",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "",
    },
    {
        "region": "assam", "metric": "people_affected", "value": 300000, "unit": "people",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "reported as 'over 3 lakh'",
    },
    {
        "region": "assam", "metric": "relief_camps", "value": 71, "unit": "camps",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "sheltering 16,500+ displaced people",
    },
    {
        "region": "assam", "metric": "relief_distribution_centers", "value": 30, "unit": "centers",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "assisting 72,000+ people",
    },
    {
        "region": "assam", "metric": "crop_damage_hectares", "value": 21500, "unit": "hectares",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "described as 'more than'",
    },
    {
        "region": "assam", "metric": "livestock_washed_away", "value": 11000, "unit": "animals",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "17,000 additional head of livestock affected (non-fatal)",
    },
    {
        "region": "assam", "metric": "worst_hit_district_population_affected", "value": 137561, "unit": "people",
        "as_of_date": "2026-07-30", "source_org": "The Week",
        "source_url": "https://www.theweek.in/news/india/2026/07/30/assam-floods-update-relief-efforts-heavy-rain-warning.html",
        "note": "Charaideo district",
    },
    # --- Assam, as of 2026-08-04 (Wikipedia) -- later snapshot, shows recovery in affected count ---
    {
        "region": "assam", "metric": "deaths", "value": 85, "unit": "people",
        "as_of_date": "2026-08-04", "source_org": "Wikipedia (2026 Assam floods)",
        "source_url": "https://en.wikipedia.org/wiki/2026_Assam_floods",
        "note": "",
    },
    {
        "region": "assam", "metric": "people_affected_remaining", "value": 100000, "unit": "people",
        "as_of_date": "2026-08-04", "source_org": "Wikipedia (2026 Assam floods)",
        "source_url": "https://en.wikipedia.org/wiki/2026_Assam_floods",
        "note": "reported as 'more than 1 lakh people still remained affected' -- distinct metric from the 2026-07-30 cumulative people_affected figure, not directly comparable",
    },
    # --- Gujarat, as of 2026-07-24 (ThePrint / ANI) ---
    {
        "region": "gujarat", "metric": "deaths", "value": 5, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ThePrint",
        "source_url": "https://theprint.in/india/gujarat-rains-see-massive-relief-ops-from-ndrf-army-and-icg-40k-shifted-2637-rescued-5-dead/2996022/",
        "note": "rain-related deaths across Tapi, Valsad, Anand, Mehsana, Panchmahal districts",
    },
    {
        "region": "gujarat", "metric": "evacuated", "value": 40500, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ThePrint",
        "source_url": "https://theprint.in/india/gujarat-rains-see-massive-relief-ops-from-ndrf-army-and-icg-40k-shifted-2637-rescued-5-dead/2996022/",
        "note": "",
    },
    {
        "region": "gujarat", "metric": "rescued", "value": 2637, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ThePrint",
        "source_url": "https://theprint.in/india/gujarat-rains-see-massive-relief-ops-from-ndrf-army-and-icg-40k-shifted-2637-rescued-5-dead/2996022/",
        "note": "",
    },
    {
        "region": "gujarat", "metric": "rescued_single_village", "value": 67, "unit": "people",
        "as_of_date": "2026-07-24", "source_org": "ANI News",
        "source_url": "https://www.aninews.in/news/national/general-news/ndrf-rescues-67-people-from-floodwaters-in-gujarats-navsari-operation-underway20260724093308/",
        "note": "NDRF rescue from Sarikhurad village, Navsari district -- illustrative single-village figure, not a district/state total",
    },
]

# known gaps as of 2026-08-14 -- deliberately not filled with guesses:
#   - Gujarat: no relief-camp count or crop/hectare damage figure found yet
#   - Assam: no confirmed embankment-breach or dam-release causation figure
#     with a citation yet (see README "why" section, which currently draws
#     only on the Down To Earth natural/human-factors summary, not a specific
#     breach event)


def build_impact_summary() -> pd.DataFrame:
    df = pd.DataFrame(ROWS)
    out_path = gold_path("impact_summary") / "impact_summary.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


if __name__ == "__main__":
    build_impact_summary()
