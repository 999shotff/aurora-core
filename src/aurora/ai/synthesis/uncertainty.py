"""Uncertainty Model — classify and expose uncertainty.

Separates KNOWN, INFERENCE, ASSUMPTION, UNKNOWN, CONTRADICTED, UNAVAILABLE.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from aurora.ai.synthesis.schemas import (
    ConfidenceLevel,
    FindingAssessment,
    UncertaintyAssessment,
    UncertaintyKind,
)


def assess_uncertainty(
    findings: list[FindingAssessment],
    known_facts: list[str],
    contradictions_exist: bool,
) -> list[UncertaintyAssessment]:
    """Classify uncertainty for each major element."""
    assessments: list[UncertaintyAssessment] = []

    for fact in known_facts:
        assessments.append(UncertaintyAssessment(
            element=fact[:120],
            kind=UncertaintyKind.KNOWN,
            description="Directly supported by evidence",
        ))

    for finding in findings:
        kind = _classify_finding_uncertainty(finding, contradictions_exist)
        desc = _describe_uncertainty(kind, finding)
        reduction = _suggest_reduction(kind)

        assessments.append(UncertaintyAssessment(
            element=finding.statement[:120],
            kind=kind,
            description=desc,
            impact=_assess_impact(kind),
            reduction_path=reduction,
        ))

    return assessments


def _classify_finding_uncertainty(
    finding: FindingAssessment,
    contradictions_exist: bool,
) -> UncertaintyKind:
    if finding.status == "CONTRADICTED":
        return UncertaintyKind.CONTRADICTED
    if finding.status == "SUPPORTED":
        if finding.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH):
            return UncertaintyKind.KNOWN
        return UncertaintyKind.SUPPORTED_INFERENCE
    if finding.status == "PARTIALLY_SUPPORTED":
        return UncertaintyKind.SUPPORTED_INFERENCE
    if finding.status == "UNRESOLVED":
        if contradictions_exist:
            return UncertaintyKind.CONTRADICTED
        return UncertaintyKind.UNKNOWN
    return UncertaintyKind.UNKNOWN


def _describe_uncertainty(kind: UncertaintyKind, finding: FindingAssessment) -> str:
    if kind == UncertaintyKind.KNOWN:
        return "Supported by sufficient evidence"
    if kind == UncertaintyKind.SUPPORTED_INFERENCE:
        return "Inferred from available evidence with some uncertainty"
    if kind == UncertaintyKind.ASSUMPTION:
        return "Based on assumptions that may not hold"
    if kind == UncertaintyKind.UNKNOWN:
        return "Cannot be determined from available evidence"
    if kind == UncertaintyKind.CONTRADICTED:
        return "Conflicting evidence exists"
    if kind == UncertaintyKind.UNAVAILABLE:
        return "Required data is unavailable"
    return "Uncertainty not classified"


def _assess_impact(kind: UncertaintyKind) -> str:
    if kind in (UncertaintyKind.KNOWN,):
        return "LOW"
    if kind in (UncertaintyKind.SUPPORTED_INFERENCE,):
        return "MODERATE"
    if kind in (UncertaintyKind.CONTRADICTED,):
        return "HIGH"
    return "MODERATE"


def _suggest_reduction(kind: UncertaintyKind) -> str | None:
    if kind == UncertaintyKind.UNKNOWN:
        return "Gather additional evidence from available sources"
    if kind == UncertaintyKind.CONTRADICTED:
        return "Resolve contradiction through source evaluation"
    if kind == UncertaintyKind.SUPPORTED_INFERENCE:
        return "Corroborate with additional independent evidence"
    return None
