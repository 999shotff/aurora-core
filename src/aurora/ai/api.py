"""AURORA Reasoning Core — REST API Endpoint (LLM-1 + LLM-2).

POST /api/v1/reason — structured reasoning endpoint (LLM-1).
POST /api/v1/reason/tool — tool-orchestrated reasoning (LLM-2).
POST /api/v1/reason/workflow — domain workflow execution (LLM-2).
GET  /api/v1/reason/tools — list available tools (LLM-2).
GET  /api/v1/reason/evidence-graph — current evidence graph (LLM-2).
GET  /api/v1/reason/safety-log — tool safety audit log (LLM-2).

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


# ── Request/Response Models ────────────────────────────────────────────────


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


class ToolReasonRequest(BaseModel):
    """API request body for /api/v1/reason/tool (LLM-2)."""

    query: str = Field(..., min_length=1, max_length=10000, description="User query")
    domain: str = Field(default="general", description="Domain: market, geo, research, general")
    goal: str = Field(default="", description="Specific goal for tool orchestration")
    context_ids: list[str] = Field(default_factory=list, description="Context identifiers")
    constraints: list[str] = Field(default_factory=list, description="Output constraints")


class ToolReasonResponse(BaseModel):
    """API response body for /api/v1/reason/tool (LLM-2)."""

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
    tools_executed: int
    evidence_nodes: int
    evidence_graph_summary: str


class WorkflowRequest(BaseModel):
    """API request body for /api/v1/reason/workflow (LLM-2)."""

    domain: str = Field(..., description="Workflow domain: market, geo, research")
    params: dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")


# ── FastAPI App ────────────────────────────────────────────────────────────


reason_app = FastAPI(
    title="AURORA Reasoning API",
    description=(
        "Structured reasoning with tool orchestration. "
        "No predictions. No trading signals. NO_DEPLOYMENT_SIGNAL."
    ),
    version="0.2.0",
)


# ── LLM-1 Endpoints ──────────────────────────────────────────────────────


@reason_app.get("/api/v1/reason/health")
def reason_health() -> dict:
    """Health check for reasoning service."""
    service = _get_service()
    registry = service.provider_registry
    return {
        "status": "healthy",
        "service": "aurora-reasoning",
        "version": "0.2.0",
        "research_conclusion": "NO_DEPLOYMENT_SIGNAL",
        "providers": registry.health_check(),
        "llm2_tools": len(service.tool_registry.names()),
        "evidence_nodes": len(service.evidence_graph._nodes),
    }


@reason_app.post("/api/v1/reason", response_model=ReasonAPIResponse)
def reason(body: ReasonAPIRequest) -> dict:
    """Process a reasoning request (LLM-1).

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


# ── LLM-2 Endpoints ──────────────────────────────────────────────────────


@reason_app.post("/api/v1/reason/tool", response_model=ToolReasonResponse)
def reason_tool(body: ToolReasonRequest) -> dict:
    """Process a reasoning request with tool orchestration (LLM-2).

    Tools gather evidence automatically. The LLM synthesizes findings.
    No trades are executed. No data is modified.
    """
    service = _get_service()

    request_id = f"req_{uuid.uuid4().hex[:12]}"

    try:
        domain_enum = ReasoningDomain(body.domain) if body.domain in [d.value for d in ReasoningDomain] else ReasoningDomain.GENERAL
    except ValueError:
        domain_enum = ReasoningDomain.GENERAL

    request = ReasoningRequest(
        request_id=request_id,
        user_query=body.query,
        domain=domain_enum,
        task_type=TaskType.GENERAL_RESEARCH,
        context_ids=body.context_ids,
        constraints=body.constraints,
    )

    response = service.process_with_tools(
        request,
        domain=body.domain,
        goal=body.goal,
    )

    graph_summary = service.evidence_graph.summary()

    return ToolReasonResponse(
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
        tools_executed=len(service.tool_registry.safety_log),
        evidence_nodes=len(service.evidence_graph._nodes),
        evidence_graph_summary=graph_summary,
    )


@reason_app.post("/api/v1/reason/workflow")
def reason_workflow(body: WorkflowRequest) -> dict:
    """Execute a domain-specific workflow (LLM-2).

    Returns raw workflow results without LLM synthesis.
    """
    service = _get_service()

    try:
        result = service.execute_workflow(body.domain, **body.params)
        return {"status": "success", "domain": body.domain, "result": result}
    except Exception as exc:
        logger.error("Workflow execution failed: %s", exc)
        return {"status": "error", "domain": body.domain, "error": str(exc)}


@reason_app.get("/api/v1/reason/tools")
def reason_tools() -> dict:
    """List all available tools (LLM-2)."""
    service = _get_service()
    return {
        "tools": service.list_tools(),
        "tool_count": len(service.tool_registry.names()),
    }


@reason_app.get("/api/v1/reason/evidence-graph")
def reason_evidence_graph() -> dict:
    """Get the current evidence graph (LLM-2)."""
    service = _get_service()
    return service.get_evidence_graph()


@reason_app.get("/api/v1/reason/safety-log")
def reason_safety_log() -> dict:
    """Get tool safety audit log (LLM-2)."""
    service = _get_service()
    return {
        "log": service.get_safety_log(),
        "total_entries": len(service.tool_registry.safety_log),
    }
