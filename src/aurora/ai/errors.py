"""AURORA Reasoning Core — Error types.

Provider-neutral errors. Never expose provider API keys or internals.
"""

from __future__ import annotations


class AURORAError(Exception):
    """Base error for all AURORA reasoning errors."""


class LLMUnavailable(AURORAError):
    """No LLM provider is configured or reachable."""

    def __init__(self, message: str = "No LLM provider available") -> None:
        super().__init__(message)
        self.message = message


class LLMTimeout(AURORAError):
    """Provider did not respond within timeout."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"LLM request timed out after {timeout_seconds}s")


class LLMRateLimited(AURORAError):
    """Provider rate limit exceeded."""

    def __init__(self, retry_after: float = 60.0) -> None:
        self.retry_after = retry_after
        super().__init__(f"LLM rate limited, retry after {retry_after}s")


class LLMAuthenticationError(AURORAError):
    """Provider authentication failed."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)
        self.message = message


class LLMInvalidResponse(AURORAError):
    """Provider returned unparseable or schema-invalid output."""

    def __init__(self, message: str = "Invalid LLM response", details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class LLMContextLimit(AURORAError):
    """Input exceeds provider context window."""

    def __init__(self, limit: int = 0, actual: int = 0) -> None:
        self.limit = limit
        self.actual = actual
        super().__init__(f"Context limit exceeded: {actual} > {limit} tokens")


class LLMProviderError(AURORAError):
    """Generic provider error."""

    def __init__(self, message: str = "Provider error", provider: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider


class InsufficientEvidence(AURORAError):
    """Not enough evidence to answer the query."""

    def __init__(self, message: str = "Insufficient evidence", required: int = 0, available: int = 0) -> None:
        self.required = required
        self.available = available
        super().__init__(message)


class SecurityViolation(AURORAError):
    """Security check failed (prompt injection, secret leakage, etc.)."""

    def __init__(self, message: str = "Security violation detected") -> None:
        super().__init__(message)
        self.message = message
