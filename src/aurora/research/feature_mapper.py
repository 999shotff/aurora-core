"""Claim → Feature mapping layer.

Maps extracted claims to computable features where possible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from aurora.research.claims import ResearchClaim

ImplementationStatus = Literal["not_implemented", "implemented", "needs_definition"]

_FEATURE_PATTERNS: list[tuple[str, str, re.Pattern[str], dict[str, str | int]]] = [
    ("sma", "sma", re.compile(r"\b(\d+)[\s-]*(?:period|bar|day)?\s*(?:SMA|simple moving average|moving average)\b", re.IGNORECASE), {"feature": "sma"}),
    ("ema", "ema", re.compile(r"\b(\d+)[\s-]*(?:period|bar|day)?\s*(?:EMA|exponential moving average)\b", re.IGNORECASE), {"feature": "ema"}),
    ("rsi", "rsi", re.compile(r"\bRSI\b[^.]*?\b(\d+)\b", re.IGNORECASE), {"feature": "rsi"}),
    ("atr", "atr", re.compile(r"\bATR\b[^.]*?\b(\d+)\b", re.IGNORECASE), {"feature": "atr"}),
    ("vwap", "vwap", re.compile(r"\bVWAP\b", re.IGNORECASE), {"feature": "vwap", "lookback": 0}),
    ("fibonacci", "fibonacci_level", re.compile(r"\b(?:fib(?:onacci)?(?:\s+level)?)\s*(?:of\s+)?0\.(\d+)", re.IGNORECASE), {"feature": "fibonacci_level"}),
    ("pivot", "pivot", re.compile(r"\bpivot\s+point\b", re.IGNORECASE), {"feature": "pivot"}),
    ("support_resistance", "support_resistance", re.compile(r"\b(support|resistance)\b", re.IGNORECASE), {"feature": "support_resistance"}),
    ("bollinger", "bollinger", re.compile(r"\bBollinger\b[^.]*?\b(\d+)\b", re.IGNORECASE), {"feature": "bollinger"}),
    ("volume", "volume", re.compile(r"\bvolume\b", re.IGNORECASE), {"feature": "volume"}),
    ("momentum", "momentum", re.compile(r"\bmomentum\b", re.IGNORECASE), {"feature": "momentum"}),
    ("volatility", "volatility", re.compile(r"\bvolatility\b", re.IGNORECASE), {"feature": "volatility"}),
]


@dataclass
class ClaimFeatureMapping:
    claim_id: str
    feature_name: str
    parameters: dict[str, str | int]
    implementation_status: ImplementationStatus
    mapping_confidence: float


def _extract_lookback(text: str, pattern: re.Pattern[str]) -> int | None:
    match = pattern.search(text)
    if match and match.groups():
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            pass
    return None


def map_claim_to_feature(claim: ResearchClaim) -> ClaimFeatureMapping | None:
    text = claim.source_text
    for feature_name, feature_key, pattern, base_params in _FEATURE_PATTERNS:
        if pattern.search(text):
            params = dict(base_params)
            lookback = _extract_lookback(text, pattern)
            if lookback is not None:
                params["lookback"] = lookback

            implemented = feature_name in {
                "sma", "ema", "rsi", "atr", "volume", "momentum", "volatility",
            }
            status: ImplementationStatus = "implemented" if implemented else "needs_definition"

            return ClaimFeatureMapping(
                claim_id=claim.claim_id,
                feature_name=feature_key,
                parameters=params,
                implementation_status=status,
                mapping_confidence=0.7,
            )
    return None


def map_claims_to_features(
    claims: list[ResearchClaim],
) -> list[ClaimFeatureMapping]:
    mappings: list[ClaimFeatureMapping] = []
    for claim in claims:
        mapping = map_claim_to_feature(claim)
        if mapping is not None:
            mappings.append(mapping)
    return mappings
