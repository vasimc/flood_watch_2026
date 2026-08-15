from flood_watch.ingest_satellite_gee import FLOOD_RATIO_THRESHOLD, pixels_to_km2


def test_pixels_to_km2_at_sentinel1_native_resolution():
    # 100 pixels at 10m x 10m = 10,000 m2 = 0.01 km2
    assert pixels_to_km2(100, scale_m=10) == 0.01


def test_pixels_to_km2_zero_pixels_is_zero():
    assert pixels_to_km2(0) == 0.0


def test_flood_ratio_threshold_matches_documented_recipe():
    # UN-SPIDER recommended practice's documented threshold -- if this ever
    # changes it should be a deliberate edit, not a silent drift
    assert FLOOD_RATIO_THRESHOLD == 1.25
