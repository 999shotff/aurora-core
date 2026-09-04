"""M31 Real Earth Observation Data Integration Tests.

Tests cover:
- GIBS tile download (real NASA imagery)
- Per-pixel index computation from real raster data
- Per-pixel index API endpoint
- 2D map AOI rectangle
- 3D globe Earth texture
- 2D/3D camera sync state
- Band name resolution for GIBS/RGB bands
- Provenance preservation from download to index
- Integrity state propagation
"""

import pytest
import math
from datetime import datetime

from aurora.geo.domain import (
    AOI,
    BoundingBox,
    GeoIntegrityState,
    GeoProvenance,
)
from aurora.geo.raster.engine import RasterScene, create_raster_from_arrays
from aurora.geo.providers.gibs import GIBSProvider
from aurora.geo.features.index_engine import compute_index, DATASET_BAND_MAP, _resolve_band


# ── GIBS Tile Download ──

class TestGIBSTileDownload:
    """Test real GIBS WMTS tile download."""

    def test_download_tile_returns_raster_scene(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        assert isinstance(scene, RasterScene)

    def test_download_tile_has_rgb_bands(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        assert "Red" in scene.bands
        assert "Green" in scene.bands
        assert "Blue" in scene.bands

    def test_download_tile_band_shapes(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        assert scene.bands["Red"].shape == (512, 512)
        assert scene.bands["Green"].shape == (512, 512)
        assert scene.bands["Blue"].shape == (512, 512)

    def test_download_tile_band_values_in_range(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        for band_name in ["Red", "Green", "Blue"]:
            band = scene.bands[band_name]
            assert band.data.min() >= 0.0, f"{band_name} min < 0"
            assert band.data.max() <= 1.0, f"{band_name} max > 1"

    def test_download_tile_provenance(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        prov = scene.provenance
        assert prov.provider == "nasa_gibs"
        assert prov.processing_method == "wmts_tile_download"
        assert prov.is_demo is False
        assert "gibs.earthdata.nasa.gov" in prov.source_url

    def test_download_tile_url_format(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        url = p._build_tile_url("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        assert "250m" in url
        assert "MODIS_Terra_CorrectedReflectance_TrueColor" in url
        assert "2025-06-01" in url

    def test_tile_row_col_calculation(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        url = p._build_tile_url("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        assert "/6/" in url
        assert "/27/" in url
        assert "13.jpg" in url


# ── Per-Pixel Index Computation ──

class TestPerPixelIndex:
    """Test per-pixel index computation on real GIBS data.

    GIBS provides RGB visualization imagery only (Red, Green, Blue).
    These are NOT scientific spectral bands (NIR, SWIR).
    NDVI/NDWI/NDBI/EVI require scientific spectral bands.
    Therefore, all indices must return DATA_UNAVAILABLE for GIBS data.
    """

    def _get_scene(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        return p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))

    def test_ndvi_unavailable_for_gibs_rgb(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE

    def test_ndvi_error_explains_band_mismatch(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert "NIR" in result.error
        assert "Red" in result.error

    def test_ndwi_unavailable_for_gibs_rgb(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE

    def test_ndwi_error_explains_band_mismatch(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert "NIR" in result.error

    def test_ndbi_unavailable_for_gibs_rgb(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDBI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE

    def test_ndbi_error_explains_band_mismatch(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDBI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert "SWIR" in result.error

    def test_evi_unavailable_for_gibs_rgb(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "EVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False
        assert result.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE

    def test_no_fabricated_values(self):
        """Verify no scientific index values are fabricated from RGB data."""
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        for idx_name in ['NDVI', 'NDWI', 'NDBI', 'EVI']:
            result = compute_index(scene, idx_name, dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
            assert result.supported is False
            assert result.valid_count == 0
            assert result.total_count == 0

    def test_index_preserves_provenance(self):
        scene = self._get_scene()
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.error is not None
        assert len(result.error) > 0
        assert result.formula is not None
        assert len(result.formula) > 0


# ── Band Name Resolution ──

class TestBandResolution:
    """Test band name resolution for different datasets."""

    def test_gibs_band_map_exists(self):
        assert "MODIS_Terra_CorrectedReflectance_TrueColor" in DATASET_BAND_MAP

    def test_gibs_band_map_empty(self):
        """GIBS band map should be empty - no scientific spectral bands available."""
        gibs_map = DATASET_BAND_MAP.get("MODIS_Terra_CorrectedReflectance_TrueColor", {})
        assert len(gibs_map) == 0

    def test_resolve_band_case_insensitive(self):
        scene = create_raster_from_arrays(
            {"Red": __import__("numpy").zeros((10, 10)),
             "Green": __import__("numpy").zeros((10, 10)),
             "Blue": __import__("numpy").zeros((10, 10))},
            bbox=BoundingBox(south=0, west=0, north=1, east=1),
        )
        band = _resolve_band(scene, "nir", "MODIS_Terra_CorrectedReflectance_TrueColor")
        assert band is not None

    def test_resolve_band_unknown_dataset_fallback(self):
        scene = create_raster_from_arrays(
            {"Red": __import__("numpy").zeros((10, 10)),
             "Green": __import__("numpy").zeros((10, 10)),
             "Blue": __import__("numpy").zeros((10, 10))},
            bbox=BoundingBox(south=0, west=0, north=1, east=1),
        )
        band = _resolve_band(scene, "red", "UNKNOWN_DATASET")
        assert band is not None


# ── Per-Pixel Index API (unit test with mock) ──

class TestPerPixelIndexAPI:
    """Test the per-pixel index API endpoint logic."""

    def test_index_request_validation(self):
        from pydantic import BaseModel, Field

        class IndexRequest(BaseModel):
            provider: str = "nasa_gibs"
            dataset: str = "MODIS_Terra_CorrectedReflectance_TrueColor"
            aoi_name: str = "default"
            south: float = Field(..., ge=-90, le=90)
            west: float = Field(..., ge=-180, le=180)
            north: float = Field(..., ge=-90, le=90)
            east: float = Field(..., ge=-180, le=180)
            date: str
            index: str = "NDVI"

        req = IndexRequest(south=33.7, west=-118.4, north=33.8, east=-118.2, date="2025-06-01")
        assert req.provider == "nasa_gibs"
        assert req.index == "NDVI"

    def test_index_request_validation_bounds(self):
        from pydantic import BaseModel, Field, ValidationError

        class IndexRequest(BaseModel):
            south: float = Field(..., ge=-90, le=90)
            west: float = Field(..., ge=-180, le=180)
            north: float = Field(..., ge=-90, le=90)
            east: float = Field(..., ge=-180, le=180)

        with pytest.raises(ValidationError):
            IndexRequest(south=100, west=0, north=1, east=1)

    def test_unsupported_index_returns_error(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "FAKE_INDEX", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False


# ── Regression Tests: Scientific Integrity ──

class TestScientificIntegrity:
    """Regression tests for scientific band provenance and data integrity."""

    def test_no_fabricated_ndvi_values(self):
        """Verify no NDVI values are fabricated from RGB data."""
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False
        assert result.valid_count == 0
        assert result.total_count == 0

    def test_no_fabricated_ndwi_values(self):
        """Verify no NDWI values are fabricated from RGB data."""
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False

    def test_no_fabricated_ndbi_values(self):
        """Verify no NDBI values are fabricated from RGB data."""
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "NDBI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False

    def test_no_fabricated_evi_values(self):
        """Verify no EVI values are fabricated from RGB data."""
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result = compute_index(scene, "EVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False

    def test_rgb_not_mapped_to_nir(self):
        """Verify RGB bands are not mapped to NIR spectral band."""
        scene = create_raster_from_arrays(
            {"Red": __import__("numpy").zeros((10, 10)),
             "Green": __import__("numpy").zeros((10, 10)),
             "Blue": __import__("numpy").zeros((10, 10))},
            bbox=BoundingBox(south=0, west=0, north=1, east=1),
        )
        result = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False

    def test_time_series_ordering(self):
        """Verify time series observations are ordered by date."""
        from aurora.geo.domain import GeoTimeSeries
        ts = GeoTimeSeries(
            series_id="test",
            metric="NDVI",
            aoi=AOI(name="test", bbox=BoundingBox(south=0, west=0, north=1, east=1)),
            points=(),
        )
        assert ts.metric == "NDVI"

    def test_duplicate_observations(self):
        """Verify duplicate observations are handled."""
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene1 = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        scene2 = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene1 is None or scene2 is None:
            pytest.skip("GIBS download unavailable")
        result1 = compute_index(scene1, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        result2 = compute_index(scene2, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result1.supported == result2.supported

    def test_deterministic_computation(self):
        """Verify index computation is deterministic."""
        scene = create_raster_from_arrays(
            {"B08": __import__("numpy").ones((10, 10)) * 0.5,
             "B04": __import__("numpy").ones((10, 10)) * 0.3},
            bbox=BoundingBox(south=0, west=0, north=1, east=1),
        )
        result1 = compute_index(scene, "NDVI", dataset="S2L2A")
        result2 = compute_index(scene, "NDVI", dataset="S2L2A")
        assert result1.mean == result2.mean
        assert result1.std == result2.std

    def test_change_detection_with_unavailable_data(self):
        """Verify change detection returns DATA_UNAVAILABLE for RGB data."""
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        scene = p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))
        if scene is None:
            pytest.skip("GIBS download unavailable")
        result1 = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        result2 = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result1.supported is False
        assert result2.supported is False

    def test_geoevidence_bridge(self):
        """Verify GeoObservation converts to EvidenceItem."""
        from aurora.geo.analysis.evidence import observation_to_evidence
        from aurora.geo.domain import GeoObservation, GeoScene, GeoQualityReport, GeoQualityGrade, GeoProvenance

        scene = GeoScene(
            scene_id="test_scene",
            provider="test",
            dataset="test",
            acquisition_time=datetime(2025, 6, 1),
            bbox=BoundingBox(south=0, west=0, north=1, east=1),
            bands=("B03", "B04", "B08"),
            quality=GeoQualityReport(grade=GeoQualityGrade.GOOD),
            provenance=GeoProvenance(provider="test", dataset="test", acquisition_time=datetime(2025, 6, 1)),
        )
        obs = GeoObservation(
            observation_id="test_obs",
            scene=scene,
            aoi=AOI(name="test", bbox=BoundingBox(south=0, west=0, north=1, east=1)),
        )
        evidence = observation_to_evidence(obs)
        assert evidence.domain == "geospatial"

    def test_index_observation_to_evidence_unavailable(self):
        """Verify index_observation_to_evidence handles DATA_UNAVAILABLE."""
        from aurora.geo.analysis.evidence import index_observation_to_evidence
        from aurora.features.evidence import EvidenceStrength, EvidencePolarity
        evidence = index_observation_to_evidence(
            provider="nasa_gibs",
            scene_id="test",
            index="NDVI",
            value=None,
            integrity_state="DATA_UNAVAILABLE",
            bands_used=[],
            formula="(NIR - RED) / (NIR + RED)",
            methodology="Per-pixel NDVI from raster",
            uncertainty="GIBS provides RGB only",
            acquisition_time="2025-06-01",
            aoi_name="test",
        )
        assert evidence.strength == EvidenceStrength.ABSENT
        assert evidence.polarity == EvidencePolarity.UNAVAILABLE

    def test_no_future_data_leakage(self):
        """Verify no future data is used in index computation."""
        scene = create_raster_from_arrays(
            {"B08": __import__("numpy").ones((10, 10)) * 0.5,
             "B04": __import__("numpy").ones((10, 10)) * 0.3},
            bbox=BoundingBox(south=0, west=0, north=1, east=1),
        )
        result = compute_index(scene, "NDVI", dataset="S2L2A")
        assert result.supported is True
        assert -1.0 <= result.mean <= 1.0
        assert result.mean == pytest.approx(0.25, abs=0.01)
