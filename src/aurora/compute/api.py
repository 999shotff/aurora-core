"""Compute Fabric — REST API endpoints.

GET  /api/v1/compute/status
GET  /api/v1/compute/providers
GET  /api/v1/compute/health
POST /api/v1/compute/enable
POST /api/v1/compute/disable
POST /api/v1/compute/mode
POST /api/v1/compute/jobs
GET  /api/v1/compute/jobs/{job_id}
POST /api/v1/compute/jobs/{job_id}/cancel
POST /api/v1/compute/workers/register
POST /api/v1/compute/workers/{worker_id}/heartbeat
POST /api/v1/compute/workers/{worker_id}/shutdown
GET  /api/v1/compute/audit

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aurora.compute.errors import (
    ComputeError,
    InvalidMode,
    JobNotFound,
    UnauthorizedWorker,
    WorkerNotFound,
)
from aurora.compute.manager import ComputeManager
from aurora.compute.schemas import (
    ComputeJobRequest,
    ComputeMode,
    ModeChangeRequest,
    WorkerHeartbeat,
    WorkerRegistration,
    WorkerShutdown,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_manager: ComputeManager | None = None


def _get_manager() -> ComputeManager:
    global _manager
    if _manager is None:
        _manager = ComputeManager()
    return _manager


# ── Health & Status ──────────────────────────────────────────────

@router.get("/api/v1/compute/health")
async def compute_health() -> dict:
    manager = _get_manager()
    return manager.health()


@router.get("/api/v1/compute/status")
async def compute_status() -> dict:
    manager = _get_manager()
    return manager.get_status().model_dump()


@router.get("/api/v1/compute/providers")
async def compute_providers() -> dict:
    manager = _get_manager()
    return {"providers": [p.model_dump() for p in manager.get_providers()]}


# ── Enable / Disable ────────────────────────────────────────────

@router.post("/api/v1/compute/enable")
async def compute_enable() -> dict:
    manager = _get_manager()
    return manager.enable().model_dump()


@router.post("/api/v1/compute/disable")
async def compute_disable() -> dict:
    manager = _get_manager()
    return manager.disable().model_dump()


# ── Mode ─────────────────────────────────────────────────────────

@router.post("/api/v1/compute/mode")
async def compute_mode(req: ModeChangeRequest) -> dict:
    manager = _get_manager()
    try:
        return manager.set_mode(req.mode).model_dump()
    except InvalidMode as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ComputeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Jobs ─────────────────────────────────────────────────────────

@router.post("/api/v1/compute/jobs")
async def submit_job(req: ComputeJobRequest) -> dict:
    manager = _get_manager()
    try:
        job = manager.submit_job(req)
        return job.model_dump()
    except ComputeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/compute/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    manager = _get_manager()
    try:
        return manager.get_job(job_id).model_dump()
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/compute/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    manager = _get_manager()
    try:
        ok = manager.cancel_job(job_id)
        return {"cancelled": ok, "job_id": job_id}
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Workers ──────────────────────────────────────────────────────

@router.post("/api/v1/compute/workers/register")
async def register_worker(req: WorkerRegistration) -> dict:
    manager = _get_manager()
    try:
        info = manager.register_worker(req)
        return info.model_dump()
    except UnauthorizedWorker as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ComputeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/compute/workers/{worker_id}/heartbeat")
async def worker_heartbeat(worker_id: str, req: WorkerHeartbeat) -> dict:
    manager = _get_manager()
    try:
        info = manager.worker_heartbeat(worker_id, req)
        return info.model_dump()
    except UnauthorizedWorker as e:
        raise HTTPException(status_code=401, detail=str(e))
    except WorkerNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/compute/workers/{worker_id}/shutdown")
async def shutdown_worker(worker_id: str, req: WorkerShutdown) -> dict:
    manager = _get_manager()
    try:
        ok = manager.shutdown_worker(req)
        return {"shutdown": ok, "worker_id": worker_id}
    except UnauthorizedWorker as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Audit ────────────────────────────────────────────────────────

@router.get("/api/v1/compute/audit")
async def compute_audit(limit: int = 50) -> dict:
    manager = _get_manager()
    entries = manager.get_audit_log(limit)
    return {"entries": [e.model_dump() for e in entries], "total": len(entries)}
