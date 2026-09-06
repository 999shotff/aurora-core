"""
LLM-4: Investigation Schemas — domain models for the Adaptive Investigation Engine.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────


class InvestigationStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNING = "PLANNING"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    INVESTIGATING = "INVESTIGATING"
    ANALYZING = "ANALYZING"
    COMPARING = "COMPARING"
    SUFFICIENCY_CHECK = "SUFFICIENCY_CHECK"
    VALIDATING = "VALIDATING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InvestigationDomain(str, Enum):
    MARKET = "market"
    GEO = "geo"
    RESEARCH = "research"
    GENERAL = "general"


class GapStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    UNRESOLVABLE = "UNRESOLVABLE"
    BLOCKED = "BLOCKED"


class FailureClassification(str, Enum):
    NON_CRITICAL = "NON_CRITICAL_FAILURE"
    CRITICAL = "CRITICAL_FAILURE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class FindingClassification(str, Enum):
    OBSERVATION = "OBSERVATION"
    COMPARISON = "COMPARISON"
    INFERENCE = "INFERENCE"
    SYNTHESIS = "SYNTHESIS"
    UNCERTAINTY = "UNCERTAINTY"
    CONFLICT = "CONFLICT"
    ABSTENTION = "ABSTENTION"


class FindingStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"


class SufficiencyState(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTED = "CONFLICTED"


class EventType(str, Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    MEMORY_RETRIEVED = "MEMORY_RETRIEVED"
    GAP_IDENTIFIED = "GAP_IDENTIFIED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    COMPARISON_COMPLETED = "COMPARISON_COMPLETED"
    SUFFICIENCY_EVALUATED = "SUFFICIENCY_EVALUATED"
    REASONING_STARTED = "REASONING_STARTED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    RESULT_CREATED = "RESULT_CREATED"
    MEMORY_UPDATED = "MEMORY_UPDATED"
    ABSTAINED = "ABSTAINED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    STATUS_CHANGED = "STATUS_CHANGED"
    RESUMED = "RESUMED"


class ComparisonChangeType(str, Enum):
    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"
    NEW = "new"
    MISSING = "missing"
    CONFLICTING = "conflicting"


# ── Investigation Objective ────────────────────────────────────────────────


class InvestigationObjective(BaseModel):
    """Represents the user's investigation objective explicitly."""

    model_config = {"extra": "forbid"}

    query: str = Field(..., min_length=1, max_length=10000)
    domain: InvestigationDomain = InvestigationDomain.GENERAL
    subject: str = Field(default="", max_length=500)
    scope: str = Field(default="", max_length=1000)
    temporal_range: dict[str, Any] = Field(default_factory=dict)
    requested_output: str = Field(default="structured")
    constraints: list[str] = Field(default_factory=list)


# ── Evidence Gap ───────────────────────────────────────────────────────────


class EvidenceGap(BaseModel):
    """Identifies missing evidence required for the investigation."""

    model_config = {"extra": "forbid"}

    gap_id: str = Field(default_factory=lambda: f"gap-{uuid.uuid4().hex[:8]}")
    description: str
    required_domain: str = ""
    required_evidence_type: str = ""
    priority: int = Field(default=5, ge=1, le=10)
    reason: str = ""
    status: GapStatus = GapStatus.OPEN
    resolvable: bool = True
    candidate_tools: list[str] = Field(default_factory=list)
    resolved_by: str | None = None


# ── Finding ────────────────────────────────────────────────────────────────


class Finding(BaseModel):
    """A structured finding from the investigation."""

    model_config = {"extra": "forbid"}

    finding_id: str = Field(default_factory=lambda: f"find-{uuid.uuid4().hex[:8]}")
    statement: str
    classification: FindingClassification = FindingClassification.OBSERVATION
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: FindingStatus = FindingStatus.UNCERTAIN
    temporal_scope: str = ""
    details: str = ""


# ── Deterministic Comparison ───────────────────────────────────────────────


class ComparisonDelta(BaseModel):
    """A single deterministic comparison between baseline and current values."""

    model_config = {"extra": "forbid"}

    field_name: str
    baseline_value: Any = None
    current_value: Any = None
    delta: Any = None
    change_type: ComparisonChangeType = ComparisonChangeType.UNCHANGED
    unit: str = ""


class InvestigationComparison(BaseModel):
    """Deterministic comparison between baseline and current evidence."""

    model_config = {"extra": "forbid"}

    baseline_refs: list[str] = Field(default_factory=list)
    current_refs: list[str] = Field(default_factory=list)
    deltas: list[ComparisonDelta] = Field(default_factory=list)
    unchanged: list[str] = Field(default_factory=list)
    new_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    comparison_timestamp: float = Field(default_factory=time.time)


# ── Investigation Event (Audit Trail) ─────────────────────────────────────


class InvestigationEvent(BaseModel):
    """An auditable event in the investigation lifecycle."""

    model_config = {"extra": "forbid"}

    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    timestamp: float = Field(default_factory=time.time)
    event_type: EventType
    investigation_id: str
    step_id: str | None = None
    summary: str = ""
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Investigation Plan ─────────────────────────────────────────────────────


class InvestigationPlanStep(BaseModel):
    """A single step in the investigation plan."""

    model_config = {"extra": "forbid"}

    step_id: str = Field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8]}")
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    gap_id: str | None = None
    timeout_seconds: float = 30.0


class InvestigationPlan(BaseModel):
    """A bounded plan for the investigation."""

    model_config = {"extra": "forbid"}

    plan_id: str = Field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}")
    steps: list[InvestigationPlanStep] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    estimated_duration_seconds: float = 0.0
    created_at: float = Field(default_factory=time.time)


# ── Investigation Result ───────────────────────────────────────────────────


class InvestigationResult(BaseModel):
    """The complete result of an investigation."""

    model_config = {"extra": "forbid"}

    investigation_id: str
    status: InvestigationStatus
    executive_summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    comparisons: list[InvestigationComparison] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    data_quality: dict[str, Any] = Field(default_factory=dict)
    generated_at: float = Field(default_factory=time.time)
    abstention_reason: str | None = None


# ── Investigation Record ──────────────────────────────────────────────────


class InvestigationRecord(BaseModel):
    """The core investigation entity."""

    model_config = {"extra": "forbid"}

    investigation_id: str = Field(
        default_factory=lambda: f"inv-{uuid.uuid4().hex[:12]}"
    )
    objective: InvestigationObjective
    status: InvestigationStatus = InvestigationStatus.DRAFT
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    plan: InvestigationPlan | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    tool_runs: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    result: InvestigationResult | None = None
    events: list[InvestigationEvent] = Field(default_factory=list)
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Investigation Limits ──────────────────────────────────────────────────


class InvestigationLimits(BaseModel):
    """Configurable safety limits for an investigation."""

    model_config = {"extra": "forbid"}

    max_steps: int = Field(default=8, ge=1, le=50)
    max_planning_iterations: int = Field(default=2, ge=1, le=10)
    max_synthesis_calls: int = Field(default=1, ge=0, le=5)
    max_memory_results: int = Field(default=10, ge=1, le=100)
    max_evidence_results: int = Field(default=50, ge=1, le=500)
    max_runtime_seconds: float = Field(default=300.0, ge=30.0, le=3600.0)
    max_context_size: int = Field(default=50000, ge=1000, le=200000)
    max_tool_result_size: int = Field(default=10000, ge=1000, le=100000)


# ── Helpers ────────────────────────────────────────────────────────────────


def generate_investigation_id() -> str:
    """Generate a unique investigation ID."""
    return f"inv-{uuid.uuid4().hex[:12]}"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt-{uuid.uuid4().hex[:8]}"
