"""Compute Fabric — provider interface.

Abstract base for CPU, Colab, Lightning providers.
Providers must NOT fabricate availability or GPU info.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import abc
import time

from aurora.compute.schemas import (
    BenchmarkResult,
    BenchmarkStatus,
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeProviderInfo,
    ComputeProviderStatus,
    ComputeProviderType,
    GPUInfo,
    JobStatus,
    WorkerHealth,
    WorkerStatus,
)


class ComputeProvider(abc.ABC):
    """Abstract compute provider interface.

    Each provider implements start/stop/health/capabilities/submit/cancel.
    """

    @property
    @abc.abstractmethod
    def provider_type(self) -> ComputeProviderType:
        ...

    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def start(self) -> None:
        """Start the provider. May be no-op for CPU."""
        ...

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the provider."""
        ...

    @abc.abstractmethod
    def health(self) -> ComputeProviderStatus:
        """Current health status. Never fabricate READY."""
        ...

    @abc.abstractmethod
    def capabilities(self) -> ComputeCapabilities:
        """What this provider can do."""
        ...

    @abc.abstractmethod
    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        """Submit a job. Raises if not ready."""
        ...

    @abc.abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        ...

    def get_info(self) -> ComputeProviderInfo:
        """Get full provider info."""
        caps = self.capabilities()
        status = self.health()
        worker_id = getattr(self, "get_worker_id", lambda: None)()
        return ComputeProviderInfo(
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            name=self.name,
            status=status,
            capabilities=caps,
            last_health_check=time.time(),
            worker_id=worker_id,
            worker_status=WorkerStatus.READY if status == ComputeProviderStatus.READY else WorkerStatus.OFFLINE,
        )

    def run_benchmark(self, matrix_size: int = 1024, iterations: int = 10) -> BenchmarkResult:
        """Run a GPU benchmark. Default: no-op for non-GPU providers."""
        return BenchmarkResult(
            worker_id="cpu-local",
            provider_type=self.provider_type,
            gpu=GPUInfo(),
            matrix_size=matrix_size,
            iterations=iterations,
            execution_time_seconds=0.0,
            result_checksum="no-gpu",
            status=BenchmarkStatus.FAILED,
            error="Provider does not support GPU benchmark",
        )

    def get_worker_health(self) -> WorkerHealth | None:
        """Get worker health if available."""
        return None

    def update_capabilities(self, capabilities: ComputeCapabilities) -> None:
        """Update provider capabilities from worker report."""
        pass
