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
POST /api/v1/compute/providers/openai-compatible/test
POST /api/v1/compute/providers/openai-compatible/configure
GET  /api/v1/compute/providers/openai-compatible/status
POST /api/v1/compute/providers/openai-compatible/infer

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


# ── OpenAI-Compatible Remote Provider ───────────────────────────

# Session-scoped configuration (never persisted, never exposed via GET)
_openai_compatible_config: dict = {}


class OpenAICompatibleTestRequest(BaseModel):
    """Request body for testing openai-compatible connection."""

    base_url: str = Field(..., min_length=1, description="API base URL")
    api_key: str = Field(..., min_length=1, description="API key (secret)")
    model: str = Field(..., min_length=1, description="Model identifier")
    provider_name: str = Field(default="openai-compatible", description="Provider display name")


class OpenAICompatibleConfigRequest(BaseModel):
    """Request body for saving openai-compatible configuration."""

    base_url: str = Field(..., min_length=1, description="API base URL")
    api_key: str = Field(..., min_length=1, description="API key (secret)")
    model: str = Field(..., min_length=1, description="Model identifier")
    provider_name: str = Field(default="openai-compatible", description="Provider display name")


@router.post("/api/v1/compute/providers/openai-compatible/test")
async def test_openai_compatible(req: OpenAICompatibleTestRequest) -> dict:
    """Test connection to an OpenAI-compatible API.

    Never returns the API key. Returns safe metadata only.
    """
    from aurora.ai.providers import OpenAICompatibleProvider

    try:
        provider = OpenAICompatibleProvider(
            api_key=req.api_key,
            base_url=req.base_url,
            model=req.model,
            provider_name=req.provider_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = provider.test_connection()
    # Never expose the API key in the response
    result.pop("api_key", None)
    return result


@router.post("/api/v1/compute/providers/openai-compatible/configure")
async def configure_openai_compatible(req: OpenAICompatibleConfigRequest) -> dict:
    """Save openai-compatible provider configuration for this session.

    API key is stored server-side in memory only. Never persisted to disk.
    Never returned in any response.
    """
    from aurora.ai.providers import OpenAICompatibleProvider, _validate_base_url, _hostname_only

    try:
        _validate_base_url(req.base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Store config in memory (session-scoped)
    _openai_compatible_config["base_url"] = req.base_url
    _openai_compatible_config["api_key"] = req.api_key
    _openai_compatible_config["model"] = req.model
    _openai_compatible_config["provider_name"] = req.provider_name

    logger.info(
        "OpenAI-compatible provider configured: host=%s model=%s",
        _hostname_only(req.base_url),
        req.model,
    )

    return {
        "status": "CONFIGURED",
        "provider": "openai-compatible",
        "base_url": _hostname_only(req.base_url),
        "model": req.model,
        "execution": "REMOTE_API",
        "gpu_required": False,
    }


@router.get("/api/v1/compute/providers/openai-compatible/status")
async def openai_compatible_status() -> dict:
    """Get openai-compatible provider status. Never returns API key."""
    if not _openai_compatible_config:
        return {
            "provider": "openai-compatible",
            "status": "NOT_CONFIGURED",
            "execution": "REMOTE_API",
            "gpu_required": False,
        }

    from aurora.ai.providers import _hostname_only, _redact_api_key

    return {
        "provider": "openai-compatible",
        "status": "CONFIGURED",
        "base_url": _hostname_only(_openai_compatible_config.get("base_url", "")),
        "model": _openai_compatible_config.get("model", ""),
        "execution": "REMOTE_API",
        "gpu_required": False,
        "api_key_configured": bool(_openai_compatible_config.get("api_key")),
        "api_key_redacted": _redact_api_key(_openai_compatible_config.get("api_key", "")),
    }


@router.post("/api/v1/compute/providers/openai-compatible/infer")
async def openai_compatible_infer(req: dict) -> dict:
    """Run inference through the configured openai-compatible provider.

    The API key is retrieved from session config, never from the request.
    """
    if not _openai_compatible_config:
        raise HTTPException(status_code=400, detail="OpenAI-compatible provider not configured")

    from aurora.ai.providers import OpenAICompatibleProvider

    try:
        provider = OpenAICompatibleProvider(
            api_key=_openai_compatible_config["api_key"],
            base_url=_openai_compatible_config["base_url"],
            model=_openai_compatible_config["model"],
            provider_name=_openai_compatible_config.get("provider_name", "openai-compatible"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    messages = req.get("messages", [])
    max_tokens = req.get("max_tokens", 2048)
    temperature = req.get("temperature", 0.0)
    timeout = req.get("timeout", 30.0)

    try:
        output = provider.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        provenance = provider.get_provenance(
            prompt=str(messages),
            output=output,
        )
        return {
            "status": "COMPLETED",
            "output": output,
            "provenance": provenance,
        }
    except Exception as e:
        error_msg = str(e)
        # Normalize error types
        if "AUTHENTICATION_ERROR" in error_msg:
            return {"status": "AUTHENTICATION_ERROR", "error": "Invalid or missing API key"}
        if "MODEL_NOT_FOUND" in error_msg:
            return {"status": "MODEL_NOT_FOUND", "error": f"Model not found"}
        if "REMOTE_UNAVAILABLE" in error_msg:
            return {"status": "REMOTE_UNAVAILABLE", "error": "Remote API unreachable"}
        return {"status": "ERROR", "error": "Inference failed"}
