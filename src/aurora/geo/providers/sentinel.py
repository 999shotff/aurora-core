"""Copernicus / Sentinel provider — open-data satellite imagery.

Uses Copernicus Data Space Ecosystem (free tier).
No API key required for catalog search. Data access requires registration.
"""

from __future__ import annotations

from datetime import datetime

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

_SENTINEL_DATASETS = {
    "S2L2A": GeoDatasetInfo(
        dataset_id="S2L2A",
        name="Sentinel-2 Level-2A",
        description="Surface reflectance, 10-60m resolution, cloud-masked",
        resolution_m=10.0,
        temporal_resolution_hours=24.0,
        bands=("B02", "B03", "B04", "B08", "B11", "B12", "SCL"),
        cloud_cover_max_pct=100.0,
    ),
    "S2L1C": GeoDatasetInfo(
        dataset_id="S2L1C",
        name="Sentinel-2 Level-1C",
        description="Top-of-atmosphere reflectance, 10-60m",
        resolution_m=10.0,
        temporal_resolution_hours=24.0,
        bands=("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"),
        cloud_cover_max_pct=100.0,
    ),
    "S1GRD": GeoDatasetInfo(
        dataset_id="S1GRD",
        name="Sentinel-1 GRD",
        description="Synthetic Aperture Radar, all-weather",
        resolution_m=10.0,
        temporal_resolution_hours=24.0,
        bands=("VV", "VH"),
        cloud_cover_max_pct=100.0,
    ),
}


class SentinelProvider(GeoProvider):
    """Copernicus / Sentinel open-data provider.

    Uses Copernicus Data Space Ecosystem OData API for catalog search.
    No API key needed for search. Data download requires token.
    """

    def __init__(self) -> None:
        self._base_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"

    @property
    def name(self) -> str:
        return "copernicus_sentinel"

    @property
    def is_open_data(self) -> bool:
        return True

    def get_capabilities(self) -> GeoProviderCapabilities:
        return GeoProviderCapabilities(
            provider=self.name,
            datasets=tuple(_SENTINEL_DATASETS.values()),
            supported_formats=("GeoTIFF", "JPEG2000"),
            max_aoi_km2=10000.0,
            requires_api_key=False,
            is_open_data=True,
            rate_limit_per_minute=60,
            provenance_url="https://dataspace.copernicus.eu/",
        )

    def search_scenes(
        self,
        aoi: AOI,
        start_date: datetime,
        end_date: datetime,
        dataset: str = "S2L2A",
        max_cloud_pct: float = 30.0,
        resolution_m: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GeoSearchResult:
        if dataset not in _SENTINEL_DATASETS:
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error=f"Unknown dataset: {dataset}. Available: {list(_SENTINEL_DATASETS.keys())}",
            )

        bbox = aoi.bbox
        footprint = (
            f"POLYGON(({bbox.west} {bbox.south},{bbox.east} {bbox.south},"
            f"{bbox.east} {bbox.north},{bbox.west} {bbox.north},"
            f"{bbox.west} {bbox.south}))"
        )

        start_str = start_date.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59.999Z")

        odata_filter = (
            f"Collection/Name eq '{dataset}' "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') "
            f"and ContentDate/Start gt {start_str} "
            f"and ContentDate/Start lt {end_str} "
            f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
            f"and att/OData.CSC.DoubleAttribute/Value le {max_cloud_pct})"
        )

        import urllib.parse
        encoded_filter = urllib.parse.quote(odata_filter, safe="")

        url = (
            f"{self._base_url}/Products?$filter={encoded_filter}"
            f"&$orderby=ContentDate/Start desc"
            f"&$top={page_size}&$skip={(page - 1) * page_size}"
            f"&$expand=Attributes"
        )

        try:
            import json
            import urllib.request
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error=f"Request failed: {exc}",
            )

        products = data.get("value", [])
        scenes: list[GeoScene] = []

        for prod in products:
            attrs = {a["Name"]: a.get("Value", 0) for a in prod.get("Attributes", [])}
            cloud_pct = attrs.get("cloudCover", 0)
            ingestion_date = prod.get("ContentDate", {}).get("IngestionDate", "")

            try:
                acq_str = prod.get("ContentDate", {}).get("Start", "")
                acq_time = datetime.fromisoformat(acq_str.replace("Z", "+00:00")) if acq_str else start_date
            except (ValueError, TypeError):
                acq_time = start_date

            prod_id = prod.get("Id", "")
            prod_name = prod.get("Name", "")

            scene = GeoScene(
                scene_id=str(prod_id),
                provider=self.name,
                dataset=dataset,
                acquisition_time=acq_time,
                bbox=aoi.bbox,
                cloud_info=CloudInfo(cloud_pct=cloud_pct),
                resolution_m=_SENTINEL_DATASETS[dataset].resolution_m,
                bands=_SENTINEL_DATASETS[dataset].bands,
                quality=GeoQualityReport(
                    grade=GeoQualityGrade.GOOD if cloud_pct < 20 else GeoQualityGrade.PARTIAL,
                    cloud_info=CloudInfo(cloud_pct=cloud_pct),
                ),
                provenance=GeoProvenance(
                    provider=self.name,
                    dataset=dataset,
                    acquisition_time=acq_time,
                    processing_method="raw",
                    source_url=f"https://dataspace.copernicus.eu/odata/v1/Products({prod_id})",
                    spatial_resolution_m=_SENTINEL_DATASETS[dataset].resolution_m,
                ),
                metadata_url=f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({prod_id})",
            )
            scenes.append(scene)

        total = data.get("@odata.count", len(scenes))

        return GeoSearchResult(
            scenes=tuple(scenes),
            total_count=total,
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
            confidence=1.0 - (scene.cloud_info.cloud_pct / 100.0),
            integrity_state=GeoIntegrityState.DATA_AVAILABLE
            if scene.cloud_info.cloud_pct < 80
            else GeoIntegrityState.LOW_CONFIDENCE,
            notes=(f"Catalog observation — imagery not downloaded. Cloud: {scene.cloud_info.cloud_pct:.1f}%",),
        )
