# Assam & Gujarat Floods 2026 — Data Story

**Live site: https://vasimc.github.io/flood_watch_2026/**

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
| [geoBoundaries](https://www.geoboundaries.org/) (India ADM1+ADM2, via GEE) | real district boundaries for 7 worst-hit districts + full state outlines (Assam, Gujarat) for map context | free via GEE catalog (`WM/geoLab/geoBoundaries/600/ADM1`, `.../ADM2`), no download needed | reference/dimension data — not a fact source, ODbL 1.0 (see licensing below) |
| [Protomaps](https://protomaps.com/) basemap (OSM-derived) | real roads, place names, water, admin boundaries for the "Real map" toggle on the district-extent view | self-hosted static `.pmtiles` extracts in `site/assets/` (cropped from a Protomaps daily build via `pmtiles extract`), no tile server at runtime | reference/dimension data, ODbL 1.0 (OpenStreetMap contributors, via Protomaps) |
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
| `gold.flood_extent_gee` | `flooded_area_km2` | flooded area from Sentinel-1 SAR before/after ratio change detection, region-level bbox |
| `gold.flood_extent_by_district` | `flooded_area_km2` | same method, per real district polygon — deliberately not reconciled with the region-level number, see README/site caveat |
| `gold.news_attention` | `lag_days` | days between peak news coverage and the independently-computed rainfall peak (negative = anticipatory) |
| `gold.impact_summary` | `source_url` | citation for every impact/causation figure (Tier B); `is_estimate` flags floor/approximation figures (e.g. "over 3 lakh") vs. exact counts |

## Architecture

A live, rendered version of this diagram (with real table names and row
counts) is on the site itself, in the "How this was built" section:
https://vasimc.github.io/flood_watch_2026/#architecture

All four sources flow through the same three real, persisted layers --
one genuinely different transform per source in silver, not four copies
of the same relabeled step:

```
SOURCE                BRONZE (raw)        SILVER (one real transform)      GOLD (story-ready)
-----------------     ----------------    ------------------------------   -----------------------
IMD Pune (rainfall) -> rainfall_imd    -> daily_mean + monthly normal   -> rainfall_anomaly_timeline
                                                                            historical_frequency
Sentinel-1 (GEE)    -> satellite_gee   -> pixel classification         -> flood_extent_gee
                        (raw passes)      (SAR ratio > 1.25)              flood_extent_by_district
                        region + per-district, same method clipped to real geoBoundaries polygons
GDELT                -> gdelt_news      -> 3-day rolling average        -> news_attention
                                                                            (peak-day / lag vs. rainfall)
News + Wikipedia     -> impact_reports -> typed + is_estimate flag     -> impact_summary
(manual)                (raw quote)       (parsed from the actual wording)
```

Every gold table above is produced by a real, re-runnable script (`gold_rainfall.py`,
`ingest_satellite_gee.py` / `ingest_flood_extent_district.py`, `gold_gdelt.py`,
`extract_impact.py`) -- not interactive one-off code. All outputs converge into `export_site_data.py`,
which writes `site/data/*.json`, which the static site fetches at runtime:

```
                         site/data/*.json (export)
                                    |
                                    v
                      static site (GitHub Pages)
```

Storage: plain Parquet files under `data/{bronze,silver,gold}/`, read and
written directly via pandas' `read_parquet()`/`to_parquet()` — no warehouse
or database layer in front of it.

## Project layout

```
flood_watch_2026/
  src/flood_watch/            importable ingestion/transform logic
    export_site_data.py       reads gold Parquet, writes site/data/*.json
  notebooks/                  thin scripts that call src/ functions for interactive checks
  data/                       bronze/silver/gold Parquet + raw downloads (gitignored, /data/ only)
    reference/                 static reference geometry (district boundaries), not a fact table
  tests/                      pytest unit tests for transform logic
  site/
    index.html                the durable site (GitHub Pages) -- reads site/data/*.json at runtime
    index_prototype.html       earlier draft, published as a Claude Artifact, kept for reference
    data/*.json                exported by export_site_data.py, committed (not gitignored)
    vendor/                    self-hosted MapLibre GL JS + PMTiles JS (BSD-3), no CDN dependency
    assets/*.pmtiles           self-hosted OSM basemap extracts (ODbL 1.0), no tile server dependency
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
- [x] Website prototype published (Claude Artifact — earlier draft, kept for reference)
- [x] Narrative/preparedness section (warning systems, cited 2026-response lessons, NDMA guidance)
- [x] Durable `site/index.html` reading `site/data/*.json`, verified with a real headless browser both locally and live
- [x] GitHub repo created + pushed: https://github.com/vasimc/flood_watch_2026
- [x] Deployed to GitHub Pages: **https://vasimc.github.io/flood_watch_2026/** (auto-redeploys on push via `.github/workflows/pages.yml`)
- [x] All 4 sources on real, consistent bronze/silver/gold (medallion architecture applied uniformly, not shortcut per-source)
- [x] District-level flood-extent map — real geoBoundaries district polygons, per-district SAR classification, rendered as an actual choropleth map on the site

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
| GDELT | fully open — "unlimited and unrestricted use for any academic, commercial, or governmental use," redistribution of derived data explicitly permitted | attribution **is mandatory**: cite the GDELT Project + link to gdeltproject.org wherever this data or anything derived from it is used |
| geoBoundaries (India ADM1+ADM2 district/state boundaries) | ODbL 1.0 — checked the actual license text (not the marketing page's "CC BY 4.0" headline claim), which is stricter for this specific dataset | derived *statistics* (flooded_area_km2 per district) only need simple attribution (ODbL §4.3); republishing the boundary *geometries themselves*, as this site does for the map, counts as extracting a substantial part of the source and requires the ODbL notice alongside that specific data (§4.2/4.4) — both included on the site and in `ingest_district_boundaries.py` |
| Protomaps basemap tiles (OpenStreetMap-derived, `site/assets/*.pmtiles`) | ODbL 1.0 — same license family and same "republishing the actual geodata triggers the stricter clause" reasoning as geoBoundaries above; Protomaps' own tooling/build pipeline is BSD-3, only the underlying OSM map *data* is ODbL | attribution required and shown on the map itself: "© OpenStreetMap contributors, Protomaps" |
| MapLibre GL JS + PMTiles JS (self-hosted in `site/vendor/`) | BSD-3-Clause, no restrictions | license file not required to be bundled for this use, but see the projects' own LICENSE files if redistributing the libraries themselves |
| Wikipedia | facts are freely reusable even without attribution; our citations link back anyway | none beyond the existing link |
| News outlets (The Week, Down To Earth, ThePrint, ANI News, Nativeplanet) | citing bare facts (death tolls, figures) with an attributed link is standard, low-risk practice in both US and Indian copyright law (facts aren't copyrightable; short attributed use for reporting/commentary falls within fair use / India's Section 52(1)(a) fair dealing) | attribute + link (already the site's practice) |

**One thing changed as a result of this check:** Down To Earth's terms use
broad "no reproduction" language, so a direct one-sentence quote on the site
was rewritten as a paraphrase instead — removes any ambiguity even though the
original short attributed quote was almost certainly fine under fair dealing.

**Not published anywhere in this repo or the site:** raw downloaded files
(NetCDF, GeoTIFF, binary grids, PDFs) — `data/` is gitignored end-to-end.
What is shown publicly is either derived statistics, cited facts, or (for
the district boundaries specifically) the real reference geometry itself,
published deliberately and with the license it actually requires (see the
geoBoundaries/ODbL row above), not by accident.
