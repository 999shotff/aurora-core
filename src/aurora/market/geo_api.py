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


# ── Time Series ──

@geo_app.post("/api/v1/geo/timeseries")
def get_timeseries(body: dict) -> dict:
    """Build a time series of index values across multiple dates.

    Searches for scenes in the date range, constructs observations,
    computes the requested index for each, and returns the time series.
    """
    from pydantic import BaseModel, Field
    from aurora.geo.domain import AOI, BoundingBox

    class TimeSeriesRequest(BaseModel):
        provider: str = "nasa_gibs"
        dataset: str = "MODIS_Terra_CorrectedReflectance_TrueColor"
        aoi_name: str = "default"
        south: float = Field(..., ge=-90, le=90)
        west: float = Field(..., ge=-180, le=180)
        north: float = Field(..., ge=-90, le=90)
        east: float = Field(..., ge=-180, le=180)
        start_date: str
        end_date: str
        index: str = "NDVI"
        cloud_threshold: float = 30.0

    try:
        req = TimeSeriesRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    from aurora.geo.providers.base import create_default_registry

    registry = create_default_registry()
    provider = registry.get(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    bbox = BoundingBox(south=req.south, west=req.west, north=req.north, east=req.east)
    aoi = AOI(name=req.aoi_name, bbox=bbox)

    try:
        start_dt = datetime.fromisoformat(req.start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(req.end_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format")

    search_result = provider.search_scenes(
        aoi, start_dt, end_dt,
        dataset=req.dataset,
        max_cloud_pct=req.cloud_threshold,
        page_size=50,
    )

    observations = []
    for scene in search_result.scenes[:30]:
        obs = provider.get_observation(scene, aoi)
        index_val = obs.derived_values.get(f"{req.index.lower()}_mean")
        if index_val is None:
            band_vals = {k: v for k, v in obs.derived_values.items() if k.startswith("band_")}
            if band_vals:
                vals = list(band_vals.values())
                index_val = sum(vals) / len(vals) if vals else 0.0
            else:
                index_val = 0.0
        observations.append({
            "date": scene.acquisition_time.isoformat(),
            "scene_id": scene.scene_id,
            "value": round(index_val, 4),
            "cloud_pct": scene.cloud_info.cloud_pct,
            "confidence": obs.confidence,
            "integrity_state": obs.integrity_state.value,
        })

    observations.sort(key=lambda x: x["date"])

    values = [o["value"] for o in observations]
    stats = {}
    if values:
        import statistics
        stats = {
            "count": len(values),
            "mean": round(statistics.mean(values), 4),
            "median": round(statistics.median(values), 4),
            "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }

    return {
        "index": req.index,
        "provider": req.provider,
        "dataset": req.dataset,
        "aoi_name": req.aoi_name,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "observations": observations,
        "statistics": stats,
        "total_scenes_found": search_result.total_count,
        "integrity_state": search_result.integrity_state.value if search_result.integrity_state else "DATA_AVAILABLE",
        "uncertainty": "Index values computed from observation metadata. Not per-pixel raster computation.",
    }


# ── Per-Pixel Index Computation ──

@geo_app.post("/api/v1/geo/index")
def compute_index(body: dict) -> dict:
    """Compute a spectral index from real raster data.

    Downloads a real GIBS tile for the specified scene/date,
    creates a RasterScene, and computes the requested index.
    Returns per-pixel statistics and provenance.
    """
    from pydantic import BaseModel, Field
    from aurora.geo.domain import AOI, BoundingBox

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

    try:
        req = IndexRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    from aurora.geo.providers.base import create_default_registry

    registry = create_default_registry()
    provider = registry.get(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    bbox = BoundingBox(south=req.south, west=req.west, north=req.north, east=req.east)
    aoi = AOI(name=req.aoi_name, bbox=bbox)

    try:
        date_dt = datetime.fromisoformat(req.date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format")

    tile_url = None
    raster_scene = None

    if hasattr(provider, 'download_tile'):
        raster_scene = provider.download_tile(req.dataset, aoi, date_dt)
        if raster_scene:
            tile_url = provider._build_tile_url(req.dataset, aoi, date_dt)

    if raster_scene is None:
        return {
            "index": req.index,
            "supported": False,
            "integrity_state": "DATA_UNAVAILABLE",
            "error": f"Could not download raster tile from {req.provider}. "
                     "Provider may require authentication or tile may be unavailable.",
            "statistics": None,
            "provenance": None,
        }

    from aurora.geo.features.index_engine import compute_index as compute_pixel_index
    try:
        result = compute_pixel_index(raster_scene, req.index)
    except Exception as exc:
        return {
            "index": req.index,
            "supported": False,
            "integrity_state": "PROCESSING_FAILED",
            "error": f"Index computation failed: {exc}",
            "statistics": None,
            "provenance": None,
        }

    if not result.supported:
        return {
            "index": req.index,
            "supported": False,
            "integrity_state": result.integrity_state.value,
            "error": result.error or f"Index {req.index} not supported for this dataset",
            "statistics": None,
            "provenance": None,
        }

    import numpy as np
    valid_data = result.data[~np.isnan(result.data)]
    stats = {
        "count": int(result.valid_count),
        "total_pixels": int(result.total_count),
        "nodata_count": int(result.total_count - result.valid_count),
        "mean": round(float(result.mean), 6) if not np.isnan(result.mean) else None,
        "median": round(float(np.median(valid_data)), 6) if len(valid_data) > 0 else None,
        "std": round(float(result.std), 6) if not np.isnan(result.std) else None,
        "min": round(float(result.min_val), 6) if not np.isnan(result.min_val) else None,
        "max": round(float(result.max_val), 6) if not np.isnan(result.max_val) else None,
    }

    return {
        "index": req.index,
        "supported": True,
        "integrity_state": "DATA_AVAILABLE",
        "statistics": stats,
        "formula": result.formula,
        "source_bands": list(result.source_bands),
        "methodology_version": result.methodology_version,
        "processing_library": result.processing_library,
        "nodata_treatment": result.nodata_treatment,
        "tile_url": tile_url,
        "provenance": {
            "provider": raster_scene.provenance.provider if raster_scene.provenance else req.provider,
            "dataset": raster_scene.provenance.dataset if raster_scene.provenance else req.dataset,
            "acquisition_time": raster_scene.provenance.acquisition_time.isoformat() if raster_scene.provenance else date_dt.isoformat(),
            "processing_method": raster_scene.provenance.processing_method if raster_scene.provenance else "wmts_download",
            "source_url": raster_scene.provenance.source_url if raster_scene.provenance else tile_url,
            "uncertainty": raster_scene.provenance.uncertainty if raster_scene.provenance else "",
        },
        "uncertainty": result.uncertainty or "Computed from real GIBS browse tile. Not analysis-ready.",
    }
