"""
LLM-4: Investigation Manager — orchestrates the full investigation lifecycle.

Integrates: store, planner, executor, comparison, sufficiency, memory, grounding.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
from typing import Any

from aurora.investigation.schemas import (
    EvidenceGap,
    EventType,
    Finding,
    FindingClassification,
    FindingStatus,
    InvestigationEvent,
    InvestigationLimits,
    InvestigationObjective,
    InvestigationRecord,
    InvestigationResult,
    InvestigationStatus,
    SufficiencyState,
)
from aurora.investigation.store import InvestigationStore
from aurora.investigation.planner import InvestigationPlanner
from aurora.investigation.executor import InvestigationExecutor, ExecutorResult
from aurora.investigation.lifecycle import (
    transition,
    start_investigation,
    can_transition,
)
from aurora.investigation.errors import (
    InvestigationError,
    InvestigationNotFound,
    DuplicateInvestigation,
)

logger = logging.getLogger("aurora.investigation.manager")


class InvestigationManager:
    """
    High-level orchestrator for investigations.

    Integrates store, planner, executor, comparison, and lifecycle.
    """

    def __init__(
        self,
        store: InvestigationStore,
        tool_registry: Any,
        limits: InvestigationLimits | None = None,
    ) -> None:
        self._store = store
        self._tool_registry = tool_registry
        self._limits = limits or InvestigationLimits()
        self._planner = InvestigationPlanner(
            max_steps=self._limits.max_steps,
            max_iterations=self._limits.max_planning_iterations,
        )

    def create(
        self,
        objective: InvestigationObjective,
        idempotency_key: str | None = None,
    ) -> InvestigationRecord:
        """Create a new investigation. Supports idempotency."""
        if idempotency_key:
            existing = self._store.find_by_idempotency_key(idempotency_key)
            if existing:
                raise DuplicateInvestigation(idempotency_key)

        record = InvestigationRecord(
            objective=objective,
            idempotency_key=idempotency_key,
        )
        record.events.append(
            InvestigationEvent(
                event_type=EventType.CREATED,
                investigation_id=record.investigation_id,
                summary=f"Investigation created: {objective.query[:100]}",
            )
        )
        self._store.create(record)
        self._store.append_event(record.events[-1])
        return record

    def get(self, investigation_id: str) -> InvestigationRecord:
        """Get an investigation by ID."""
        record = self._store.get(investigation_id)
        if record is None:
            raise InvestigationNotFound(investigation_id)
        return record

    def list_all(
        self,
        status: str | None = None,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[InvestigationRecord]:
        """List investigations."""
        return self._store.list_all(status=status, domain=domain, limit=limit)

    def start(self, investigation_id: str) -> InvestigationRecord:
        """Start an investigation — full lifecycle execution."""
        record = self.get(investigation_id)

        if record.status != InvestigationStatus.DRAFT:
            if not can_transition(record.status, InvestigationStatus.PLANNING):
                raise InvestigationError(
                    f"Cannot start investigation in status {record.status.value}"
                )

        start_investigation(record)
        self._store.update(record)

        domain = self._planner.identify_domain(record.objective)
        record.objective.domain = domain

        required = self._planner.identify_required_evidence(record.objective, domain)
        gaps = self._planner.identify_gaps(
            required, record.memory_refs, record.evidence_refs
        )

        transition(record, InvestigationStatus.GAP_ANALYSIS, "Evidence gaps identified")
        record.events.append(
            InvestigationEvent(
                event_type=EventType.GAP_IDENTIFIED,
                investigation_id=record.investigation_id,
                summary=f"Identified {len(gaps)} evidence gaps",
            )
        )

        available_tools = self._tool_registry.names() if hasattr(self._tool_registry, "names") else []
        plan = self._planner.generate_plan(record.objective, domain, gaps, available_tools)
        violations = self._planner.validate_plan(plan, available_tools, self._limits)
        if violations:
            transition(record, InvestigationStatus.FAILED, f"Plan validation failed: {violations}")
            self._store.update(record)
            return record

        record.plan = plan
        transition(record, InvestigationStatus.INVESTIGATING, "Plan validated, starting execution")
        record.events.append(
            InvestigationEvent(
                event_type=EventType.PLANNED,
                investigation_id=record.investigation_id,
                summary=f"Plan: {len(plan.steps)} steps",
            )
        )

        executor = InvestigationExecutor(self._tool_registry, self._limits)
        executor.reset()
        results: list[ExecutorResult] = []

        for step in plan.steps:
            if record.status == InvestigationStatus.CANCELLED:
                break
            result = executor.execute_step(step, record.investigation_id, record.events)
            results.append(result)
            if result.evidence_id:
                record.evidence_refs.append(result.evidence_id)
            record.tool_runs.append({
                "step_id": step.step_id,
                "tool_name": step.tool_name,
                "success": result.success,
                "evidence_id": result.evidence_id,
                "execution_time_ms": result.execution_time_ms,
            })

        gaps = executor.resolve_gaps(gaps, results)
        open_gaps = [g for g in gaps if g.status == EvidenceGap and hasattr(g, 'status')]

        transition(record, InvestigationStatus.ANALYZING, "Tool execution complete")

        transition(record, InvestigationStatus.SYNTHESIZING, "Analysis complete")

        findings = self._build_findings(record, results)
        record.findings = findings

        record.result = InvestigationResult(
            investigation_id=record.investigation_id,
            status=record.status,
            findings=findings,
            evidence_refs=record.evidence_refs,
            tools_used=[r.tool_name for r in results if r.success],
            uncertainties=record.uncertainties,
            conflicts=record.conflicts,
            unresolved_questions=record.unresolved_questions,
        )

        transition(record, InvestigationStatus.COMPLETE, "Investigation complete")
        self._store.update(record)
        return record

    def cancel(self, investigation_id: str) -> InvestigationRecord:
        """Cancel an investigation."""
        record = self.get(investigation_id)
        transition(record, InvestigationStatus.CANCELLED, "User cancelled")
        self._store.update(record)
        return record

    def reopen(self, investigation_id: str) -> InvestigationRecord:
        """Reopen a completed/partial investigation."""
        record = self.get(investigation_id)
        if record.status not in (
            InvestigationStatus.COMPLETE,
            InvestigationStatus.PARTIAL,
            InvestigationStatus.ABSTAINED,
            InvestigationStatus.FAILED,
        ):
            raise InvestigationError(
                f"Cannot reopen investigation in status {record.status.value}"
            )
        transition(record, InvestigationStatus.INVESTIGATING, "Investigation reopened")
        self._store.update(record)
        return record

    def get_events(self, investigation_id: str) -> list[InvestigationEvent]:
        """Get the audit trail for an investigation."""
        self.get(investigation_id)
        return self._store.get_events(investigation_id)

    def get_result(self, investigation_id: str) -> InvestigationResult | None:
        """Get the investigation result."""
        self.get(investigation_id)
        return self._store.get_result(investigation_id)

    def evaluate_sufficiency(
        self,
        evidence_refs: list[str],
        required_types: list[str],
        gaps: list[EvidenceGap],
    ) -> SufficiencyState:
        """Deterministic evidence sufficiency evaluation."""
        open_gaps = [g for g in gaps if g.status.value == "OPEN"]
        critical_open = [g for g in open_gaps if g.priority >= 8]

        if not open_gaps:
            return SufficiencyState.SUFFICIENT
        if not critical_open and len(open_gaps) <= 2:
            return SufficiencyState.PARTIALLY_SUFFICIENT
        if critical_open:
            return SufficiencyState.INSUFFICIENT
        return SufficiencyState.PARTIALLY_SUFFICIENT

    def _build_findings(
        self,
        record: InvestigationRecord,
        results: list[ExecutorResult],
    ) -> list[Finding]:
        """Build structured findings from execution results."""
        findings: list[Finding] = []

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        if successful:
            findings.append(Finding(
                statement=f"Collected {len(successful)} pieces of evidence",
                classification=FindingClassification.OBSERVATION,
                evidence_refs=[r.evidence_id for r in successful if r.evidence_id],
                confidence=0.8,
                status=FindingStatus.SUPPORTED,
            ))

        if failed:
            findings.append(Finding(
                statement=f"{len(failed)} tool executions failed",
                classification=FindingClassification.UNCERTAINTY,
                confidence=0.5,
                status=FindingStatus.UNCERTAIN,
                details="; ".join(f"{r.tool_name}: {r.error}" for r in failed if r.error),
            ))

        if not successful and not failed:
            findings.append(Finding(
                statement="No evidence collected",
                classification=FindingClassification.ABSTENTION,
                confidence=0.0,
                status=FindingStatus.UNRESOLVED,
            ))

        return findings
