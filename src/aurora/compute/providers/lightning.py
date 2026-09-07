"""Compute Fabric — Lightning AI provider.

Configured via AURORA_LIGHTNING_* environment variables.
Does NOT fabricate connectivity. Reports NOT_CONFIGURED if missing credentials.

Worker lifecycle:
  NOT_CONFIGURED -> DISCONNECTED -> CONNECTING -> AUTHENTICATING -> READY -> BUSY -> DISCONNECTED

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import os
import time
import uuid

from aurora.compute.provider import ComputeProvider
from aurora.compute.schemas import (
    BenchmarkResult,
    BenchmarkStatus,
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeProviderStatus,
    ComputeProviderType,
    GPUInfo,
    JobStatus,
    WorkerHealth,
    WorkerStatus,
)


class LightningProvider(ComputeProvider):
    """Lightning AI GPU provider.

    Status depends on real configuration and worker connectivity.
    NOT_CONFIGURED if AURORA_LIGHTNING_ENDPOINT or AURORA_LIGHTNING_API_KEY missing.
    DISCONNECTED if endpoint unreachable.
    READY only when health check confirms real connectivity.
    """

    WORKER_TIMEOUT_SECONDS = 120

    def __init__(self) -> None:
        self._endpoint = os.environ.get("AURORA_LIGHTNING_ENDPOINT", "")
        self._api_key = os.environ.get("AURORA_LIGHTNING_API_KEY", "")
        self._workspace = os.environ.get("AURORA_LIGHTNING_WORKSPACE", "")
        self._project = os.environ.get("AURORA_LIGHTNING_PROJECT", "")
        self._configured = bool(self._endpoint and self._api_key)
        self._worker_registered = False
        self._worker_id: str | None = None
        self._worker_capabilities: ComputeCapabilities = ComputeCapabilities()
        self._worker_status: WorkerStatus = WorkerStatus.OFFLINE
        self._last_heartbeat: float | None = None
        self._worker_started_at: float | None = None
        self._gpu_info: GPUInfo | None = None
        self._jobs: dict[str, ComputeJob] = {}
        self._provider_id = "lightning"

    @property
    def provider_type(self) -> ComputeProviderType:
        return ComputeProviderType.LIGHTNING

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return "Lightning AI"

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self._worker_registered = False
        self._worker_id = None
        self._worker_status = WorkerStatus.OFFLINE
        self._gpu_info = None

    def health(self) -> ComputeProviderStatus:
        if not self._configured:
            return ComputeProviderStatus.NOT_CONFIGURED
        if not self._worker_registered:
            return ComputeProviderStatus.DISCONNECTED
        if self._is_worker_stale():
            self._worker_registered = False
            self._worker_status = WorkerStatus.DISCONNECTED
            return ComputeProviderStatus.DISCONNECTED
        if self._worker_status == WorkerStatus.BUSY:
            return ComputeProviderStatus.BUSY
        if self._worker_status == WorkerStatus.UNHEALTHY:
            return ComputeProviderStatus.DEGRADED
        return ComputeProviderStatus.READY

    def capabilities(self) -> ComputeCapabilities:
        if not self._worker_registered:
            return ComputeCapabilities()
        return self._worker_capabilities

    def register_worker(
        self,
        worker_id: str,
        capabilities: ComputeCapabilities,
    ) -> None:
        """Register a Lightning worker."""
        self._worker_registered = True
        self._worker_id = worker_id
        self._worker_capabilities = capabilities
        self._worker_status = WorkerStatus.READY
        self._last_heartbeat = time.time()
        self._worker_started_at = time.time()
        if capabilities.gpu:
            self._gpu_info = capabilities.gpu

    def heartbeat(
        self,
        worker_id: str,
        capabilities: ComputeCapabilities,
        status: WorkerStatus = WorkerStatus.READY,
    ) -> None:
        if worker_id != self._worker_id:
            return
        self._last_heartbeat = time.time()
        self._worker_capabilities = capabilities
        self._worker_status = status
        if capabilities.gpu:
            self._gpu_info = capabilities.gpu

    def disconnect_worker(self) -> None:
        self._worker_registered = False
        self._worker_id = None
        self._worker_status = WorkerStatus.DISCONNECTED
        self._gpu_info = None

    def get_worker_id(self) -> str | None:
        return self._worker_id

    def get_last_heartbeat(self) -> float | None:
        return self._last_heartbeat

    def is_configured(self) -> bool:
        return self._configured

    def get_worker_health(self) -> WorkerHealth | None:
        if not self._worker_registered or not self._worker_id:
            return None
        uptime = time.time() - self._worker_started_at if self._worker_started_at else 0.0
        return WorkerHealth(
            worker_id=self._worker_id,
            status=self._worker_status,
            gpu=self._gpu_info,
            uptime_seconds=uptime,
        )

    def update_capabilities(self, capabilities: ComputeCapabilities) -> None:
        if self._worker_registered:
            self._worker_capabilities = capabilities
            if capabilities.gpu:
                self._gpu_info = capabilities.gpu

    def _is_worker_stale(self) -> bool:
        if self._last_heartbeat is None:
            return True
        return (time.time() - self._last_heartbeat) > self.WORKER_TIMEOUT_SECONDS

    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        if self.health() != ComputeProviderStatus.READY:
            from aurora.compute.errors import ProviderUnavailable
            raise ProviderUnavailable(f"Lightning provider not ready: {self.health().value}")

        job_id = f"job-lightning-{uuid.uuid4().hex[:12]}"
        job = ComputeJob(
            job_id=job_id,
            workload_type=request.workload_type,
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            worker_id=self._worker_id,
            status=JobStatus.QUEUED,
        )
        self._jobs[job_id] = job
        return job

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            job = self._jobs[job_id]
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                return True
        return False

    def run_benchmark(self, matrix_size: int = 1024, iterations: int = 10) -> BenchmarkResult:
        if self.health() != ComputeProviderStatus.READY or not self._worker_id:
            return BenchmarkResult(
                worker_id="none",
                provider_type=ComputeProviderType.LIGHTNING,
                gpu=GPUInfo(),
                matrix_size=matrix_size,
                iterations=iterations,
                execution_time_seconds=0.0,
                result_checksum="",
                status=BenchmarkStatus.FAILED,
                error="No worker connected",
            )
        return BenchmarkResult(
            worker_id=self._worker_id,
            provider_type=ComputeProviderType.LIGHTNING,
            gpu=self._gpu_info or GPUInfo(),
            matrix_size=matrix_size,
            iterations=iterations,
            execution_time_seconds=0.0,
            result_checksum="pending-worker",
            status=BenchmarkStatus.NOT_RUN,
            error="Benchmark must be executed by connected worker",
        )

    def get_info(self):
        info = super().get_info()
        info.worker_status = self._worker_status
        if self._worker_started_at:
            info.metadata["worker_started_at"] = self._worker_started_at
        if self._gpu_info:
            info.metadata["gpu"] = self._gpu_info.model_dump()
        info.metadata["endpoint_configured"] = bool(self._endpoint)
        return info
