"""Unified Analysis — shared analysis contracts.

Defines the AnalysisInput envelope and EvidenceClass classification
that all analysis sources must use.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Evidence Classification
# ============================================================


class EvidenceClass(str, Enum):
    """Mandatory classification for every analytical contribution."""

    OBSERVED = "OBSERVED"           # Direct real-world observation
    DERIVED = "DERIVED"             # Computed from observations (indicators)
    STATISTICAL = "STATISTICAL"     # Statistical test result
    SIMULATED = "SIMULATED"         # Behavioral simulation (MatrAIx)
    HYPOTHESIS = "HYPOTHESIS"       # Unvalidated hypothesis (Gann, cycles)
    UNAVAILABLE = "UNAVAILABLE"     # Data not available


class AnalysisSourceType(str, Enum):
    """Types of analysis sources."""

    MARKET_INDICATORS = "MARKET_INDICATORS"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    MARKET_CONTEXT = "MARKET_CONTEXT"
    TECHNICAL_ANALYSIS = "TECHNICAL_ANALYSIS"
    CYCLE_ANALYSIS = "CYCLE_ANALYSIS"
    PERSONA_SIMULATION = "PERSONA_SIMULATION"
    REGIME_DETECTION = "REGIME_DETECTION"
    RESEARCH_EVIDENCE = "RESEARCH_EVIDENCE"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    INVESTIGATION = "INVESTIGATION"
    GEO_OBSERVATION = "GEO_OBSERVATION"
    NEWS = "NEWS"
    EXTERNAL = "EXTERNAL"


class MethodologyType(str, Enum):
    """How the analysis was produced."""

    DETERMINISTIC = "DETERMINISTIC"
    STATISTICAL = "STATISTICAL"
    SIMULATION = "SIMULATION"
    HYPOTHETICAL = "HYPOTHETICAL"
    LLM_REASONING = "LLM_REASONING"
    HUMAN_INPUT = "HUMAN_INPUT"
    UNKNOWN = "UNKNOWN"


# ============================================================
# Analysis Input Envelope
# ============================================================


class AnalysisInput(BaseModel):
    """Shared envelope for all analytical contributions.

    Every analysis source MUST produce this envelope.
    EvidenceClass is mandatory — no contribution can omit classification.
    """

    model_config = ConfigDict(extra="forbid")

    source_type: AnalysisSourceType
    source_id: str = Field(..., min_length=1, max_length=128)
    timestamp: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )
    domain: str = "general"
    asset: str | None = None
    timeframe: str | None = None

    # Evidence classification — MANDATORY
    evidence_class: EvidenceClass
    methodology: MethodologyType = MethodologyType.UNKNOWN

    # Content
    observations: dict[str, Any] = Field(default_factory=dict)
    features: dict[str, Any] = Field(default_factory=dict)
    indicators: dict[str, Any] = Field(default_factory=dict)
    structure: dict[str, Any] = Field(default_factory=dict)
    regime: str | None = None

    # Quality
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    sample_size: int | None = None
    limitations: list[str] = Field(default_factory=list)

    # Provenance
    methodology_description: str = ""
    data_source: str = ""
    provenance_chain: list[str] = Field(default_factory=list)


class AnalysisCollection(BaseModel):
    """Collection of analysis inputs for a single question/request."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=10000)
    inputs: list[AnalysisInput] = Field(default_factory=list)
    asset: str | None = None
    timeframe: str | None = None
    domain: str = "general"
    timestamp: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )

    @property
    def evidence_classes(self) -> dict[EvidenceClass, int]:
        """Count contributions by evidence class."""
        counts: dict[EvidenceClass, int] = {}
        for inp in self.inputs:
            counts[inp.evidence_class] = counts.get(inp.evidence_class, 0) + 1
        return counts

    @property
    def has_simulated(self) -> bool:
        return any(i.evidence_class == EvidenceClass.SIMULATED for i in self.inputs)

    @property
    def has_hypothesis(self) -> bool:
        return any(i.evidence_class == EvidenceClass.HYPOTHESIS for i in self.inputs)

    @property
    def observed_count(self) -> int:
        return sum(1 for i in self.inputs if i.evidence_class == EvidenceClass.OBSERVED)

    @property
    def derived_count(self) -> int:
        return sum(1 for i in self.inputs if i.evidence_class == EvidenceClass.DERIVED)

    def get_by_type(self, source_type: AnalysisSourceType) -> list[AnalysisInput]:
        return [i for i in self.inputs if i.source_type == source_type]

    def get_by_class(self, evidence_class: EvidenceClass) -> list[AnalysisInput]:
        return [i for i in self.inputs if i.evidence_class == evidence_class]
