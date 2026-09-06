"""Decision Intelligence — decision-support considerations.

NOT automated decision-making.
Answers: what is known, what is uncertain, what matters most.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from aurora.ai.synthesis.schemas import (
    ConfidenceLevel,
    DecisionConsideration,
    EvidenceAssessment,
    EvidenceGap,
    FindingAssessment,
    Hypothesis,
)


def generate_decision_considerations(
    question: str,
    findings: list[FindingAssessment],
    hypotheses: list[Hypothesis],
    evidence_gaps: list[EvidenceGap],
    contradictions_exist: bool,
) -> list[DecisionConsideration]:
    """Generate decision-support considerations from synthesis results."""
    considerations: list[DecisionConsideration] = []

    supported = [f for f in findings if f.status == "SUPPORTED"]
    if supported:
        considerations.append(DecisionConsideration(
            consideration="Strongest supported conclusion",
            evidence_basis=[eid for f in supported for eid in f.supporting_evidence][:5],
            confidence=supported[0].confidence,
            key_uncertainty="Depends on evidence quality and completeness",
        ))

    if contradictions_exist:
        considerations.append(DecisionConsideration(
            consideration="Contradictory evidence exists — conclusions may change",
            confidence=ConfidenceLevel.LOW,
            key_uncertainty="Resolution of contradictions is required for higher confidence",
        ))

    unresolved = [f for f in findings if f.status == "UNRESOLVED"]
    if unresolved:
        considerations.append(DecisionConsideration(
            consideration=f"{len(unresolved)} finding(s) remain unresolved",
            evidence_basis=[eid for f in unresolved for eid in f.supporting_evidence][:3],
            confidence=ConfidenceLevel.UNDETERMINED,
            key_uncertainty="Additional evidence needed",
        ))

    if evidence_gaps:
        gap_descriptions = [g.description for g in evidence_gaps[:3]]
        considerations.append(DecisionConsideration(
            consideration=f"Key evidence gaps: {'; '.join(gap_descriptions)}",
            confidence=ConfidenceLevel.LOW,
            key_uncertainty="Missing evidence limits conclusion strength",
            assumption_dependency="Existing evidence is complete and accurate",
        ))

    best = max(hypotheses, key=lambda h: _rank(h.confidence)) if hypotheses else None
    if best:
        considerations.append(DecisionConsideration(
            consideration=f"Best-supported hypothesis: {best.statement[:120]}",
            evidence_basis=best.supporting_evidence[:5],
            confidence=best.confidence,
            key_uncertainty="Other hypotheses remain possible",
            assumption_dependency="; ".join(best.assumptions[:2]) if best.assumptions else "",
        ))

    considerations.append(DecisionConsideration(
        consideration="What additional evidence would reduce uncertainty?",
        evidence_basis=[],
        confidence=ConfidenceLevel.UNDETERMINED,
        key_uncertainty="Identifying evidence gaps is itself uncertain",
    ))

    return considerations


def _rank(level: ConfidenceLevel) -> int:
    return {
        ConfidenceLevel.VERY_HIGH: 5,
        ConfidenceLevel.HIGH: 4,
        ConfidenceLevel.MODERATE: 3,
        ConfidenceLevel.LOW: 2,
        ConfidenceLevel.VERY_LOW: 1,
        ConfidenceLevel.UNDETERMINED: 0,
    }.get(level, 0)
