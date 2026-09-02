"""Derived environmental features — research-grade indices.

Every derived feature explicitly states:
- SOURCE DATA
- PROCESSING METHOD
- FORMULA/METHOD VERSION
- TIME RANGE
- QUALITY
- UNCERTAINTY

Do not invent missing bands. Return unsupported if bands unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aurora.geo.domain import (
    GeoIntegrityState,
    GeoObservation,
    GeoTimeSeries,
    GeoTimeSeriesPoint,
    GeoProvenance,
)


class DerivedFeature(str, Enum):
    NDVI = "NDVI"
    NDWI = "NDWI"
    NDBI = "NDBI"
    VEGETATION_CHANGE = "vegetation_change"
    WATER_CHANGE = "water_change"
    BUILT_AREA_CHANGE = "built_area_change"
    TEMPORAL_ANOMALY = "temporal_anomaly"


@dataclass(frozen=True)
class FeatureResult:
    feature: DerivedFeature
    value: float
    unit: str = ""
    confidence: float = 0.0
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE
    source_bands: tuple[str, ...] = ()
    formula: str = ""
    methodology_version: str = "1.0"
    time_range: str = ""
    quality: str = ""
    uncertainty: str = ""
    supported: bool = True
    error: str = ""


def _get_band_values(
    observation: GeoObservation, band_name: str
) -> tuple[float, ...] | None:
    """Extract band values from observation derived_values."""
    key = f"band_{band_name}_mean"
    if key in observation.derived_values:
        return (observation.derived_values[key],)
    return None


def compute_ndvi(observation: GeoObservation) -> FeatureResult:
    """NDVI = (NIR - RED) / (NIR + RED)

    SOURCE DATA: Sentinel-2 B08 (NIR), B04 (RED)
    FORMULA: (B08 - B04) / (B08 + B04)
    METHODOLOGY VERSION: 1.0
    RANGE: [-1, 1]

    Requires bands B08 and B04. Returns unsupported if missing.
    """
    required = {"B08", "B04"}
    available = set(observation.scene.bands)

    if not required.issubset(available):
        missing = required - available
        return FeatureResult(
            feature=DerivedFeature.NDVI,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty=f"Missing required bands: {sorted(missing)}",
            error=f"NDVI requires {sorted(required)}, scene has {sorted(available)}",
        )

    nir_vals = _get_band_values(observation, "B08")
    red_vals = _get_band_values(observation, "B04")

    if nir_vals is None or red_vals is None:
        return FeatureResult(
            feature=DerivedFeature.NDVI,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty="Band values not available in observation derived_values",
            error="No band data in derived_values. Supply band_B08_mean and band_B04_mean.",
        )

    nir = nir_vals[0]
    red = red_vals[0]
    denominator = nir + red

    if abs(denominator) < 1e-10:
        return FeatureResult(
            feature=DerivedFeature.NDVI,
            value=0.0,
            confidence=0.0,
            uncertainty="Near-zero denominator — values may be unreliable",
        )

    ndvi = (nir - red) / denominator
    ndvi = max(-1.0, min(1.0, ndvi))

    cloud_penalty = observation.scene.cloud_info.cloud_pct / 100.0
    confidence = max(0.0, 1.0 - cloud_penalty * 0.8)

    return FeatureResult(
        feature=DerivedFeature.NDVI,
        value=ndvi,
        unit="index",
        confidence=confidence,
        source_bands=("B08", "B04"),
        formula="(B08 - B04) / (B08 + B04)",
        methodology_version="1.0",
        time_range=observation.acquisition_timestamp.isoformat(),
        quality=f"Cloud: {observation.scene.cloud_info.cloud_pct:.1f}%",
        uncertainty="Surface reflectance assumed. Atmospheric correction quality varies.",
    )


def compute_ndwi(observation: GeoObservation) -> FeatureResult:
    """NDWI = (GREEN - NIR) / (GREEN + NIR)

    SOURCE DATA: Sentinel-2 B03 (GREEN), B08 (NIR)
    FORMULA: (B03 - B08) / (B03 + B08)
    RANGE: [-1, 1]
    """
    required = {"B03", "B08"}
    available = set(observation.scene.bands)

    if not required.issubset(available):
        missing = required - available
        return FeatureResult(
            feature=DerivedFeature.NDWI,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty=f"Missing required bands: {sorted(missing)}",
            error=f"NDWI requires {sorted(required)}, scene has {sorted(available)}",
        )

    green_vals = _get_band_values(observation, "B03")
    nir_vals = _get_band_values(observation, "B08")

    if green_vals is None or nir_vals is None:
        return FeatureResult(
            feature=DerivedFeature.NDWI,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty="Band values not available in observation derived_values",
        )

    green = green_vals[0]
    nir = nir_vals[0]
    denom = green + nir

    if abs(denom) < 1e-10:
        return FeatureResult(
            feature=DerivedFeature.NDWI,
            value=0.0,
            confidence=0.0,
            uncertainty="Near-zero denominator",
        )

    ndwi = (green - nir) / denom
    ndwi = max(-1.0, min(1.0, ndwi))

    cloud_penalty = observation.scene.cloud_info.cloud_pct / 100.0
    confidence = max(0.0, 1.0 - cloud_penalty * 0.8)

    return FeatureResult(
        feature=DerivedFeature.NDWI,
        value=ndwi,
        unit="index",
        confidence=confidence,
        source_bands=("B03", "B08"),
        formula="(B03 - B08) / (B03 + B08)",
        methodology_version="1.0",
        time_range=observation.acquisition_timestamp.isoformat(),
        quality=f"Cloud: {observation.scene.cloud_info.cloud_pct:.1f}%",
        uncertainty="McFeeters (1996). Sensitive to built-up area false positives.",
    )


def compute_ndbi(observation: GeoObservation) -> FeatureResult:
    """NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)

    SOURCE DATA: Sentinel-2 B11 (SWIR1), B08 (NIR)
    FORMULA: (B11 - B08) / (B11 + B08)
    RANGE: [-1, 1]
    """
    required = {"B11", "B08"}
    available = set(observation.scene.bands)

    if not required.issubset(available):
        missing = required - available
        return FeatureResult(
            feature=DerivedFeature.NDBI,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty=f"Missing required bands: {sorted(missing)}",
            error=f"NDBI requires {sorted(required)}, scene has {sorted(available)}",
        )

    swir_vals = _get_band_values(observation, "B11")
    nir_vals = _get_band_values(observation, "B08")

    if swir_vals is None or nir_vals is None:
        return FeatureResult(
            feature=DerivedFeature.NDBI,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty="Band values not available in observation derived_values",
        )

    swir = swir_vals[0]
    nir = nir_vals[0]
    denom = swir + nir

    if abs(denom) < 1e-10:
        return FeatureResult(
            feature=DerivedFeature.NDBI,
            value=0.0,
            confidence=0.0,
            uncertainty="Near-zero denominator",
        )

    ndbi = (swir - nir) / denom
    ndbi = max(-1.0, min(1.0, ndbi))

    cloud_penalty = observation.scene.cloud_info.cloud_pct / 100.0
    confidence = max(0.0, 1.0 - cloud_penalty * 0.8)

    return FeatureResult(
        feature=DerivedFeature.NDBI,
        value=ndbi,
        unit="index",
        confidence=confidence,
        source_bands=("B11", "B08"),
        formula="(B11 - B08) / (B11 + B08)",
        methodology_version="1.0",
        time_range=observation.acquisition_timestamp.isoformat(),
        quality=f"Cloud: {observation.scene.cloud_info.cloud_pct:.1f}%",
        uncertainty="Zha et al. (2003). Positive values indicate built-up areas.",
    )


def compute_vegetation_change(
    before: GeoObservation,
    after: GeoObservation,
) -> FeatureResult:
    """ΔNDVI between two observations.

    SOURCE DATA: NDVI from two dates
    FORMULA: NDVI_after - NDVI_before
    """
    ndvi_before = compute_ndvi(before)
    ndvi_after = compute_ndvi(after)

    if not ndvi_before.supported or not ndvi_after.supported:
        return FeatureResult(
            feature=DerivedFeature.VEGETATION_CHANGE,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty="Cannot compute: one or both observations lack required bands",
            error=f"Before: {ndvi_before.error or 'OK'}, After: {ndvi_after.error or 'OK'}",
        )

    delta = ndvi_after.value - ndvi_before.value
    confidence = min(ndvi_before.confidence, ndvi_after.confidence)

    return FeatureResult(
        feature=DerivedFeature.VEGETATION_CHANGE,
        value=delta,
        unit="delta_index",
        confidence=confidence,
        source_bands=("B08", "B04"),
        formula="NDVI_after - NDVI_before",
        methodology_version="1.0",
        time_range=f"{before.acquisition_timestamp.isoformat()} to {after.acquisition_timestamp.isoformat()}",
        quality=f"Before cloud: {before.scene.cloud_info.cloud_pct:.1f}%, After: {after.scene.cloud_info.cloud_pct:.1f}%",
        uncertainty="Change may be seasonal or noise. Requires validation.",
    )


def compute_water_change(
    before: GeoObservation,
    after: GeoObservation,
) -> FeatureResult:
    """ΔNDWI between two observations."""
    ndwi_before = compute_ndwi(before)
    ndwi_after = compute_ndwi(after)

    if not ndwi_before.supported or not ndwi_after.supported:
        return FeatureResult(
            feature=DerivedFeature.WATER_CHANGE,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty="Cannot compute: one or both observations lack required bands",
        )

    delta = ndwi_after.value - ndwi_before.value
    confidence = min(ndwi_before.confidence, ndwi_after.confidence)

    return FeatureResult(
        feature=DerivedFeature.WATER_CHANGE,
        value=delta,
        unit="delta_index",
        confidence=confidence,
        source_bands=("B03", "B08"),
        formula="NDWI_after - NDWI_before",
        methodology_version="1.0",
        time_range=f"{before.acquisition_timestamp.isoformat()} to {after.acquisition_timestamp.isoformat()}",
        uncertainty="Water detection may be affected by seasonal variation.",
    )


def compute_built_area_change(
    before: GeoObservation,
    after: GeoObservation,
) -> FeatureResult:
    """ΔNDBI between two observations."""
    ndbi_before = compute_ndbi(before)
    ndbi_after = compute_ndbi(after)

    if not ndbi_before.supported or not ndbi_after.supported:
        return FeatureResult(
            feature=DerivedFeature.BUILT_AREA_CHANGE,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            uncertainty="Cannot compute: one or both observations lack required bands",
        )

    delta = ndbi_after.value - ndbi_before.value
    confidence = min(ndbi_before.confidence, ndbi_after.confidence)

    return FeatureResult(
        feature=DerivedFeature.BUILT_AREA_CHANGE,
        value=delta,
        unit="delta_index",
        confidence=confidence,
        source_bands=("B11", "B08"),
        formula="NDBI_after - NDBI_before",
        methodology_version="1.0",
        time_range=f"{before.acquisition_timestamp.isoformat()} to {after.acquisition_timestamp.isoformat()}",
        uncertainty="Built-up detection may be confused with bare soil.",
    )


def compute_temporal_anomaly(
    time_series: GeoTimeSeries,
    threshold_sigma: float = 2.0,
) -> FeatureResult:
    """Detect anomalous values in a geospatial time series.

    Uses mean ± sigma thresholding.
    """
    if len(time_series.points) < 3:
        return FeatureResult(
            feature=DerivedFeature.TEMPORAL_ANOMALY,
            value=0.0,
            supported=False,
            integrity_state=GeoIntegrityState.INSUFFICIENT_TEMPORAL_COVERAGE,
            uncertainty=f"Need >= 3 points, got {len(time_series.points)}",
        )

    values = [p.value for p in time_series.points]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    std = variance ** 0.5 if variance > 0 else 0.0

    if std < 1e-10:
        return FeatureResult(
            feature=DerivedFeature.TEMPORAL_ANOMALY,
            value=0.0,
            confidence=0.0,
            uncertainty="Zero standard deviation — no variation in time series",
        )

    last_val = values[-1]
    z_score = (last_val - mean) / std
    is_anomaly = abs(z_score) > threshold_sigma

    return FeatureResult(
        feature=DerivedFeature.TEMPORAL_ANOMALY,
        value=z_score,
        unit="z_score",
        confidence=0.8 if is_anomaly else 0.5,
        source_bands=(),
        formula=f"(last - mean) / std, threshold={threshold_sigma}σ",
        methodology_version="1.0",
        time_range=f"{time_series.points[0].timestamp.isoformat()} to {time_series.points[-1].timestamp.isoformat()}",
        quality=f"n={len(values)}, mean={mean:.4f}, std={std:.4f}",
        uncertainty="Simple z-score anomaly detection. May miss gradual shifts.",
    )
