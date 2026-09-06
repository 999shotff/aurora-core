"""AURORA Reasoning Core — Domain Connectors."""

from aurora.ai.connectors.geo import (
    geo_change_to_evidence,
    geo_index_to_evidence,
    geo_scene_to_evidence,
    geo_timeseries_to_evidence,
)
from aurora.ai.connectors.market import (
    build_market_request,
    market_analysis_to_evidence,
)
from aurora.ai.connectors.research import (
    evidence_aggregation_to_records,
    research_claim_to_evidence,
    research_hypothesis_to_evidence,
)

__all__ = [
    "build_market_request",
    "evidence_aggregation_to_records",
    "geo_change_to_evidence",
    "geo_index_to_evidence",
    "geo_scene_to_evidence",
    "geo_timeseries_to_evidence",
    "market_analysis_to_evidence",
    "research_claim_to_evidence",
    "research_hypothesis_to_evidence",
]
