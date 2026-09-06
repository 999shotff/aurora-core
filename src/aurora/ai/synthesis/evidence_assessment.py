"""Evidence Assessment — deterministic evidence evaluation.

Evaluates evidence items for relevance, reliability, and limitations
without fabricating scores or inventing reliability data.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from aurora.ai.synthesis.schemas import (
    ConfidenceLevel,
    EvidenceAssessment,
)


def assess_evidence(
    evidence_id: str,
    source: str,
    evidence_type: str,
    domain: str,
    claim: str,
    timestamp: str | None = None,
    source_status: str = "unknown",
) -> EvidenceAssessment:
    """Produce a deterministic evidence assessment.

    Does NOT invent reliability scores. Uses only available metadata.
    """
    freshness = _classify_freshness(timestamp)
    reliability = _classify_reliability(source_status)
    direct_vs_derived = _classify_directness(evidence_type)
    limitations = _identify_limitations(evidence_type, source_status)

    return EvidenceAssessment(
        evidence_id=evidence_id,
        source=source,
        evidence_type=evidence_type,
        domain=domain,
        claim=claim,
        freshness=freshness,
        relevance=ConfidenceLevel.MODERATE,
        reliability=reliability,
        direct_vs_derived=direct_vs_derived,
        limitations=limitations,
    )


def assess_evidences(
    evidence_items: list[dict],
) -> list[EvidenceAssessment]:
    """Assess a batch of evidence items."""
    results = []
    for item in evidence_items:
        results.append(assess_evidence(
            evidence_id=item.get("evidence_id", ""),
            source=item.get("source", "unknown"),
            evidence_type=item.get("evidence_type", "unknown"),
            domain=item.get("domain", "general"),
            claim=item.get("claim", ""),
            timestamp=item.get("timestamp"),
            source_status=item.get("source_status", "unknown"),
        ))
    return results


def _classify_freshness(timestamp: str | None) -> str:
    """Classify evidence freshness from timestamp. No fabrication."""
    if not timestamp:
        return "UNKNOWN"
    return "AVAILABLE"


def _classify_reliability(source_status: str) -> ConfidenceLevel:
    """Classify reliability from source status. Never fabricate scores."""
    if source_status in ("operational", "live"):
        return ConfidenceLevel.MODERATE
    if source_status == "stale":
        return ConfidenceLevel.LOW
    if source_status in ("error", "unavailable"):
        return ConfidenceLevel.VERY_LOW
    return ConfidenceLevel.UNDETERMINED


def _classify_directness(evidence_type: str) -> str:
    """Classify whether evidence is direct or derived."""
    direct_types = {"satellite_observation", "market_data", "research_claim"}
    if evidence_type in direct_types:
        return "DIRECT"
    if "derived" in evidence_type.lower() or "analysis" in evidence_type.lower():
        return "DERIVED"
    return "UNKNOWN"


def _identify_limitations(evidence_type: str, source_status: str) -> list[str]:
    """Identify evidence limitations without fabrication."""
    limits = []
    if source_status == "stale":
        limits.append("Source data is stale")
    if source_status in ("error", "unavailable"):
        limits.append("Source unavailable")
    if "derived" in evidence_type.lower():
        limits.append("Derived from primary data, not direct observation")
    return limits
