"""Compute Fabric — REST API endpoints (v2).

GET  /api/v1/compute/status
GET  /api/v1/compute/providers
GET  /api/v1/compute/health
POST /api/v1/compute/enable
POST /api/v1/compute/disable
POST /api/v1/compute/mode
POST /api/v1/compute/jobs
GET  /api/v1/compute/jobs
GET  /api/v1/compute/jobs/{job_id}
POST /api/v1/compute/jobs/{job_id}/cancel
POST /api/v1/compute/benchmark
POST /api/v1/compute/workers/register
POST /api/v1/compute/workers/{worker_id}/heartbeat
POST /api/v1/compute/workers/{worker_id}/capabilities
GET  /api/v1/compute/workers/{worker_id}/health
POST /api/v1/compute/workers/{worker_id}/shutdown
GET  /api/v1/compute/audit

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from aurora.compute.errors import (
    ComputeError,
    InvalidMode,
    JobNotFound,
    UnauthorizedWorker,
    WorkerNotFound,
)
from aurora.compute.manager import ComputeManager
from aurora.compute.schemas import (
    BenchmarkRequest,
    ComputeCapabilities,
    ComputeJobRequest,
    ComputeMode,
    ModeChangeRequest,
    WorkerCapabilities,
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


@router.get("/api/v1/compute/jobs")
async def list_jobs(limit: int = 50) -> dict:
    manager = _get_manager()
    jobs = manager.list_jobs(limit)
    return {"jobs": [j.model_dump() for j in jobs], "total": len(jobs)}


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


# ── Benchmark ────────────────────────────────────────────────────

@router.post("/api/v1/compute/benchmark")
async def run_benchmark(req: BenchmarkRequest) -> dict:
    manager = _get_manager()
    result = manager.run_benchmark(req)
    return result.model_dump()


# ── Workers ──────────────────────────────────────────────────────

@router.post("/api/v1/compute/workers/register")
async def register_worker(req: WorkerRegistration) -> dict:
    manager = _get_manager()
    try:
        ack = manager.register_worker(req)
        return ack.model_dump()
    except UnauthorizedWorker as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ComputeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/compute/workers/{worker_id}/heartbeat")
async def worker_heartbeat(worker_id: str, req: WorkerHeartbeat) -> dict:
    manager = _get_manager()
    try:
        ack = manager.worker_heartbeat(worker_id, req)
        return ack.model_dump()
    except UnauthorizedWorker as e:
        raise HTTPException(status_code=401, detail=str(e))
    except WorkerNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/v1/compute/workers/{worker_id}/capabilities")
async def update_worker_capabilities(worker_id: str, req: WorkerCapabilities) -> dict:
    manager = _get_manager()
    ok = manager.update_worker_capabilities(worker_id, req.capabilities)
    if not ok:
        raise HTTPException(status_code=404, detail="Worker not found")
    return {"updated": True, "worker_id": worker_id}


@router.get("/api/v1/compute/workers/{worker_id}/health")
async def get_worker_health(worker_id: str) -> dict:
    manager = _get_manager()
    health = manager.get_worker_health(worker_id)
    if health is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return health.model_dump()


@router.post("/api/v1/compute/workers/{worker_id}/shutdown")
async def shutdown_worker(worker_id: str, req: WorkerShutdown) -> dict:
    manager = _get_manager()
    try:
        ok = manager.shutdown_worker(req)
        return {"shutdown": ok, "worker_id": worker_id}
    except UnauthorizedWorker as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Worker Job Dispatch (for runtime operations) ────────────────

@router.get("/api/v1/compute/workers/{worker_id}/jobs/pending")
async def get_pending_jobs(worker_id: str) -> dict:
    """Worker polls for pending jobs during heartbeat."""
    manager = _get_manager()
    jobs = manager.get_pending_jobs_for_worker(worker_id)
    return {
        "worker_id": worker_id,
        "jobs": [
            {
                "job_id": j.job_id,
                "workload_type": j.workload_type.value if hasattr(j.workload_type, 'value') else str(j.workload_type),
                "payload": j.metadata.get("payload", {}),
            }
            for j in jobs
        ],
        "count": len(jobs),
    }


@router.post("/api/v1/compute/workers/{worker_id}/jobs/{job_id}/result")
async def report_job_result(worker_id: str, job_id: str, result: dict) -> dict:
    """Worker reports job completion with result."""
    manager = _get_manager()
    try:
        job = manager.complete_worker_job(
            job_id,
            result=result,
            result_hash=result.get("result_hash"),
        )
        return {"completed": True, "job_id": job_id}
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Audit ────────────────────────────────────────────────────────

@router.get("/api/v1/compute/audit")
async def compute_audit(limit: int = 50) -> dict:
    manager = _get_manager()
    entries = manager.get_audit_log(limit)
    return {"entries": [e.model_dump() for e in entries], "total": len(entries)}
