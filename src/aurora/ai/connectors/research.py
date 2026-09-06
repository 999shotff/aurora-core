"""AURORA Reasoning Core — Research Reasoning Connector.

Connects the LLM layer to existing research/evidence architecture.
"""

from __future__ import annotations

from aurora.ai.schemas import (
    EvidenceRecord,
    EvidenceSource,
    ReasoningDomain,
)


def research_claim_to_evidence(claim_data: dict) -> EvidenceRecord:
    """Convert a research claim to an evidence record."""
    return EvidenceRecord(
        evidence_id=f"res_claim_{claim_data.get('claim_id', 'unknown')[:20]}",
        source=EvidenceSource.RESEARCH_CLAIM,
        domain=ReasoningDomain.RESEARCH,
        claim=claim_data.get("claim_text", claim_data.get("text", "")),
        value=claim_data.get("value", ""),
        timestamp=claim_data.get("timestamp"),
        confidence=claim_data.get("confidence", 0.5),
        provenance=(
            f"document={claim_data.get('source_document_id', '')} "
            f"page={claim_data.get('page_number', 0)}"
        ),
        quality=claim_data.get("validation_status", "unreviewed"),
    )


def research_hypothesis_to_evidence(hypothesis_data: dict) -> EvidenceRecord:
    """Convert a research hypothesis to an evidence record."""
    return EvidenceRecord(
        evidence_id=f"res_hyp_{hypothesis_data.get('hypothesis_id', 'unknown')[:20]}",
        source=EvidenceSource.RESEARCH_CLAIM,
        domain=ReasoningDomain.RESEARCH,
        claim=(
            f"Hypothesis: {hypothesis_data.get('description', '')}. "
            f"Status: {hypothesis_data.get('status', 'untested')}. "
            f"Methodology: {hypothesis_data.get('methodology', 'unknown')}."
        ),
        value=hypothesis_data.get("status", "untested"),
        confidence=hypothesis_data.get("confidence", 0.5),
        provenance=f"source={hypothesis_data.get('source', '')}",
        quality=hypothesis_data.get("status", "untested"),
    )


def evidence_aggregation_to_records(evidence_items: list[dict]) -> list[EvidenceRecord]:
    """Convert M26 EvidenceItem dicts to EvidenceRecords."""
    records: list[EvidenceRecord] = []
    for item in evidence_items:
        domain_str = item.get("domain", "general")
        try:
            domain = ReasoningDomain(domain_str)
        except ValueError:
            domain = ReasoningDomain.GENERAL

        records.append(EvidenceRecord(
            evidence_id=f"ev_{item.get('source_indicator', 'unknown')}_{hash(item.get('claim', '')) % 10000:04d}",
            source=EvidenceSource.MARKET_ANALYSIS,
            domain=domain,
            claim=item.get("description", item.get("value", "")),
            value=item.get("value", ""),
            confidence=1.0 if item.get("strength") == "strong" else 0.7 if item.get("strength") == "moderate" else 0.3,
            provenance=f"polarity={item.get('polarity', '')} classification={item.get('classification', '')}",
            quality="deterministic",
        ))
    return records
