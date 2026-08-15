"""Static geographic reference data for the Assam & Gujarat flood regions.

Bounding boxes are coarse (state level) for the Phase 1-2 slice. Precise
per-district polygon joins (via a GeoJSON boundary file) are a later
enhancement once the pipeline shape is proven -- see PROGRESS.md Next steps.

Event details and district lists below were corrected 2026-08-14 against real
sources (Wikipedia "2026 Assam floods", a Nativeplanet report on the South
Gujarat floods) after the original Phase-1 guesses turned out wrong -- e.g.
Assam's actual worst-hit districts (Sivasagar, Charaideo, Jorhat, Golaghat,
upper Assam / Brahmaputra-Nagaland border) are nothing like the first guess
(Barpeta, Cachar, Nagaon, lower/central Assam). Re-verify against the latest
sitreps before trusting these for anything beyond a rough date-window/bbox.
"""

# (min_lon, min_lat, max_lon, max_lat)
REGIONS = {
    "assam": {
        "bbox": (89.7, 24.1, 96.0, 28.2),
        "basin": "Brahmaputra",
        "basin_detail": "Brahmaputra + south-bank tributaries Dikhow, Disang, Janji, Dhansiri",
        # source: https://en.wikipedia.org/wiki/2026_Assam_floods, checked 2026-08-14
        "most_affected_districts_2026": [
            "Sivasagar",
            "Charaideo",
            "Jorhat",
            "Golaghat",
        ],
        # cloudburst trigger 2026-07-19 (Mon district, Nagaland), peak
        # devastation 2026-07-21/22, still ongoing/worsening as of early Aug
        "event_window_2026": ("2026-07-15", "2026-08-10"),
        # rainfall pipeline's own computed peak day (+226.6% departure) --
        # used as the reference date for satellite before/after windows and
        # for the GDELT coverage-lag calc, so both stay anchored to the same
        # independently-derived date instead of each hardcoding it separately
        "rainfall_peak_date_2026": "2026-07-20",
        # approximate cluster around Sivasagar/Charaideo/Jorhat/Golaghat --
        # NOT a precise administrative boundary, just a tighter box than the
        # full state so satellite pixel counts stay computationally sane
        "flood_extent_bbox": (93.5, 26.3, 95.5, 27.3),
    },
    "gujarat": {
        "bbox": (68.1, 20.1, 74.5, 24.7),
        "basin": "Damanganga/Purna",
        "basin_detail": "Damanganga and Purna rivers, South Gujarat",
        # source: nativeplanet.com South Gujarat floods report, checked 2026-08-14
        "most_affected_districts_2026": [
            "Valsad",
            "Navsari",
            "Surat",
        ],
        # Valsad recorded >100cm rain in 24h around 2026-07-24
        "event_window_2026": ("2026-07-20", "2026-07-30"),
        # rainfall pipeline's own computed peak day (+540.9% departure) --
        # see the Assam field above for why this lives here instead of being
        # hardcoded separately in each downstream script
        "rainfall_peak_date_2026": "2026-07-24",
        # approximate cluster around Valsad/Navsari/Surat -- same caveat as Assam's
        "flood_extent_bbox": (72.6, 20.3, 73.3, 21.3),
    },
}


def get_bbox(region: str) -> tuple:
    return REGIONS[region]["bbox"]


def get_event_window(region: str) -> tuple:
    """(start_date_iso, end_date_iso) covering the 2026 event, padded a few
    days on each side of the confirmed peak dates -- see module docstring."""
    return REGIONS[region]["event_window_2026"]


def get_flood_extent_bbox(region: str) -> tuple:
    """Tighter bbox around the worst-hit district cluster, for satellite
    flood-extent analysis where full-state pixel counts would be wasteful."""
    return REGIONS[region]["flood_extent_bbox"]


def get_rainfall_peak_date(region: str) -> str:
    """ISO date of the rainfall pipeline's own computed peak day -- the
    single source of truth other pipeline stages (satellite before/after
    windows, GDELT coverage-lag) anchor to, instead of each re-deriving or
    re-hardcoding it."""
    return REGIONS[region]["rainfall_peak_date_2026"]


def get_districts(region: str) -> list[str]:
    return REGIONS[region]["most_affected_districts_2026"]


def district_region_map() -> dict[str, str]:
    """{district_name: region} for every district across all regions --
    used to label district-level results with their parent region."""
    return {district: region for region in REGIONS for district in get_districts(region)}
