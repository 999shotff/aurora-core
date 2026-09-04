"""Google Earth Engine provider stub.

GEE requires authentication via service account or OAuth.
When not configured, returns NOT_CONFIGURED status.
"""

from __future__ import annotations

from datetime import datetime

from aurora.geo.domain import (
    AOI,
    GeoDatasetInfo,
    GeoIntegrityState,
    GeoObservation,
    GeoProviderCapabilities,
    GeoScene,
    GeoSearchResult,
)
from aurora.geo.providers.base import GeoProvider

_GEE_DATASETS = {
    "LANDSAT/LC09/C02/T1_L2": GeoDatasetInfo(
        dataset_id="LANDSAT/LC09/C02/T1_L2",
        name="Landsat 9 Level-2",
        description="Landsat 9 surface reflectance, 30m resolution",
        resolution_m=30.0,
        temporal_resolution_hours=720.0,
        bands=("SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"),
    ),
    "COPERNICUS/S2_SR_HARMONIZED": GeoDatasetInfo(
        dataset_id="COPERNICUS/S2_SR_HARMONIZED",
        name="Sentinel-2 SR Harmonized",
        description="Sentinel-2 surface reflectance, 10-60m",
        resolution_m=10.0,
        temporal_resolution_hours=24.0,
        bands=("B2", "B3", "B4", "B8", "B11", "B12"),
    ),
    "MODIS/061/MOD09GA": GeoDatasetInfo(
        dataset_id="MODIS/061/MOD09GA",
        name="MODIS Terra Daily",
        description="MODIS Terra surface reflectance daily, 500m-1km",
        resolution_m=500.0,
        temporal_resolution_hours=24.0,
        bands=("sur_refl_b01", "sur_refl_b02", "sur_refl_b06"),
    ),
}


class GEEProvider(GeoProvider):
    """Google Earth Engine provider.

    Requires GEE authentication (service account or OAuth).
    When not configured, returns NOT_CONFIGURED status.
    """

    @property
    def name(self) -> str:
        return "google_earth_engine"

    @property
    def is_open_data(self) -> bool:
        return False

    def get_capabilities(self) -> GeoProviderCapabilities:
        return GeoProviderCapabilities(
            provider=self.name,
            datasets=tuple(_GEE_DATASETS.values()),
            supported_formats=("GeoTIFF", "COG"),
            max_aoi_km2=100000.0,
            requires_api_key=True,
            is_open_data=False,
            rate_limit_per_minute=60,
            provenance_url="https://earthengine.google.com/",
        )

    def _is_configured(self) -> bool:
        """Check if GEE credentials are available."""
        import os
        return bool(os.environ.get("GOOGLE_EARTH_ENGINE_CREDENTIALS") or os.environ.get("GEE_SERVICE_ACCOUNT_KEY"))

    def search_scenes(
        self,
        aoi: AOI,
        start_date: datetime,
        end_date: datetime,
        dataset: str = "COPERNICUS/S2_SR_HARMONIZED",
        max_cloud_pct: float = 30.0,
        resolution_m: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GeoSearchResult:
        if not self._is_configured():
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error="GOOGLE_EARTH_ENGINE_CREDENTIALS not configured. GEE requires authentication.",
            )

        if dataset not in _GEE_DATASETS:
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error=f"Unknown dataset: {dataset}. Available: {list(_GEE_DATASETS.keys())}",
            )

        return GeoSearchResult(
            provider=self.name,
            aoi=aoi,
            date_range=(start_date, end_date),
            integrity_state=GeoIntegrityState.DATA_AVAILABLE,
            error="GEE search requires authenticated client. Not implemented in this environment.",
        )

    def get_observation(
        self,
        scene: GeoScene,
        aoi: AOI,
    ) -> GeoObservation:
        return GeoObservation(
            observation_id=f"gee_{scene.scene_id}",
            scene=scene,
            aoi=aoi,
            derived_values={},
            confidence=0.0,
            uncertainty="GEE requires authentication for pixel access. Not configured.",
            integrity_state=GeoIntegrityState.PROVIDER_ERROR,
            notes=("GEE provider requires GOOGLE_EARTH_ENGINE_CREDENTIALS.",),
        )
