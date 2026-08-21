"""Conflict detection between claims.

Finds contradictory claims by detecting opposing directional assertions
on the same or similar conditions.
"""
from __future__ import annotations

import re

from aurora.research.claims import ResearchClaim
from aurora.research.graph import GraphEdge

_BULLISH = re.compile(
    r"\b(bullish|increase|rise|rally|up|higher|long|buy|positive|upward|gains?)\b",
    re.IGNORECASE,
)
_BEARISH = re.compile(
    r"\b(bearish|decrease|fall|drop|down|lower|short|sell|negative|downward|loss)\b",
    re.IGNORECASE,
)


def _direction_from_text(text: str) -> str | None:
    text_lower = text.lower()
    has_bull = bool(_BULLISH.search(text_lower))
    has_bear = bool(_BEARISH.search(text_lower))
    if has_bull and not has_bear:
        return "bullish"
    if has_bear and not has_bull:
        return "bearish"
    return None


def _methodology_match(c1: ResearchClaim, c2: ResearchClaim) -> bool:
    return bool(c1.methodology == c2.methodology and c1.methodology != "unknown")


def _same_topic(c1: ResearchClaim, c2: ResearchClaim) -> bool:
    if c1.document_id == c2.document_id:
        return True
    words1 = set(c1.normalized_text.lower().split())
    words2 = set(c2.normalized_text.lower().split())
    if len(words1) == 0 or len(words2) == 0:
        return False
    overlap = len(words1 & words2) / min(len(words1), len(words2))
    return overlap > 0.5


def detect_conflicts(claims: list[ResearchClaim]) -> list[GraphEdge]:
    conflicts: list[GraphEdge] = []
    seen: set[tuple[str, str]] = set()

    for i, c1 in enumerate(claims):
        if c1.claim_type not in ("rule", "observation", "empirical_claim", "hypothesis"):
            continue
        d1 = _direction_from_text(c1.source_text)
        if d1 is None:
            continue

        for c2 in claims[i + 1 :]:
            if c2.claim_type not in ("rule", "observation", "empirical_claim", "hypothesis"):
                continue
            if c1.claim_id == c2.claim_id:
                continue

            a_id, b_id = sorted((c1.claim_id, c2.claim_id))
            pair_key: tuple[str, str] = (a_id, b_id)
            if pair_key in seen:
                continue

            if not _methodology_match(c1, c2) and not _same_topic(c1, c2):
                continue

            d2 = _direction_from_text(c2.source_text)
            if d2 is None:
                continue

            if d1 != d2:
                seen.add(pair_key)
                conflicts.append(GraphEdge(
                    source_id=c1.claim_id,
                    target_id=c2.claim_id,
                    relationship="contradicts",
                    weight=1.0,
                    metadata={"c1_direction": d1, "c2_direction": d2},
                ))

    return conflicts
