# Assam & Gujarat Floods 2026 — Data Story

A personal, cause-driven data project — separate from my consulting portfolio work
— built in response to the 2026 Assam and Gujarat floods. Real ingestion of
satellite flood-extent and historical rainfall data, plus an honestly-labeled
structured extraction of impact/causation figures from published situation
reports, telling what happened, where, why, and how to prepare next time.

## Why this project

The 2026 floods in Assam and Gujarat displaced large numbers of people and did
serious damage, and most public coverage of it is either raw news or static
government bulletins — nothing that ties rainfall, flood extent, and impact
together into one queryable, visual story. This project builds that: a small,
honest data pipeline end-to-end, solo, using public data — and a website that
presents it as accessible infographics rather than another dashboard.

## Dataset

| source | what it provides | access | tier |
|---|---|---|---|
| [Sentinel-1 SAR via Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) | 10m flood-extent (radar, sees through monsoon cloud cover) | GEE non-commercial project registration (same-day self-service) | A — automated ingestion, **primary satellite source**, run live 2026-08-15 (Assam 2,389 km², Gujarat 83 km² — see PROGRESS.md for the Gujarat undercount caveat) |
| [NASA LANCE MODIS/VIIRS Global Flood Product](https://nrt3.modaps.eosdis.nasa.gov/) | 250m flood-extent GeoTIFF, near-real-time | Earthdata Login | A — automated ingestion, kept as a documented but deprioritized alternative (Earthdata Login wait is open-ended; GEE was faster to access and better suited to monsoon cloud cover) |
| [IMD Pune gridded rainfall — yearly archive](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) | 0.25°×0.25° daily rainfall, NetCDF, one file per year (years up to 2025 as of 2026-08-14) | free, no registration (verified POST endpoint) | A — automated ingestion, historical-normal baseline |
| [IMD Pune gridded rainfall — realtime daily](https://www.imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html) | 0.25°×0.25° single-day rainfall, raw binary grid, **includes current 2026 dates** | free, no registration (verified POST endpoint) | A — automated ingestion, actual event-date rainfall |
| [GDELT](https://www.gdeltproject.org/) | daily news-article-volume timeline per query (DOC 2.0 API) | free, no auth; strict rate limit in practice (~30s between requests) | A — automated ingestion, attribution required by GDELT's own terms |
| [ReliefWeb](https://reliefweb.int/) / ASDMA / Gujarat SEOC sitreps | deaths, relief camps, crop damage, embankment breach reports | manual PDF/HTML | B — structured extraction |

**Honest data-pipeline note:** rainfall, GDELT, and satellite flood-extent are
genuinely automated ingestion, rerunnable end-to-end. Rainfall and GDELT are
fully verified working end-to-end as of 2026-08-15, including real 2026
event-date numbers (e.g. Assam on 2026-07-20: +226.6% rainfall departure vs.
the 2016-2025 July normal, computed from real IMD data). Satellite ingestion
(`ingest_satellite_gee.py`, Sentinel-1 via Google Earth Engine) is run live
as of 2026-08-15 against a citable methodology (UN-SPIDER's Sentinel-1
change-detection recipe): Assam shows 2,389 km² flooded from a clean
same-week before/after comparison; Gujarat shows 83 km², but its after-window
had to auto-widen out to 10 days post-peak (Sentinel-1's ~12-day revisit
interval left it with no closer pass), so that number is a real measurement
but likely an undercount of the true peak extent — flagged in the data itself
(`after_window_widened` column) and on the site, not smoothed over. Impact
and causation figures (deaths,
damage, breach causes, dam-release decisions) are hand-extracted from cited
published reports — no open real-time government API exists for these right
now (CWC/WRIS river-gauge data is view-only with no export, Brahmaputra
basin data is on-request only, IMD's district API has registrations paused,
Google Flood Hub's API is waitlist-only). Every Tier B row carries `source_url` /
`source_org` / `report_date` so the extraction is traceable, not invented.

We also considered Google's other flood-data resources before picking
Earth Engine: Google Flood Hub's API remains waitlist-gated (approval takes
"several months" per their own docs) — not an improvement over the NASA
Earthdata wait, so skipped. GDELT's raw 15-minute bulk files were considered
as an alternative to their DOC 2.0 API for the news-attention timeline, but
would have meant ~3,500 file downloads across both event windows for a
lower-priority chart — the pre-aggregated timeline API was the right tool
for that specific job.

Column glossary (gold layer, added as tables land):

| table | column | meaning |
|---|---|---|
| `gold.rainfall_anomaly_timeline` | `pct_departure` | % actual rainfall vs. historical normal for that district/date |
| `gold.historical_frequency` | `extreme_day_count` | monsoon days/year exceeding 2x the 26-year monsoon-day mean, per region |
| `gold.flood_extent_gee` | `flooded_area_km2` | flooded area from Sentinel-1 SAR before/after ratio change detection |
| `gold.impact_summary` | `source_url` | citation for every impact/causation figure (Tier B) |

## Architecture

```
Sentinel-1 (via GEE) --+
NASA LANCE (GeoTIFF)   +
IMD CDSP (NetCDF)      +--> BRONZE (raw, as-received, Parquet)
GDELT (JSON)           +
ReliefWeb/SEOC (PDF) --+        [manual retrieval + structured extraction]
                                    |
                                    v
                    +----------------------------+
                    |   SILVER  (silver_*.py)    |  district-level aggregation,
                    |                            |  rainfall anomaly vs. normal,
                    |                            |  flood-extent by district/date
                    +----------------------------+
                                    |
                                    v
                    +----------------------------+
                    |   GOLD    (gold_metrics.py)|  story-ready joined tables
                    +----------------------------+
                                    |
                                    v
                         site/data/*.json (export)
                                    |
                                    v
                      static site (GitHub Pages)
```

Warehouse: a single local DuckDB file (`data/flood_watch.duckdb`) reading Parquet
directly via `read_parquet()` — no double-storage, inspectable with plain SQL.

## Project layout

```
flood_watch_2026/
  src/flood_watch/            importable ingestion/transform logic
    export_site_data.py       reads gold Parquet, writes site/data/*.json
  notebooks/                  thin scripts that call src/ functions for interactive checks
  data/                       bronze/silver/gold Parquet + raw downloads (gitignored, /data/ only)
  tests/                      pytest unit tests for transform logic
  site/
    index.html                the durable site (GitHub Pages) -- reads site/data/*.json at runtime
    index_prototype.html       earlier draft, published as a Claude Artifact, kept for reference
    data/*.json                exported by export_site_data.py, committed (not gitignored)
```

Run `python -m flood_watch.export_site_data` (with `src` on `PYTHONPATH`, same as the
other scripts) any time upstream gold data changes -- `site/index.html` picks it up
on next load, no HTML edits needed. `site/index.html` must be served over `http(s)://`
(GitHub Pages does this); opening it directly as a `file://` URL blocks `fetch()` of
the local JSON via CORS, same limitation every static site with client-side fetch has.

## Setup / run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in GEE_PROJECT_ID (and NASA_EARTHDATA_TOKEN if you want the alternative)
```

**One-time Earth Engine registration** (do this yourself — it's tied to your
own Google account, same principle as the NASA token below):
1. Create/pick a Google Cloud project.
2. Register it for Earth Engine non-commercial use at
   [code.earthengine.google.com/register](https://code.earthengine.google.com/register)
   (a same-day eligibility questionnaire, not a manual approval queue).
3. Put that project's ID in `.env` as `GEE_PROJECT_ID`.
4. Run `python -m flood_watch.ingest_satellite_gee` once from the project
   root with `src` on `PYTHONPATH` — the first run opens a browser OAuth
   prompt (`ee.Authenticate()`); after that, credentials are cached and
   later runs are headless.

```bash
python notebooks/02_explore_lance_flood.py   # bootstraps src/ onto sys.path itself
python -m pytest tests/ -q                    # pytest.ini sets pythonpath = src
```

## Status

- [x] Repo skeleton
- [x] Sentinel-1 (GEE) flood-extent ingestion — run live 2026-08-15 (Assam 2,389 km², Gujarat 83 km² with an undercount caveat, see PROGRESS.md)
- [x] IMD rainfall ingestion + anomaly calc (Assam)
- [x] Gujarat extension
- [x] Impact/causation extraction table (13 cited rows)
- [x] Historical trend analysis (2000-2025, monsoon rainfall extremity)
- [x] GDELT attention timeline
- [x] Website prototype published (Claude Artifact, not yet the durable GitHub Pages site)
- [x] Narrative/preparedness section (warning systems, cited 2026-response lessons, NDMA guidance)
- [x] Durable `site/index.html` reading `site/data/*.json` (built, tested locally with a headless browser, not yet deployed)
- [ ] GitHub repo created + pushed (site/index.html not yet live on GitHub Pages)

## Data licensing & attribution

Checked 2026-08-14 against each source's actual terms (not assumed) — every
source below is safe for this project's use (public, non-commercial, derived
statistics with attribution), with one adjustment already made.

| source | verdict | requirement |
|---|---|---|
| Copernicus Sentinel-1 (via Google Earth Engine) | free, full, open access under EU Regulation 377/2014 — explicitly covers reproduction, distribution, and *adaptation/modification* (our derived flood-extent stats qualify) | attribution required: `Contains modified Copernicus Sentinel data [Year]` |
| Google Earth Engine (platform ToS, separate from the Sentinel-1 data license) | safe — ToS explicitly permits using "data, diagrams, charts, figures created by use of the Services in research or educational publications" | non-commercial use only (this project qualifies; commercial use needs separate GEE enrollment) |
| NASA LANCE / LAADS (MCDWD) | no reuse restrictions — NASA data is effectively public domain | attribution requested, not required: *"We acknowledge the use of data and/or imagery from NASA's Land, Atmosphere Near real-time Capability for Earth observations (LANCE)..."* |
| IMD Pune gridded rainfall | safe for derived statistics; site-wide disclaimer restricts reproducing raw content without permission | cite Pai et al. (2014), MAUSAM 65(1), pp1–18; don't publicly host/link the raw NetCDF/binary files (they stay in gitignored `data/`) |
| GDELT (planned, not yet ingested) | fully open — "unlimited and unrestricted use for any academic, commercial, or governmental use," redistribution of derived data explicitly permitted | attribution **is mandatory**: cite the GDELT Project + link to gdeltproject.org wherever this data or anything derived from it is used |
| Wikipedia | facts are freely reusable even without attribution; our citations link back anyway | none beyond the existing link |
| News outlets (The Week, Down To Earth, ThePrint, ANI News, Nativeplanet) | citing bare facts (death tolls, figures) with an attributed link is standard, low-risk practice in both US and Indian copyright law (facts aren't copyrightable; short attributed use for reporting/commentary falls within fair use / India's Section 52(1)(a) fair dealing) | attribute + link (already the site's practice) |

**One thing changed as a result of this check:** Down To Earth's terms use
broad "no reproduction" language, so a direct one-sentence quote on the site
was rewritten as a paraphrase instead — removes any ambiguity even though the
original short attributed quote was almost certainly fine under fair dealing.

**Not published anywhere in this repo or the site:** raw downloaded files
(NetCDF, GeoTIFF, binary grids, PDFs) — `data/` is gitignored end-to-end.
Only derived statistics and cited facts are shown publicly.
