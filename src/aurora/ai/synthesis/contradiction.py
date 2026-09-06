"""Contradiction Analysis — detect conflicts between evidence.

Detects contradictions without automatically resolving them.
Produces CONFLICT DETECTED with references.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib

from aurora.ai.synthesis.schemas import (
    ContradictionAssessment,
    ContradictionType,
    EvidenceAssessment,
)


def detect_contradictions(
    evidence_assessments: list[EvidenceAssessment],
) -> list[ContradictionAssessment]:
    """Detect contradictions between evidence items.

    Deterministic: compares claims and sources for conflicts.
    """
    contradictions: list[ContradictionAssessment] = []

    for i, a in enumerate(evidence_assessments):
        for b in evidence_assessments[i + 1:]:
            ct = _check_contradiction(a, b)
            if ct is not None:
                contradictions.append(ContradictionAssessment(
                    contradiction_id=_contradiction_id(a.evidence_id, b.evidence_id),
                    contradiction_type=ct,
                    evidence_a=a.evidence_id,
                    evidence_b=b.evidence_id,
                    description=f"Conflict between {a.source} and {b.source}: {a.claim[:80]} vs {b.claim[:80]}",
                    severity=_severity_from_type(ct),
                ))

    return contradictions


def _check_contradiction(
    a: EvidenceAssessment, b: EvidenceAssessment
) -> ContradictionType | None:
    """Check if two evidence items contradict each other."""
    if a.source == b.source:
        return None

    if a.domain != b.domain:
        return None

    a_claim = a.claim.lower().strip()
    b_claim = b.claim.lower().strip()

    if not a_claim or not b_claim:
        return None

    negation_pairs = [
        ("increase", "decrease"),
        ("rise", "fall"),
        ("above", "below"),
        ("positive", "negative"),
        ("bullish", "bearish"),
        ("supports", "contradicts"),
        ("confirms", "denies"),
        ("present", "absent"),
    ]

    for pos, neg in negation_pairs:
        if (pos in a_claim and neg in b_claim) or (neg in a_claim and pos in b_claim):
            return ContradictionType.DIRECT

    if _has_numeric_conflict(a_claim, b_claim):
        return ContradictionType.NUMERICAL

    if a.source != b.source and _claims_differ(a_claim, b_claim):
        return ContradictionType.SOURCE_DISAGREEMENT

    return None


def _has_numeric_conflict(claim_a: str, claim_b: str) -> bool:
    """Check if claims contain conflicting numbers."""
    import re
    nums_a = re.findall(r'[\d.]+', claim_a)
    nums_b = re.findall(r'[\d.]+', claim_b)
    if nums_a and nums_b:
        try:
            a_val = float(nums_a[0])
            b_val = float(nums_b[0])
            if a_val != b_val and abs(a_val - b_val) > abs(a_val) * 0.1:
                return True
        except (ValueError, ZeroDivisionError):
            pass
    return False


def _claims_differ(claim_a: str, claim_b: str) -> bool:
    """Check if two claims are meaningfully different."""
    words_a = set(claim_a.split())
    words_b = set(claim_b.split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
    return overlap < 0.5


def _contradiction_id(eid_a: str, eid_b: str) -> str:
    pair = tuple(sorted([eid_a, eid_b]))
    h = hashlib.sha256(f"{pair[0]}:{pair[1]}".encode()).hexdigest()[:12]
    return f"con-{h}"


def _severity_from_type(ct: ContradictionType) -> str:
    if ct == ContradictionType.DIRECT:
        return "WARNING"
    if ct == ContradictionType.NUMERICAL:
        return "WARNING"
    return "INFO"
