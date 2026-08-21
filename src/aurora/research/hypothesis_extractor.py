"""Hypothesis extraction from candidate claims.

Creates testable hypotheses from rule/observation claims.
Only extracts when the source can be reasonably expressed as a testable relationship.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from aurora.research.claims import ResearchClaim
from aurora.research.hypotheses import Direction, Horizon, ResearchHypothesis

_IF_THEN = re.compile(r"\bif\b\s+(.+?)\s+\bthen\b\s+(.+)", re.IGNORECASE)
_WHEN_THEN = re.compile(r"\bwhen\b\s+(.+?)\s+\bthen\b\s+(.+)", re.IGNORECASE)
_BUY_SIGNAL = re.compile(
    r"\b(buy|go long|enter long|take long position)\b", re.IGNORECASE
)
_SELL_SIGNAL = re.compile(
    r"\b(sell|go short|enter short|take short position)\b", re.IGNORECASE
)
_HORIZON_PATTERNS: dict[str, Horizon] = {
    "intraday": "intraday",
    "day trade": "intraday",
    "swing": "swing",
    "position": "position",
    "long term": "position",
    "long-term": "position",
    "tick": "tick",
}


def _detect_direction(text: str) -> Direction:
    text_lower = text.lower()
    has_buy = bool(_BUY_SIGNAL.search(text_lower))
    has_sell = bool(_SELL_SIGNAL.search(text_lower))
    bullish_words = [
        "increase", "rise", "rally", "up", "higher", "bullish", "positive", "upward",
    ]
    bearish_words = [
        "decrease", "fall", "drop", "down", "lower", "bearish", "negative", "downward",
    ]
    bullish = any(w in text_lower for w in bullish_words)
    bearish = any(w in text_lower for w in bearish_words)

    if has_buy and not has_sell:
        return "long"
    if has_sell and not has_buy:
        return "short"
    if bullish and not bearish:
        return "long"
    if bearish and not bullish:
        return "short"
    return "unknown"


def _detect_horizon(text: str) -> Horizon:
    text_lower = text.lower()
    for pattern, horizon in _HORIZON_PATTERNS.items():
        if pattern in text_lower:
            return horizon
    return "unknown"


def _extract_condition_effect(text: str) -> tuple[str, str]:
    match = _IF_THEN.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    match = _WHEN_THEN.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return "", text.strip()


def hypothesis_from_claim(claim: ResearchClaim) -> ResearchHypothesis | None:
    if claim.claim_type not in ("rule", "observation", "empirical_claim", "hypothesis"):
        return None

    condition, effect = _extract_condition_effect(claim.source_text)
    if not condition and not effect:
        return None

    direction = _detect_direction(claim.source_text + " " + effect)
    horizon = _detect_horizon(claim.source_text)

    hypothesis = ResearchHypothesis(
        hypothesis_id=f"hyp_{claim.claim_id}",
        source_claim_id=claim.claim_id,
        document_id=claim.document_id,
        methodology=claim.methodology,
        condition=condition,
        expected_effect=effect,
        target_variable="future_return",
        horizon=horizon,
        direction=direction,
        confidence=claim.extraction_confidence,
        test_status="untested",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        notes=f"Extracted from {claim.claim_type}: {claim.normalized_text[:100]}",
    )
    return hypothesis


def extract_hypotheses(
    claims: list[ResearchClaim],
) -> list[ResearchHypothesis]:
    hypotheses: list[ResearchHypothesis] = []
    for claim in claims:
        hyp = hypothesis_from_claim(claim)
        if hyp is not None:
            hypotheses.append(hyp)
    return hypotheses
