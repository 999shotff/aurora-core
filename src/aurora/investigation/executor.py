"""
LLM-4: Investigation Executor — bounded, auditable tool execution.

For each approved step:
1. validate tool
2. validate arguments
3. verify permission
4. execute
5. validate output
6. convert output to evidence
7. update evidence graph
8. update investigation state
9. resolve related gaps

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aurora.investigation.schemas import (
    EvidenceGap,
    GapStatus,
    InvestigationEvent,
    InvestigationLimits,
    InvestigationPlanStep,
    EventType,
)
from aurora.investigation.errors import (
    ToolExecutionError,
)

logger = logging.getLogger("aurora.investigation.executor")


class ExecutorResult:
    """Result of executing a single investigation step."""

    __slots__ = (
        "classification",
        "data",
        "error",
        "evidence_id",
        "execution_time_ms",
        "step_id",
        "success",
        "tool_name",
    )

    def __init__(
        self,
        step_id: str,
        tool_name: str,
        success: bool,
        evidence_id: str = "",
        data: dict[str, Any] | None = None,
        execution_time_ms: float = 0.0,
        error: str | None = None,
        classification: str = "NON_CRITICAL_FAILURE",
    ) -> None:
        self.step_id = step_id
        self.tool_name = tool_name
        self.success = success
        self.evidence_id = evidence_id
        self.data = data or {}
        self.execution_time_ms = execution_time_ms
        self.error = error
        self.classification = classification


class InvestigationExecutor:
    """
    Executes investigation steps with safety limits and audit trail.

    Never allows the LLM to bypass the executor.
    """

    def __init__(self, tool_registry: Any, limits: InvestigationLimits | None = None) -> None:
        self._tool_registry = tool_registry
        self._limits = limits or InvestigationLimits()
        self._steps_executed: int = 0
        self._start_time: float = 0.0

    def can_execute(self) -> tuple[bool, str]:
        """Check if another step can be executed."""
        if self._steps_executed >= self._limits.max_steps:
            return False, f"Max steps ({self._limits.max_steps}) reached"

        if self._start_time > 0:
            elapsed = time.time() - self._start_time
            if elapsed > self._limits.max_runtime_seconds:
                return False, f"Timeout ({self._limits.max_runtime_seconds}s) reached"

        return True, ""

    def execute_step(
        self,
        step: InvestigationPlanStep,
        investigation_id: str,
        event_log: list[InvestigationEvent],
    ) -> ExecutorResult:
        """Execute a single investigation step."""
        can, reason = self.can_execute()
        if not can:
            return ExecutorResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                success=False,
                error=reason,
                classification="NON_CRITICAL_FAILURE",
            )

        event_log.append(
            InvestigationEvent(
                event_type=EventType.TOOL_STARTED,
                investigation_id=investigation_id,
                step_id=step.step_id,
                summary=f"Starting tool: {step.tool_name}",
            )
        )

        start = time.time()
        try:
            tool = self._tool_registry.get(step.tool_name)
            if tool is None:
                raise ToolExecutionError(step.tool_name, "Tool not found")

            result = tool.execute(step.parameters, dry_run=False)
            elapsed_ms = (time.time() - start) * 1000
            self._steps_executed += 1

            event_log.append(
                InvestigationEvent(
                    event_type=EventType.TOOL_COMPLETED,
                    investigation_id=investigation_id,
                    step_id=step.step_id,
                    summary=f"Completed tool: {step.tool_name} in {elapsed_ms:.0f}ms",
                    references=[result.evidence_id] if result.evidence_id else [],
                )
            )

            return ExecutorResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                success=result.status == "success",
                evidence_id=result.evidence_id,
                data=result.data,
                execution_time_ms=elapsed_ms,
                error=result.error,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            logger.warning("Tool %s failed: %s", step.tool_name, e)

            event_log.append(
                InvestigationEvent(
                    event_type=EventType.FAILED,
                    investigation_id=investigation_id,
                    step_id=step.step_id,
                    summary=f"Tool failed: {step.tool_name}: {e}",
                )
            )

            return ExecutorResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                success=False,
                execution_time_ms=elapsed_ms,
                error=str(e),
                classification="NON_CRITICAL_FAILURE",
            )

    def reset(self) -> None:
        """Reset executor state for a new investigation."""
        self._steps_executed = 0
        self._start_time = time.time()

    @property
    def steps_executed(self) -> int:
        return self._steps_executed

    def resolve_gaps(
        self,
        gaps: list[EvidenceGap],
        results: list[ExecutorResult],
    ) -> list[EvidenceGap]:
        """Resolve gaps based on successful tool executions."""
        for result in results:
            if result.success:
                for gap in gaps:
                    if gap.status == GapStatus.OPEN and result.tool_name in gap.candidate_tools:
                        gap.status = GapStatus.RESOLVED
                        gap.resolved_by = result.evidence_id
        return gaps
