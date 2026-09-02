"""Change detection — compare observations across acquisition dates.

Avoids presenting modeled/inferred changes as confirmed physical facts.
Every change result includes confidence, methodology, and uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from aurora.geo.domain import (
    AOI,
    GeoChange,
    GeoChangeType,
    GeoIntegrityState,
    GeoObservation,
)
from aurora.geo.features.indices import (
    compute_ndvi,
    compute_ndwi,
    compute_ndbi,
    DerivedFeature,
)


@dataclass(frozen=True)
class ChangeDetectionResult:
    change: GeoChange | None
    integrity_state: GeoIntegrityState
    error: str = ""


def detect_change(
    before: GeoObservation,
    after: GeoObservation,
    feature: DerivedFeature = DerivedFeature.NDVI,
    threshold: float = 0.1,
) -> ChangeDetectionResult:
    """Compare two observations for change in a derived feature.

    METHODOLOGY: Pixel-level index difference.
    CONFIDENCE: Based on cloud cover and temporal gap.
    UNCERTAINTY: Change detection is inherently uncertain.
    """
    if before.aoi.name != after.aoi.name:
        return ChangeDetectionResult(
            change=None,
            integrity_state=GeoIntegrityState.PROCESSING_FAILED,
            error=f"AOI mismatch: '{before.aoi.name}' vs '{after.aoi.name}'",
        )

    aoi = before.aoi

    if feature == DerivedFeature.NDVI:
        idx_before = compute_ndvi(before)
        idx_after = compute_ndvi(after)
    elif feature == DerivedFeature.NDWI:
        idx_before = compute_ndwi(before)
        idx_after = compute_ndwi(after)
    elif feature == DerivedFeature.NDBI:
        idx_before = compute_ndbi(before)
        idx_after = compute_ndbi(after)
    else:
        return ChangeDetectionResult(
            change=None,
            integrity_state=GeoIntegrityState.PROCESSING_FAILED,
            error=f"Unsupported feature for change detection: {feature}",
        )

    if not idx_before.supported or not idx_after.supported:
        return ChangeDetectionResult(
            change=None,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            error=f"Feature not supported: before={idx_before.error}, after={idx_after.error}",
        )

    delta = idx_after.value - idx_before.value

    if abs(delta) < threshold:
        change_type = GeoChangeType.NO_CHANGE
    elif delta > 0:
        change_type = GeoChangeType.INCREASE
    else:
        change_type = GeoChangeType.DECREASE

    temporal_gap_days = abs(
        (after.acquisition_timestamp - before.acquisition_timestamp).total_seconds() / 86400
    )

    cloud_penalty = (
        before.scene.cloud_info.cloud_pct + after.scene.cloud_info.cloud_pct
    ) / 200.0
    temporal_penalty = min(0.3, temporal_gap_days / 365.0 * 0.1)
    confidence = max(0.0, 1.0 - cloud_penalty * 0.6 - temporal_penalty)

    if confidence < 0.3:
        integrity = GeoIntegrityState.LOW_CONFIDENCE
    elif cloud_penalty > 0.5:
        integrity = GeoIntegrityState.LOW_CONFIDENCE
    else:
        integrity = GeoIntegrityState.DATA_AVAILABLE

    change = GeoChange(
        change_id=f"change_{before.observation_id}_{after.observation_id}_{feature.value}",
        aoi=aoi,
        before=before,
        after=after,
        change_type=change_type,
        changed_area_km2=0.0,
        unchanged_area_km2=aoi.area_km2,
        magnitude=abs(delta),
        spatial_extent_pct=0.0,
        confidence=confidence,
        methodology=f"index_difference_{feature.value}",
        methodology_version="1.0",
        integrity_state=integrity,
        derived_feature=feature.value,
        uncertainty=(
            f"Change detection based on single-date comparison. "
            f"Temporal gap: {temporal_gap_days:.0f} days. "
            f"May be seasonal or noise. Requires validation."
        ),
        notes=(
            f"Before {feature.value}: {idx_before.value:.4f}",
            f"After {feature.value}: {idx_after.value:.4f}",
            f"Δ: {delta:+.4f}",
        ),
    )

    return ChangeDetectionResult(
        change=change,
        integrity_state=integrity,
    )
