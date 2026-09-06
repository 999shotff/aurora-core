"""LLM-5 Synthesis API — FastAPI endpoints for evidence-grounded synthesis.

POST /api/v1/synthesis           — execute synthesis
GET  /api/v1/synthesis/{id}      — get synthesis result
GET  /api/v1/synthesis/health    — health check
GET  /api/v1/synthesis/audit     — audit log

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aurora.ai.synthesis.engine import SynthesisEngine
from aurora.ai.synthesis.schemas import SynthesisRequest

logger = logging.getLogger(__name__)

router = APIRouter()

_engine: SynthesisEngine | None = None
_results_store: dict[str, dict] = {}


def _get_engine() -> SynthesisEngine:
    global _engine
    if _engine is None:
        _engine = SynthesisEngine()
    return _engine


# ============================================================
# Request/Response Schemas
# ============================================================


class SynthesisExecuteRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)
    investigation_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    domain: str = "general"
    comparison_context: str | None = None
    decision_context: str | None = None


class SynthesisHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    audit_entries: int
    cache_entries: int


# ============================================================
# Endpoints
# ============================================================


@router.get("/api/v1/synthesis/health")
async def synthesis_health() -> dict:
    engine = _get_engine()
    return engine.health()


@router.post("/api/v1/synthesis")
async def execute_synthesis(req: SynthesisExecuteRequest) -> dict:
    engine = _get_engine()

    request = SynthesisRequest(
        request_id=f"req-{__import__('uuid').uuid4().hex[:12]}",
        question=req.question,
        investigation_id=req.investigation_id,
        evidence_ids=req.evidence_ids,
        finding_ids=req.finding_ids,
        memory_ids=req.memory_ids,
        domain=req.domain,
        comparison_context=req.comparison_context,
        decision_context=req.decision_context,
    )

    try:
        result = engine.synthesize(request)
        result_dict = result.model_dump()
        _results_store[result.synthesis_id] = result_dict
        return result_dict
    except Exception as e:
        logger.exception("Synthesis failed")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e}")


@router.get("/api/v1/synthesis/{synthesis_id}")
async def get_synthesis(synthesis_id: str) -> dict:
    result = _results_store.get(synthesis_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Synthesis {synthesis_id} not found")
    return result


@router.get("/api/v1/synthesis/audit")
async def get_audit_log(limit: int = 50) -> dict:
    engine = _get_engine()
    records = engine.get_audit_log(limit)
    return {"records": [r.model_dump() for r in records], "total": len(records)}
