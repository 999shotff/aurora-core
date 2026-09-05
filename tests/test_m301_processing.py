"""M30.1 Earth Observation Processing Tests.

35 tests covering:
- Raster engine (create, clip, resample, mask, stats)
- Index engine (NDVI, NDWI, NDBI, EVI per-pixel)
- Edge cases (zero denominator, NaN, infinity, nodata, missing bands)
- Time series engine (add, filter, stats, missing dates)
- Pixel change detection (area, magnitude, confidence)
- Change detection (before/after, threshold)
- Provenance chain
- No fabricated data
- Deterministic processing
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from aurora.geo.analysis.pixel_change import detect_pixel_change
from aurora.geo.domain import (
    BoundingBox,
    GeoIntegrityState,
)
from aurora.geo.features.index_engine import (
    _safe_divide,
    compute_evi,
    compute_index,
    compute_ndbi,
    compute_ndvi,
    compute_ndwi,
)
from aurora.geo.features.time_series import GeoTimeSeriesEngine
from aurora.geo.raster.engine import (
    RasterScene,
    clip_raster_to_bbox,
    compute_band_stats,
    create_raster_from_arrays,
    mask_nodata,
    resample_raster,
)

NOW = datetime(2025, 6, 15, tzinfo=timezone.utc)


def _make_scene(
    h: int = 100, w: int = 100,
    nodata: float = np.nan,
    include_scl: bool = False,
) -> RasterScene:
    np.random.seed(42)
    bands = {
        "B02": np.random.uniform(0.03, 0.08, (h, w)),
        "B03": np.random.uniform(0.05, 0.12, (h, w)),
        "B04": np.random.uniform(0.03, 0.08, (h, w)),
        "B08": np.random.uniform(0.15, 0.35, (h, w)),
        "B11": np.random.uniform(0.10, 0.20, (h, w)),
    }
    if include_scl:
        scl = np.zeros((h, w), dtype=float)
        scl[50:60, 50:60] = 8
        bands["SCL"] = scl

    return create_raster_from_arrays(
        bands,
        bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2),
        pixel_size_m=10.0,
        nodata=nodata,
    )


# ── Raster Engine ──


class TestRasterEngine:
    def test_create_raster(self):
        scene = _make_scene()
        assert scene.width == 100
        assert scene.height == 100
        assert "B04" in scene.band_names

    def test_create_raster_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape mismatch"):
            create_raster_from_arrays({"A": np.zeros((10, 10)), "B": np.zeros((10, 20))})

    def test_create_raster_empty(self):
        with pytest.raises(ValueError, match="empty"):
            create_raster_from_arrays({})

    def test_band_stats(self):
        scene = _make_scene()
        stats = compute_band_stats(scene, "B04")
        assert "mean" in stats
        assert stats["valid_count"] == 10000.0

    def test_band_stats_missing(self):
        scene = _make_scene()
        stats = compute_band_stats(scene, "B99")
        assert stats.get("error") == 1.0

    def test_clip_to_bbox(self):
        scene = _make_scene()
        clip_bbox = BoundingBox(south=33.72, west=-118.35, north=33.78, east=-118.25)
        clipped = clip_raster_to_bbox(scene, clip_bbox)
        assert clipped.width < scene.width
        assert clipped.height < scene.height
        assert "clip" in clipped.provenance.processing_method

    def test_clip_no_intersect(self):
        scene = _make_scene()
        with pytest.raises(ValueError, match="does not intersect"):
            clip_raster_to_bbox(scene, BoundingBox(south=40, west=-74, north=41, east=-73))

    def test_resample(self):
        scene = _make_scene(100, 100)
        resampled = resample_raster(scene, 50, 50)
        assert resampled.width == 50
        assert resampled.height == 50
        assert "resample" in resampled.provenance.processing_method

    def test_mask_nodata(self):
        scene = _make_scene(include_scl=True)
        masked = mask_nodata(scene, mask_band="SCL", invalid_values=(8,))
        assert masked is not scene
        assert "cloud_mask" in masked.provenance.processing_method

    def test_mask_no_scl(self):
        scene = _make_scene()
        result = mask_nodata(scene)
        assert result is scene


# ── Index Engine ──


class TestIndexEngine:
    def test_ndvi(self):
        scene = _make_scene()
        result = compute_ndvi(scene)
        assert result.supported
        assert -1.0 <= result.mean <= 1.0
        assert result.valid_count > 0

    def test_ndwi(self):
        scene = _make_scene()
        result = compute_ndwi(scene)
        assert result.supported
        assert -1.0 <= result.mean <= 1.0

    def test_ndbi(self):
        scene = _make_scene()
        result = compute_ndbi(scene)
        assert result.supported

    def test_evi(self):
        scene = _make_scene()
        result = compute_evi(scene)
        assert result.supported

    def test_ndvi_missing_bands(self):
        scene = create_raster_from_arrays({"B02": np.zeros((10, 10))})
        result = compute_ndvi(scene)
        assert not result.supported
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE

    def test_ndwi_missing_bands(self):
        scene = create_raster_from_arrays({"B04": np.zeros((10, 10))})
        result = compute_ndwi(scene)
        assert not result.supported

    def test_ndbi_missing_bands(self):
        scene = create_raster_from_arrays({"B03": np.zeros((10, 10))})
        result = compute_ndbi(scene)
        assert not result.supported

    def test_zero_denominator(self):
        zeros = np.zeros((10, 10))
        scene = create_raster_from_arrays({"B08": zeros, "B04": zeros})
        result = compute_ndvi(scene)
        assert result.supported
        assert result.mean == np.nan or np.isnan(result.mean)

    def test_nan_handling(self):
        data = np.full((10, 10), np.nan)
        scene = create_raster_from_arrays({"B08": data, "B04": data})
        result = compute_ndvi(scene)
        assert result.valid_count == 0

    def test_infinity_handling(self):
        data = np.full((10, 10), np.inf)
        scene = create_raster_from_arrays({"B08": data, "B04": data})
        result = compute_ndvi(scene)
        assert result.valid_count == 0

    def test_generic_index(self):
        scene = _make_scene()
        result = compute_index(scene, "NDVI")
        assert result.supported

    def test_unknown_index(self):
        scene = _make_scene()
        result = compute_index(scene, "FAKE")
        assert not result.supported

    def test_safe_divide_zero(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([0.0, 1.0, 0.0])
        result = _safe_divide(a, b)
        assert np.isnan(result[0])
        assert result[1] == 2.0
        assert np.isnan(result[2])


# ── Time Series Engine ──


class TestTimeSeriesEngine:
    def test_add_scalar(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        engine.add_scalar(NOW, 0.5)
        assert engine.count == 1

    def test_add_multiple(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        for i in range(5):
            engine.add_scalar(NOW + timedelta(days=i), 0.5 + i * 0.01)
        assert engine.count == 5

    def test_date_ordering(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        engine.add_scalar(NOW + timedelta(days=10), 0.6)
        engine.add_scalar(NOW, 0.5)
        engine.add_scalar(NOW + timedelta(days=5), 0.55)
        assert engine._points[0].timestamp == NOW
        assert engine._points[-1].timestamp == NOW + timedelta(days=10)

    def test_filter_by_quality(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        engine.add_scalar(NOW, 0.5, confidence=0.9)
        engine.add_scalar(NOW + timedelta(days=1), 0.5, confidence=0.2)
        filtered = engine.filter_by_quality(min_confidence=0.5)
        assert len(filtered) == 1

    def test_stats(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        for i in range(10):
            engine.add_scalar(NOW + timedelta(days=i), 0.5 + i * 0.01)
        stats = engine.compute_stats()
        assert stats.count == 10
        assert not np.isnan(stats.mean)

    def test_missing_dates(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        engine.add_scalar(NOW, 0.5)
        engine.add_scalar(NOW + timedelta(days=20), 0.6)
        gaps = engine.detect_missing_dates(expected_interval_days=5)
        assert len(gaps) == 1

    def test_interpolate(self):
        engine = GeoTimeSeriesEngine("ts1", "NDVI")
        engine.add_scalar(NOW, 0.5)
        engine.add_scalar(NOW + timedelta(days=5), 0.6)
        result = engine.interpolate_missing()
        assert len(result) >= 2


# ── Pixel Change Detection ──


class TestPixelChange:
    def test_no_change(self):
        scene = _make_scene()
        result = detect_pixel_change(scene, scene, change_threshold=0.1)
        assert result.changed_pixels == 0
        assert result.change_type.value == "no_change"

    def test_change_detected(self):
        before = _make_scene()
        np.random.seed(99)
        after_bands = {
            "B02": before.bands["B02"].data.copy(),
            "B03": before.bands["B03"].data.copy(),
            "B04": before.bands["B04"].data.copy(),
            "B08": before.bands["B08"].data + 0.15,
            "B11": before.bands["B11"].data.copy(),
        }
        after = create_raster_from_arrays(after_bands, bbox=before.bbox)
        result = detect_pixel_change(before, after, change_threshold=0.05)
        assert result.changed_pixels > 0
        assert result.changed_area_km2 > 0

    def test_area_calculation(self):
        before = _make_scene(50, 50)
        np.random.seed(99)
        after_bands = {name: band.data.copy() for name, band in before.bands.items()}
        after_bands["B08"] = after_bands["B08"] + 0.2
        after = create_raster_from_arrays(after_bands, bbox=before.bbox, pixel_size_m=10.0)
        result = detect_pixel_change(before, after, change_threshold=0.05, pixel_size_m=10.0)
        assert result.changed_area_km2 >= 0

    def test_missing_bands(self):
        s1 = create_raster_from_arrays({"B02": np.zeros((10, 10))})
        s2 = create_raster_from_arrays({"B02": np.zeros((10, 10))})
        result = detect_pixel_change(s1, s2)
        assert result.change_type.value != "no_change" or result.total_pixels == 0

    def test_shape_mismatch(self):
        s1 = _make_scene(100, 100)
        s2 = _make_scene(80, 80)
        result = detect_pixel_change(s1, s2)
        assert result.total_pixels > 0

    def test_confidence(self):
        scene = _make_scene()
        result = detect_pixel_change(scene, scene)
        assert 0.0 <= result.confidence <= 1.0


# ── Deterministic Tests ──


class TestDeterministic:
    def test_ndvi_deterministic(self):
        scene = _make_scene()
        r1 = compute_ndvi(scene)
        r2 = compute_ndvi(scene)
        np.testing.assert_array_equal(r1.data, r2.data)

    def test_change_deterministic(self):
        s1 = _make_scene()
        s2 = _make_scene()
        r1 = detect_pixel_change(s1, s2)
        r2 = detect_pixel_change(s1, s2)
        assert r1.changed_pixels == r2.changed_pixels
        np.testing.assert_array_equal(r1.change_mask, r2.change_mask)


# ── No Fabrication Tests ──


class TestNoFabrication:
    def test_no_fake_pixels(self):
        scene = _make_scene()
        result = compute_ndvi(scene)
        assert result.data.shape == (100, 100)

    def test_result_is_real_math(self):
        nir = np.full((5, 5), 0.3)
        red = np.full((5, 5), 0.1)
        scene = create_raster_from_arrays({"B08": nir, "B04": red})
        result = compute_ndvi(scene)
        expected = (0.3 - 0.1) / (0.3 + 0.1)
        assert result.mean == pytest.approx(expected, abs=0.001)
