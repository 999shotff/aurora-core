"""GeoEvidence integration — bridge geospatial observations to AURORA evidence engine.

A GeoEvidence item becomes a FACT/OBSERVATION in the evidence system.
It NEVER automatically becomes a financial prediction.
"""

from __future__ import annotations

from aurora.features.evidence import (
    EvidenceItem,
    EvidencePolarity,
    EvidenceStrength,
    ResearchClassification,
)
from aurora.geo.domain import (
    GeoChange,
    GeoIntegrityState,
    GeoObservation,
    GeoTimeSeries,
)


def observation_to_evidence(observation: GeoObservation) -> EvidenceItem:
    """Convert a GeoObservation to an EvidenceItem.

    CLASSIFICATION: OBSERVATION (not INFERENCE)
    DOMAIN: geospatial
    """
    confidence = observation.confidence
    if confidence >= 0.7:
        strength = EvidenceStrength.STRONG
    elif confidence >= 0.4:
        strength = EvidenceStrength.MODERATE
    elif confidence > 0.0:
        strength = EvidenceStrength.WEAK
    else:
        strength = EvidenceStrength.ABSENT

    cloud_note = ""
    if observation.scene.cloud_info.cloud_pct > 30:
        cloud_note = f" High cloud cover ({observation.scene.cloud_info.cloud_pct:.0f}%) reduces confidence."

    integrity_note = ""
    if observation.integrity_state == GeoIntegrityState.DATA_UNAVAILABLE:
        integrity_note = " DATA_UNAVAILABLE: Required spectral bands not provided by source."
        strength = EvidenceStrength.ABSENT

    return EvidenceItem(
        domain="geospatial",
        classification=ResearchClassification.OBSERVATION,
        polarity=EvidencePolarity.NEUTRAL,
        strength=strength,
        value=f"{observation.source} scene {observation.scene.scene_id}",
        description=(
            f"Satellite observation from {observation.source} "
            f"acquired {observation.acquisition_timestamp.strftime('%Y-%m-%d')}. "
            f"Resolution: {observation.scene.resolution_m:.0f}m. "
            f"Cloud: {observation.scene.cloud_info.cloud_pct:.1f}%."
            f"{cloud_note}"
            f"{integrity_note}"
        ),
        source_indicator=f"satellite_observation_{observation.source}",
    )


def index_observation_to_evidence(
    provider: str,
    scene_id: str,
    index: str,
    value: float | None,
    integrity_state: str,
    bands_used: list[str],
    formula: str,
    methodology: str,
    uncertainty: str,
    acquisition_time: str,
    aoi_name: str,
) -> EvidenceItem:
    """Create EvidenceItem from index computation result.

    This bridges the new API response format to M26 evidence.
    """
    if integrity_state == "DATA_UNAVAILABLE":
        strength = EvidenceStrength.ABSENT
        polarity = EvidencePolarity.UNAVAILABLE
        value_str = f"{index} DATA_UNAVAILABLE"
        desc = (
            f"Index {index} computation for {provider} scene {scene_id}: "
            f"DATA_UNAVAILABLE. {uncertainty}"
        )
    elif integrity_state == "PROCESSING_FAILED":
        strength = EvidenceStrength.ABSENT
        polarity = EvidencePolarity.UNAVAILABLE
        value_str = f"{index} PROCESSING_FAILED"
        desc = f"Index {index} computation failed for {provider} scene {scene_id}."
    elif value is not None:
        strength = EvidenceStrength.MODERATE
        polarity = EvidencePolarity.NEUTRAL
        value_str = f"{index}={value:.4f}"
        desc = (
            f"Index {index} for {provider} scene {scene_id}: {value:.4f}. "
            f"Formula: {formula}. Bands: {', '.join(bands_used)}. "
            f"Methodology: {methodology}."
        )
    else:
        strength = EvidenceStrength.ABSENT
        polarity = EvidencePolarity.UNAVAILABLE
        value_str = f"{index} NO_VALUE"
        desc = f"Index {index} produced no value for {provider} scene {scene_id}."

    return EvidenceItem(
        domain="geospatial",
        classification=ResearchClassification.OBSERVATION,
        polarity=polarity,
        strength=strength,
        value=value_str,
        description=desc,
        source_indicator=f"geo_index_{provider}_{index}",
    )


def change_to_evidence(change: GeoChange) -> EvidenceItem:
    """Convert a GeoChange to an EvidenceItem.

    CLASSIFICATION: OBSERVATION (not INFERENCE)
    """
    if change.confidence < 0.3:
        strength = EvidenceStrength.WEAK
    elif change.confidence < 0.6:
        strength = EvidenceStrength.MODERATE
    else:
        strength = EvidenceStrength.STRONG

    polarity = EvidencePolarity.NEUTRAL
    if change.change_type.value == "increase" and change.derived_feature == "NDVI":
        polarity = EvidencePolarity.BULLISH
    elif change.change_type.value == "decrease" and change.derived_feature == "NDVI":
        polarity = EvidencePolarity.BEARISH

    return EvidenceItem(
        domain="geospatial",
        classification=ResearchClassification.OBSERVATION,
        polarity=polarity,
        strength=strength,
        value=f"{change.derived_feature} Δ={change.magnitude:+.4f}",
        description=(
            f"Geospatial change detected: {change.derived_feature} "
            f"changed by {change.magnitude:+.4f} "
            f"({change.change_type.value}) "
            f"between {change.before.acquisition_timestamp.strftime('%Y-%m-%d')} "
            f"and {change.after.acquisition_timestamp.strftime('%Y-%m-%d')}. "
            f"Confidence: {change.confidence:.1%}."
        ),
        source_indicator=f"change_detection_{change.derived_feature}",
    )


def timeseries_to_evidence(ts: GeoTimeSeries) -> EvidenceItem:
    """Convert a GeoTimeSeries summary to an EvidenceItem."""
    if not ts.points:
        return EvidenceItem(
            domain="geospatial",
            classification=ResearchClassification.UNCERTAINTY,
            polarity=EvidencePolarity.UNAVAILABLE,
            strength=EvidenceStrength.ABSENT,
            value="no data",
            description=f"Empty time series for {ts.metric}",
            source_indicator=f"timeseries_{ts.metric}",
        )

    values = [p.value for p in ts.points]
    mean_val = sum(values) / len(values)
    last_val = values[-1]
    trend = "stable"
    if len(values) >= 2:
        slope = (values[-1] - values[0]) / len(values)
        if abs(slope) > 0.01:
            trend = "increasing" if slope > 0 else "decreasing"

    return EvidenceItem(
        domain="geospatial",
        classification=ResearchClassification.OBSERVATION,
        polarity=EvidencePolarity.NEUTRAL,
        strength=EvidenceStrength.MODERATE,
        value=f"{ts.metric}={last_val:.4f} (trend: {trend})",
        description=(
            f"Geospatial time series for {ts.metric}: "
            f"{len(ts.points)} observations, "
            f"mean={mean_val:.4f}, last={last_val:.4f}, "
            f"trend={trend}."
        ),
        source_indicator=f"timeseries_{ts.metric}",
    )


def aggregate_geo_evidence(
    observations: list[GeoObservation],
    changes: list[GeoChange],
    time_series: list[GeoTimeSeries],
) -> list[EvidenceItem]:
    """Convert all geospatial data to evidence items.

    Returns a list of EvidenceItem for integration with the AURORA evidence engine.
    """
    items: list[EvidenceItem] = []

    for obs in observations:
        items.append(observation_to_evidence(obs))

    for change in changes:
        items.append(change_to_evidence(change))

    for ts in time_series:
        items.append(timeseries_to_evidence(ts))

    return items
