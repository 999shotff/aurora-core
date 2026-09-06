"""AURORA Reasoning Core — LLM-1 Domain Model.

Strict Pydantic schemas for the reasoning lifecycle.
Every model enforces extra="forbid" to prevent unvalidated blobs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Enums
# ============================================================


class ReasoningDomain(str, Enum):
    MARKET = "market"
    GEO = "geo"
    RESEARCH = "research"
    GENERAL = "general"


class TaskType(str, Enum):
    ANALYZE_MARKET = "ANALYZE_MARKET"
    EXPLAIN_MARKET = "EXPLAIN_MARKET"
    ANALYZE_GEO = "ANALYZE_GEO"
    EXPLAIN_GEO = "EXPLAIN_GEO"
    SUMMARIZE_RESEARCH = "SUMMARIZE_RESEARCH"
    COMPARE_EVIDENCE = "COMPARE_EVIDENCE"
    EXPLAIN_EVIDENCE = "EXPLAIN_EVIDENCE"
    GENERAL_RESEARCH = "GENERAL_RESEARCH"


class ReasoningStatus(str, Enum):
    IDLE = "IDLE"
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    ROUTING = "ROUTING"
    DATA_INGESTION = "DATA_INGESTION"
    EVIDENCE_ASSEMBLY = "EVIDENCE_ASSEMBLY"
    DETERMINISTIC_ANALYSIS = "DETERMINISTIC_ANALYSIS"
    LLM_REASONING = "LLM_REASONING"
    VALIDATION = "VALIDATION"
    SYNTHESIS = "SYNTHESIS"
    COMPLETE = "COMPLETE"
    ABSTAINED = "ABSTAINED"
    ERROR = "ERROR"


class EvidenceGrounding(str, Enum):
    SUPPORTED_BY_EVIDENCE = "SUPPORTED_BY_EVIDENCE"
    INFERENCE = "INFERENCE"
    UNCERTAIN = "UNCERTAIN"
    ABSTAINED = "ABSTAINED"


class EvidenceSource(str, Enum):
    MARKET_DATA = "market_data"
    MARKET_ANALYSIS = "market_analysis"
    GEO_OBSERVATION = "geo_observation"
    GEO_CHANGE = "geo_change"
    GEO_TIMESERIES = "geo_timeseries"
    RESEARCH_CLAIM = "research_claim"
    USER_INPUT = "user_input"


# ============================================================
# Evidence
# ============================================================


class EvidenceRecord(BaseModel):
    """A single piece of evidence supplied to the reasoning engine."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: EvidenceSource
    domain: ReasoningDomain
    claim: str
    value: str = ""
    timestamp: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: str = ""
    quality: str = "verified"


# ============================================================
# Request
# ============================================================


class ReasoningRequest(BaseModel):
    """User request for reasoning."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    user_query: str = Field(..., min_length=1, max_length=10000)
    domain: ReasoningDomain = ReasoningDomain.GENERAL
    task_type: TaskType = TaskType.GENERAL_RESEARCH
    context_ids: list[str] = Field(default_factory=list)
    requested_output: str = "structured"
    constraints: list[str] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ============================================================
# Context
# ============================================================


class ReasoningContext(BaseModel):
    """Bounded evidence package sent to the LLM."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    evidence_items: list[EvidenceRecord] = Field(default_factory=list)
    context_hash: str = ""
    total_evidence: int = 0
    domain_summary: str = ""
    constraints: list[str] = Field(default_factory=list)


# ============================================================
# Response
# ============================================================


class ReasoningPoint(BaseModel):
    """A single reasoning step with evidence grounding."""

    model_config = ConfigDict(extra="forbid")

    point: str
    grounding: EvidenceGrounding = EvidenceGrounding.INFERENCE
    evidence_refs: list[str] = Field(default_factory=list)


class ReasoningResponse(BaseModel):
    """Structured output from the reasoning engine."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: ReasoningStatus = ReasoningStatus.COMPLETE
    answer: str = ""
    summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    reasoning_points: list[ReasoningPoint] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    abstention_reason: str | None = None
    provider: str = ""
    model: str = ""
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    context_hash: str = ""
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0)


# ============================================================
# Provider Metadata
# ============================================================


class ProviderMetadata(BaseModel):
    """Metadata about the provider used for reasoning."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    context_limit: int = 0
    cost_usd: float = 0.0
