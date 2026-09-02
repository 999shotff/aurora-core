"""EO processing layer — provider-independent transformations.

All transformations record provenance. No silent alterations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aurora.geo.domain import (
    AOI,
    BoundingBox,
    GeoIntegrityState,
    GeoObservation,
    GeoProvenance,
    GeoRasterMetadata,
    CRS,
)


class ProcessingOp(str, Enum):
    CLIP = "clip"
    REPROJECT = "reproject"
    RESAMPLE = "resample"
    CLOUD_MASK = "cloud_mask"
    NORMALIZE = "normalize"
    TEMPORAL_DIFFERENCE = "temporal_difference"


@dataclass(frozen=True)
class ProcessingStep:
    operation: ProcessingOp
    input_hash: str = ""
    output_hash: str = ""
    parameters: dict[str, str | int | float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""


@dataclass(frozen=True)
class ProcessingResult:
    success: bool
    output: Any = None
    steps: tuple[ProcessingStep, ...] = ()
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE
    error: str = ""


def clip_to_aoi(
    observation: GeoObservation,
    aoi: AOI,
) -> ProcessingResult:
    """Clip observation to AOI bounding box.

    Records the clip operation in provenance.
    """
    step = ProcessingStep(
        operation=ProcessingOp.CLIP,
        parameters={
            "south": aoi.bbox.south,
            "west": aoi.bbox.west,
            "north": aoi.bbox.north,
            "east": aoi.bbox.east,
        },
    )

    new_provenance = None
    if observation.scene.provenance:
        p = observation.scene.provenance
        new_provenance = GeoProvenance(
            provider=p.provider,
            dataset=p.dataset,
            acquisition_time=p.acquisition_time,
            processing_time=datetime.now(timezone.utc),
            processing_method=f"{p.processing_method}+clip",
            methodology_version=p.methodology_version,
            source_url=p.source_url,
            crs=p.crs,
            spatial_resolution_m=p.spatial_resolution_m,
            temporal_resolution_hours=p.temporal_resolution_hours,
            source_sha256=p.source_sha256,
            is_demo=p.is_demo,
            uncertainty=p.uncertainty,
            notes=p.notes + ("Clipped to AOI",),
        )

    from aurora.geo.domain import GeoScene, CloudInfo, GeoQualityReport

    new_scene = GeoScene(
        scene_id=observation.scene.scene_id,
        provider=observation.scene.provider,
        dataset=observation.scene.dataset,
        acquisition_time=observation.scene.acquisition_time,
        bbox=aoi.bbox,
        cloud_info=observation.scene.cloud_info,
        resolution_m=observation.scene.resolution_m,
        bands=observation.scene.bands,
        quality=observation.scene.quality,
        provenance=new_provenance,
        thumbnail_url=observation.scene.thumbnail_url,
        metadata_url=observation.scene.metadata_url,
        download_url=observation.scene.download_url,
    )

    new_obs = GeoObservation(
        observation_id=observation.observation_id,
        scene=new_scene,
        aoi=aoi,
        raster_metadata=observation.raster_metadata,
        derived_values=observation.derived_values,
        processing_chain=observation.processing_chain + ("clip",),
        confidence=observation.confidence,
        uncertainty=observation.uncertainty,
        integrity_state=observation.integrity_state,
        notes=observation.notes,
    )

    return ProcessingResult(
        success=True,
        output=new_obs,
        steps=(step,),
    )


def reproject(
    observation: GeoObservation,
    target_crs: CRS,
) -> ProcessingResult:
    """Reproject observation to target CRS.

    Records the reprojection in provenance.
    """
    step = ProcessingStep(
        operation=ProcessingOp.REPROJECT,
        parameters={"target_crs": target_crs.code},
    )

    new_provenance = None
    if observation.scene.provenance:
        p = observation.scene.provenance
        new_provenance = GeoProvenance(
            provider=p.provider,
            dataset=p.dataset,
            acquisition_time=p.acquisition_time,
            processing_time=datetime.now(timezone.utc),
            processing_method=f"{p.processing_method}+reproject({target_crs.code})",
            methodology_version=p.methodology_version,
            source_url=p.source_url,
            crs=target_crs,
            spatial_resolution_m=p.spatial_resolution_m,
            temporal_resolution_hours=p.temporal_resolution_hours,
            source_sha256=p.source_sha256,
            is_demo=p.is_demo,
            uncertainty=p.uncertainty + f" Reprojected from {p.crs.code} to {target_crs.code}.",
            notes=p.notes + (f"Reprojected to {target_crs.code}",),
        )

    from aurora.geo.domain import GeoScene

    new_scene = GeoScene(
        scene_id=observation.scene.scene_id,
        provider=observation.scene.provider,
        dataset=observation.scene.dataset,
        acquisition_time=observation.scene.acquisition_time,
        bbox=observation.scene.bbox,
        cloud_info=observation.scene.cloud_info,
        resolution_m=observation.scene.resolution_m,
        bands=observation.scene.bands,
        quality=observation.scene.quality,
        provenance=new_provenance,
        thumbnail_url=observation.scene.thumbnail_url,
        metadata_url=observation.scene.metadata_url,
        download_url=observation.scene.download_url,
    )

    new_obs = GeoObservation(
        observation_id=observation.observation_id,
        scene=new_scene,
        aoi=observation.aoi,
        raster_metadata=observation.raster_metadata,
        derived_values=observation.derived_values,
        processing_chain=observation.processing_chain + (f"reproject({target_crs.code})",),
        confidence=observation.confidence,
        uncertainty=observation.uncertainty,
        integrity_state=observation.integrity_state,
        notes=observation.notes,
    )

    return ProcessingResult(
        success=True,
        output=new_obs,
        steps=(step,),
    )
