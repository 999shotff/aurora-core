"""Provenance Tracking — traceability for conclusions.

Every conclusion must be traceable:
Conclusion → Finding → Evidence → Source

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from aurora.ai.synthesis.schemas import (
    EvidenceAssessment,
    FindingAssessment,
    ProvenanceRecord,
)


def build_provenance(
    findings: list[FindingAssessment],
    evidence_assessments: list[EvidenceAssessment],
) -> list[ProvenanceRecord]:
    """Build provenance chain from findings to evidence to sources."""
    evidence_map = {e.evidence_id: e for e in evidence_assessments}
    records: list[ProvenanceRecord] = []

    for finding in findings:
        sources = []
        for eid in finding.supporting_evidence:
            ea = evidence_map.get(eid)
            if ea:
                sources.append(ea.source)

        records.append(ProvenanceRecord(
            conclusion=finding.statement,
            finding_ids=[finding.finding_id],
            evidence_ids=finding.supporting_evidence,
            source_ids=list(set(sources)),
            reasoning_chain=[
                f"Finding: {finding.statement[:80]}",
                f"Classified as: {finding.status}",
                f"Confidence: {finding.confidence}",
                f"Supporting evidence: {len(finding.supporting_evidence)} items",
                f"Contradicting evidence: {len(finding.contradicting_evidence)} items",
            ],
        ))

    return records
