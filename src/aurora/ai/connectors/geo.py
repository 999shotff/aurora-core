"""AURORA Reasoning Core — Geo Reasoning Connector.

Connects the LLM layer to Geo Observatory evidence.
"""

from __future__ import annotations

from aurora.ai.schemas import (
    EvidenceRecord,
    EvidenceSource,
    ReasoningDomain,
)


def geo_scene_to_evidence(scene_data: dict) -> EvidenceRecord:
    """Convert a Geo scene search result to an evidence record."""
    return EvidenceRecord(
        evidence_id=f"geo_scene_{scene_data.get('scene_id', 'unknown')[:20]}",
        source=EvidenceSource.GEO_OBSERVATION,
        domain=ReasoningDomain.GEO,
        claim=(
            f"Satellite scene {scene_data.get('scene_id', 'unknown')} "
            f"from {scene_data.get('provider', 'unknown')} "
            f"acquired {scene_data.get('acquisition_time', 'unknown')}. "
            f"Cloud: {scene_data.get('cloud_pct', 0):.1f}%. "
            f"Resolution: {scene_data.get('resolution_m', 0)}m."
        ),
        value=scene_data.get("dataset", ""),
        timestamp=scene_data.get("acquisition_time"),
        confidence=max(0.0, 1.0 - scene_data.get("cloud_pct", 0) / 100),
        provenance=f"provider={scene_data.get('provider', '')} dataset={scene_data.get('dataset', '')}",
        quality=scene_data.get("quality_grade", "unknown"),
    )


def geo_index_to_evidence(index_data: dict) -> EvidenceRecord:
    """Convert a spectral index computation result to an evidence record."""
    stats = index_data.get("statistics") or {}
    return EvidenceRecord(
        evidence_id=f"geo_idx_{index_data.get('index', 'unknown')}_{hash(str(stats)) % 10000:04d}",
        source=EvidenceSource.GEO_OBSERVATION,
        domain=ReasoningDomain.GEO,
        claim=(
            f"Index {index_data.get('index', 'unknown')}: "
            f"mean={stats.get('mean', 'N/A')}, "
            f"std={stats.get('std', 'N/A')}, "
            f"valid={stats.get('count', 0)}/{stats.get('total_pixels', 0)} pixels. "
            f"Formula: {index_data.get('formula', 'unknown')}."
        ),
        value=str(stats.get("mean", "N/A")),
        timestamp=index_data.get("tile_url", ""),
        confidence=1.0 if index_data.get("supported") else 0.0,
        provenance=f"provider={index_data.get('provenance', {}).get('provider', '')}",
        quality=index_data.get("integrity_state", "unknown"),
    )


def geo_change_to_evidence(change_data: dict) -> EvidenceRecord:
    """Convert change detection result to an evidence record."""
    stats = change_data.get("change_statistics", {})
    return EvidenceRecord(
        evidence_id=f"geo_change_{hash(str(change_data)) % 10000:04d}",
        source=EvidenceSource.GEO_CHANGE,
        domain=ReasoningDomain.GEO,
        claim=(
            f"Change detection: {'Change detected' if change_data.get('change_detected') else 'No change'}. "
            f"Magnitude: {stats.get('magnitude', 'N/A')}. "
            f"Affected area: {stats.get('affected_area_pct', 0):.1f}%. "
            f"Index: {change_data.get('index', 'unknown')}."
        ),
        value=str(stats.get("magnitude", 0)),
        confidence=0.7 if change_data.get("change_detected") else 0.3,
        provenance=f"methodology={change_data.get('methodology', '')}",
        quality=change_data.get("integrity_state", "unknown"),
    )


def geo_timeseries_to_evidence(ts_data: dict) -> EvidenceRecord:
    """Convert time series result to an evidence record."""
    stats = ts_data.get("statistics") or {}
    return EvidenceRecord(
        evidence_id=f"geo_ts_{ts_data.get('index', 'unknown')}_{ts_data.get('provider', '')}",
        source=EvidenceSource.GEO_TIMESERIES,
        domain=ReasoningDomain.GEO,
        claim=(
            f"Time series for {ts_data.get('index', 'unknown')}: "
            f"{stats.get('count', 0)} observations, "
            f"mean={stats.get('mean', 'N/A')}, "
            f"range=[{stats.get('min', 'N/A')}, {stats.get('max', 'N/A')}]. "
            f"Provider: {ts_data.get('provider', 'unknown')}."
        ),
        value=str(stats.get("mean", "N/A")),
        confidence=0.8 if stats.get("count", 0) > 0 else 0.0,
        provenance=f"provider={ts_data.get('provider', '')} dataset={ts_data.get('dataset', '')}",
        quality=ts_data.get("integrity_state", "unknown"),
    )
