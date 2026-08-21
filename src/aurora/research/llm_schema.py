"""LLM output schema — strict JSON schema for structured extraction.

Every LLM response must conform to this schema.
Missing information must be null, never invented.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

VALID_CLAIM_TYPES = {
    "definition", "observation", "rule", "hypothesis",
    "empirical_claim", "formula", "historical_claim", "opinion", "unknown",
}

VALID_METHODLOGIES = {
    "liquidity", "market_structure", "order_flow", "volume", "vwap",
    "market_profile", "fibonacci", "gann", "elliott_wave", "volatility",
    "technical_analysis", "news", "market_psychology", "astrology",
    "time_cycles", "quantitative_finance", "machine_learning",
    "risk_management", "unknown",
}

VALID_HORIZONS = {"tick", "intraday", "swing", "position", "unknown", None}
VALID_DIRECTIONS = {"long", "short", "neutral", "unknown", None}


class LLMCandidateClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_document_id: str = ""
    page_number: int = Field(ge=0, default=0)
    exact_source_text: str
    claim_type: str = "unknown"
    methodology: str = "unknown"
    claim_text: str = ""
    condition: str | None = None
    expected_effect: str | None = None
    target_variable: str | None = None
    horizon: str | None = None
    direction: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    extraction_notes: str = ""


class LLMExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = ""
    candidate_claims: list[LLMCandidateClaim] = Field(default_factory=list)
    extraction_notes: str = ""
    token_count: int = Field(ge=0, default=0)


class ValidatedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_document_id: str
    page_number: int = Field(ge=0, default=0)
    exact_source_text: str
    claim_type: str
    methodology: str
    claim_text: str
    condition: str | None = None
    expected_effect: str | None = None
    target_variable: str | None = None
    horizon: str | None = None
    direction: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_notes: str = ""
    validation_errors: list[str] = Field(default_factory=list)
    is_valid: bool = True
    source_grounded: bool = False
    hallucinated: bool = False
