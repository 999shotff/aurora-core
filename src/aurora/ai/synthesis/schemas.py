"""LLM-5 Synthesis Schemas.

Strict Pydantic models for evidence-grounded synthesis.
All models are deterministic, serializable, and provenance-aware.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Enums
# ============================================================


class SynthesisStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INDETERMINATE = "INDETERMINATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


class ConfidenceLevel(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    UNDETERMINED = "UNDETERMINED"


class HypothesisStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ContradictionType(str, Enum):
    DIRECT = "DIRECT"
    NUMERICAL = "NUMERICAL"
    TEMPORAL = "TEMPORAL"
    SOURCE_DISAGREEMENT = "SOURCE_DISAGREEMENT"
    SEMANTIC = "SEMANTIC"


class UncertaintyKind(str, Enum):
    KNOWN = "KNOWN"
    SUPPORTED_INFERENCE = "SUPPORTED_INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"
    UNAVAILABLE = "UNAVAILABLE"


class CausalLevel(str, Enum):
    CORRELATION = "CORRELATION"
    TEMPORAL_ASSOCIATION = "TEMPORAL_ASSOCIATION"
    MECHANISTIC_EVIDENCE = "MECHANISTIC_EVIDENCE"
    CAUSAL_EVIDENCE = "CAUSAL_EVIDENCE"
    INSUFFICIENT = "INSUFFICIENT"


class MemoryUpdateType(str, Enum):
    NEW_KNOWLEDGE = "NEW_KNOWLEDGE"
    UPDATED_KNOWLEDGE = "UPDATED_KNOWLEDGE"
    CONTRADICTION = "CONTRADICTION"
    SUPERSEDED_KNOWLEDGE = "SUPERSEDED_KNOWLEDGE"
    UNRESOLVED_FINDING = "UNRESOLVED_FINDING"


class EvidenceGapStatus(str, Enum):
    OPEN = "OPEN"
    IDENTIFIED = "IDENTIFIED"
    NOT_CONNECTED = "NOT_CONNECTED"


# ============================================================
# Core Models
# ============================================================


class SynthesisRequest(BaseModel):
    """Input request for synthesis."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=10000)
    investigation_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    domain: str = "general"
    comparison_context: str | None = None
    requested_output: str = "full"
    decision_context: str | None = None
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


class EvidenceAssessment(BaseModel):
    """Assessment of a single evidence item."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: str
    evidence_type: str
    domain: str
    claim: str
    freshness: str = "UNKNOWN"
    relevance: ConfidenceLevel = ConfidenceLevel.UNDETERMINED
    reliability: ConfidenceLevel = ConfidenceLevel.UNDETERMINED
    direct_vs_derived: str = "UNKNOWN"
    supporting_findings: list[str] = Field(default_factory=list)
    contradicting_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class FindingAssessment(BaseModel):
    """Assessment of a single finding."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    statement: str
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    provenance: str = ""
    status: HypothesisStatus = HypothesisStatus.UNRESOLVED
    confidence: ConfidenceLevel = ConfidenceLevel.UNDETERMINED
    uncertainty: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""


class Hypothesis(BaseModel):
    """A competing explanatory hypothesis."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    statement: str
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    unresolved_evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNDETERMINED
    status: HypothesisStatus = HypothesisStatus.UNRESOLVED


class HypothesisComparison(BaseModel):
    """Comparison between competing hypotheses."""

    model_config = ConfigDict(extra="forbid")

    hypotheses: list[Hypothesis]
    distinguishing_evidence: list[str] = Field(default_factory=list)
    unresolved_question: str = ""
    determination: str = "INDETERMINATE"


class ContradictionAssessment(BaseModel):
    """Detected contradiction between evidence items."""

    model_config = ConfigDict(extra="forbid")

    contradiction_id: str
    contradiction_type: ContradictionType
    evidence_a: str
    evidence_b: str
    description: str
    resolution_basis: str | None = None
    severity: str = "INFO"


class UncertaintyAssessment(BaseModel):
    """Uncertainty classification for a conclusion."""

    model_config = ConfigDict(extra="forbid")

    element: str
    kind: UncertaintyKind
    description: str
    impact: str = ""
    reduction_path: str | None = None


class Scenario(BaseModel):
    """Conditional scenario analysis."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    label: str
    assumptions: list[str] = Field(default_factory=list)
    evidence_basis: list[str] = Field(default_factory=list)
    trigger_conditions: list[str] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class EvidenceGap(BaseModel):
    """Identified gap in evidence coverage."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    description: str
    why_it_matters: str = ""
    distinguishes_hypotheses: list[str] = Field(default_factory=list)
    expected_uncertainty_reduction: str = ""
    available_source: str = ""
    status: EvidenceGapStatus = EvidenceGapStatus.OPEN


class DecisionConsideration(BaseModel):
    """Decision-support consideration (not a command)."""

    model_config = ConfigDict(extra="forbid")

    consideration: str
    evidence_basis: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNDETERMINED
    key_uncertainty: str = ""
    assumption_dependency: str = ""


class MemoryUpdateProposal(BaseModel):
    """Proposed memory update from synthesis."""

    model_config = ConfigDict(extra="forbid")

    update_type: MemoryUpdateType
    title: str
    content: str
    domain: str
    source_investigation: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    previous_memory_id: str | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNDETERMINED


class ProvenanceRecord(BaseModel):
    """Traceability record for a conclusion."""

    model_config = ConfigDict(extra="forbid")

    conclusion: str
    finding_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    reasoning_chain: list[str] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    """Complete synthesis output."""

    model_config = ConfigDict(extra="forbid")

    synthesis_id: str
    question: str
    executive_summary: str = ""
    key_findings: list[FindingAssessment] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    contradictions: list[ContradictionAssessment] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    supported_inferences: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    decision_considerations: list[DecisionConsideration] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRecord] = Field(default_factory=list)
    memory_updates: list[MemoryUpdateProposal] = Field(default_factory=list)
    synthesis_status: SynthesisStatus = SynthesisStatus.FAILED
    evidence_assessments: list[EvidenceAssessment] = Field(default_factory=list)
    uncertainty_assessments: list[UncertaintyAssessment] = Field(default_factory=list)
    causal_level: CausalLevel = CausalLevel.INSUFFICIENT
    provider: str = "stub"
    model: str = "stub"
    context_hash: str = ""
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


# ============================================================
# Audit
# ============================================================


class SynthesisAuditRecord(BaseModel):
    """Audit log entry for synthesis execution."""

    model_config = ConfigDict(extra="forbid")

    synthesis_id: str
    investigation_id: str | None = None
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    provider: str = ""
    model: str = ""
    context_hash: str = ""
    evidence_references: list[str] = Field(default_factory=list)
    memory_references: list[str] = Field(default_factory=list)
    validation_result: str = ""
    final_status: str = ""
