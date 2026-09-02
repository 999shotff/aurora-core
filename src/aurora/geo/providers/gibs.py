"""NASA GIBS / Worldview provider — near-real-time satellite imagery.

Global Imagery Browse Services (GIBS) provides free, cached imagery tiles.
No API key required. Imagery is tiled (not downloadable as full scenes).
Clearly distinguished as LIVE/REMOTE DATA.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from aurora.geo.domain import (
    AOI,
    CloudInfo,
    GeoDatasetInfo,
    GeoIntegrityState,
    GeoObservation,
    GeoProvenance,
    GeoProviderCapabilities,
    GeoQualityGrade,
    GeoQualityReport,
    GeoScene,
)
from aurora.geo.providers.base import GeoProvider, GeoSearchResult


_GIBS_DATASETS = {
    "MODIS_Terra_CorrectedReflectance_TrueColor": GeoDatasetInfo(
        dataset_id="MODIS_Terra_CorrectedReflectance_TrueColor",
        name="MODIS Terra True Color",
        description="Daily true-color composite from MODIS Terra, 250m-1km",
        resolution_m=250.0,
        temporal_resolution_hours=24.0,
        bands=("Red", "Green", "Blue"),
    ),
    "MODIS_Aqua_CorrectedReflectance_TrueColor": GeoDatasetInfo(
        dataset_id="MODIS_Aqua_CorrectedReflectance_TrueColor",
        name="MODIS Aqua True Color",
        description="Daily true-color composite from MODIS Aqua",
        resolution_m=250.0,
        temporal_resolution_hours=24.0,
        bands=("Red", "Green", "Blue"),
    ),
    "VIIRS_SNPP_CorrectedReflectance_TrueColor": GeoDatasetInfo(
        dataset_id="VIIRS_SNPP_CorrectedReflectance_TrueColor",
        name="VIIRS SNPP True Color",
        description="Daily true-color from VIIRS Suomi NPP, 375m",
        resolution_m=375.0,
        temporal_resolution_hours=24.0,
        bands=("Red", "Green", "Blue"),
    ),
    " Landsat_WELD_CorrectedReflectance_TrueColor_Global_Monthly": GeoDatasetInfo(
        dataset_id="Landsat_WELD_CorrectedReflectance_TrueColor_Global_Monthly",
        name="Landsat WELD Monthly",
        description="Monthly Landsat composites, 30m",
        resolution_m=30.0,
        temporal_resolution_hours=720.0,
        bands=("Red", "Green", "Blue", "NIR"),
    ),
}


class GIBSProvider(GeoProvider):
    """NASA GIBS — tiled imagery via WMTS.

    Imagery is REMOTE DATA served as tiles. Not downloaded locally.
    No API key required.
    """

    def __init__(self) -> None:
        self._base_url = "https://gibs.earthdata.nasa.gov"

    @property
    def name(self) -> str:
        return "nasa_gibs"

    @property
    def is_open_data(self) -> bool:
        return True

    def get_capabilities(self) -> GeoProviderCapabilities:
        return GeoProviderCapabilities(
            provider=self.name,
            datasets=tuple(_GIBS_DATASETS.values()),
            supported_formats=("WMTS", "PNG", "JPEG"),
            max_aoi_km2=50000.0,
            requires_api_key=False,
            is_open_data=True,
            rate_limit_per_minute=300,
            provenance_url="https://gibs.earthdata.nasa.gov/",
        )

    def search_scenes(
        self,
        aoi: AOI,
        start_date: datetime,
        end_date: datetime,
        dataset: str = "MODIS_Terra_CorrectedReflectance_TrueColor",
        max_cloud_pct: float = 30.0,
        resolution_m: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GeoSearchResult:
        if dataset not in _GIBS_DATASETS:
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error=f"Unknown dataset: {dataset}. Available: {list(_GIBS_DATASETS.keys())}",
            )

        ds_info = _GIBS_DATASETS[dataset]
        scenes: list[GeoScene] = []
        current = start_date
        idx = 0

        while current <= end_date and len(scenes) < page_size:
            idx += 1
            if idx <= (page - 1) * page_size:
                current += timedelta(days=1)
                continue

            tile_url = self._build_tile_url(dataset, aoi, current)

            scene = GeoScene(
                scene_id=f"gibs_{dataset}_{current.strftime('%Y%m%d')}",
                provider=self.name,
                dataset=dataset,
                acquisition_time=current,
                bbox=aoi.bbox,
                cloud_info=CloudInfo(cloud_pct=0.0),
                resolution_m=ds_info.resolution_m,
                bands=ds_info.bands,
                quality=GeoQualityReport(
                    grade=GeoQualityGrade.PARTIAL,
                    notes=("GIBS provides browse-quality tiles, not analysis-ready data.",),
                ),
                provenance=GeoProvenance(
                    provider=self.name,
                    dataset=dataset,
                    acquisition_time=current,
                    processing_method="tile_composite",
                    source_url=tile_url,
                    spatial_resolution_m=ds_info.resolution_m,
                    uncertainty="GIBS tiles are browse-quality. Not analysis-ready.",
                ),
                thumbnail_url=tile_url,
            )
            scenes.append(scene)
            current += timedelta(days=1)

        return GeoSearchResult(
            scenes=tuple(scenes),
            total_count=(end_date - start_date).days + 1,
            page=page,
            page_size=page_size,
            provider=self.name,
            aoi=aoi,
            date_range=(start_date, end_date),
        )

    def get_observation(
        self,
        scene: GeoScene,
        aoi: AOI,
    ) -> GeoObservation:
        return GeoObservation(
            observation_id=f"{scene.scene_id}_{aoi.name}",
            scene=scene,
            aoi=aoi,
            confidence=0.5,
            integrity_state=GeoIntegrityState.DATA_AVAILABLE,
            notes=(
                "GIBS browse tile — NOT analysis-ready data.",
                "Resolution is approximate. No atmospheric correction.",
            ),
        )

    def _build_tile_url(
        self, dataset: str, aoi: AOI, date: datetime
    ) -> str:
        bbox = aoi.bbox
        date_str = date.strftime("%Y-%m-%d")
        return (
            f"{self._base_url}/wmts/epsg4326/best/"
            f"{dataset}/GoogleMapsCompatible_Level9/"
            f"{date_str}/default/GoogleMapsCompatible/512/512.jpg"
            f"?TIME={date_str}"
            f"&BBOX={bbox.south},{bbox.west},{bbox.north},{bbox.east}"
        )
