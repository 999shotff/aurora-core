"""Runtime REST API — runtime lifecycle and inference endpoints.

All endpoints require API key auth. Runtime operations are bounded and validated.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from aurora.runtime.schemas import (
    InferenceRequest,
    InferenceResult,
    InferenceStatus,
    ModelRegistry,
    RuntimeDiscoverRequest,
    RuntimeDiscoverResult,
    RuntimeHealthRequest,
    RuntimeInfo,
    RuntimeLoadRequest,
    RuntimeLoadResult,
    RuntimeStatus,
    RuntimeUnloadRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


# ============================================================
# Request / Response models for API layer
# ============================================================


class RuntimeAPIHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    runtimes: int
    registry_models: int
    inference_jobs: int
    timestamp: float = Field(default_factory=time.time)


class RuntimeListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtimes: list[RuntimeInfo]
    count: int


class InferenceJobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[InferenceResult]
    count: int


# ============================================================
# Dependency injection (set at startup)
# ============================================================

_runtime_manager: Any = None


def set_runtime_manager(manager: Any) -> None:
    global _runtime_manager
    _runtime_manager = manager


def _get_manager():
    if _runtime_manager is None:
        raise HTTPException(status_code=503, detail="Runtime manager not initialized")
    return _runtime_manager


# ============================================================
# Endpoints
# ============================================================


@router.get("/health")
async def runtime_health() -> RuntimeAPIHealthResponse:
    manager = _get_manager()
    runtimes = manager.list_runtimes()
    registry = manager.registry
    jobs = manager.list_inference_jobs()
    return RuntimeAPIHealthResponse(
        status="ok",
        runtimes=len(runtimes),
        registry_models=len(registry.models),
        inference_jobs=len(jobs),
    )


@router.get("/runtimes")
async def list_runtimes() -> RuntimeListResponse:
    manager = _get_manager()
    runtimes = manager.list_runtimes()
    return RuntimeListResponse(runtimes=runtimes, count=len(runtimes))


@router.get("/runtimes/{runtime_id}")
async def get_runtime(runtime_id: str) -> RuntimeInfo:
    manager = _get_manager()
    runtime = manager.get_runtime(runtime_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Runtime not found")
    return runtime


@router.post("/runtimes/discover")
async def discover_runtime(
    request: RuntimeDiscoverRequest,
) -> RuntimeDiscoverResult:
    manager = _get_manager()
    result = await manager.discover_runtime(request)
    if result.status == RuntimeStatus.ERROR:
        raise HTTPException(status_code=400, detail=result.error)
    return result


@router.post("/runtimes/load")
async def load_model(request: RuntimeLoadRequest) -> RuntimeLoadResult:
    manager = _get_manager()
    result = await manager.load_model(request)
    if result.status.value == "ERROR":
        raise HTTPException(status_code=400, detail=result.error)
    return result


@router.post("/runtimes/unload")
async def unload_model(request: RuntimeUnloadRequest) -> RuntimeLoadResult:
    manager = _get_manager()
    result = await manager.unload_model(request)
    if result.status.value == "ERROR":
        raise HTTPException(status_code=400, detail=result.error)
    return result


@router.post("/runtimes/{runtime_id}/health")
async def runtime_health_check(runtime_id: str) -> RuntimeInfo:
    manager = _get_manager()
    runtime = manager.get_runtime(runtime_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="Runtime not found")
    return runtime


@router.post("/inference")
async def run_inference(request: InferenceRequest) -> InferenceResult:
    manager = _get_manager()
    result = await manager.run_inference(request)
    if result.status == InferenceStatus.FAILED:
        raise HTTPException(status_code=400, detail=result.error)
    return result


@router.get("/inference")
async def list_inference_jobs() -> InferenceJobListResponse:
    manager = _get_manager()
    jobs = manager.list_inference_jobs()
    return InferenceJobListResponse(jobs=jobs, count=len(jobs))


@router.get("/inference/{job_id}")
async def get_inference_job(job_id: str) -> InferenceResult:
    manager = _get_manager()
    result = manager.get_inference_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Inference job not found")
    return result


@router.get("/registry")
async def get_registry() -> ModelRegistry:
    manager = _get_manager()
    return manager.registry


@router.get("/registry/models")
async def list_registry_models() -> list[dict[str, Any]]:
    manager = _get_manager()
    return [m.model_dump() for m in manager.registry.models]
