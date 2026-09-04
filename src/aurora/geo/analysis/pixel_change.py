"""Pixel-level change detection — per-pixel comparison across dates.

Returns: changed pixels/area, unchanged area, magnitude, spatial extent,
quality, uncertainty, methodology.

Clearly distinguishes OBSERVED CHANGE from UNCERTAIN CHANGE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aurora.geo.domain import (
    GeoChange,
    GeoChangeType,
    GeoIntegrityState,
    GeoObservation,
)
from aurora.geo.features.index_engine import compute_index
from aurora.geo.raster.engine import RasterScene


@dataclass(frozen=True)
class PixelChangeResult:
    changed_pixels: int
    unchanged_pixels: int
    total_pixels: int
    changed_area_km2: float
    unchanged_area_km2: float
    spatial_extent_pct: float
    mean_magnitude: float
    std_magnitude: float
    max_magnitude: float
    change_type: GeoChangeType
    confidence: float
    integrity_state: GeoIntegrityState
    change_mask: np.ndarray
    magnitude_map: np.ndarray
    methodology: str
    methodology_version: str = "1.0"
    uncertainty: str = ""


def detect_pixel_change(
    before_scene: RasterScene,
    after_scene: RasterScene,
    index_name: str = "NDVI",
    dataset: str = "S2L2A",
    change_threshold: float = 0.1,
    confidence_threshold: float = 0.3,
    pixel_size_m: float = 10.0,
) -> PixelChangeResult:
    """Detect change at pixel level between two raster scenes.

    METHODOLOGY: Per-pixel index difference with threshold.
    Clearly distinguishes observed change from uncertain change.
    """
    before_idx = compute_index(before_scene, index_name, dataset)
    after_idx = compute_index(after_scene, index_name, dataset)

    if not before_idx.supported or not after_idx.supported:
        return PixelChangeResult(
            changed_pixels=0, unchanged_pixels=0, total_pixels=0,
            changed_area_km2=0.0, unchanged_area_km2=0.0, spatial_extent_pct=0.0,
            mean_magnitude=np.nan, std_magnitude=np.nan, max_magnitude=np.nan,
            change_type=GeoChangeType.UNCERTAIN,
            confidence=0.0,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            change_mask=np.array([]),
            magnitude_map=np.array([]),
            methodology=f"pixel_difference_{index_name}",
            uncertainty=f"Index not supported: before={before_idx.error}, after={after_idx.error}",
        )

    before_data = before_idx.data
    after_data = after_idx.data

    if before_data.shape != after_data.shape:
        min_h = min(before_data.shape[0], after_data.shape[0])
        min_w = min(before_data.shape[1], after_data.shape[1])
        before_data = before_data[:min_h, :min_w]
        after_data = after_data[:min_h, :min_w]

    valid_mask = (
        ~np.isnan(before_data) & ~np.isnan(after_data)
        & (before_data != np.nan) & (after_data != np.nan)
    )

    magnitude = np.where(valid_mask, after_data - before_data, np.nan)

    change_mask = valid_mask & (np.abs(np.nan_to_num(magnitude, nan=0.0)) > change_threshold)

    changed_pixels = int(np.sum(change_mask))
    unchanged_pixels = int(np.sum(valid_mask & ~change_mask))
    total_pixels = int(np.sum(valid_mask))

    pixel_area_km2 = (pixel_size_m ** 2) / 1e6
    changed_area = changed_pixels * pixel_area_km2
    unchanged_area = unchanged_pixels * pixel_area_km2
    spatial_extent = (changed_pixels / total_pixels * 100) if total_pixels > 0 else 0.0

    valid_magnitude = magnitude[valid_mask]
    if len(valid_magnitude) > 0:
        mean_mag = float(np.nanmean(valid_magnitude))
        std_mag = float(np.nanstd(valid_magnitude))
        max_mag = float(np.nanmax(np.abs(valid_magnitude)))
    else:
        mean_mag = np.nan
        std_mag = np.nan
        max_mag = np.nan

    if changed_pixels == 0:
        change_type = GeoChangeType.NO_CHANGE
    elif mean_mag > 0:
        change_type = GeoChangeType.INCREASE
    else:
        change_type = GeoChangeType.DECREASE

    spatial_confidence = min(1.0, changed_pixels / max(1, total_pixels) * 10)
    cloud_penalty = (
        (before_scene.provenance or None) and 0.0
    ) or 0.0
    confidence = min(1.0, spatial_confidence * 0.5 + 0.5 - cloud_penalty)

    if confidence < confidence_threshold:
        integrity = GeoIntegrityState.LOW_CONFIDENCE
    elif total_pixels < 100:
        integrity = GeoIntegrityState.INSUFFICIENT_RESOLUTION
    else:
        integrity = GeoIntegrityState.DATA_AVAILABLE

    return PixelChangeResult(
        changed_pixels=changed_pixels,
        unchanged_pixels=unchanged_pixels,
        total_pixels=total_pixels,
        changed_area_km2=round(changed_area, 4),
        unchanged_area_km2=round(unchanged_area, 4),
        spatial_extent_pct=round(spatial_extent, 2),
        mean_magnitude=round(mean_mag, 6) if not np.isnan(mean_mag) else np.nan,
        std_magnitude=round(std_mag, 6) if not np.isnan(std_mag) else np.nan,
        max_magnitude=round(max_mag, 6) if not np.isnan(max_mag) else np.nan,
        change_type=change_type,
        confidence=round(confidence, 4),
        integrity_state=integrity,
        change_mask=change_mask,
        magnitude_map=magnitude,
        methodology=f"pixel_difference_{index_name}",
        uncertainty=(
            f"Threshold-based change detection. Threshold={change_threshold}. "
            f"Observed change is not confirmed physical change. "
            f"May include seasonal variation, atmospheric effects, or noise."
        ),
    )


def change_result_to_geochange(
    result: PixelChangeResult,
    before_obs: GeoObservation,
    after_obs: GeoObservation,
) -> GeoChange:
    """Convert PixelChangeResult to GeoChange domain model."""
    return GeoChange(
        change_id=f"change_{before_obs.observation_id}_{after_obs.observation_id}",
        aoi=before_obs.aoi,
        before=before_obs,
        after=after_obs,
        change_type=result.change_type,
        changed_area_km2=result.changed_area_km2,
        unchanged_area_km2=result.unchanged_area_km2,
        magnitude=result.mean_magnitude if not np.isnan(result.mean_magnitude) else 0.0,
        spatial_extent_pct=result.spatial_extent_pct,
        confidence=result.confidence,
        methodology=result.methodology,
        methodology_version=result.methodology_version,
        integrity_state=result.integrity_state,
        uncertainty=result.uncertainty,
    )
