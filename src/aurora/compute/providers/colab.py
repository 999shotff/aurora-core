"""Compute Fabric — Google Colab provider.

User-controlled Colab worker connects via authenticated worker protocol.
Provider does NOT assume Colab is running. Reports DISCONNECTED when no worker.

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


class ColabProvider(ComputeProvider):
    """Google Colab GPU provider.

    Status depends entirely on a real worker connection.
    NOT_CONFIGURED if AURORA_COLAB_WORKER_ENABLED != true.
    DISCONNECTED if no worker has registered/heartbeated.
    READY only when a real worker has authenticated and passed health checks.
    """

    WORKER_TIMEOUT_SECONDS = 120

    def __init__(self) -> None:
        self._configured = os.environ.get("AURORA_COLAB_WORKER_ENABLED", "false").lower() == "true"
        self._worker_registered = False
        self._worker_id: str | None = None
        self._worker_capabilities: ComputeCapabilities = ComputeCapabilities()
        self._worker_status: WorkerStatus = WorkerStatus.OFFLINE
        self._last_heartbeat: float | None = None
        self._worker_started_at: float | None = None
        self._gpu_info: GPUInfo | None = None
        self._jobs: dict[str, ComputeJob] = {}
        self._provider_id = "colab"

    @property
    def provider_type(self) -> ComputeProviderType:
        return ComputeProviderType.GOOGLE_COLAB

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return "Google Colab"

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
        """Register a Colab worker. Called by worker protocol."""
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
        """Worker heartbeat with updated capabilities and status."""
        if worker_id != self._worker_id:
            return
        self._last_heartbeat = time.time()
        self._worker_capabilities = capabilities
        self._worker_status = status
        if capabilities.gpu:
            self._gpu_info = capabilities.gpu

    def disconnect_worker(self) -> None:
        """Mark worker as disconnected."""
        self._worker_registered = False
        self._worker_id = None
        self._worker_status = WorkerStatus.DISCONNECTED
        self._gpu_info = None

    def get_worker_id(self) -> str | None:
        return self._worker_id

    def get_last_heartbeat(self) -> float | None:
        return self._last_heartbeat

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
            raise ProviderUnavailable(f"Colab provider not ready: {self.health().value}")

        job_id = f"job-colab-{uuid.uuid4().hex[:12]}"
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
                provider_type=ComputeProviderType.GOOGLE_COLAB,
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
            provider_type=ComputeProviderType.GOOGLE_COLAB,
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
        return info
