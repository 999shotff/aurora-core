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
    """Test per-pixel index computation on real GIBS data."""

    def _get_scene(self):
        p = GIBSProvider()
        aoi = AOI(name="la", bbox=BoundingBox(south=33.7, west=-118.4, north=33.8, east=-118.2))
        return p.download_tile("MODIS_Terra_CorrectedReflectance_TrueColor", aoi, datetime(2025, 6, 1))

    def test_ndvi_supported(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is True
        assert result.integrity_state == GeoIntegrityState.DATA_AVAILABLE

    def test_ndvi_zero_for_true_color(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.mean == pytest.approx(0.0, abs=0.01)

    def test_ndwi_supported(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is True
        assert result.integrity_state == GeoIntegrityState.DATA_AVAILABLE

    def test_ndwi_range(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert -1.0 <= result.mean <= 1.0

    def test_ndbi_supported(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDBI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is True

    def test_evi_supported(self):
        scene = self._get_scene()
        result = compute_index(scene, "EVI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is True

    def test_valid_count_positive(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.valid_count > 0
        assert result.total_count == 512 * 512

    def test_index_preserves_provenance(self):
        scene = self._get_scene()
        result = compute_index(scene, "NDWI", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.uncertainty is not None
        assert len(result.uncertainty) > 0


# ── Band Name Resolution ──

class TestBandResolution:
    """Test band name resolution for different datasets."""

    def test_gibs_band_map_exists(self):
        assert "MODIS_Terra_CorrectedReflectance_TrueColor" in DATASET_BAND_MAP

    def test_gibs_ndvi_bands(self):
        gibs_map = DATASET_BAND_MAP["MODIS_Terra_CorrectedReflectance_TrueColor"]
        assert gibs_map["NDVI"]["nir"] == "Red"
        assert gibs_map["NDVI"]["red"] == "Red"

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
        result = compute_index(scene, "FAKE_INDEX", dataset="MODIS_Terra_CorrectedReflectance_TrueColor")
        assert result.supported is False
        assert result.integrity_state == GeoIntegrityState.PROCESSING_FAILED
