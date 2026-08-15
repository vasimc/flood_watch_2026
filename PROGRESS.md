# Progress Log — Assam & Gujarat Floods 2026

Read this first at the start of a new session. See README.md for architecture/dataset.

**Repo:** not yet created on GitHub (local only so far — see Next steps).

## Status

- [x] Repo skeleton
- [ ] NASA LANCE ingestion — written, deprioritized in favor of GEE (below), not run live
- [x] IMD rainfall ingestion + anomaly calc (Assam & Gujarat) — run live, real numbers
- [x] Gujarat extension — full event-window timelines for both regions, real numbers
- [x] Impact/causation extraction table — 13 cited rows
- [x] Historical trend analysis — 2000-2025, monsoon rainfall extremity
- [x] GDELT attention timeline — run live for both regions
- [x] Sentinel-1 (GEE) satellite flood-extent — run live 2026-08-15, see below
- [x] Narrative/preparedness section — warning systems, cited 2026-response lessons, NDMA guidance
- [x] Durable `site/index.html` reading `site/data/*.json` (built + verified in a real browser)
- [x] GitHub repo created + pushed: https://github.com/vasimc/flood_watch_2026
- [x] Deployed to GitHub Pages: https://vasimc.github.io/flood_watch_2026/
- [x] All 4 sources on real, consistent bronze/silver/gold (not shortcut per-source)
- [x] District-level flood-extent map — real geoBoundaries polygons, per-district SAR, actual choropleth map

## 2026-08-14 — Session entry (skeleton + satellite scaffold)

- What was built: project skeleton (`src/flood_watch/`, `notebooks/`, `data/`,
  `tests/`, `site/`), `requirements.txt`, `.env.example`, `.gitignore`, README.md,
  this file. `warehouse.py`, `geo_reference.py`, `ingest_satellite.py`, and
  `notebooks/02_explore_lance_flood.py` written but **not yet run** — needs a
  NASA Earthdata Login account (create at https://urs.earthdata.nasa.gov/) and a
  `.env` with real credentials before it can pull data.
- Evidence: n/a yet for satellite — still next session's target.

## 2026-08-14 — Session entry (rainfall ingestion, run live)

- What was built: `ingest_rainfall.py` and `silver_rainfall.py`, both run
  end-to-end for real against IMD Pune's public endpoints — no auth needed,
  unlike the satellite source. Two data paths, both verified working:
  - `RF25.php` (yearly archive): POST `{"RF25": year}` returns a real NetCDF
    file (`RAINFALL` var, dims TIME/LATITUDE/LONGITUDE). Years up to 2025
    available.
  - `rain.php` (realtime daily): POST `{"rain": "ddmmyyyy"}` returns a raw
    135x129 float32 binary grid for that single date — **including current
    2026 dates**, which corrects the original assumption (from the Phase 0
    research pass) that IMD gridded rainfall lags the current year. That
    lag applies only to the yearly bulk archive, not this endpoint.
- Evidence (real, computed from real data, not synthetic):
  - Pulled 2026-07-20 (Assam) via the realtime endpoint: region mean 44.9mm,
    max single-cell 354.5mm, 290 of 416 grid cells valid (rest are
    outside-India/ocean, correctly excluded by the missing-value filter).
  - Pulled 2016-2025 yearly archives (Assam), computed the July historical
    normal: 13.7mm mean daily regional rainfall.
  - `compute_anomaly()` result: **2026-07-20 was +226.6% above the 10-year
    July normal for Assam** — a real, defensible number for the "why"
    analysis, not invented.
  - Landed as bronze parquet: `data/bronze/rainfall_imd/assam_daily_2026-07-20.parquet`
    (290 rows) and `data/bronze/rainfall_imd/assam_yearly_2016_2025.parquet`
    (1,059,370 rows).
  - `pytest tests/ -q` — 4 passed, including a binary-grid-parsing test
    (synthetic grid, checks clipping + missing-value handling) and an
    anomaly-calc test (synthetic historical series, checks the +125% case).

## 2026-08-14 — Session entry (real event dates, Gujarat extension, anomaly timelines)

- Corrected the Phase-1 guessed district lists in `geo_reference.py` against
  real sources — the original guess for Assam (Barpeta, Cachar, Nagaon —
  lower/central Assam) was wrong. Confirmed via Wikipedia's "2026 Assam
  floods" article: actual worst-hit districts are Sivasagar, Charaideo,
  Jorhat, Golaghat (upper Assam, Nagaland border), trigger was a 2026-07-19
  cloudburst in Mon district Nagaland, peak devastation 2026-07-21/22,
  worsening again through early August. For Gujarat, confirmed via a
  Nativeplanet report: Valsad, Navsari, Surat, event peaked 2026-07-24
  (Valsad recorded >100cm rain in 24h), rivers Damanganga/Purna (not
  Narmada/Tapi as originally assumed in the Phase-0 research pass).
  `geo_reference.py` now has an `event_window_2026` per region built from
  these dates.
- Added `ingest_daily_range()` to `ingest_rainfall.py` (loops the existing
  verified `rain.php` daily pull over a date range, one bronze Parquet for
  the whole window instead of one file per day).
- Ran it for real: Assam 2026-07-15 to 2026-08-10 (7,830 rows), Gujarat
  2026-07-20 to 2026-07-30 (4,026 rows), plus 2016-2025 yearly baselines for
  both regions (~2.4M rows total).
- Built the anomaly timeline (`silver_rainfall.py` functions, unchanged) for
  both regions, landed as `data/gold/{region}_rainfall_anomaly_timeline.parquet`.
- **Validation that matters:** the rainfall data's own peak-day, computed
  with zero reference to news reports, landed exactly on the independently
  confirmed event date for Gujarat — 2026-07-24, +540.9% vs. the 2016-2025
  normal. Assam's rainfall peaked 2026-07-20 (+226.6%), one day before the
  reported devastation peak (2026-07-21/22) — the kind of runoff lag you'd
  expect physically. This is real cross-validation between an independent
  data pipeline and independently-reported news facts, not circular.
- `pytest tests/ -q` still 4 passed (no test changes this entry, existing
  tests cover the underlying grid-parsing/anomaly-calc logic that
  `ingest_daily_range` reuses unchanged).

## 2026-08-14 — Session entry (infographic prototype, published as a Claude Artifact)

- Per the plan's "Claude Artifact use: prototyping only" step: built
  `site/index_prototype.html`, a single-page infographic reading real numbers
  straight out of `data/gold/*_rainfall_anomaly_timeline.parquet` (embedded
  inline as JSON for now — no external fetches, matches Artifact CSP), plus
  the cited impact/causation figures gathered this session (Wikipedia, Down
  To Earth, Nativeplanet).
- Published: https://claude.ai/code/artifact/4f59475c-d251-46af-a667-2106d4982cc6
  (private until shared from the page's share menu).
- Sections: masthead with headline stats, a status strip (automated / pending
  / manual, matching the Tier A/B framing), combined rainfall-line +
  departure-bar charts per region with hover tooltips and a table-view
  fallback, cited impact stats, a natural-vs-human causes panel (cited), and
  a roadmap footer that's honest about what's still pending (satellite,
  historical trend, GDELT, structured impact table, GitHub Pages deploy).
- Palette validated with the dataviz skill's script before use — light pair
  `#2f7fb0/#c1503f` and dark pair `#4a9bcc/#d1614e` both pass all checks for
  the diverging (above/below normal) encoding.
- **Not yet done:** this is the prototype, not the durable site. Per the
  plan, once satellite/trend/impact-table work lands, port this into
  `site/index.html` reading from real exported `site/data/*.json` (not
  inline-embedded like this draft) and deploy to GitHub Pages.

## 2026-08-14 — Session entry (structured impact table, real citations)

- Built `extract_impact.py`: 13 hand-transcribed, cited rows in
  `data/gold/impact_summary/impact_summary.parquet` (region, metric, value,
  as_of_date, source_org, source_url, note — every row traceable).
- Sourced via targeted search: The Week (Assam, as of 2026-07-30 — 78 deaths,
  300k+ affected, 71 relief camps/16,500+ sheltered, 30 distribution
  centers/72,000+ assisted, 21,500+ ha crop damage, 11,000+ livestock washed
  away, Charaideo 137,561 affected), Wikipedia (Assam, as of 2026-08-04 — 85
  deaths, 100,000+ "still remained affected," a later/lower snapshot as
  waters receded), ThePrint + ANI News (Gujarat, as of 2026-07-24 — 5
  rain-related deaths, 40,500+ evacuated, 2,637 rescued, 67 rescued from one
  Navsari village).
- Two tests added (`test_extract_impact.py`): every row has a real citation,
  no duplicate (region, metric, as_of_date) rows. `pytest tests/ -q` — 6
  passed.
- Known gaps, deliberately left unfilled: Gujarat relief-camp count and
  crop/hectare damage; a specific cited embankment-breach or dam-release
  causation event for Assam (the "why" section still draws only on Down To
  Earth's general natural/human-factors summary).
- Updated `site/index_prototype.html`'s impact section to show all of this
  (three dated snapshot groups instead of 4 placeholder tiles) and
  republished the same Artifact URL. Roadmap footer checkbox updated.

## 2026-08-14 — Session entry (licensing check across all data sources)

- User asked for an explicit licensing/redistribution check before continuing
  — ran 4 parallel research agents against actual terms-of-use pages (not
  assumptions) for NASA LANCE/LAADS, IMD Pune, GDELT + Wikipedia, and the 5
  news outlets cited on the site.
- **All clear**, full findings written into README.md's new "Data licensing
  & attribution" section:
  - NASA LANCE/LAADS: no reuse restrictions, attribution requested not
    required (LANCE acknowledgment text captured in README).
  - IMD Pune: safe for derived stats; site disclaimer restricts raw-file
    reproduction, not derived statistics — cite Pai et al. (2014), don't
    publicly host raw files (already the case, `data/` is gitignored).
  - GDELT (not yet ingested): fully open, but attribution is **mandatory**
    per their own terms, unlike the others where it's a request — note this
    for whenever GDELT ingestion actually happens.
  - Wikipedia: facts freely reusable, our link-back already satisfies even
    the stricter reading.
  - News outlets: bare-fact + attributed-link citation is standard, low-risk
    practice (Feist v. Rural Telephone precedent for facts not being
    copyrightable, India's Section 52(1)(a) fair dealing) across all 5
    outlets checked.
- **One real change made:** Down To Earth's terms use broad "no
  reproduction" language, so the one direct quote on the site (in the "why"
  section's human-factors column) was rewritten as a paraphrase instead of a
  verbatim quote — removes ambiguity even though the original short
  attributed quote was almost certainly fine under fair dealing.
- Added attribution notes directly onto the site: an IMD/Pai-et-al. citation
  line above the rainfall charts, and a "data attribution & licensing"
  paragraph in the methodology footer covering all sources (including
  NASA/GDELT pre-emptively, so nothing needs revisiting once those ship).
  Republished the same Artifact URL.

## 2026-08-14 — Session entry (26-year historical rainfall-extremity trend)

- Extended the yearly IMD archive back to 2000 for both regions (was
  2016-2025) — reused cached per-year files where already downloaded, only
  fetched 2000-2015 fresh. `data/bronze/rainfall_imd/{region}_yearly_2000_2025.parquet`.
- Built `silver_historical_trend.py`: monsoon-season (Jun-Sep) rainfall
  extremity per year — total monsoon rainfall, max daily rainfall, and a
  count of days exceeding 2x the 26-year monsoon-day mean (the plan's own
  proxy definition, since real flood-event/gauge history isn't open).
  2 tests added, `pytest tests/ -q` — 8 passed.
- Landed `data/gold/historical_frequency.parquet` (26 years x 2 regions).
- **Real, honestly-surprising finding:** the two regions tell different
  stories. Assam's monsoon rainfall trend over 2000-2025 is roughly flat,
  if anything slightly *down* (extreme-day-count slope -0.067/year, total
  monsoon rainfall -5.6mm/year) — the 2026 disaster wasn't riding a rising
  rainfall baseline, which strengthens the human-factors half of the "why"
  section rather than a pure climate-trend story. Gujarat's trend is
  genuinely upward (+0.27 extreme days/year, +9.0mm total monsoon rainfall/year)
  — 2022, 2024, 2025 are among its most extreme years in the 26-year window.
- Added a new "Is this getting worse?" section to the site (bar charts +
  fitted trend line per region, hover tooltips) with this exact honest
  framing — didn't force a single "climate change" narrative onto both
  regions when the data doesn't support it for Assam. Republished the same
  Artifact URL.

## 2026-08-15 — Session entry (GDELT news-attention timeline)

- Considered two approaches: GDELT's DOC 2.0 timeline API vs. the raw 15-min
  bulk GKG/event files. Checked the raw-file route for real before choosing
  — the master file list (data.gdeltproject.org/gdeltv2/masterfilelist.txt)
  is real and current (121MB, updates continuously), but covering both
  regions' event windows at 15-min granularity means ~3,500 file downloads
  and a from-scratch GKG theme/location parser. User chose the DOC 2.0 API
  instead (already proven working) rather than that much heavier lift for a
  lower-priority chart.
- Built `ingest_gdelt.py` against `api.gdeltproject.org/api/v2/doc/doc`,
  `mode=timelinevolraw` -- confirmed via direct curl testing that the
  documented "1 request/5s" limit is optimistic on a shared cloud egress IP;
  real testing needed ~20-30s gaps, and a 429 hit mid-run confirmed it.
  `_get_with_retry` backs off 30s/60s/90s... across 5 attempts, treating
  both HTTP 429 and a non-JSON 200 response (GDELT's plain-text rate-limit
  notice) as retryable.
- Ran for real: Assam 2026-07-15 to 2026-08-10 (27 days), Gujarat 2026-07-20
  to 2026-07-30 (11 days) -- both landed as bronze parquet.
- **Real finding:** Gujarat's coverage peaked 2026-07-23, one day *before*
  the rainfall peak (07-24) -- consistent with IMD red-alert coverage
  anticipating the event. Assam's coverage didn't spike once at the initial
  cloudburst (Jul 19-22) and fade -- it stayed elevated and grew into early
  August, tracking the rising death toll (68 on Jul 26 -> 85 on Aug 4) more
  than the initial weather event.
- 1 test added (`test_ingest_gdelt.py`, mocks the network call, tests JSON
  parsing only). `pytest tests/ -q` -- 9 passed.
- Added an "Did coverage track the actual event?" section to the site with
  both charts, GDELT attribution updated from "pending" to live in the
  methodology footer (their terms require attribution, unlike the other
  Tier A sources where it's a request). Republished the same Artifact URL.

## 2026-08-15 — Session entry (switched satellite source to Sentinel-1 via Google Earth Engine)

- User asked whether Google's own flood-data resources were worth using —
  researched properly rather than assuming: Google Flood Hub API is still
  waitlist-gated ("several months"), no better than what we already knew.
  But Google Earth Engine (GEE) turned out to be a real improvement over the
  stalled NASA LANCE approach: same-day self-service signup (an automated
  eligibility questionnaire, not a manual queue) vs. NASA's open-ended
  Earthdata Login wait, Python API fits our local pipeline, and it hosts
  Sentinel-1 SAR (radar) which sees through monsoon cloud cover that would
  obstruct MODIS/VIIRS optical imagery during exactly the events this
  project cares about. User approved switching to GEE as the primary
  satellite source, keeping NASA LANCE code in the repo as a documented but
  deprioritized alternative (not deleted).
- Researched the exact technical details before writing code (same
  verify-don't-guess pattern as every other source this project): Python
  API auth (`ee.Authenticate()` + `ee.Initialize(project=...)`, interactive
  once then headless), `COPERNICUS/S1_GRD` band names/units (VV/VH, already
  in dB), and the citable UN-SPIDER "Flood Mapping and Damage Assessment
  Using Sentinel-1 SAR Data in Google Earth Engine" recommended-practice
  methodology (before/after change detection on VH, ~50m speckle filter,
  ratio > 1.25 threshold) rather than inventing a detection approach.
- Built `ingest_satellite_gee.py` against that verified methodology. Added
  `flood_extent_bbox` per region to `geo_reference.py` (tighter district-
  cluster boxes than the full state bbox, so Sentinel-1's 10m pixel counts
  stay computationally sane) — flagged as approximate, same caveat as the
  existing state-level bboxes.
- Installed `earthengine-api` locally (safe — just a Python package, no
  account access) and confirmed the module imports cleanly. 3 tests added
  for the pure-Python pieces (pixel-area math, threshold constant) --
  the actual Earth Engine calls can't be tested without live credentials,
  same limitation as NASA LANCE. `pytest tests/ -q` -- 12 passed.
- **Checked licensing for the new source before finalizing** (same rigor as
  the 2026-08-14 licensing pass): Copernicus Sentinel data is free/open
  under EU Regulation 377/2014, explicitly covers derived/modified products,
  attribution format `Contains modified Copernicus Sentinel data [Year]`.
  GEE's own ToS permits publishing derived charts/figures for non-commercial
  research/educational use, which this project is. Both added to README's
  licensing table and the site's methodology footer.
- Still not run live -- needs the user's own Google Cloud project
  registered for Earth Engine (README has exact steps). This is the one
  remaining piece of Tier A blocked on the user, per the standing
  hands-on-execution preference (account registration is his to do).

## 2026-08-15 — Session entry (Sentinel-1 satellite ingestion run live, real numbers)

- User completed the Google Cloud/Earth Engine registration this session
  (project ID `subtle-harmony-113913`). Created `.env` (gitignored) with
  `GEE_PROJECT_ID`. User ran `python -m flood_watch.ingest_satellite_gee`
  himself (per the usual pattern: anything tied to his own Google/GitHub
  account is his to run) to complete the one-time interactive
  `ee.Authenticate()` browser OAuth flow — succeeded.
- First real run hit a genuine bug, not a credentials issue:
  `Image.divide: If one image has no bands, the other must also have no
  bands. Got 0 and 1.` — one of the before/after mosaics was built from an
  empty `ImageCollection`. Diagnosed for real rather than guessing a fix:
  wrote `notebooks/03_diag_gee_coverage.py` (one-off diagnostic, kept in
  the repo) and queried actual Sentinel-1 image counts per region/window.
  Root cause confirmed: Gujarat's `after_days=(-3, 3)` window around its
  2026-07-24 peak has **zero** Sentinel-1 passes — the single operational
  satellite's revisit interval is ~12 days, and Gujarat's first pass after
  peak doesn't land until peak+10 days. Assam's original narrow window was
  fine (6 images).
- Fixed `ingest_satellite_gee.py` properly instead of hardcoding a wider
  window: `_find_nonempty_window()` now dynamically widens the search
  outward (earlier for the before-window, later for the after-window) in
  7-day steps, capped at 30 days, until it finds real imagery — generalizes
  to any future region rather than a region-specific magic number. The
  output row now carries `before_image_count`, `after_image_count`,
  `before_window_widened`, `after_window_widened` so a thin/widened result
  is visible in the data itself, not silently trusted.
- Ran for real: `data/gold/flood_extent/flood_extent_gee.parquet`.
  - **Assam: 2,389 km² flooded** — clean same-week comparison, 20 before-
    images, 6 after-images, no widening needed.
  - **Gujarat: 83 km² flooded** — after-window had to widen out to
    peak+10 days (2 images), so this is a real measurement but very likely
    an *undercount* of the true peak extent, since floodwaters may have
    partly receded by the time of the first available pass. Recorded
    honestly, not smoothed over.
  - Existing 3 pure-Python GEE tests still pass (pixel-area math, threshold
    constant) — the live Earth Engine calls themselves still can't be unit
    tested without credentials, same limitation as before.
  - `pytest tests/ -q` — 12 passed (no test count change; this was a bug
    fix in code paths the existing tests don't reach, same as the NASA
    LANCE/GEE precedent of untestable live-API calls).
- Added a new "Flood extent from radar" section to the site with the real
  km² numbers per region and an explicit amber caveat box (new `.caveat`
  CSS pattern, reusing the existing amber token) explaining the Gujarat
  undercount risk rather than hiding it. Updated the masthead status strip,
  footer roadmap, and licensing paragraph from "pending" to "done" for
  satellite. Republished the same Artifact URL.

## 2026-08-15 — Session entry (narrative/preparedness section, real citations)

- Last unbuilt content section: "how to prepare next time." Held to the same
  bar as the rest of the site — real, named sources only, gaps stated rather
  than filled with generic listicle advice. Delegated the research pass to
  an agent (6 categories: NDMA guidelines, early-warning systems, Assam-
  specific, Gujarat-specific, what-worked/failed in the actual 2026 event,
  household guidance), then personally re-fetched and verified the
  strongest primary sources myself before writing site copy — same
  verify-before-cite discipline as every other section.
- Verified directly: NDMA's own Do's/Don'ts page (exact quotes pulled, not
  paraphrased), CWC's flood-forecasting-network page (325 stations, 4 alert
  tiers, >90% accuracy claim), an India Today NE opinion piece by engineer
  Nayan Sharma on the actual embankment/drainage failures behind the Jorhat
  breaches, and NESAC's FLEWS page (corrected the research agent's guessed
  "85% accuracy" to the real figure, 75%, straight from the primary page).
- Added three subsections to the site: (1) **Real warning systems already
  exist** — CWC network, NDMA's SACHET app, Assam-specific FLEWS (24-36hr
  lead time, NESAC); (2) **What the 2026 response revealed** — Assam
  (embankments lacked drainage sluices per Nayan Sharma; Guwahati's ₹6,000cr
  drainage plan didn't prevent flooding elsewhere, per Mahabahu.com) and
  Gujarat (rescue shifted to air-only in Navsari/Valsad/Tapi per ThePrint;
  urban drainage/encroachment blamed for severity per Counterview.net),
  with an explicit gap-note that no official post-event institutional
  review exists yet for either state as of this writing; (3) **What NDMA
  actually recommends** — verbatim quoted Do's/Don'ts by phase (before /
  likely / evacuation), not paraphrased.
- Explicitly left out (per the research agent's honest gap-flagging):
  a GSDMA-branded household checklist (doesn't appear to exist, unlike
  NDMA's), and a Tribune India "lessons learnt" piece the agent couldn't
  confirm actually covered 2026 Assam/Gujarat.
- No code changes this entry (content-only) — `pytest tests/ -q` unaffected,
  still 12 passed. Added new CSS component classes (`.system-grid`,
  `.lesson-cols`, `.prep-grid`, `.gap-note`) reusing existing design tokens,
  no new colors introduced. Republished the same Artifact URL.

## 2026-08-15 — Session entry (durable site/index.html, real browser verification)

- Built `export_site_data.py`: reads the gold-layer Parquet tables (rainfall
  anomaly timelines, historical_frequency, flood_extent_gee, impact_summary,
  plus the GDELT bronze files since GDELT has no gold table) and writes
  `site/data/{rainfall,trend,news,flood_extent,impact}.json`. Reused
  `silver_historical_trend`'s existing polyfit logic rather than
  reimplementing it — added a small `linear_trend()` helper there that
  returns (slope, intercept) together, with `linear_trend_slope()` now a
  thin wrapper over it so the existing test still passes unchanged.
  Cross-checked the exported trend numbers against the prototype's
  hand-verified hardcoded values (slope/intercept/years) — exact match.
- Copied `site/index_prototype.html` to `site/index.html` and rewired the
  three inline data constants (`DATA`, `TREND`, `NEWS`) plus the two
  flood-extent headline tiles to `fetch()` the JSON exports at load time
  instead of embedding numbers in the page. Chart-drawing functions
  (`buildChart`, `buildTrendChart`, `buildNewsChart`) are unchanged — only
  where their input comes from changed. Impact tiles, "why," and
  preparedness sections stay as authored editorial HTML (same content as
  the prototype) rather than being re-templated from JSON — a deliberate
  scope decision, not an oversight: those are narrative copy referencing
  already-cited facts, not chart series.
- **Verified this actually works, not just that it typechecks:** installed
  Playwright + a headless Chromium, served `site/` over a local HTTP
  server, and drove a real browser against it. Confirmed all three charts
  populate from the fetched JSON, the flood-extent tiles show the correct
  live numbers (2,389 km² / 83 km², matching the pipeline output exactly),
  zero console errors, and took screenshots to visually check the render.
- **Caught and fixed a real encoding bug this way, not something a syntax
  check would show:** `index.html` (copied from the Artifact-fragment
  convention used for the prototype) had no `<!DOCTYPE html>`, `<html>`,
  `<head>`, or `<meta charset="utf-8">` — fine when the Artifact tool wraps
  it in its own skeleton, but a real problem for a file meant to stand
  alone. Served raw, browsers guessed the wrong encoding and every non-ASCII
  character (²  in "km²", em/en dashes) rendered as mojibake ("kmÂ²").
  Wrapped the file properly (doctype/html/head+charset/body) and reverified
  in the browser — clean UTF-8 rendering confirmed.
- **Caught and fixed a real .gitignore bug** while checking the file would
  actually get committed: the existing `data/` rule (no leading slash) is
  unanchored in git's pattern syntax and was silently also matching
  `site/data/` — meaning the JSON exports this whole feature depends on
  would never have made it into a commit. Verified with `git check-ignore`
  in a throwaway test repo before and after; fixed to `/data/` (anchored to
  repo root) so only the real bronze/silver/gold data stays ignored.
- `pytest tests/ -q` — still 12 passed (the refactor changed shared logic
  but not behavior, confirmed by the existing `linear_trend_slope` test
  still passing unchanged).
- Not done yet: GitHub repo creation + push, so `site/index.html` isn't
  live on GitHub Pages yet — that's the very next step and it's the user's
  to run (account-tied action, same principle as every other GitHub/Google
  step this session).

## 2026-08-15 — Session entry (GitHub push + GitHub Pages deploy)

- User asked to push to GitHub. `gh auth status` confirmed an existing
  authenticated session (account `vasimc`, `repo` scope) — used that rather
  than asking for fresh credentials. Confirmed repo name/visibility with
  the user first (public, `flood_watch_2026`) since repo creation + push is
  a visible, hard-to-fully-reverse action.
- `git init`, renamed default branch `master` → `main` (GitHub's current
  default), staged files explicitly by path (not `-A`), reviewed the staged
  list against `git status --ignored` before committing — confirmed `.env`,
  `.venv/`, `data/`, and `__pycache__/` all correctly excluded, no secrets.
  33 files, initial commit, pushed to `https://github.com/vasimc/flood_watch_2026`
  (public).
- Added `.github/workflows/pages.yml`: deploys `site/` directly as the
  Pages root on every push touching `site/**`, via the modern
  `actions/upload-pages-artifact` + `actions/deploy-pages` flow (not the
  legacy branch/`docs`-folder method) — gives a clean root URL
  (`https://vasimc.github.io/flood_watch_2026/`) without moving `site/` to
  `docs/` or nesting the live URL under `/site/`. Enabled Pages via
  `gh api repos/vasimc/flood_watch_2026/pages` with `build_type=workflow`
  before the first push so the workflow had something to deploy to.
- Watched the deploy run to completion (`gh run watch`) rather than
  assuming success from the push alone — confirmed all steps green.
- **Verified live, not just "deployed":** curled `index.html` and
  `data/rainfall.json` on the real `github.io` URL (both 200), then reran
  the same Playwright browser check from the local-server verification
  earlier against the live URL — flood-extent tiles show the correct
  numbers, all three chart types populate, zero console errors, correct
  UTF-8 rendering (²/em-dashes). Same rigor as the local check, not skipped
  just because it's "just a deploy."

## 2026-08-15 — Session entry (architecture diagram, "How this was built")

- User asked for an architecture diagram on the site. Checked the real
  pipeline structure against the code before drawing anything (per the
  usual verify-don't-guess pattern) rather than reusing README's existing
  ASCII diagram at face value — found it was slightly idealized. The real
  routes diverge: rainfall lands in bronze then gets transformed twice into
  two gold tables; Sentinel-1 (GEE) and the manually-extracted impact
  figures write their gold tables directly, with no bronze layer in
  between (there's no meaningful "raw" form of a GEE computation result or
  a hand-read news figure); GDELT never gets a gold table at all — it's
  read straight from its bronze pull in `export_site_data.py`. This
  divergence is the one thing actually worth a diagram; a generic
  bronze→silver→gold box stack would have been inaccurate.
  - `linear_trend_slope`'s intercept, added in the site-port session, gets
    no separate `silver` layer either — both rainfall gold tables are
    landed directly from ad-hoc transform-function calls, another
    real-not-idealized detail (not drawn separately in the diagram, judged
    not worth the extra complexity for a page-level figure).
- Added a new "How this was built" section (`site/index.html` only —
  `index_prototype.html` stays frozen as the historical draft) with a
  hand-authored inline SVG diagram following the site's existing chart
  conventions (reuses `--accent`/`--amber` tokens for the
  automated-vs-manual distinction, matching the masthead's status-strip
  dots; reuses the existing arrow-marker/label pattern). Both light and
  dark theme rendering verified with the same Playwright screenshot
  workflow used for the rest of the site this session — caught and fixed
  two real label-collision bugs before calling it done (an "anomaly calc"
  label overlapping the gold box header, and two edge labels overlapping
  box titles in narrow column gaps) rather than shipping on a first-pass
  screenshot.
- No Python changes this entry; `pytest tests/ -q` unaffected, still 12
  passed. Committed and pushed — GitHub Actions redeployed automatically.

## 2026-08-15 — Session entry (real bronze/silver/gold for all 4 sources)

- User pushed back on the architecture diagram: it accurately showed
  GDELT/satellite/impact skipping bronze and/or gold, but per medallion
  architecture convention wanted every source to genuinely flow through
  all three layers. Asked first whether that meant a full pipeline
  refactor or just a diagram redraw, since forcing 3 literal layers for
  sources with nothing to transform (GDELT is already 1 row/day,
  satellite computes server-side in GEE, impact is hand-cited facts)
  means inventing real intermediate steps, not just relabeling — user
  chose the full refactor (portfolio/interview-prep project, textbook-
  correct architecture matters more here than minimal-code purism).
- **Closed a real pre-existing gap along the way**: discovered
  `silver_rainfall.py`/`silver_historical_trend.py` were always pure
  transform functions with no committed script that actually called them
  and wrote gold — the two rainfall gold tables on disk had been produced
  by interactive one-off code in an earlier session and were not
  reproducible from a clean checkout. New `gold_rainfall.py` fixes this:
  persists a real silver daily-mean layer, then gold. **Caught a real bug
  while rebuilding it**: initially read the 26-year (2000-2025) archive
  for both the trend AND the anomaly-vs-normal calc, which silently
  shifted the published "+226.6%/+540.9%" figures (recomputed as
  +267%/+579.5% against the wrong baseline) — the anomaly calc must stay
  pinned to the 2016-2025 normal that's been quoted throughout the site
  since the first session, the 26-year archive is only for the separate
  trend table. Fixed and reverified against the exact known-good numbers.
- Added `silver_gdelt.py` + `gold_gdelt.py`: real 3-day rolling-average
  smoothing (silver) and a genuinely new `gold.news_attention` table
  (silver) formalizing "did coverage track the event" as an actual
  peak-day/lag-vs-rainfall-peak number instead of only prose on the site.
  Reproduced the already-documented finding exactly (Gujarat: peaked
  Jul 23, -1 day lag / anticipatory) plus a new one for Assam (peaked
  Aug 3, 87 articles, +14 day lag — coverage tracked the death toll, not
  the initial cloudburst).
- Restructured `ingest_satellite_gee.py` into three real persisted steps:
  bronze (`satellite_gee/passes.parquet`, one row per actual Sentinel-1
  pass used — 32 rows across both regions), silver (pixel-classification
  result before km2 conversion), gold (same schema as before). Re-ran
  live against real Earth Engine credentials (cached from the earlier
  session, no new browser auth needed) and got exact matches to the
  previously-verified numbers (Assam 2,389 km², Gujarat 83 km²). Also
  fixed a `datetime.utcfromtimestamp` deprecation warning surfaced along
  the way.
- Restructured `extract_impact.py` into bronze (raw quote text alongside
  the analyst's numeric read — documented explicitly that there's no
  fake auto-parser turning "over 3 lakh" into 300000, a human did that in
  one step, same as any transcription), silver (`is_estimate` flag, a
  real function checking the actual wording for "over"/"more than"/"+"),
  gold (dedup validation, same as before). Split the pure transform
  functions (`compute_silver`/`compute_gold`) from the I/O-performing
  ones (`build_silver`/`build_gold`) after almost letting a new test call
  the I/O version and silently clobber real pipeline output with toy
  fixture data — caught before it happened, not after.
- Added `geo_reference.get_rainfall_peak_date()` — the peak dates were
  previously hardcoded separately in `ingest_satellite_gee.py`'s
  `__main__` block; now both that and the new GDELT lag calc read from
  one place.
- 8 new tests (GDELT silver/gold pure functions, impact estimate-flag
  parsing + silver/gold pure transforms) — `pytest tests/ -q` now 23
  passed (was 12 at the start of this session, then 15, now 23).
- Updated `export_site_data.py`: `impact.json` now carries `is_estimate`
  per row; new `news_attention.json` export.
- Site changes: impact section's citation note now names the real
  bronze→silver→gold path (the existing "+" suffix on estimate figures
  already visually matched the new `is_estimate` flag — nice
  confirmation the editorial convention and the formal flag agree). The
  GDELT/attention section's peak-day and lag numbers are now genuinely
  fetched from `news_attention.json` at runtime (added `id` spans +
  `applyNewsAttention()`) instead of being hand-typed prose, matching the
  section's own new claim that they're a real gold-layer table.
- **Redrew the architecture diagram from scratch**: four consistent
  lanes (source → bronze → silver → gold), all four converging into
  `export_site_data.py` → site. Much simpler than the old diagram's
  special-cased bypass paths, because the underlying pipeline is now
  actually consistent — the diagram got easier to draw *because* the
  architecture is more correct, not despite it. Removed the now-dead
  `.flow.bypass`/`.flow-label` CSS rules that had no remaining users.
  Verified in a real headless browser, light and dark mode, same as every
  other diagram/chart change this project has made.
- Live GEE re-run + Playwright browser checks both required real waits
  (satellite ingestion ~2min, browser installs) — ran the satellite
  re-ingestion in the background and worked on the impact-layer restructure
  while it completed, rather than blocking on it.

## 2026-08-15 — Session entry (removed a false DuckDB claim)

- User asked, reasonably, whether DuckDB was actually used given the site's
  "How this was built" section listed it. Checked rather than assumed:
  `warehouse.py` had a `get_connection()` DuckDB helper and a `DB_PATH`,
  but grepped the whole codebase and found **nothing ever called it** --
  no `.duckdb` file exists on disk, and all 36 real read/write calls across
  the pipeline go through plain `pandas.read_parquet`/`to_parquet`. DuckDB
  was scaffolded early on and never actually wired in; the site/README
  mentions were describing planned infrastructure, not what's running.
- Fixed by removing the claim (user's choice over the alternative of
  actually wiring DuckDB in for real): dropped `get_connection()`/`DB_PATH`/
  the `duckdb` import from `warehouse.py` (genuinely dead code, not just
  unmentioned), removed `duckdb` from `requirements.txt`, and updated both
  the site's architecture section-note and README's "Warehouse" paragraph
  to describe what's actually there -- plain Parquet, pandas I/O, no
  database layer. `pytest tests/ -q` still 23 passed (nothing imported the
  removed symbols).

## 2026-08-15 — Session entry (district-level flood-extent map, real district polygons)

- User pointed at the site's own "District-level flood-extent map" roadmap
  item, still pending. Before building anything, researched real district
  boundary sources rather than assuming one existed or reaching for a
  hand-drawn approximation -- delegated to a research agent covering
  geoBoundaries, datameet/maps, GADM, Natural Earth, HDX, Bhuvan, and two
  Earth Engine-native options (geoBoundaries' own EE asset, FAO GAUL).
  **Verified the winning candidate myself** rather than trusting the
  research report at face value: queried `WM/geoLab/geoBoundaries/600/ADM2`
  live against my own GEE session, confirmed all 7 target districts present
  by exact name (including Charaideo, Assam's newest district, created
  2015 -- a good staleness check), and cross-checked Charaideo's computed
  area (1,051 km²) against its known real area as a sanity check.
- Asked the user directly whether "map" should mean a real geographic
  choropleth (new projection/rendering code) or a simpler bar-chart
  re-skin of the existing chart style -- chose real geography, since a
  genuine small map is a stronger portfolio piece than another bar chart
  wearing a "map" label.
- **Licensing, checked properly, not assumed:** geoBoundaries markets
  itself as "CC BY 4.0" but the actual API metadata for this specific
  India ADM2 boundary states ODbL 1.0 -- fetched and read the real ODbL
  license text before deciding how to comply, rather than trusting the
  marketing page. Distinction that mattered: derived *statistics*
  (flooded_area_km2 per district) only need simple attribution (§4.3);
  republishing the boundary *geometries themselves* (which the map does)
  counts as extracting a substantial part of the source database and
  triggers §4.2/4.4 -- so the geometry file and the site both carry their
  own ODbL notice, stricter than every other source's simple-attribution
  requirement in this project.
- Added `ingest_district_boundaries.py`: fetches the 7 districts' real
  polygons directly from the GEE catalog (no ~48MB national file download
  needed), simplifies server-side, writes `data/reference/district_boundaries.geojson`.
  Treated explicitly as reference/dimension data, not a medallion fact
  table -- same category as `geo_reference.py`'s existing hand-typed
  bboxes, just sourced from a real dataset instead of typed in.
  **Hit and fixed a real geometry bug**: Surat's simplified geometry came
  back as a `GeometryCollection` padded with degenerate 2-point
  `LineString` slivers alongside the real polygons (a `.simplify()`
  artifact on complex coastal district shapes) -- wrote `_clean_geometry()`
  to filter to real polygons and collapse to Polygon/MultiPolygon, with 4
  tests covering the plain-polygon, artifact-stripping, multi-polygon-merge,
  and all-artifacts-no-polygon-survives cases.
- Refactored `resolve_windows()` in `ingest_satellite_gee.py` to take
  geometry as an explicit parameter instead of deriving it internally from
  a region name -- a small, safe change that let the existing
  bronze/silver/gold primitives (`build_bronze_passes`,
  `build_silver_classification`, `build_gold_summary`) get reused
  unchanged for district-level ingestion, rather than duplicating the
  actual GEE computation logic. New `ingest_flood_extent_district.py`
  does the per-district orchestration on top of those reused primitives.
  Traced through a labeling bug by hand before running anything live: a
  naive pop-based rename would have mislabeled the `district` column with
  the region name instead of the actual district, once
  `build_gold_summary` propagated the relabeled silver row's `region` key
  forward. Fixed with explicit values instead of pop-tricks.
- Ran live: 49 bronze pass rows, 7 silver/gold rows (one per district).
  **Real, honest finding, not smoothed over**: district-level sums don't
  match the region-level bbox numbers from the earlier session --
  Assam's 4 districts sum to 723 km² vs. the regional 2,389 km² (the
  region bbox captured extra non-district land); Gujarat's 3 districts
  sum to 144 km² vs. the regional 83 km² (each district resolved its own
  before/after window independently and landed on different satellite
  passes than the shared regional window). Both numbers are real; they're
  measuring different things. Stated explicitly on the site as a caveat,
  not reconciled or hidden.
- Built the actual map: hand-authored an equirectangular-ish projection
  (cosine-latitude corrected for the small area involved) computed live in
  JS from the real polygon coordinates -- not decorative hand-drawn path
  data, programmatically generated from real geometry, consistent with
  the diagramming guidance this project follows elsewhere. Choropleth
  color scale reads `--surface-2`/`--alert` from the live computed
  CSS custom properties (not hardcoded hex), so it adapts correctly to
  light/dark theme automatically. Verified real hover interaction with
  Playwright's `.hover()` after an initial manual-mouse-position test gave
  a false negative (bounding-box center landed outside an irregular
  concave district shape, not an actual bug).
- 4 new tests (`_clean_geometry`), `pytest tests/ -q` now 27 passed (was
  23). Updated the architecture diagram's satellite row to show the
  second gold table, README's dataset/architecture/licensing tables and
  status checklist, and the site's own roadmap footer + licensing
  paragraph. Verified in a real browser, light and dark, before shipping.

## 2026-08-15 — Session entry (district labels + full state map context)

- User asked for district names on the map (quick win, chosen over the
  other options offered: % of district flooded, scale bar, river
  overlays) — added `geometryCentroid()` (shoelace-formula area-weighted
  centroid, MultiPolygon-aware so Surat's label lands in its main
  landmass not a stray fragment) and rendered each district's name with a
  halo (`paint-order: stroke fill`) so it stays legible across the full
  choropleth color range in both themes.
- Then asked to show the full state, not just the tracked district
  cluster. Added `fetch_state_boundaries()` to `ingest_district_boundaries.py`
  (geoBoundaries ADM1, same GEE catalog family as the district layer).
  **Hit a real upstream data-quality bug**: Gujarat's ADM1 `shapeName` is
  literally `"Gujar?t"` in this dataset (a raw '?' byte where a diacritic
  should be, confirmed by checking the character's actual codepoint --
  0x3f, not a terminal-rendering artifact). Matched by substring instead
  of exact name to sidestep it, which is also more robust generally.
  Used a coarser simplify tolerance (1000m vs. 100m) for state outlines
  specifically, since they're background context, not analysis precision
  -- cut Gujarat's point count from 9,142 to 1,794 with no visible loss
  at map scale.
- State outline renders as a stroke-only shape (no fill) so it can't be
  confused with a real district's near-zero choropleth color, and the
  map's projection now fits the full state extent instead of just the
  district cluster, so the reader sees where the tracked districts
  actually sit (upper Assam near the Nagaland border; coastal South
  Gujarat).
- `pytest tests/ -q` unaffected (JS-only change plus one Python function
  covered by the existing `_clean_geometry` tests), still 27 passed.
  Verified in a real browser, both themes, hover interaction still works
  correctly with the new background layer present.

## 2026-08-15 — Session entry (real MapLibre basemap toggle)

- User asked whether the Google Maps Embed API could improve the district
  map. Checked rather than assumed: the Embed API is place/directions/
  street-view only, no support for custom-colored polygon overlays at all
  -- that needs the full Maps JavaScript API, which requires a billing-
  enabled GCP project even on the free tier. Explained the tradeoff
  (self-contained SVG vs. API-key-and-billing basemap) rather than either
  building it or dismissing the question.
- User then asked to research free web-map alternatives properly.
  Delegated to a research agent with instructions to verify *current*
  terms, not stale training-data assumptions, since tile-provider free
  tiers change (the Stamen-\>Stadia migration was the flagged example).
  Real findings that would have been wrong from memory: **CARTO's free
  basemaps are now gated to enterprise/nonprofit-grant only** (used to be
  open); OSM's own tile server explicitly discourages being relied on for
  a production site (no SLA, "access may be withdrawn at any point").
  Two options held up: OpenFreeMap (free, no key, single-maintainer
  infra) and **Protomaps PMTiles, self-hosted** (a static file served by
  GitHub Pages itself, zero external tile-server dependency at runtime --
  the best fit for this project's self-containment values). Flagged a
  real, currently-open bug: Firefox mishandles PMTiles range-request
  caching specifically on GitHub Pages (protomaps/PMTiles #582/#272,
  confirmed reproducing by the maintainer as of mid-2025).
- User chose the recommendation: MapLibre GL JS + self-hosted Protomaps
  PMTiles, added as an optional "Real map" toggle alongside the existing
  SVG choropleth (not a replacement) per the research's own honest
  pushback about added complexity for two small district clusters.
- **Built it for real, verifying each piece rather than assuming it'd
  work:**
  - Downloaded the `go-pmtiles` CLI (prebuilt Windows binary from the
    real GitHub release, since neither the Python nor npm `pmtiles`
    packages include the `extract` command). Found today's live daily
    build at `build.protomaps.com/20260815.pmtiles` by testing dates
    directly against `pmtiles show`, not guessing a URL pattern.
  - Dry-ran extraction at a few zoom levels before committing to a real
    download to pick a size/detail tradeoff (maxzoom=13 -> 14MB Assam +
    9.7MB Gujarat, vs. 25MB+9.7MB at maxzoom=14) -- reasonable for a git
    repo, real roads and place names retained.
  - Self-hosted MapLibre GL JS + the PMTiles JS decoder in `site/vendor/`
    (BSD-3, verified license headers in the actual downloaded files, not
    just the package page) -- no CDN dependency, consistent with how the
    rest of this project treats external dependencies.
  - Built a **custom minimal map style** from the real Protomaps vector
    schema (checked actual layer names/fields via `pmtiles show
    --metadata` first) using the site's own CSS design tokens read live
    via `getComputedStyle`, rather than importing Protomaps' default
    busy OSM-styled theme -- keeps the real map visually consistent with
    the rest of the site (muted palette, same typography) instead of a
    jarring different-app-pasted-in look, and it means the map
    automatically matches light/dark theme the same way every other
    chart on the site does.
  - District polygons + labels render as a GeoJSON overlay on top,
    reusing the exact same `interpolateColor`/`geometryCentroid` logic
    already written for the SVG map -- same colors, same district names,
    genuinely the same data, different basemap underneath.
- **Two real debugging dead ends, resolved by checking rather than
  guessing:**
  1. First test threw `"Server returned no content-length header..."` --
     turned out to be Python's built-in `http.server`, which silently
     ignores Range headers and returns the whole file with `200 OK`
     instead of `206 Partial Content` (confirmed via a raw `curl -H
     "Range: ..."` request, not assumed). Not a bug in the map code --
     switched local testing to `http-server` (proper Range/206 support,
     confirmed the same way) before re-testing.
  2. Basemap looked completely blank in a full-page screenshot even after
     confirming (via `map.querySourceFeatures`) that tiles were loading
     and 58 place features + 8 road features were present. Turned out to
     be a false alarm from screenshot compression at small scale, not a
     real rendering bug -- a cropped, high-DPI screenshot of just the map
     canvas showed the Brahmaputra river, real town names, roads, and
     state borders rendering correctly all along.
  3. Fixed a genuine bug caught along the way: `pmtiles://` source URLs
     for the two regions must be relative paths (`assets/{region}.pmtiles`),
     not absolute -- verified this resolves correctly under both a local
     dev server and GitHub Pages' actual subpath structure before
     committing to it.
- Verified locally in both Chromium and Firefox (including a pan/zoom
  interaction to trigger fresh range requests, not just the initial
  load) -- zero errors either way. **Then verified against the actual
  live GitHub Pages URL in Firefox specifically** (the one environment
  the known upstream bug was reported in) -- pushed, watched the deploy,
  and drove Firefox against `vasimc.github.io` directly: 4 separate range
  requests for Assam (zoom interactions), then a completely fresh set of
  4 for Gujarat after a region switch, every one a correct `206 Partial
  Content` with the right `Content-Range` header, zero console errors.
  The flagged bug did not reproduce here -- didn't just assume it was
  fine because local testing passed; confirmed it on the actual
  deployment target before calling this shipped.
- `pytest tests/ -q` unaffected (this entry is site-only), still 27 passed.

## Gotchas hit and fixed

- The rainfall download pages (`Rainfall_25_NetCDF.html`, `Rain_Download.html`)
  look like they need a browser to use (year dropdown / date picker + submit
  button), but both are plain HTML `<form method="post">` elements. Fetching
  the raw HTML and grepping for `<form` revealed the real POST targets
  (`RF25.php`, `rain.php`) and field names — no browser automation needed.
- The realtime daily endpoint's date format is `ddmmyyyy` (8 digits, e.g.
  `20072026` for 2026-07-20) — other formats (with dashes/slashes, 2-digit
  year) return HTTP 200 but a 0-byte body, which looks like success unless
  you check the response size.
- Cross-checked the binary grid's row/column orientation (135 lon x 129 lat,
  row-major latitude-then-longitude) against the yearly NetCDF's own
  explicit LATITUDE/LONGITUDE dims for the same Assam bbox and got the exact
  same valid-cell count (290 of 416) from two independent parsing paths —
  good evidence the manual binary layout is right, not just plausible.

## How to run things

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # fill in NASA_EARTHDATA_TOKEN
python notebooks/02_explore_lance_flood.py   # bootstraps src/ onto sys.path itself
python -m pytest tests/ -q                    # pytest.ini sets pythonpath = src
```

## Next steps

Everything in the original plan is done and live:
https://vasimc.github.io/flood_watch_2026/ (repo:
https://github.com/vasimc/flood_watch_2026, public).

What's left is optional follow-on work, not required to call this
complete:

1. Re-run `export_site_data.py` + push whenever upstream data changes
   (e.g. a later, less-recent-event snapshot of the impact figures) — the
   GitHub Actions workflow (`.github/workflows/pages.yml`) redeploys
   automatically on any push that touches `site/**`.
2. If continuing to track the event, extend rainfall/GDELT windows and
   re-ingest satellite (region and per-district) for a later date range.
