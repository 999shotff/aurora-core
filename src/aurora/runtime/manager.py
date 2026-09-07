"""Runtime Manager — lifecycle management for model runtimes.

Manages runtime discovery, model loading/unloading, inference jobs, provenance.
No code execution. No weight storage. All operations delegated to compute workers.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from aurora.compute.manager import ComputeManager
from aurora.runtime.registry import get_model_by_id, get_default_registry
from aurora.runtime.schemas import (
    InferenceProvenance,
    InferenceRequest,
    InferenceResult,
    InferenceStatus,
    ModelLoadStatus,
    ModelRegistry,
    RuntimeCapability,
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


class RuntimeManager:
    """Manages model runtime lifecycle across compute workers."""

    def __init__(self, compute_manager: ComputeManager) -> None:
        self._compute = compute_manager
        self._runtimes: dict[str, RuntimeInfo] = {}
        self._inference_jobs: dict[str, InferenceResult] = {}
        self._registry = get_default_registry()

    @property
    def registry(self) -> ModelRegistry:
        return self._registry

    def list_runtimes(self) -> list[RuntimeInfo]:
        return list(self._runtimes.values())

    def get_runtime(self, runtime_id: str) -> RuntimeInfo | None:
        return self._runtimes.get(runtime_id)

    def get_inference_job(self, job_id: str) -> InferenceResult | None:
        return self._inference_jobs.get(job_id)

    def list_inference_jobs(self, limit: int = 50) -> list[InferenceResult]:
        jobs = sorted(self._inference_jobs.values(),
                       key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    # --------------------------------------------------------
    # Discovery
    # --------------------------------------------------------

    async def discover_runtime(
        self, request: RuntimeDiscoverRequest
    ) -> RuntimeDiscoverResult:
        worker = self._compute.get_worker(request.worker_id)
        if not worker:
            return RuntimeDiscoverResult(
                worker_id=request.worker_id,
                runtime_id="",
                status=RuntimeStatus.ERROR,
                error="Worker not registered",
            )

        runtime_id = f"rt-{worker.worker_id[:8]}-{int(time.time())}"

        available_models = [
            m.model_id for m in self._registry.models
            if self._gpu_has_enough_vram(worker.vram_mb, m.required_vram_gb)
        ]

        runtime_info = RuntimeInfo(
            runtime_id=runtime_id,
            status=RuntimeStatus.READY,
            worker_id=worker.worker_id,
            provider_type=worker.provider_type.value
            if hasattr(worker.provider_type, "value")
            else str(worker.provider_type),
            gpu_name=worker.gpu_name,
            vram_mb=worker.vram_mb,
            cuda_version=worker.cuda_version,
            framework=worker.framework,
            pytorch_version=worker.pytorch_version,
        )
        self._runtimes[runtime_id] = runtime_info

        return RuntimeDiscoverResult(
            worker_id=worker.worker_id,
            runtime_id=runtime_id,
            status=RuntimeStatus.READY,
            gpu_name=worker.gpu_name,
            vram_mb=worker.vram_mb,
            cuda_version=worker.cuda_version,
            pytorch_version=worker.pytorch_version,
            available_models=available_models,
        )

    # --------------------------------------------------------
    # Model Loading
    # --------------------------------------------------------

    async def load_model(self, request: RuntimeLoadRequest) -> RuntimeLoadResult:
        model_config = get_model_by_id(request.model_id)
        if not model_config:
            return RuntimeLoadResult(
                worker_id=request.worker_id,
                runtime_id="",
                model_id=request.model_id,
                status=ModelLoadStatus.ERROR,
                error=f"Model '{request.model_id}' not in approved registry",
            )

        worker = self._compute.get_worker(request.worker_id)
        if not worker:
            return RuntimeLoadResult(
                worker_id=request.worker_id,
                runtime_id="",
                model_id=request.model_id,
                status=ModelLoadStatus.ERROR,
                error="Worker not registered",
            )

        if not self._gpu_has_enough_vram(worker.vram_mb, model_config.required_vram_gb):
            return RuntimeLoadResult(
                worker_id=request.worker_id,
                runtime_id="",
                model_id=request.model_id,
                status=ModelLoadStatus.ERROR,
                error=(
                    f"Insufficient VRAM: worker has {worker.vram_mb or 0:.0f}MB, "
                    f"model needs {model_config.required_vram_gb * 1024:.0f}MB"
                ),
            )

        existing_runtime = self._find_runtime_for_worker(request.worker_id)
        runtime_id = existing_runtime.runtime_id if existing_runtime else (
            f"rt-{worker.worker_id[:8]}-{int(time.time())}"
        )

        if existing_runtime:
            existing_runtime.status = RuntimeStatus.LOADING
            existing_runtime.model = model_config
            existing_runtime.model_load_status = ModelLoadStatus.LOADING
        else:
            runtime_info = RuntimeInfo(
                runtime_id=runtime_id,
                status=RuntimeStatus.LOADING,
                model=model_config,
                model_load_status=ModelLoadStatus.LOADING,
                worker_id=worker.worker_id,
                provider_type=worker.provider_type.value
                if hasattr(worker.provider_type, "value")
                else str(worker.provider_type),
                gpu_name=worker.gpu_name,
                vram_mb=worker.vram_mb,
                cuda_version=worker.cuda_version,
                framework=worker.framework,
                pytorch_version=worker.pytorch_version,
            )
            self._runtimes[runtime_id] = runtime_info

        load_start = time.time()
        try:
            await self._send_load_command(worker, model_config, request.dtype)
        except Exception as exc:
            if runtime_id in self._runtimes:
                rt = self._runtimes[runtime_id]
                rt.status = RuntimeStatus.ERROR
                rt.model_load_status = ModelLoadStatus.ERROR
                rt.error_message = str(exc)
            return RuntimeLoadResult(
                worker_id=request.worker_id,
                runtime_id=runtime_id,
                model_id=request.model_id,
                status=ModelLoadStatus.ERROR,
                error=str(exc),
            )

        load_time = time.time() - load_start
        if runtime_id in self._runtimes:
            rt = self._runtimes[runtime_id]
            rt.status = RuntimeStatus.READY
            rt.model_load_status = ModelLoadStatus.LOADED
            rt.loaded_at = time.time()
            rt.model_memory_mb = model_config.required_vram_gb * 1024

        return RuntimeLoadResult(
            worker_id=request.worker_id,
            runtime_id=runtime_id,
            model_id=request.model_id,
            status=ModelLoadStatus.LOADED,
            load_time_seconds=load_time,
            model_memory_mb=model_config.required_vram_gb * 1024,
        )

    # --------------------------------------------------------
    # Model Unloading
    # --------------------------------------------------------

    async def unload_model(self, request: RuntimeUnloadRequest) -> RuntimeLoadResult:
        runtime = self._runtimes.get(request.runtime_id)
        if not runtime:
            return RuntimeLoadResult(
                worker_id=request.worker_id,
                runtime_id=request.runtime_id,
                model_id="",
                status=ModelLoadStatus.ERROR,
                error="Runtime not found",
            )

        runtime.status = RuntimeStatus.UNLOADING
        runtime.model_load_status = ModelLoadStatus.UNLOADING

        try:
            await self._send_unload_command(request.worker_id, request.runtime_id)
        except Exception as exc:
            runtime.status = RuntimeStatus.ERROR
            runtime.error_message = str(exc)
            return RuntimeLoadResult(
                worker_id=request.worker_id,
                runtime_id=request.runtime_id,
                model_id=runtime.model.model_id if runtime.model else "",
                status=ModelLoadStatus.ERROR,
                error=str(exc),
            )

        runtime.status = RuntimeStatus.READY
        runtime.model_load_status = ModelLoadStatus.NOT_LOADED
        runtime.model = None
        runtime.loaded_at = None
        runtime.model_memory_mb = None

        return RuntimeLoadResult(
            worker_id=request.worker_id,
            runtime_id=request.runtime_id,
            model_id="",
            status=ModelLoadStatus.NOT_LOADED,
        )

    # --------------------------------------------------------
    # Inference
    # --------------------------------------------------------

    async def run_inference(self, request: InferenceRequest) -> InferenceResult:
        worker_id = request.worker_id
        if not worker_id:
            runtime = self._find_runtime_with_model(request.model_id)
            if not runtime or not runtime.worker_id:
                return InferenceResult(
                    job_id="",
                    inference_id="",
                    model_id=request.model_id,
                    worker_id="",
                    runtime_id="",
                    status=InferenceStatus.FAILED,
                    prompt_hash=InferenceResult.compute_hash(request.prompt),
                    error="No available runtime with loaded model",
                )
            worker_id = runtime.worker_id
            runtime_id = runtime.runtime_id
        else:
            runtime = self._find_runtime_for_worker(worker_id)
            runtime_id = runtime.runtime_id if runtime else ""

        job_id = f"ij-{uuid.uuid4().hex[:12]}"
        inference_id = f"inf-{uuid.uuid4().hex[:12]}"
        prompt_hash = InferenceResult.compute_hash(request.prompt)

        result = InferenceResult(
            job_id=job_id,
            inference_id=inference_id,
            model_id=request.model_id,
            worker_id=worker_id,
            runtime_id=runtime_id,
            status=InferenceStatus.PENDING,
            prompt_hash=prompt_hash,
        )
        self._inference_jobs[job_id] = result

        try:
            result.status = InferenceStatus.RUNNING
            result.started_at = time.time()

            if runtime:
                runtime.status = RuntimeStatus.BUSY
                runtime.last_inference_at = time.time()

            output, gen_time = await self._execute_inference(
                worker_id, request, prompt_hash
            )

            result.output = output
            result.output_hash = InferenceResult.compute_hash(output) if output else None
            result.tokens_generated = len(output.split()) if output else 0
            result.generation_time_seconds = gen_time
            result.tokens_per_second = (
                result.tokens_generated / gen_time if gen_time > 0 else 0
            )
            result.status = InferenceStatus.COMPLETED
            result.completed_at = time.time()
            result.model_name = (
                runtime.model.model_name if runtime and runtime.model else None
            )
            result.device = "cuda"
            result.gpu_name = runtime.gpu_name if runtime else None
            result.framework = runtime.framework if runtime else None

            if runtime:
                runtime.status = RuntimeStatus.READY
                runtime.total_inferences += 1

        except TimeoutError:
            result.status = InferenceStatus.TIMEOUT
            result.error = "Inference timed out"
            result.completed_at = time.time()
            if runtime:
                runtime.status = RuntimeStatus.READY
                runtime.total_errors += 1
        except Exception as exc:
            result.status = InferenceStatus.FAILED
            result.error = str(exc)[:500]
            result.completed_at = time.time()
            if runtime:
                runtime.status = RuntimeStatus.ERROR
                runtime.error_message = str(exc)[:200]
                runtime.total_errors += 1

        return result

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    def build_provenance(self, result: InferenceResult) -> InferenceProvenance:
        runtime = self._runtimes.get(result.runtime_id)
        model = runtime.model if runtime else None
        limitations = []
        if result.status != InferenceStatus.COMPLETED:
            limitations.append(f"Inference did not complete: {result.status.value}")
        if not result.gpu_name:
            limitations.append("No GPU information available")
        if result.tokens_per_second < 1.0:
            limitations.append("Very low tokens/second — possible resource contention")

        return InferenceProvenance(
            job_id=result.job_id,
            inference_id=result.inference_id,
            worker_id=result.worker_id,
            runtime_id=result.runtime_id,
            model_id=result.model_id,
            model_name=result.model_name or (model.model_name if model else None),
            model_version=model.model_revision if model else None,
            execution_device=result.device,
            gpu_name=result.gpu_name,
            framework=result.framework,
            dtype=model.dtype if model else None,
            prompt_hash=result.prompt_hash,
            output_hash=result.output_hash,
            tokens_generated=result.tokens_generated,
            generation_time_seconds=result.generation_time_seconds,
            created_at=result.created_at,
            started_at=result.started_at,
            completed_at=result.completed_at,
            status=result.status,
            error=result.error,
            evidence_class="MODEL_INFERENCE",
            limitations=limitations,
        )

    # --------------------------------------------------------
    # Internal helpers — dispatch to compute fabric
    # --------------------------------------------------------

    def _gpu_has_enough_vram(self, worker_vram_mb: float | None,
                              required_gb: float) -> bool:
        if worker_vram_mb is None:
            return False
        return worker_vram_mb >= required_gb * 1024

    def _find_runtime_for_worker(self, worker_id: str) -> RuntimeInfo | None:
        for rt in self._runtimes.values():
            if rt.worker_id == worker_id:
                return rt
        return None

    def _find_runtime_with_model(self, model_id: str) -> RuntimeInfo | None:
        for rt in self._runtimes.values():
            if rt.model and rt.model.model_id == model_id:
                return rt
        return None

    def _find_any_ready_worker(self) -> str | None:
        """Find a worker that is registered and ready."""
        try:
            status = self._compute.get_status()
            for provider in status.providers:
                if provider.worker_id and provider.worker_status.value == "READY":
                    return provider.worker_id
        except Exception:
            pass
        return None

    async def _send_load_command(
        self, worker: Any, model_config: Any, dtype: str | None
    ) -> None:
        """Dispatch RUNTIME_LOAD job to the connected worker via compute fabric."""
        worker_id = worker.worker_id if hasattr(worker, 'worker_id') else str(worker)
        payload = {
            "model_id": model_config.model_id,
            "dtype": dtype or model_config.dtype,
        }
        job = self._compute.dispatch_job_to_worker(
            worker_id, "RUNTIME_LOAD", payload
        )
        logger.info("Dispatched RUNTIME_LOAD to %s: job %s", worker_id, job.job_id)

    async def _send_unload_command(
        self, worker_id: str, runtime_id: str
    ) -> None:
        """Dispatch RUNTIME_UNLOAD job to the connected worker."""
        payload = {"runtime_id": runtime_id}
        job = self._compute.dispatch_job_to_worker(
            worker_id, "RUNTIME_UNLOAD", payload
        )
        logger.info("Dispatched RUNTIME_UNLOAD to %s: job %s", worker_id, job.job_id)

    async def _execute_inference(
        self, worker_id: str, request: InferenceRequest, prompt_hash: str
    ) -> tuple[str, float]:
        """Dispatch RUNTIME_INFER job and wait for result via polling."""
        import asyncio

        payload = {
            "model_id": request.model_id,
            "prompt": request.prompt,
            "max_new_tokens": request.max_new_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        job = self._compute.dispatch_job_to_worker(
            worker_id, "RUNTIME_INFER", payload
        )
        logger.info("Dispatched RUNTIME_INFER to %s: job %s", worker_id, job.job_id)

        # Poll for job completion
        start = time.time()
        timeout = request.timeout_seconds
        poll_interval = 1.0

        while (time.time() - start) < timeout:
            try:
                completed_job = self._compute._completed_jobs.get(job.job_id)
                if completed_job and completed_job.status.value == "COMPLETED":
                    result_data = completed_job.result
                    output = result_data.get("output", "")
                    gen_time = result_data.get("generation_time_seconds", 0.0)
                    return output, gen_time
            except Exception:
                pass
            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.2, 3.0)

        raise TimeoutError(f"Inference timed out after {timeout}s")
