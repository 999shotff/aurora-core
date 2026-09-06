"""
LLM-4: Investigation REST API — FastAPI endpoints.

POST   /api/v1/investigations          — create investigation
GET    /api/v1/investigations          — list investigations
GET    /api/v1/investigations/{id}     — get investigation
POST   /api/v1/investigations/{id}/start  — start investigation
POST   /api/v1/investigations/{id}/cancel — cancel investigation
POST   /api/v1/investigations/{id}/reopen — reopen investigation
GET    /api/v1/investigations/{id}/events  — audit trail
GET    /api/v1/investigations/{id}/findings — findings
GET    /api/v1/investigations/{id}/result  — investigation result

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from aurora.investigation.schemas import (
    InvestigationDomain,
    InvestigationObjective,
)
from aurora.investigation.store import InvestigationStore
from aurora.investigation.manager import InvestigationManager
from aurora.investigation.errors import (
    InvestigationError,
    InvestigationNotFound,
    DuplicateInvestigation,
)

logger = logging.getLogger("aurora.investigation.api")

_store: InvestigationStore | None = None
_manager: InvestigationManager | None = None


def _get_manager() -> InvestigationManager:
    global _store, _manager
    if _manager is None:
        _store = InvestigationStore("investigations")
        from aurora.ai.tools.base import ToolRegistry
        from aurora.ai.tools.market import MARKET_TOOLS
        from aurora.ai.tools.geo import GEO_TOOLS
        from aurora.ai.tools.research import RESEARCH_TOOLS

        registry = ToolRegistry()
        registry.register_many(MARKET_TOOLS)
        registry.register_many(GEO_TOOLS)
        registry.register_many(RESEARCH_TOOLS)
        _manager = InvestigationManager(_store, registry)
    return _manager


# ── Request/Response Models ────────────────────────────────────────────────


class CreateInvestigationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    query: str = Field(..., min_length=1, max_length=10000)
    domain: str = Field(default="general")
    subject: str = Field(default="", max_length=500)
    scope: str = Field(default="", max_length=1000)
    temporal_range: dict[str, Any] = Field(default_factory=dict)
    requested_output: str = Field(default="structured")
    constraints: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


class InvestigationAPIResponse(BaseModel):
    model_config = {"extra": "forbid"}

    investigation_id: str
    status: str
    domain: str
    query: str
    subject: str
    created_at: float
    updated_at: float
    started_at: float | None
    completed_at: float | None
    evidence_count: int
    findings_count: int
    tools_used: list[str]


# ── FastAPI App ────────────────────────────────────────────────────────────


investigation_app = FastAPI(
    title="AURORA Investigation API",
    description="Adaptive Investigation Engine. NO_DEPLOYMENT_SIGNAL.",
    version="0.1.0",
)


@investigation_app.get("/api/v1/investigations")
def list_investigations(
    status: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    manager = _get_manager()
    records = manager.list_all(status=status, domain=domain, limit=limit)
    return {
        "investigations": [
            InvestigationAPIResponse(
                investigation_id=r.investigation_id,
                status=r.status.value,
                domain=r.objective.domain.value,
                query=r.objective.query,
                subject=r.objective.subject,
                created_at=r.created_at,
                updated_at=r.updated_at,
                started_at=r.started_at,
                completed_at=r.completed_at,
                evidence_count=len(r.evidence_refs),
                findings_count=len(r.findings),
                tools_used=[t.get("tool_name", "") for t in r.tool_runs if t.get("success")],
            ).model_dump()
            for r in records
        ],
        "total": len(records),
    }


@investigation_app.post("/api/v1/investigations")
def create_investigation(body: CreateInvestigationRequest) -> dict:
    manager = _get_manager()
    try:
        domain = InvestigationDomain(body.domain)
    except ValueError:
        domain = InvestigationDomain.GENERAL

    objective = InvestigationObjective(
        query=body.query,
        domain=domain,
        subject=body.subject,
        scope=body.scope,
        temporal_range=body.temporal_range,
        requested_output=body.requested_output,
        constraints=body.constraints,
    )

    try:
        record = manager.create(objective, idempotency_key=body.idempotency_key)
    except DuplicateInvestigation as e:
        return {"error": str(e), "code": "DUPLICATE"}

    return InvestigationAPIResponse(
        investigation_id=record.investigation_id,
        status=record.status.value,
        domain=record.objective.domain.value,
        query=record.objective.query,
        subject=record.objective.subject,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        evidence_count=0,
        findings_count=0,
        tools_used=[],
    ).model_dump()


@investigation_app.get("/api/v1/investigations/{investigation_id}")
def get_investigation(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        record = manager.get(investigation_id)
    except InvestigationNotFound as e:
        return {"error": str(e)}

    return InvestigationAPIResponse(
        investigation_id=record.investigation_id,
        status=record.status.value,
        domain=record.objective.domain.value,
        query=record.objective.query,
        subject=record.objective.subject,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        evidence_count=len(record.evidence_refs),
        findings_count=len(record.findings),
        tools_used=[t.get("tool_name", "") for t in record.tool_runs if t.get("success")],
    ).model_dump()


@investigation_app.post("/api/v1/investigations/{investigation_id}/start")
def start_investigation_endpoint(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        record = manager.start(investigation_id)
    except InvestigationError as e:
        return {"error": str(e)}

    return InvestigationAPIResponse(
        investigation_id=record.investigation_id,
        status=record.status.value,
        domain=record.objective.domain.value,
        query=record.objective.query,
        subject=record.objective.subject,
        created_at=record.created_at,
        updated_at=record.updated_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        evidence_count=len(record.evidence_refs),
        findings_count=len(record.findings),
        tools_used=[t.get("tool_name", "") for t in record.tool_runs if t.get("success")],
    ).model_dump()


@investigation_app.post("/api/v1/investigations/{investigation_id}/cancel")
def cancel_investigation_endpoint(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        record = manager.cancel(investigation_id)
    except InvestigationError as e:
        return {"error": str(e)}

    return {"investigation_id": record.investigation_id, "status": record.status.value}


@investigation_app.post("/api/v1/investigations/{investigation_id}/reopen")
def reopen_investigation_endpoint(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        record = manager.reopen(investigation_id)
    except InvestigationError as e:
        return {"error": str(e)}

    return {"investigation_id": record.investigation_id, "status": record.status.value}


@investigation_app.get("/api/v1/investigations/{investigation_id}/events")
def get_events(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        events = manager.get_events(investigation_id)
    except InvestigationNotFound as e:
        return {"error": str(e)}

    return {
        "investigation_id": investigation_id,
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp,
                "event_type": e.event_type.value,
                "summary": e.summary,
                "references": e.references,
            }
            for e in events
        ],
    }


@investigation_app.get("/api/v1/investigations/{investigation_id}/findings")
def get_findings(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        record = manager.get(investigation_id)
    except InvestigationNotFound as e:
        return {"error": str(e)}

    return {
        "investigation_id": investigation_id,
        "findings": [
            {
                "finding_id": f.finding_id,
                "statement": f.statement,
                "classification": f.classification.value,
                "confidence": f.confidence,
                "status": f.status.value,
                "evidence_refs": f.evidence_refs,
            }
            for f in record.findings
        ],
    }


@investigation_app.get("/api/v1/investigations/{investigation_id}/result")
def get_result(investigation_id: str) -> dict:
    manager = _get_manager()
    try:
        result = manager.get_result(investigation_id)
    except InvestigationNotFound as e:
        return {"error": str(e)}

    if result is None:
        return {"investigation_id": investigation_id, "result": None}

    return {
        "investigation_id": investigation_id,
        "result": {
            "status": result.status.value,
            "executive_summary": result.executive_summary,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "statement": f.statement,
                    "classification": f.classification.value,
                    "confidence": f.confidence,
                    "status": f.status.value,
                }
                for f in result.findings
            ],
            "evidence_refs": result.evidence_refs,
            "uncertainties": result.uncertainties,
            "conflicts": result.conflicts,
            "tools_used": result.tools_used,
        },
    }
