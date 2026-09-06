"""AURORA Reasoning Core — Evidence Grounding.

Validates that LLM output is grounded in supplied evidence.
Classifies each reasoning point as SUPPORTED_BY_EVIDENCE, INFERENCE, UNCERTAIN, or ABSTAINED.
"""

from __future__ import annotations

from aurora.ai.schemas import (
    EvidenceGrounding,
    EvidenceRecord,
    ReasoningPoint,
    ReasoningResponse,
)


def validate_grounding(
    response: ReasoningResponse,
    evidence: list[EvidenceRecord],
) -> ReasoningResponse:
    """Validate and annotate the grounding of each reasoning point.

    Returns the response with updated grounding scores.
    """
    evidence_ids = {e.evidence_id for e in evidence}
    evidence_claims = {e.claim.lower().strip() for e in evidence}

    grounded_count = 0
    total_points = len(response.reasoning_points)

    annotated_points: list[ReasoningPoint] = []
    for point in response.reasoning_points:
        annotated = _annotate_point(point, evidence_ids, evidence_claims)
        annotated_points.append(annotated)
        if annotated.grounding == EvidenceGrounding.SUPPORTED_BY_EVIDENCE:
            grounded_count += 1

    response.reasoning_points = annotated_points
    response.grounding_score = grounded_count / total_points if total_points > 0 else 0.0

    return response


def _annotate_point(
    point: ReasoningPoint,
    evidence_ids: set[str],
    evidence_claims: set[str],
) -> ReasoningPoint:
    """Annotate a single reasoning point with its grounding level."""
    if point.grounding == EvidenceGrounding.ABSTAINED:
        return point

    if point.evidence_refs:
        refs_found = [ref for ref in point.evidence_refs if ref in evidence_ids]
        if refs_found:
            return ReasoningPoint(
                point=point.point,
                grounding=EvidenceGrounding.SUPPORTED_BY_EVIDENCE,
                evidence_refs=refs_found,
            )

    point_lower = point.point.lower().strip()
    for claim in evidence_claims:
        if point_lower in claim or claim in point_lower:
            return ReasoningPoint(
                point=point.point,
                grounding=EvidenceGrounding.INFERENCE,
                evidence_refs=point.evidence_refs,
            )

    if any(kw in point_lower for kw in ["uncertain", "may", "might", "possibly", " unclear"]):
        return ReasoningPoint(
            point=point.point,
            grounding=EvidenceGrounding.UNCERTAIN,
            evidence_refs=point.evidence_refs,
        )

    return ReasoningPoint(
        point=point.point,
        grounding=EvidenceGrounding.INFERENCE,
        evidence_refs=point.evidence_refs,
    )


def compute_grounding_score(
    response: ReasoningResponse,
    evidence: list[EvidenceRecord],
) -> float:
    """Compute the fraction of reasoning points grounded in evidence."""
    evidence_ids = {e.evidence_id for e in evidence}
    total = len(response.reasoning_points)
    if total == 0:
        return 0.0

    grounded = 0
    for point in response.reasoning_points:
        if point.evidence_refs and any(ref in evidence_ids for ref in point.evidence_refs):
            grounded += 1

    return grounded / total


def detect_unsupported_claims(
    response: ReasoningResponse,
    evidence: list[EvidenceRecord],
) -> list[str]:
    """Detect claims in the answer that are not supported by any evidence.

    Returns a list of flagged claim fragments.
    """
    evidence_claims = {e.claim.lower() for e in evidence}
    flagged: list[str] = []

    sentences = [s.strip() for s in response.answer.replace(".", ".\n").split("\n") if s.strip()]
    for sentence in sentences:
        s_lower = sentence.lower()
        supported = any(claim in s_lower or s_lower in claim for claim in evidence_claims)
        if not supported and len(sentence) > 20:
            flagged.append(sentence[:200])

    return flagged
