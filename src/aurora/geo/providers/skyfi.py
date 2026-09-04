"""SkyFi provider — optional commercial satellite imagery.

Requires SKYFI_API_KEY environment variable.
Optional: not required for the core system to function.
Uses SkyFi REST API specification.
"""

from __future__ import annotations

import json
import os
import urllib.request
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

_SKYFI_DATASETS = {
    "skyfi_analytics": GeoDatasetInfo(
        dataset_id="skyfi_analytics",
        name="SkyFi Analytics",
        description="High-resolution commercial satellite imagery via SkyFi",
        resolution_m=0.5,
        temporal_resolution_hours=24.0,
        bands=("Red", "Green", "Blue", "NIR"),
        cloud_cover_max_pct=20.0,
    ),
}


class SkyFiProvider(GeoProvider):
    """SkyFi commercial satellite imagery provider.

    REQUIRES: SKYFI_API_KEY environment variable.
    This provider is OPTIONAL — core system works without it.
    """

    def __init__(self) -> None:
        self._api_key = os.environ.get("SKYFI_API_KEY", "")
        self._base_url = "https://api.skyfi.com/v1"

    @property
    def name(self) -> str:
        return "skyfi"

    @property
    def is_open_data(self) -> bool:
        return False

    def _has_key(self) -> bool:
        return bool(self._api_key)

    def get_capabilities(self) -> GeoProviderCapabilities:
        return GeoProviderCapabilities(
            provider=self.name,
            datasets=tuple(_SKYFI_DATASETS.values()),
            supported_formats=("GeoTIFF", "JPEG"),
            max_aoi_km2=1000.0,
            requires_api_key=True,
            is_open_data=False,
            rate_limit_per_minute=30,
            provenance_url="https://skyfi.com/",
        )

    def search_scenes(
        self,
        aoi: AOI,
        start_date: datetime,
        end_date: datetime,
        dataset: str = "skyfi_analytics",
        max_cloud_pct: float = 20.0,
        resolution_m: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GeoSearchResult:
        if not self._has_key():
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error="SKYFI_API_KEY environment variable not set. SkyFi is an optional provider.",
            )

        bbox = aoi.bbox
        payload = {
            "bbox": [bbox.west, bbox.south, bbox.east, bbox.north],
            "from_date": start_date.strftime("%Y-%m-%d"),
            "to_date": end_date.strftime("%Y-%m-%d"),
            "max_cloud_cover": max_cloud_pct,
            "page": page,
            "page_size": page_size,
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self._base_url}/scenes/search",
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            return GeoSearchResult(
                provider=self.name,
                aoi=aoi,
                date_range=(start_date, end_date),
                integrity_state=GeoIntegrityState.PROVIDER_ERROR,
                error=f"SkyFi API request failed: {exc}",
            )

        scenes_list = data.get("scenes", [])
        scenes: list[GeoScene] = []
        for s in scenes_list:
            try:
                acq = datetime.fromisoformat(
                    s.get("acquisition_date", "").replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                acq = start_date

            scene = GeoScene(
                scene_id=s.get("id", ""),
                provider=self.name,
                dataset=dataset,
                acquisition_time=acq,
                bbox=aoi.bbox,
                cloud_info=CloudInfo(cloud_pct=s.get("cloud_cover", 0)),
                resolution_m=s.get("resolution_m", 0.5),
                bands=_SKYFI_DATASETS.get(dataset, _SKYFI_DATASETS["skyfi_analytics"]).bands,
                quality=GeoQualityReport(
                    grade=GeoQualityGrade.GOOD
                    if s.get("cloud_cover", 100) < 10
                    else GeoQualityGrade.PARTIAL,
                    cloud_info=CloudInfo(cloud_pct=s.get("cloud_cover", 0)),
                ),
                provenance=GeoProvenance(
                    provider=self.name,
                    dataset=dataset,
                    acquisition_time=acq,
                    processing_method="raw",
                    source_url=s.get("download_url", ""),
                    spatial_resolution_m=s.get("resolution_m", 0.5),
                ),
                thumbnail_url=s.get("thumbnail_url", ""),
                download_url=s.get("download_url", ""),
            )
            scenes.append(scene)

        return GeoSearchResult(
            scenes=tuple(scenes),
            total_count=data.get("total_count", len(scenes)),
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
            if scene.cloud_info.cloud_pct < 50
            else GeoIntegrityState.LOW_CONFIDENCE,
            notes=(
                "SkyFi commercial imagery — requires valid subscription for download.",
                f"Cloud cover: {scene.cloud_info.cloud_pct:.1f}%",
            ),
        )
