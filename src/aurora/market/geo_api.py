"""Geo API endpoints — geospatial research layer.

REST endpoints for satellite catalog search, observations, change detection.
NO_DEPLOYMENT_SIGNAL. No predictions. No targeting. Research evidence only.
"""

from __future__ import annotations

import os
import time
from datetime import datetime

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

    from aurora.geo.domain import (
        CloudInfo,
        GeoProvenance,
        GeoQualityGrade,
        GeoQualityReport,
        GeoScene,
    )
    from aurora.geo.providers.base import create_default_registry

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

    from aurora.geo.domain import AOI, BoundingBox
    from aurora.geo.features.index_engine import compute_index as compute_pixel_index

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
        index: str = "NDVI"
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

    provider = registry.get(req.provider)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{req.provider}' not found")

    before_raster = None
    after_raster = None
    before_tile_url = None
    after_tile_url = None

    if hasattr(provider, 'download_tile'):
        before_raster = provider.download_tile(req.dataset, aoi, before_dt)
        after_raster = provider.download_tile(req.dataset, aoi, after_dt)
        if before_raster:
            before_tile_url = provider._build_tile_url(req.dataset, aoi, before_dt)
        if after_raster:
            after_tile_url = provider._build_tile_url(req.dataset, aoi, after_dt)

    if before_raster is None or after_raster is None:
        missing = []
        if before_raster is None: missing.append("before")
        if after_raster is None: missing.append("after")
        return {
            "change_detected": False,
            "integrity_state": "DATA_UNAVAILABLE",
            "error": f"Could not download raster tiles for {', '.join(missing)} date(s)",
            "baseline_scene": {"date": before_dt.isoformat(), "tile_url": before_tile_url},
            "comparison_scene": {"date": after_dt.isoformat(), "tile_url": after_tile_url},
        }

    try:
        before_idx = compute_pixel_index(before_raster, req.index, dataset=req.dataset)
        after_idx = compute_pixel_index(after_raster, req.index, dataset=req.dataset)
    except Exception as exc:
        return {
            "change_detected": False,
            "integrity_state": "PROCESSING_FAILED",
            "error": f"Index computation failed: {exc}",
        }

    if not before_idx.supported or not after_idx.supported:
        errors = []
        if not before_idx.supported: errors.append(f"before: {before_idx.error}")
        if not after_idx.supported: errors.append(f"after: {after_idx.error}")
        return {
            "change_detected": False,
            "integrity_state": "DATA_UNAVAILABLE",
            "error": f"Required spectral bands unavailable. {'; '.join(errors)}",
            "baseline_scene": {
                "date": before_dt.isoformat(),
                "index": req.index,
                "supported": before_idx.supported,
                "integrity_state": before_idx.integrity_state.value,
                "error": before_idx.error,
                "tile_url": before_tile_url,
            },
            "comparison_scene": {
                "date": after_dt.isoformat(),
                "index": req.index,
                "supported": after_idx.supported,
                "integrity_state": after_idx.integrity_state.value,
                "error": after_idx.error,
                "tile_url": after_tile_url,
            },
        }

    import numpy as np
    diff = after_idx.data - before_idx.data
    valid_diff = diff[~np.isnan(diff)]
    magnitude = float(np.mean(np.abs(valid_diff))) if len(valid_diff) > 0 else 0.0
    change_detected = magnitude > req.threshold

    affected_pixels = int(np.sum(np.abs(valid_diff) > req.threshold)) if len(valid_diff) > 0 else 0
    total_valid = int(np.sum(~np.isnan(diff)))
    affected_area_pct = round(affected_pixels / total_valid * 100, 2) if total_valid > 0 else 0.0

    return {
        "change_detected": change_detected,
        "integrity_state": "DATA_AVAILABLE" if change_detected else "NO_CHANGE",
        "index": req.index,
        "baseline_scene": {
            "date": before_dt.isoformat(),
            "tile_url": before_tile_url,
            "mean": round(float(before_idx.mean), 4),
            "std": round(float(before_idx.std), 4),
            "valid_count": before_idx.valid_count,
        },
        "comparison_scene": {
            "date": after_dt.isoformat(),
            "tile_url": after_tile_url,
            "mean": round(float(after_idx.mean), 4),
            "std": round(float(after_idx.std), 4),
            "valid_count": after_idx.valid_count,
        },
        "change_statistics": {
            "magnitude": round(magnitude, 4),
            "threshold": req.threshold,
            "affected_area_pct": affected_area_pct,
            "affected_pixels": affected_pixels,
            "total_valid_pixels": total_valid,
        },
        "methodology": f"Pixel-wise {req.index} difference on real raster tiles",
        "uncertainty": (
            "GIBS provides RGB visualization imagery only. "
            "Scientific change detection requires NIR/SWIR bands. "
            "Change computed on visualization channels, not scientific spectral data."
            if not before_idx.supported else
            "Change computed from real raster tiles with valid spectral bands."
        ),
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

    from aurora.geo.features.index_engine import compute_index as compute_pixel_index

    observations = []
    for scene in search_result.scenes[:30]:
        raster_scene = None
        if hasattr(provider, 'download_tile'):
            raster_scene = provider.download_tile(req.dataset, aoi, scene.acquisition_time)

        if raster_scene is not None:
            try:
                idx_result = compute_pixel_index(raster_scene, req.index, dataset=req.dataset)
                obs_value = round(float(idx_result.mean), 4) if idx_result.supported else None
                obs_state = idx_result.integrity_state.value
                obs_methodology = f"Per-pixel {req.index} from raster bands: {', '.join(idx_result.source_bands)}"
                obs_bands_used = list(idx_result.source_bands)
                obs_formula = idx_result.formula
                obs_error = idx_result.error
            except Exception as exc:
                obs_value = None
                obs_state = "PROCESSING_FAILED"
                obs_methodology = f"Index computation failed: {exc}"
                obs_bands_used = []
                obs_formula = ""
                obs_error = str(exc)
        else:
            obs_value = None
            obs_state = "DATA_UNAVAILABLE"
            obs_methodology = "Tile download failed or unavailable"
            obs_bands_used = []
            obs_formula = ""
            obs_error = "Could not download raster tile"

        observations.append({
            "date": scene.acquisition_time.isoformat(),
            "scene_id": scene.scene_id,
            "product_id": getattr(scene, 'product_id', scene.scene_id),
            "index": req.index,
            "value": obs_value,
            "integrity_state": obs_state,
            "resolution_m": scene.resolution_m,
            "bands_used": obs_bands_used,
            "formula": obs_formula,
            "methodology": obs_methodology,
            "quality": scene.quality_grade,
            "cloud_pct": scene.cloud_info.cloud_pct,
            "error": obs_error,
            "uncertainty": (
                "GIBS provides RGB visualization imagery only. "
                "Scientific spectral indices (NDVI/NDWI/NDBI/EVI) require Near-Infrared or "
                "Short-Wave Infrared bands which are not available in true-color composites."
                if obs_state == "DATA_UNAVAILABLE" and "NIR" in (obs_error or "") else ""
            ),
        })

    observations.sort(key=lambda x: x["date"])

    valid_values = [o["value"] for o in observations if o["value"] is not None]
    stats = {}
    if valid_values:
        import statistics
        stats = {
            "count": len(valid_values),
            "mean": round(statistics.mean(valid_values), 4),
            "median": round(statistics.median(valid_values), 4),
            "stdev": round(statistics.stdev(valid_values), 4) if len(valid_values) > 1 else 0.0,
            "min": round(min(valid_values), 4),
            "max": round(max(valid_values), 4),
        }

    return {
        "index": req.index,
        "provider": req.provider,
        "dataset": req.dataset,
        "aoi_name": req.aoi_name,
        "start_date": start_dt.isoformat(),
        "end_date": end_dt.isoformat(),
        "observations": observations,
        "missing_dates": [],
        "statistics": stats,
        "total_scenes_found": search_result.total_count,
        "integrity_state": search_result.integrity_state.value if search_result.integrity_state else "DATA_AVAILABLE",
        "uncertainty": (
            "Time series computed from real raster tiles. "
            "GIBS provides RGB visualization imagery only. "
            "Scientific spectral indices require NIR/SWIR bands unavailable in true-color composites. "
            "Valid values: None. All observations are DATA_UNAVAILABLE for scientific indices."
            if not valid_values else
            "Time series computed from real raster tiles with valid spectral bands."
        ),
        "provenance": {
            "provider": req.provider,
            "dataset": req.dataset,
            "index": req.index,
            "methodology": f"Per-pixel {req.index} from raster data",
            "source": "gibs.earthdata.nasa.gov" if req.provider == "nasa_gibs" else req.provider,
            "is_demo": req.provider == "nasa_gibs",
        },
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
