"""
LLM-4: Adaptive Investigation Engine — bounded, auditable investigation orchestration.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

from aurora.investigation.schemas import (
    InvestigationStatus,
    InvestigationDomain,
    GapStatus,
    FindingClassification,
    FindingStatus,
    SufficiencyState,
    EventType,
    ComparisonChangeType,
    FailureClassification,
    InvestigationObjective,
    EvidenceGap,
    Finding,
    ComparisonDelta,
    InvestigationComparison,
    InvestigationEvent,
    InvestigationPlanStep,
    InvestigationPlan,
    InvestigationResult,
    InvestigationRecord,
    InvestigationLimits,
    generate_investigation_id,
    generate_event_id,
)

from aurora.investigation.errors import (
    InvestigationError,
    InvestigationLimitExceeded,
    InvestigationTimeout,
    InvestigationCancelled,
    InvestigationNotFound,
    EvidenceUnavailable,
    InsufficientEvidence,
    ToolExecutionError,
    PlanValidationFailed,
    DuplicateInvestigation,
    SecurityViolation as InvestigationSecurityViolation,
)

from aurora.investigation.store import InvestigationStore
from aurora.investigation.planner import InvestigationPlanner
from aurora.investigation.executor import InvestigationExecutor, ExecutorResult
from aurora.investigation.comparison import compare_deterministic
from aurora.investigation.lifecycle import (
    can_transition,
    transition,
    start_investigation,
    complete_investigation,
    cancel_investigation,
)
from aurora.investigation.manager import InvestigationManager

__all__ = [
    "ComparisonChangeType",
    "ComparisonDelta",
    "DuplicateInvestigation",
    "EventType",
    "EvidenceGap",
    "EvidenceUnavailable",
    "ExecutorResult",
    "FailureClassification",
    "Finding",
    "FindingClassification",
    "FindingStatus",
    "GapStatus",
    "InsufficientEvidence",
    "InvestigationCancelled",
    "InvestigationComparison",
    "InvestigationDomain",
    "InvestigationError",
    "InvestigationEvent",
    "InvestigationExecutor",
    "InvestigationLimitExceeded",
    "InvestigationLimits",
    "InvestigationManager",
    "InvestigationNotFound",
    "InvestigationObjective",
    "InvestigationPlan",
    "InvestigationPlanStep",
    "InvestigationPlanner",
    "InvestigationRecord",
    "InvestigationResult",
    "InvestigationSecurityViolation",
    "InvestigationStatus",
    "InvestigationStore",
    "InvestigationTimeout",
    "PlanValidationFailed",
    "SufficiencyState",
    "ToolExecutionError",
    "can_transition",
    "cancel_investigation",
    "compare_deterministic",
    "complete_investigation",
    "generate_event_id",
    "generate_investigation_id",
    "start_investigation",
    "transition",
]
