"""
AURORA AI — Reasoning Core Package (LLM-1 + LLM-2)
====================================================

LLM-1: Evidence-grounded reasoning with structured responses.
LLM-2: Grounded intelligence with controlled tool orchestration.

Provides:
- Structured reasoning with evidence grounding (LLM-1)
- Provider-agnostic LLM integration (LLM-1)
- Deterministic context building (LLM-1)
- Prompt injection defense (LLM-1)
- Controlled tool registry (LLM-2)
- Bounded planning with step limits (LLM-2)
- Evidence graph with relationship tracking (LLM-2)
- Extended grounding validation (LLM-2)
- Tool safety logging (LLM-2)
- Domain workflows: market, geo, research (LLM-2)

All tools are READ-only. No trades. No data modification.
NO_DEPLOYMENT_SIGNAL — research tool, not production trading.
"""

from aurora.ai.schemas import (
    EvidenceGrounding,
    EvidenceRecord,
    EvidenceSource,
    ReasoningContext,
    ReasoningDomain,
    ReasoningPoint,
    ReasoningRequest,
    ReasoningResponse,
    ReasoningStatus,
    TaskType,
)
from aurora.ai.providers import LLMProvider, ProviderRegistry, create_provider_registry
from aurora.ai.context import build_context, serialize_context
from aurora.ai.grounding import validate_grounding
from aurora.ai.security import sanitize_user_input, redact_secrets
from aurora.ai.router import route_request
from aurora.ai.errors import (
    AURORAError,
    LLMUnavailable,
    LLMTimeout,
    LLMRateLimited,
    SecurityViolation,
    InsufficientEvidence,
    LLMContextLimit,
    LLMInvalidResponse,
)
from aurora.ai.service import ReasoningService

__all__ = [
    "AURORAError",
    "EvidenceGrounding",
    "EvidenceRecord",
    "EvidenceSource",
    "InsufficientEvidence",
    "LLMContextLimit",
    "LLMInvalidResponse",
    "LLMProvider",
    "LLMRateLimited",
    "LLMTimeout",
    "LLMUnavailable",
    "ProviderRegistry",
    "ReasoningContext",
    "ReasoningDomain",
    "ReasoningPoint",
    "ReasoningRequest",
    "ReasoningResponse",
    "ReasoningService",
    "ReasoningStatus",
    "SecurityViolation",
    "TaskType",
    "build_context",
    "create_provider_registry",
    "redact_secrets",
    "route_request",
    "sanitize_user_input",
    "serialize_context",
    "validate_grounding",
]
