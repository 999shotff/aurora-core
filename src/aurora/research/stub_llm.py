"""Stub LLM model for benchmarking without local inference.

Returns structured JSON matching the schema.
Does not use any LLM backend.
"""
from __future__ import annotations

import re
import time
from typing import Literal

from aurora.research.llm_schema import (
    LLMCandidateClaim,
    LLMExtractionResponse,
)
from aurora.research.model_adapter import (
    ExtractionRequest,
    ExtractionResult,
    ResearchExtractionModel,
)

_METHODLOGY_KEYWORDS: dict[str, list[str]] = {
    "fibonacci": ["fibonacci", "fib", "retracement", "extension", "0.618", "1.618", "2.618"],
    "gann": ["gann", "1x1", "45 degree", "law of vibration", "gann angle"],
    "liquidity": ["liquidity", "stop loss", "stop hunt", "sweep", "order block", "imbalance"],
    "technical_analysis": ["rsi", "moving average", "macd", "bollinger", "support", "resistance", "indicator"],
    "volatility": ["volatility", "atr", "implied", "vix", "option chain", "standard deviation"],
    "market_psychology": ["fear", "greed", "sentiment", "bias", "discipline", "contrarian"],
    "news": ["earnings", "payroll", "economic", "announcement", "news", "report"],
    "astrology": ["astrology", "mercury retrograde", "planetary", "zodiac", "celestial"],
    "time_cycles": ["cycle", "period", "turning point", "rhythm", "seasonal"],
    "elliott_wave": ["elliott", "impulse", "corrective", "wave count", "wave pattern"],
    "quantitative_finance": ["sharpe", "sortino", "risk-adjusted", "portfolio", "variance", "standard deviation"],
    "risk_management": ["kelly", "position sizing", "stop loss", "risk per trade", "drawdown"],
    "volume": ["volume", "distribution", "accumulation", "volume divergence"],
    "vwap": ["vwap", "volume weighted", "mean reversion"],
    "order_flow": ["cumulative delta", "order flow", "absorption", "footprint"],
    "market_profile": ["point of control", "value area", "market profile", "time price"],
    "market_structure": ["break of structure", "swing high", "swing low", "market structure"],
    "machine_learning": ["neural network", "lstm", "machine learning", "deep learning"],
}

_CLAIM_PATTERNS: list[tuple[str, str, str]] = [
    (r"(when|if)\s+(.+?),?\s+(.+)", "rule", "condition-effect"),
    (r"(.+)\s+(acts as|serves as|functions as)\s+(.+)", "observation", "role"),
    (r"(.+)\s+correlates?\s+with\s+(.+)", "observation", "correlation"),
    (r"(.+)\s+causes?\s+(.+)", "empirical_claim", "causation"),
    (r"(.+)\s+is\s+(a|an|the)\s+(.+)", "definition", "definition"),
]


def _detect_methodology(text: str) -> str:
    text_lower = text.lower()
    for method, keywords in _METHODLOGY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return method
    return "unknown"


def _detect_claim_type(text: str) -> str:
    for pattern, ctype, _ in _CLAIM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return ctype
    return "observation"


class StubLLMModel(ResearchExtractionModel):
    def __init__(self) -> None:
        self._model_id = "stub"

    def is_available(self) -> bool:
        return True

    def model_id(self) -> str:
        return self._model_id

    def model_status(self) -> Literal['available', 'unavailable', 'error']:
        return "available"

    def extract_claims(self, request: ExtractionRequest) -> ExtractionResult:
        start = time.time()
        text = request.text
        methodology = _detect_methodology(text)
        claim_type = _detect_claim_type(text)

        source_text = text[:500]
        if len(text) > 500:
            idx = text.rfind(". ", 0, 500)
            if idx > 100:
                source_text = text[:idx + 1]

        candidate = LLMCandidateClaim(
            source_document_id=request.document_id,
            page_number=request.page_number,
            exact_source_text=source_text,
            claim_type=claim_type,
            methodology=methodology,
            claim_text=source_text,
            confidence=0.5,
            extraction_notes="stub extraction",
        )
        response = LLMExtractionResponse(
            model_id="stub",
            candidate_claims=[candidate],
            extraction_notes="stub model — deterministic keyword extraction",
            token_count=0,
        )
        latency = (time.time() - start) * 1000
        return ExtractionResult(
            claims=[candidate.model_dump()],
            model_id="stub",
            status="available",
            latency_ms=latency,
            token_count=0,
            raw_output=response.model_dump_json(),
        )
