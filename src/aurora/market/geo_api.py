"""Geo API endpoints — geospatial research layer.

REST endpoints for satellite catalog search, observations, change detection.
NO_DEPLOYMENT_SIGNAL. No predictions. No targeting. Research evidence only.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

_start_time = time.monotonic()


def _get_cors_origins() -> list[str]:
    raw = os.environ.get("AURORA_CORS_ORIGINS", "https://aurora-core.vercel.app")
    return [o.strip() for o in raw.split(",") if o.strip()]


geo_app = FastAPI(
    title="AURORA GEO — Earth Observation Research API",
    description="Geospatial research evidence. No predictions. No targeting.",
    version="0.1.0",
)

geo_app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Health ──

@geo_app.get("/api/v1/geo/health")
def geo_health() -> dict:
    from aurora.geo.providers.base import create_default_registry

    registry = create_default_registry()
    providers = {}
    for name in registry.list_providers():
        caps = registry.list_all_capabilities().get(name)
        providers[name] = {
            "available": True,
            "open_data": caps.is_open_data if caps else False,
            "requires_key": caps.requires_api_key if caps else False,
            "datasets": len(caps.datasets) if caps else 0,
        }

    return {
        "status": "healthy",
        "service": "aurora-geo",
        "version": "0.1.0",
        "research_conclusion": "NO_DEPLOYMENT_SIGNAL",
        "providers": providers,
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
    }


# ── Providers ──

@geo_app.get("/api/v1/geo/providers")
def list_providers() -> dict:
    from aurora.geo.providers.base import create_default_registry

    registry = create_default_registry()
    caps = registry.list_all_capabilities()

    providers = []
    for name, capability in caps.items():
        providers.append({
            "name": capability.provider,
            "is_open_data": capability.is_open_data,
            "requires_api_key": capability.requires_api_key,
            "max_aoi_km2": capability.max_aoi_km2,
            "supported_formats": capability.supported_formats,
            "rate_limit_per_minute": capability.rate_limit_per_minute,
            "provenance_url": capability.provenance_url,
            "dataset_count": len(capability.datasets),
        })

    return {
        "providers": providers,
        "count": len(providers),
    }


# ── Datasets ──

@geo_app.get("/api/v1/geo/datasets")
def list_datasets(provider: str = "") -> dict:
    from aurora.geo.providers.base import create_default_registry

    registry = create_default_registry()
    caps = registry.list_all_capabilities()

    datasets = []
    for name, capability in caps.items():
        if provider and name != provider:
            continue
        for ds in capability.datasets:
            datasets.append({
                "provider": name,
                "dataset_id": ds.dataset_id,
                "name": ds.name,
                "description": ds.description,
                "resolution_m": ds.resolution_m,
                "temporal_resolution_hours": ds.temporal_resolution_hours,
                "bands": ds.bands,
                "cloud_cover_max_pct": ds.cloud_cover_max_pct,
            })

    return {
        "datasets": datasets,
        "count": len(datasets),
    }


# ── Search ──

@geo_app.post("/api/v1/geo/search")
def search_scenes(body: dict) -> dict:
    """Search for satellite scenes matching an AOI and date range."""
    from pydantic import BaseModel, Field
    from aurora.geo.domain import AOI, BoundingBox

    class SearchRequest(BaseModel):
        aoi_name: str = "default"
        south: float = Field(..., ge=-90, le=90)
        west: float = Field(..., ge=-180, le=180)
        north: float = Field(..., ge=-90, le=90)
        east: float = Field(..., ge=-180, le=180)
        start_date: str
        end_date: str
        provider: str = ""
        dataset: str = ""
        max_cloud_pct: float = 30.0
        resolution_m: float = 0.0
        page: int = 1
        page_size: int = 20

    try:
        req = SearchRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        start_dt = datetime.fromisoformat(req.start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(req.end_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use ISO 8601.")

    bbox = BoundingBox(south=req.south, west=req.west, north=req.north, east=req.east)
    aoi = AOI(name=req.aoi_name, bbox=bbox)

    from aurora.geo.providers.base import create_default_registry

    registry = create_default_registry()

    if req.provider:
        provider = registry.get(req.provider)
        if not provider:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{req.provider}' not found. Available: {registry.list_providers()}",
            )
        providers_to_search = [provider]
    else:
        providers_to_search = [registry.get(n) for n in registry.list_providers()]
        providers_to_search = [p for p in providers_to_search if p is not None]

    all_scenes: list[dict] = []
    total = 0

    for prov in providers_to_search:
        result = prov.search_scenes(
            aoi=aoi,
            start_date=start_dt,
            end_date=end_dt,
            dataset=req.dataset,
            max_cloud_pct=req.max_cloud_pct,
            resolution_m=req.resolution_m,
            page=req.page,
            page_size=req.page_size,
        )
        for scene in result.scenes:
            all_scenes.append({
                "scene_id": scene.scene_id,
                "provider": scene.provider,
                "dataset": scene.dataset,
                "acquisition_time": scene.acquisition_time.isoformat(),
                "cloud_pct": scene.cloud_info.cloud_pct,
                "resolution_m": scene.resolution_m,
                "bands": scene.bands,
                "quality_grade": scene.quality.grade.value,
                "thumbnail_url": scene.thumbnail_url,
                "metadata_url": scene.metadata_url,
                "provenance": {
                    "provider": scene.provenance.provider if scene.provenance else "",
                    "dataset": scene.provenance.dataset if scene.provenance else "",
                    "source_url": scene.provenance.source_url if scene.provenance else "",
                } if scene.provenance else None,
            })
        total += result.total_count

    return {
        "scenes": all_scenes,
        "total_count": total,
        "page": req.page,
        "page_size": req.page_size,
        "aoi": {
            "name": aoi.name,
            "south": bbox.south,
            "west": bbox.west,
            "north": bbox.north,
            "east": bbox.east,
            "area_km2": round(aoi.area_km2, 2),
        },
        "date_range": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
        },
    }


# ── Observations ──

@geo_app.post("/api/v1/geo/observations")
def get_observations(body: dict) -> dict:
    """Get observations for a scene and AOI."""
    from pydantic import BaseModel, Field
    from aurora.geo.domain import AOI, BoundingBox

    class ObservationRequest(BaseModel):
        scene_id: str
        provider: str
        dataset: str = ""
        aoi_name: str = "default"
        south: float = Field(..., ge=-90, le=90)
        west: float = Field(..., ge=-180, le=180)
        north: float = Field(..., ge=-90, le=90)
        east: float = Field(..., ge=-180, le=180)
        acquisition_time: str

    try:
        req = ObservationRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    from aurora.geo.providers.base import create_default_registry
    from aurora.geo.domain import GeoScene, GeoProvenance, CloudInfo, GeoQualityReport, GeoQualityGrade

    registry = create_default_registry()
    provider = registry.get(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    bbox = BoundingBox(south=req.south, west=req.west, north=req.north, east=req.east)
    aoi = AOI(name=req.aoi_name, bbox=bbox)

    try:
        acq_time = datetime.fromisoformat(req.acquisition_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid acquisition_time format")

    scene = GeoScene(
        scene_id=req.scene_id,
        provider=req.provider,
        dataset=req.dataset,
        acquisition_time=acq_time,
        bbox=bbox,
        cloud_info=CloudInfo(),
        resolution_m=10.0,
        bands=(),
        quality=GeoQualityReport(grade=GeoQualityGrade.GOOD),
        provenance=GeoProvenance(
            provider=req.provider,
            dataset=req.dataset,
            acquisition_time=acq_time,
        ),
    )

    observation = provider.get_observation(scene, aoi)

    return {
        "observation_id": observation.observation_id,
        "source": observation.source,
        "acquisition_time": observation.acquisition_timestamp.isoformat(),
        "confidence": observation.confidence,
        "integrity_state": observation.integrity_state.value,
        "bands": observation.scene.bands,
        "resolution_m": observation.scene.resolution_m,
        "cloud_pct": observation.scene.cloud_info.cloud_pct,
        "processing_chain": observation.processing_chain,
        "notes": observation.notes,
        "uncertainty": observation.uncertainty,
        "provenance": {
            "provider": observation.scene.provenance.provider if observation.scene.provenance else "",
            "dataset": observation.scene.provenance.dataset if observation.scene.provenance else "",
            "processing_method": observation.scene.provenance.processing_method if observation.scene.provenance else "",
            "source_url": observation.scene.provenance.source_url if observation.scene.provenance else "",
            "spatial_resolution_m": observation.scene.provenance.spatial_resolution_m if observation.scene.provenance else 0,
            "uncertainty": observation.scene.provenance.uncertainty if observation.scene.provenance else "",
        } if observation.scene.provenance else None,
    }


# ── Change Detection ──

@geo_app.post("/api/v1/geo/change-detection")
def detect_change(body: dict) -> dict:
    """Detect change between two observations."""
    from pydantic import BaseModel, Field
    from aurora.geo.domain import AOI, BoundingBox, GeoScene, CloudInfo, GeoQualityReport, GeoQualityGrade, GeoProvenance
    from aurora.geo.features.indices import DerivedFeature
    from aurora.geo.analysis.change import detect_change

    class ChangeRequest(BaseModel):
        aoi_name: str = "default"
        south: float = Field(..., ge=-90, le=90)
        west: float = Field(..., ge=-180, le=180)
        north: float = Field(..., ge=-90, le=90)
        east: float = Field(..., ge=-180, le=180)
        provider: str
        dataset: str = ""
        before_time: str
        after_time: str
        before_bands: list[str] = Field(default_factory=lambda: ["B03", "B04", "B08"])
        after_bands: list[str] = Field(default_factory=lambda: ["B03", "B04", "B08"])
        before_values: dict[str, float] = Field(default_factory=dict)
        after_values: dict[str, float] = Field(default_factory=dict)
        feature: str = "NDVI"
        threshold: float = 0.1

    try:
        req = ChangeRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    bbox = BoundingBox(south=req.south, west=req.west, north=req.north, east=req.east)
    aoi = AOI(name=req.aoi_name, bbox=bbox)

    try:
        before_dt = datetime.fromisoformat(req.before_time.replace("Z", "+00:00"))
        after_dt = datetime.fromisoformat(req.after_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format")

    feature_enum = DerivedFeature(req.feature)

    before_scene = GeoScene(
        scene_id=f"before_{req.aoi_name}",
        provider=req.provider,
        dataset=req.dataset,
        acquisition_time=before_dt,
        bbox=bbox,
        bands=tuple(req.before_bands),
        quality=GeoQualityReport(grade=GeoQualityGrade.GOOD),
        provenance=GeoProvenance(provider=req.provider, dataset=req.dataset, acquisition_time=before_dt),
    )
    after_scene = GeoScene(
        scene_id=f"after_{req.aoi_name}",
        provider=req.provider,
        dataset=req.dataset,
        acquisition_time=after_dt,
        bbox=bbox,
        bands=tuple(req.after_bands),
        quality=GeoQualityReport(grade=GeoQualityGrade.GOOD),
        provenance=GeoProvenance(provider=req.provider, dataset=req.dataset, acquisition_time=after_dt),
    )

    from aurora.geo.domain import GeoObservation

    before_obs = GeoObservation(
        observation_id=f"obs_before_{req.aoi_name}",
        scene=before_scene,
        aoi=aoi,
        derived_values=req.before_values,
        confidence=0.9,
    )
    after_obs = GeoObservation(
        observation_id=f"obs_after_{req.aoi_name}",
        scene=after_scene,
        aoi=aoi,
        derived_values=req.after_values,
        confidence=0.9,
    )

    result = detect_change(before_obs, after_obs, feature=feature_enum, threshold=req.threshold)

    if result.change is None:
        return {
            "change_detected": False,
            "integrity_state": result.integrity_state.value,
            "error": result.error,
        }

    c = result.change
    return {
        "change_detected": c.change_type.value != "no_change",
        "change_id": c.change_id,
        "change_type": c.change_type.value,
        "feature": c.derived_feature,
        "magnitude": c.magnitude,
        "confidence": c.confidence,
        "integrity_state": c.integrity_state.value,
        "methodology": c.methodology,
        "methodology_version": c.methodology_version,
        "before_date": c.before.acquisition_timestamp.isoformat(),
        "after_date": c.after.acquisition_timestamp.isoformat(),
        "uncertainty": c.uncertainty,
        "notes": c.notes,
    }
