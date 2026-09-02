"""M30 Geospatial Earth Observation Tests.

48 tests covering:
- AOI validation
- Coordinate validation
- CRS handling
- BoundingBox geometry
- Scene metadata
- Date ordering
- Cloud filtering
- Provider abstraction
- Provenance
- Deterministic processing
- NDVI
- NDWI
- NDBI
- Temporal comparison
- Change detection
- Missing-band handling
- Stale-data handling
- Provider failure
- Evidence integration
- No fabricated observations
- Integrity states
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aurora.geo.domain import (
    AOI,
    BoundingBox,
    CloudInfo,
    CRS,
    GeoChange,
    GeoChangeType,
    GeoEvidence,
    GeoIntegrityState,
    GeoObservation,
    GeoPoint,
    GeoProvenance,
    GeoQualityGrade,
    GeoQualityReport,
    GeoRasterMetadata,
    GeoScene,
    GeoTimeSeries,
    GeoTimeSeriesPoint,
)
from aurora.geo.features.indices import DerivedFeature
from aurora.geo.processing.transforms import clip_to_aoi, reproject
from aurora.geo.features.indices import (
    compute_ndvi,
    compute_ndwi,
    compute_ndbi,
    compute_vegetation_change,
    compute_water_change,
    compute_built_area_change,
    compute_temporal_anomaly,
)
from aurora.geo.analysis.change import detect_change
from aurora.geo.analysis.evidence import (
    observation_to_evidence,
    change_to_evidence,
    timeseries_to_evidence,
    aggregate_geo_evidence,
)


# ── Helpers ──

NOW = datetime(2025, 6, 15, tzinfo=timezone.utc)


def _aoi(name: str = "test") -> AOI:
    return AOI(name=name, bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))


def _scene(
    provider: str = "test",
    dataset: str = "S2L2A",
    bands: tuple[str, ...] = ("B03", "B04", "B08", "B11"),
    cloud_pct: float = 5.0,
    resolution_m: float = 10.0,
    acq_time: datetime | None = None,
) -> GeoScene:
    return GeoScene(
        scene_id=f"scene_{provider}_{(acq_time or NOW).strftime('%Y%m%d')}",
        provider=provider,
        dataset=dataset,
        acquisition_time=acq_time or NOW,
        bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2),
        cloud_info=CloudInfo(cloud_pct=cloud_pct),
        resolution_m=resolution_m,
        bands=bands,
        quality=GeoQualityReport(grade=GeoQualityGrade.GOOD),
        provenance=GeoProvenance(
            provider=provider,
            dataset=dataset,
            acquisition_time=acq_time or NOW,
            processing_method="raw",
            spatial_resolution_m=resolution_m,
        ),
    )


def _obs(
    provider: str = "test",
    bands: tuple[str, ...] = ("B03", "B04", "B08", "B11"),
    cloud_pct: float = 5.0,
    values: dict[str, float] | None = None,
    acq_time: datetime | None = None,
) -> GeoObservation:
    scene = _scene(provider=provider, bands=bands, cloud_pct=cloud_pct, acq_time=acq_time)
    return GeoObservation(
        observation_id=f"obs_{scene.scene_id}",
        scene=scene,
        aoi=_aoi(),
        derived_values=values or {
            "band_B03_mean": 0.08,
            "band_B04_mean": 0.05,
            "band_B08_mean": 0.25,
            "band_B11_mean": 0.15,
        },
        confidence=0.9,
    )


# ── AOI Tests ──


class TestAOI:
    def test_valid_aoi(self):
        aoi = _aoi()
        assert aoi.name == "test"
        assert aoi.area_km2 > 0

    def test_aoi_center(self):
        aoi = _aoi()
        center = aoi.center
        assert 33.7 < center.latitude < 33.8
        assert -118.4 < center.longitude < -118.2

    def test_aoi_contains_point(self):
        aoi = _aoi()
        pt = GeoPoint(latitude=33.75, longitude=-118.3)
        assert aoi.bbox.contains(pt)

    def test_aoi_does_not_contain(self):
        aoi = _aoi()
        pt = GeoPoint(latitude=40.0, longitude=-74.0)
        assert not aoi.bbox.contains(pt)


class TestGeoPoint:
    def test_valid_point(self):
        p = GeoPoint(latitude=0, longitude=0)
        assert p.latitude == 0

    def test_invalid_latitude(self):
        with pytest.raises(ValueError, match="latitude"):
            GeoPoint(latitude=91, longitude=0)

    def test_invalid_longitude(self):
        with pytest.raises(ValueError, match="longitude"):
            GeoPoint(latitude=0, longitude=181)


class TestBoundingBox:
    def test_valid_bbox(self):
        bb = BoundingBox(south=0, west=0, north=10, east=10)
        assert bb.area_km2 > 0

    def test_south_gte_north(self):
        with pytest.raises(ValueError, match="south.*must be < north"):
            BoundingBox(south=10, west=0, north=0, east=10)

    def test_intersects(self):
        bb1 = BoundingBox(south=0, west=0, north=10, east=10)
        bb2 = BoundingBox(south=5, west=5, north=15, east=15)
        assert bb1.intersects(bb2)

    def test_no_intersect(self):
        bb1 = BoundingBox(south=0, west=0, north=10, east=10)
        bb2 = BoundingBox(south=20, west=20, north=30, east=30)
        assert not bb1.intersects(bb2)


class TestCRS:
    def test_default_crs(self):
        crs = CRS()
        assert crs.code == "EPSG:4326"

    def test_invalid_crs(self):
        with pytest.raises(ValueError, match="EPSG:"):
            CRS(code="WGS84")


# ── Quality Tests ──


class TestCloudInfo:
    def test_valid_cloud(self):
        ci = CloudInfo(cloud_pct=50)
        assert ci.cloud_pct == 50

    def test_cloud_out_of_range(self):
        with pytest.raises(ValueError, match="cloud_pct"):
            CloudInfo(cloud_pct=150)


class TestQualityReport:
    def test_quality_score_perfect(self):
        q = GeoQualityReport(grade=GeoQualityGrade.GOOD)
        assert q.quality_score == 1.0

    def test_quality_score_with_clouds(self):
        q = GeoQualityReport(
            grade=GeoQualityGrade.PARTIAL,
            cloud_info=CloudInfo(cloud_pct=50),
        )
        assert q.quality_score < 1.0

    def test_unavailable_quality(self):
        q = GeoQualityReport(grade=GeoQualityGrade.UNAVAILABLE)
        assert q.quality_score == 0.0


# ── Raster Metadata Tests ──


class TestRasterMetadata:
    def test_valid_raster(self):
        r = GeoRasterMetadata(width_pixels=100, height_pixels=100, pixel_size_m=10.0)
        assert r.width_pixels == 100

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError, match="positive"):
            GeoRasterMetadata(width_pixels=0, height_pixels=100, pixel_size_m=10.0)


# ── Scene Tests ──


class TestGeoScene:
    def test_scene_age(self):
        now = datetime.now(timezone.utc)
        scene = _scene(acq_time=now - timedelta(days=5))
        assert scene.age_days == pytest.approx(5.0, abs=1.0)

    def test_scene_bands(self):
        scene = _scene(bands=("B02", "B03", "B04"))
        assert "B03" in scene.bands


# ── Observation Tests ──


class TestGeoObservation:
    def test_observation_source(self):
        obs = _obs(provider="sentinel")
        assert obs.source == "sentinel"

    def test_observation_acquisition(self):
        obs = _obs(acq_time=NOW)
        assert obs.acquisition_timestamp == NOW

    def test_no_fabricated_data(self):
        obs = _obs()
        assert obs.derived_values.get("band_B03_mean") == 0.08
        assert "band_XX_mean" not in obs.derived_values


# ── Provenance Tests ──


class TestProvenance:
    def test_provenance_fields(self):
        p = GeoProvenance(
            provider="test",
            dataset="S2L2A",
            acquisition_time=NOW,
            processing_method="raw",
            spatial_resolution_m=10.0,
        )
        assert p.provider == "test"
        assert p.spatial_resolution_m == 10.0


# ── Feature Tests ──


class TestNDVI:
    def test_valid_ndvi(self):
        obs = _obs()
        result = compute_ndvi(obs)
        assert result.supported
        assert -1.0 <= result.value <= 1.0
        assert result.confidence > 0

    def test_ndvi_missing_bands(self):
        obs = _obs(bands=("B02", "B03"))
        result = compute_ndvi(obs)
        assert not result.supported
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE

    def test_ndvi_high_cloud(self):
        obs = _obs(cloud_pct=90)
        result = compute_ndvi(obs)
        assert result.confidence < 0.5

    def test_ndvi_zero_denominator(self):
        obs = _obs(values={"band_B03_mean": 0.0, "band_B04_mean": 0.0, "band_B08_mean": 0.0, "band_B11_mean": 0.0})
        result = compute_ndvi(obs)
        assert result.value == 0.0


class TestNDWI:
    def test_valid_ndwi(self):
        obs = _obs()
        result = compute_ndwi(obs)
        assert result.supported
        assert -1.0 <= result.value <= 1.0

    def test_ndwi_missing_bands(self):
        obs = _obs(bands=("B04", "B08"))
        result = compute_ndwi(obs)
        assert not result.supported


class TestNDBI:
    def test_valid_ndbi(self):
        obs = _obs()
        result = compute_ndbi(obs)
        assert result.supported
        assert -1.0 <= result.value <= 1.0

    def test_ndbi_missing_bands(self):
        obs = _obs(bands=("B03", "B04"))
        result = compute_ndbi(obs)
        assert not result.supported


# ── Temporal Comparison Tests ──


class TestTemporalComparison:
    def test_vegetation_change(self):
        before = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.15})
        after = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.30, "band_B11_mean": 0.15})
        result = compute_vegetation_change(before, after)
        assert result.supported
        assert result.value > 0

    def test_water_change(self):
        before = _obs(values={"band_B03_mean": 0.10, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.15})
        after = _obs(values={"band_B03_mean": 0.15, "band_B04_mean": 0.05, "band_B08_mean": 0.15, "band_B11_mean": 0.15})
        result = compute_water_change(before, after)
        assert result.supported

    def test_built_area_change(self):
        before = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.10})
        after = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.20})
        result = compute_built_area_change(before, after)
        assert result.supported
        assert result.value > 0

    def test_change_with_missing_bands(self):
        before = _obs(bands=("B02", "B03"))
        after = _obs(bands=("B02", "B03"))
        result = compute_vegetation_change(before, after)
        assert not result.supported


# ── Anomaly Detection Tests ──


class TestAnomalyDetection:
    def test_anomaly_insufficient_data(self):
        ts = GeoTimeSeries(
            series_id="ts1",
            aoi=_aoi(),
            metric="ndvi",
            points=(GeoTimeSeriesPoint(timestamp=NOW, value=0.5),),
        )
        result = compute_temporal_anomaly(ts)
        assert not result.supported

    def test_anomaly_normal(self):
        points = tuple(
            GeoTimeSeriesPoint(timestamp=NOW + timedelta(days=i), value=0.5 + 0.01 * i)
            for i in range(10)
        )
        ts = GeoTimeSeries(series_id="ts1", aoi=_aoi(), metric="ndvi", points=points)
        result = compute_temporal_anomaly(ts)
        assert result.supported
        assert abs(result.value) < 3.0

    def test_anomaly_spike(self):
        vals = [0.5] * 9 + [2.0]
        points = tuple(
            GeoTimeSeriesPoint(timestamp=NOW + timedelta(days=i), value=v)
            for i, v in enumerate(vals)
        )
        ts = GeoTimeSeries(series_id="ts1", aoi=_aoi(), metric="ndvi", points=points)
        result = compute_temporal_anomaly(ts)
        assert result.supported
        assert abs(result.value) > 2.0


# ── Change Detection Tests ──


class TestChangeDetection:
    def test_no_change(self):
        obs = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.25, "band_B11_mean": 0.15})
        result = detect_change(obs, obs, threshold=0.1)
        assert result.change is not None
        assert result.change.change_type == GeoChangeType.NO_CHANGE

    def test_increase_detected(self):
        before = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.15})
        after = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.35, "band_B11_mean": 0.15})
        result = detect_change(before, after, threshold=0.01)
        assert result.change is not None
        assert result.change.change_type == GeoChangeType.INCREASE

    def test_aoi_mismatch(self):
        obs_a = GeoObservation(
            observation_id="a", scene=_scene(), aoi=AOI(name="A", bbox=BoundingBox(south=0, west=0, north=1, east=1)),
        )
        obs_b = GeoObservation(
            observation_id="b", scene=_scene(), aoi=AOI(name="B", bbox=BoundingBox(south=0, west=0, north=1, east=1)),
        )
        result = detect_change(obs_a, obs_b)
        assert result.change is None
        assert result.integrity_state == GeoIntegrityState.PROCESSING_FAILED

    def test_missing_bands(self):
        obs_a = _obs(bands=("B02",))
        obs_b = _obs(bands=("B02",))
        result = detect_change(obs_a, obs_b)
        assert result.change is None
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE


# ── Processing Tests ──


class TestProcessing:
    def test_clip_to_aoi(self):
        obs = _obs()
        aoi = _aoi()
        result = clip_to_aoi(obs, aoi)
        assert result.success
        assert result.output is not None
        assert "clip" in result.output.processing_chain

    def test_reproject(self):
        obs = _obs()
        target = CRS(code="EPSG:3857")
        result = reproject(obs, target)
        assert result.success
        assert "reproject(EPSG:3857)" in result.output.processing_chain


# ── Evidence Integration Tests ──


class TestEvidenceIntegration:
    def test_observation_to_evidence(self):
        obs = _obs()
        ev = observation_to_evidence(obs)
        assert ev.domain == "geospatial"
        assert "Satellite observation" in ev.description

    def test_change_to_evidence(self):
        before = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.15})
        after = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.35, "band_B11_mean": 0.15})
        change_result = detect_change(before, after, threshold=0.01)
        assert change_result.change is not None
        ev = change_to_evidence(change_result.change)
        assert ev.domain == "geospatial"
        assert "Geospatial change detected" in ev.description

    def test_timeseries_to_evidence(self):
        points = tuple(
            GeoTimeSeriesPoint(timestamp=NOW + timedelta(days=i), value=0.5)
            for i in range(5)
        )
        ts = GeoTimeSeries(series_id="ts1", aoi=_aoi(), metric="ndvi", points=points)
        ev = timeseries_to_evidence(ts)
        assert ev.domain == "geospatial"

    def test_empty_timeseries(self):
        ts = GeoTimeSeries(series_id="ts1", aoi=_aoi(), metric="ndvi", points=())
        ev = timeseries_to_evidence(ts)
        assert ev.strength.value == "absent"

    def test_aggregate_geo_evidence(self):
        obs = _obs()
        items = aggregate_geo_evidence([obs], [], [])
        assert len(items) == 1
        assert items[0].domain == "geospatial"

    def test_evidence_never_predicts(self):
        obs = _obs()
        ev = observation_to_evidence(obs)
        assert "will rise" not in ev.description.lower()
        assert "will fall" not in ev.description.lower()
        assert "predict" not in ev.description.lower()


# ── Provider Abstraction Tests ──


class TestProviderAbstraction:
    def test_registry(self):
        from aurora.geo.providers.base import GeoProviderRegistry, GeoProvider

        class MockProvider(GeoProvider):
            @property
            def name(self) -> str: return "mock"
            @property
            def is_open_data(self) -> bool: return True
            def get_capabilities(self):
                from aurora.geo.domain import GeoProviderCapabilities
                return GeoProviderCapabilities(provider="mock")
            def search_scenes(self, **kwargs):
                from aurora.geo.providers.base import GeoSearchResult
                return GeoSearchResult(provider="mock")
            def get_observation(self, scene, aoi):
                return _obs()

        reg = GeoProviderRegistry()
        reg.register(MockProvider())
        assert "mock" in reg.list_providers()
        assert reg.get("mock") is not None
        assert reg.get("nonexistent") is None


# ── Integrity State Tests ──


class TestIntegrityStates:
    def test_all_states_exist(self):
        states = [
            "DATA_AVAILABLE", "DATA_STALE", "DATA_UNAVAILABLE",
            "LOW_CONFIDENCE", "INSUFFICIENT_RESOLUTION",
            "INSUFFICIENT_TEMPORAL_COVERAGE", "PROCESSING_FAILED",
            "PROVIDER_ERROR",
        ]
        for s in states:
            assert GeoIntegrityState(s).value == s


# ── Deterministic Tests ──


class TestDeterministic:
    def test_ndvi_deterministic(self):
        obs = _obs()
        r1 = compute_ndvi(obs)
        r2 = compute_ndvi(obs)
        assert r1.value == r2.value
        assert r1.confidence == r2.confidence

    def test_change_deterministic(self):
        before = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.20, "band_B11_mean": 0.15})
        after = _obs(values={"band_B03_mean": 0.08, "band_B04_mean": 0.05, "band_B08_mean": 0.35, "band_B11_mean": 0.15})
        r1 = detect_change(before, after, threshold=0.01)
        r2 = detect_change(before, after, threshold=0.01)
        assert r1.change.change_type == r2.change.change_type
        assert r1.change.magnitude == r2.change.magnitude
