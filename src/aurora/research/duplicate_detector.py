"""Duplicate detection for extracted claims.

Identifies duplicate claims based on source document/page/text overlap.
Does NOT aggressively merge semantically similar claims.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict

from aurora.research.claims import ResearchClaim


def _text_fingerprint(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:12]


def detect_duplicates(
    claims: list[ResearchClaim],
    exact_threshold: float = 1.0,
    overlap_threshold: float = 0.85,
) -> list[tuple[str, str, str]]:
    """Return list of (claim_id_a, claim_id_b, reason) for duplicate pairs."""
    duplicates: list[tuple[str, str, str]] = []

    by_source: dict[str, list[ResearchClaim]] = defaultdict(list)
    for claim in claims:
        key = f"{claim.document_id}:{claim.page}"
        by_source[key].append(claim)

    for group in by_source.values():
        if len(group) < 2:
            continue
        fingerprints: dict[str, list[ResearchClaim]] = defaultdict(list)
        for claim in group:
            fp = _text_fingerprint(claim.source_text)
            fingerprints[fp].append(claim)

        for fp, group_claims in fingerprints.items():
            if len(group_claims) < 2:
                continue
            for i in range(len(group_claims)):
                for j in range(i + 1, len(group_claims)):
                    c1 = group_claims[i]
                    c2 = group_claims[j]
                    if c1.source_hash == c2.source_hash:
                        duplicates.append((c1.claim_id, c2.claim_id, "identical_text"))
                    else:
                        overlap = _text_overlap(c1.source_text, c2.source_text)
                        if overlap >= overlap_threshold:
                            duplicates.append((c1.claim_id, c2.claim_id, f"overlap_{overlap:.2f}"))

    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str, str]] = []
    for a, b, reason in duplicates:
        a_id, b_id = sorted((a, b))
        pair_key: tuple[str, str] = (a_id, b_id)
        if pair_key not in seen:
            seen.add(pair_key)
            unique.append((a, b, reason))

    return unique


def _text_overlap(t1: str, t2: str) -> float:
    words1 = set(t1.lower().split())
    words2 = set(t2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    return intersection / union if union > 0 else 0.0


def deduplicate_claims(
    claims: list[ResearchClaim],
    duplicates: list[tuple[str, str, str]],
) -> list[ResearchClaim]:
    """Remove duplicate claims, keeping the first occurrence."""
    to_remove: set[str] = set()
    for a, b, _reason in duplicates:
        to_remove.add(b)
    return [c for c in claims if c.claim_id not in to_remove]
