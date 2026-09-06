"""Hypothesis Engine — competing explanations from evidence.

Allows multiple hypotheses, never forces one to win.
Evidence-grounded, no fabrication.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import json

from aurora.ai.synthesis.schemas import (
    ConfidenceLevel,
    FindingAssessment,
    Hypothesis,
    HypothesisStatus,
)


def generate_hypotheses(
    question: str,
    findings: list[FindingAssessment],
    evidence_ids: list[str],
) -> list[Hypothesis]:
    """Generate competing hypotheses from findings and evidence.

    Deterministic: no LLM call. Produces hypotheses based on
    the structure of available evidence.
    """
    if not findings:
        return [_no_evidence_hypothesis(question)]

    hypotheses = []

    supported = [f for f in findings if f.status == HypothesisStatus.SUPPORTED]
    contradicted = [f for f in findings if f.status == HypothesisStatus.CONTRADICTED]
    unresolved = [f for f in findings if f.status == HypothesisStatus.UNRESOLVED]

    if supported:
        h1 = Hypothesis(
            hypothesis_id=_hypothesis_id(question, "supported"),
            statement=f"Evidence supports: {supported[0].statement}",
            supporting_evidence=[eid for f in supported for eid in f.supporting_evidence],
            contradicting_evidence=[eid for f in contradicted for eid in f.contradicting_evidence],
            unresolved_evidence=[eid for f in unresolved for eid in f.supporting_evidence],
            assumptions=["Findings are accurately classified"],
            confidence=_confidence_from_findings(supported),
            status=HypothesisStatus.SUPPORTED,
        )
        hypotheses.append(h1)

    if contradicted:
        h2 = Hypothesis(
            hypothesis_id=_hypothesis_id(question, "contradicted"),
            statement=f"Contradictory evidence suggests: {contradicted[0].statement}",
            supporting_evidence=[eid for f in contradicted for eid in f.supporting_evidence],
            contradicting_evidence=[eid for f in supported for eid in f.supporting_evidence],
            assumptions=["Contradicting evidence is valid"],
            confidence=ConfidenceLevel.LOW,
            status=HypothesisStatus.CONTRADICTED,
        )
        hypotheses.append(h2)

    if unresolved:
        h3 = Hypothesis(
            hypothesis_id=_hypothesis_id(question, "unresolved"),
            statement="Evidence is insufficient to determine a conclusion",
            supporting_evidence=[eid for f in unresolved for eid in f.supporting_evidence],
            unresolved_evidence=[eid for f in unresolved for eid in f.supporting_evidence],
            assumptions=["Additional evidence may change assessment"],
            confidence=ConfidenceLevel.UNDETERMINED,
            status=HypothesisStatus.UNRESOLVED,
        )
        hypotheses.append(h3)

    if not hypotheses:
        hypotheses.append(Hypothesis(
            hypothesis_id=_hypothesis_id(question, "indeterminate"),
            statement="Available evidence does not support a definitive conclusion",
            supporting_evidence=evidence_ids[:5],
            confidence=ConfidenceLevel.UNDETERMINED,
            status=HypothesisStatus.INSUFFICIENT_EVIDENCE,
        ))

    return hypotheses


def compare_hypotheses(hypotheses: list[Hypothesis]) -> dict:
    """Compare competing hypotheses. Deterministic."""
    if len(hypotheses) < 2:
        return {
            "hypotheses": hypotheses,
            "distinguishing_evidence": [],
            "unresolved_question": "Need at least two hypotheses to compare",
            "determination": "INSUFFICIENT_HYPOTHESES",
        }

    all_supporting = set()
    all_contradicting = set()
    for h in hypotheses:
        all_supporting.update(h.supporting_evidence)
        all_contradicting.update(h.contradicting_evidence)

    distinguishing = list(all_supporting.symmetric_difference(all_contradicting))

    best = max(hypotheses, key=lambda h: _confidence_rank(h.confidence))

    return {
        "hypotheses": hypotheses,
        "distinguishing_evidence": distinguishing[:10],
        "unresolved_question": "Evidence quality and completeness determines confidence",
        "determination": best.status.value if best.status != HypothesisStatus.UNRESOLVED else "INDETERMINATE",
    }


def _no_evidence_hypothesis(question: str) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=_hypothesis_id(question, "no_evidence"),
        statement="No findings available to form a hypothesis",
        confidence=ConfidenceLevel.UNDETERMINED,
        status=HypothesisStatus.INSUFFICIENT_EVIDENCE,
    )


def _hypothesis_id(question: str, label: str) -> str:
    h = hashlib.sha256(f"{question}:{label}".encode()).hexdigest()[:12]
    return f"hyp-{h}"


def _confidence_rank(level: ConfidenceLevel) -> int:
    return {
        ConfidenceLevel.VERY_HIGH: 5,
        ConfidenceLevel.HIGH: 4,
        ConfidenceLevel.MODERATE: 3,
        ConfidenceLevel.LOW: 2,
        ConfidenceLevel.VERY_LOW: 1,
        ConfidenceLevel.UNDETERMINED: 0,
    }.get(level, 0)


def _confidence_from_findings(findings: list[FindingAssessment]) -> ConfidenceLevel:
    if not findings:
        return ConfidenceLevel.UNDETERMINED
    ranks = [_confidence_rank(f.confidence) for f in findings]
    avg = sum(ranks) / len(ranks)
    if avg >= 4.5:
        return ConfidenceLevel.VERY_HIGH
    if avg >= 3.5:
        return ConfidenceLevel.HIGH
    if avg >= 2.5:
        return ConfidenceLevel.MODERATE
    if avg >= 1.5:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.VERY_LOW
