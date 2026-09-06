"""AURORA Reasoning Core — REST API Endpoint.

POST /api/v1/reason — structured reasoning endpoint.
Do not expose provider credentials. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from aurora.ai.schemas import (
    ReasoningDomain,
    ReasoningRequest,
    TaskType,
)
from aurora.ai.service import ReasoningService

logger = logging.getLogger("aurora.ai.api")

_service: ReasoningService | None = None


def _get_service() -> ReasoningService:
    global _service
    if _service is None:
        _service = ReasoningService()
    return _service


class ReasonAPIRequest(BaseModel):
    """API request body for /api/v1/reason."""

    query: str = Field(..., min_length=1, max_length=10000, description="User query")
    domain: str = Field(default="general", description="Domain: market, geo, research, general")
    task: str = Field(default="GENERAL_RESEARCH", description="Task type")
    context_ids: list[str] = Field(default_factory=list, description="Context identifiers")
    constraints: list[str] = Field(default_factory=list, description="Output constraints")
    evidence: list[dict[str, Any]] = Field(default_factory=list, description="Explicit evidence items")


class ReasonAPIResponse(BaseModel):
    """API response body for /api/v1/reason."""

    request_id: str
    status: str
    answer: str
    summary: str
    evidence_refs: list[str]
    reasoning_points: list[dict[str, Any]]
    uncertainties: list[str]
    conflicts: list[str]
    abstention_reason: str | None
    provider: str
    model: str
    context_hash: str
    grounding_score: float


reason_app = FastAPI(
    title="AURORA Reasoning API",
    description="Structured reasoning. No predictions. No trading signals. NO_DEPLOYMENT_SIGNAL.",
    version="0.1.0",
)


@reason_app.get("/api/v1/reason/health")
def reason_health() -> dict:
    """Health check for reasoning service."""
    service = _get_service()
    registry = service.provider_registry
    return {
        "status": "healthy",
        "service": "aurora-reasoning",
        "version": "0.1.0",
        "research_conclusion": "NO_DEPLOYMENT_SIGNAL",
        "providers": registry.health_check(),
    }


@reason_app.post("/api/v1/reason", response_model=ReasonAPIResponse)
def reason(body: ReasonAPIRequest) -> dict:
    """Process a reasoning request.

    The LLM is a reasoning/synthesis component.
    Deterministic engines are the source of truth for all numerical data.
    """
    service = _get_service()

    request_id = f"req_{uuid.uuid4().hex[:12]}"

    try:
        domain = ReasoningDomain(body.domain) if body.domain in [d.value for d in ReasoningDomain] else ReasoningDomain.GENERAL
    except ValueError:
        domain = ReasoningDomain.GENERAL

    try:
        task_type = TaskType(body.task) if body.task in [t.value for t in TaskType] else TaskType.GENERAL_RESEARCH
    except ValueError:
        task_type = TaskType.GENERAL_RESEARCH

    request = ReasoningRequest(
        request_id=request_id,
        user_query=body.query,
        domain=domain,
        task_type=task_type,
        context_ids=body.context_ids,
        constraints=body.constraints,
    )

    from aurora.ai.schemas import EvidenceRecord, EvidenceSource

    evidence: list[EvidenceRecord] = []
    for ev in body.evidence:
        try:
            evidence.append(EvidenceRecord(
                evidence_id=ev.get("evidence_id", f"ev_{uuid.uuid4().hex[:8]}"),
                source=EvidenceSource(ev.get("source", "market_analysis")),
                domain=ReasoningDomain(ev.get("domain", "general")),
                claim=ev.get("claim", ""),
                value=ev.get("value", ""),
                timestamp=ev.get("timestamp"),
                confidence=float(ev.get("confidence", 1.0)),
                provenance=ev.get("provenance", ""),
                quality=ev.get("quality", "verified"),
            ))
        except (ValueError, KeyError) as exc:
            logger.warning("Skipping invalid evidence item: %s", exc)

    response = service.process_with_evidence(request, evidence)

    return ReasonAPIResponse(
        request_id=response.request_id,
        status=response.status.value,
        answer=response.answer,
        summary=response.summary,
        evidence_refs=response.evidence_refs,
        reasoning_points=[
            {
                "point": rp.point,
                "grounding": rp.grounding.value,
                "evidence_refs": rp.evidence_refs,
            }
            for rp in response.reasoning_points
        ],
        uncertainties=response.uncertainties,
        conflicts=response.conflicts,
        abstention_reason=response.abstention_reason,
        provider=response.provider,
        model=response.model,
        context_hash=response.context_hash,
        grounding_score=response.grounding_score,
    )
