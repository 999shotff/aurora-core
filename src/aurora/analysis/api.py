"""Unified Analysis — REST API endpoints.

POST /api/v1/analysis/unified         — run unified analysis
GET  /api/v1/analysis/unified/{id}    — get assessment result
GET  /api/v1/analysis/unified/health  — health check

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aurora.analysis.orchestrator import UnifiedOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

_orchestrator: UnifiedOrchestrator | None = None


def _get_orchestrator() -> UnifiedOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = UnifiedOrchestrator()
    return _orchestrator


# ============================================================
# Request/Response
# ============================================================


class UnifiedAnalysisRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)
    asset: str | None = None
    timeframe: str | None = None
    domain: str = "general"
    market_context: dict | None = None
    indicator_data: dict | None = None
    structure_data: dict | None = None
    research_evidence: list[dict] | None = None
    memory_items: list[dict] | None = None
    run_persona: bool = False
    run_cycles: bool = False


# ============================================================
# Endpoints
# ============================================================


@router.get("/api/v1/analysis/unified/health")
async def unified_health() -> dict:
    orch = _get_orchestrator()
    return orch.health()


@router.post("/api/v1/analysis/unified")
async def run_unified_analysis(req: UnifiedAnalysisRequest) -> dict:
    orch = _get_orchestrator()
    try:
        assessment = orch.analyze(
            question=req.question,
            market_context=req.market_context,
            indicator_data=req.indicator_data,
            structure_data=req.structure_data,
            research_evidence=req.research_evidence,
            memory_items=req.memory_items,
            run_persona=req.run_persona,
            run_cycles=req.run_cycles,
            asset=req.asset,
            timeframe=req.timeframe,
            domain=req.domain,
        )
        return assessment.model_dump()
    except Exception as e:
        logger.exception("Unified analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/api/v1/analysis/unified/{assessment_id}")
async def get_assessment(assessment_id: str) -> dict:
    orch = _get_orchestrator()
    assessment = orch.get_assessment(assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
    return assessment.model_dump()
