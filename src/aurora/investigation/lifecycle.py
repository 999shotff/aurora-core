"""
LLM-4: Investigation Lifecycle — state transitions and validation.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import time

from aurora.investigation.schemas import (
    InvestigationEvent,
    InvestigationRecord,
    InvestigationStatus,
    EventType,
)
from aurora.investigation.errors import InvestigationError

# ── Valid State Transitions ────────────────────────────────────────────────

VALID_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    InvestigationStatus.DRAFT: {
        InvestigationStatus.PLANNING,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.PLANNING: {
        InvestigationStatus.MEMORY_RETRIEVAL,
        InvestigationStatus.GAP_ANALYSIS,
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.MEMORY_RETRIEVAL: {
        InvestigationStatus.GAP_ANALYSIS,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.GAP_ANALYSIS: {
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.ABSTAINED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.INVESTIGATING: {
        InvestigationStatus.ANALYZING,
        InvestigationStatus.PARTIAL,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.ANALYZING: {
        InvestigationStatus.COMPARING,
        InvestigationStatus.SYNTHESIZING,
        InvestigationStatus.PARTIAL,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.COMPARING: {
        InvestigationStatus.SUFFICIENCY_CHECK,
        InvestigationStatus.SYNTHESIZING,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.SUFFICIENCY_CHECK: {
        InvestigationStatus.VALIDATING,
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.PARTIAL,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.VALIDATING: {
        InvestigationStatus.SYNTHESIZING,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.SYNTHESIZING: {
        InvestigationStatus.COMPLETE,
        InvestigationStatus.PARTIAL,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.COMPLETE: {
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.PARTIAL: {
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.ABSTAINED: {
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.FAILED: {
        InvestigationStatus.INVESTIGATING,
        InvestigationStatus.CANCELLED,
    },
    InvestigationStatus.CANCELLED: {
        InvestigationStatus.INVESTIGATING,
    },
}


def can_transition(
    current: InvestigationStatus, target: InvestigationStatus
) -> bool:
    """Check if a state transition is valid."""
    return target in VALID_TRANSITIONS.get(current, set())


def transition(
    record: InvestigationRecord,
    target: InvestigationStatus,
    summary: str = "",
    references: list[str] | None = None,
) -> InvestigationEvent:
    """
    Validate and execute a state transition.

    Raises InvestigationError if transition is invalid.
    """
    if not can_transition(record.status, target):
        raise InvestigationError(
            f"Invalid transition: {record.status.value} -> {target.value}"
        )

    old_status = record.status
    record.status = target
    record.updated_at = time.time()

    if target == InvestigationStatus.PLANNING and record.started_at is None:
        record.started_at = time.time()

    if target in (
        InvestigationStatus.COMPLETE,
        InvestigationStatus.PARTIAL,
        InvestigationStatus.ABSTAINED,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
    ):
        record.completed_at = time.time()

    event = InvestigationEvent(
        event_type=EventType.STATUS_CHANGED,
        investigation_id=record.investigation_id,
        summary=summary or f"Status: {old_status.value} -> {target.value}",
        references=references or [],
        metadata={"old_status": old_status.value, "new_status": target.value},
    )
    record.events.append(event)
    return event


def start_investigation(record: InvestigationRecord) -> InvestigationEvent:
    """Transition from DRAFT to PLANNING."""
    return transition(record, InvestigationStatus.PLANNING, "Investigation started")


def complete_investigation(
    record: InvestigationRecord, summary: str = ""
) -> InvestigationEvent:
    """Transition to COMPLETE."""
    return transition(record, InvestigationStatus.COMPLETE, summary or "Investigation complete")


def cancel_investigation(
    record: InvestigationRecord, reason: str = ""
) -> InvestigationEvent:
    """Transition to CANCELLED."""
    return transition(record, InvestigationStatus.CANCELLED, reason or "Investigation cancelled")
