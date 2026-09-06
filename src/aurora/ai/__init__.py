"""AURORA Reasoning Core — AI/LLM Abstraction Layer.

The deterministic analysis engine is the source of truth.
The LLM receives structured analytical facts and cannot modify raw data.

Architecture:
  User Query → Task Router → Evidence Assembly → Context Builder → LLM → Validation → Structured Response

If the AI service is unavailable, the deterministic analysis continues working.
No API key is required for core functionality.
NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from aurora.ai.context import build_context, serialize_context
from aurora.ai.errors import (
    AURORAError,
    InsufficientEvidence,
    LLMAuthenticationError,
    LLMContextLimit,
    LLMInvalidResponse,
    LLMProviderError,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
    SecurityViolation,
)
from aurora.ai.grounding import (
    compute_grounding_score,
    detect_unsupported_claims,
    validate_grounding,
)
from aurora.ai.providers import (
    LLMProvider,
    OpenAICompatibleProvider,
    ProviderCapabilities,
    ProviderRegistry,
    StubProvider,
    create_provider_registry,
)
from aurora.ai.router import infer_domain_from_query, route_request
from aurora.ai.schemas import (
    EvidenceGrounding,
    EvidenceRecord,
    EvidenceSource,
    ProviderMetadata,
    ReasoningContext,
    ReasoningDomain,
    ReasoningPoint,
    ReasoningRequest,
    ReasoningResponse,
    ReasoningStatus,
    TaskType,
)
from aurora.ai.security import (
    redact_secrets,
    sanitize_evidence,
    sanitize_user_input,
    validate_no_secrets,
)
from aurora.ai.service import ReasoningService

__all__ = [
    "AURORAError",
    "EvidenceGrounding",
    "EvidenceRecord",
    "EvidenceSource",
    "InsufficientEvidence",
    "LLMAuthenticationError",
    "LLMContextLimit",
    "LLMInvalidResponse",
    "LLMProvider",
    "LLMProviderError",
    "LLMRateLimited",
    "LLMTimeout",
    "LLMUnavailable",
    "OpenAICompatibleProvider",
    "ProviderCapabilities",
    "ProviderMetadata",
    "ProviderRegistry",
    "ReasoningContext",
    "ReasoningDomain",
    "ReasoningPoint",
    "ReasoningRequest",
    "ReasoningResponse",
    "ReasoningService",
    "ReasoningStatus",
    "SecurityViolation",
    "StubProvider",
    "TaskType",
    "build_context",
    "compute_grounding_score",
    "create_provider_registry",
    "detect_unsupported_claims",
    "infer_domain_from_query",
    "redact_secrets",
    "route_request",
    "sanitize_evidence",
    "sanitize_user_input",
    "serialize_context",
    "validate_grounding",
    "validate_no_secrets",
]
