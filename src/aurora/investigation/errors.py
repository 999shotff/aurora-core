"""
LLM-4: Investigation Errors — typed exceptions for the Investigation Engine.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations


class InvestigationError(Exception):
    """Base exception for investigation errors."""


class InvestigationLimitExceeded(InvestigationError):
    """Raised when an investigation exceeds configured limits."""

    def __init__(self, limit_name: str, limit_value: float) -> None:
        self.limit_name = limit_name
        self.limit_value = limit_value
        super().__init__(f"Investigation limit exceeded: {limit_name}={limit_value}")


class InvestigationTimeout(InvestigationError):
    """Raised when an investigation exceeds its time limit."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Investigation timed out after {timeout_seconds}s")


class InvestigationCancelled(InvestigationError):
    """Raised when an investigation is cancelled by the user."""


class InvestigationNotFound(InvestigationError):
    """Raised when an investigation cannot be found."""

    def __init__(self, investigation_id: str) -> None:
        self.investigation_id = investigation_id
        super().__init__(f"Investigation not found: {investigation_id}")


class EvidenceUnavailable(InvestigationError):
    """Raised when required evidence is not available."""

    def __init__(self, description: str = "Evidence unavailable") -> None:
        self.description = description
        super().__init__(description)


class InsufficientEvidence(InvestigationError):
    """Raised when evidence is insufficient for the investigation objective."""

    def __init__(self, required: int = 0, available: int = 0) -> None:
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient evidence: {available}/{required} required pieces available"
        )


class ToolExecutionError(InvestigationError):
    """Raised when a tool execution fails."""

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Tool execution failed: {tool_name}: {reason}")


class PlanValidationFailed(InvestigationError):
    """Raised when a plan fails validation."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"Plan validation failed: {'; '.join(violations)}")


class DuplicateInvestigation(InvestigationError):
    """Raised when a duplicate investigation start is detected."""

    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(f"Duplicate investigation detected for key: {idempotency_key}")


class SecurityViolation(InvestigationError):
    """Raised when a security constraint is violated during investigation."""

    def __init__(self, message: str = "Security violation in investigation") -> None:
        super().__init__(message)
