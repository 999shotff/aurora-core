"""Compute Fabric — Google Colab provider.

User-controlled Colab worker connects via authenticated worker protocol.
Provider does NOT assume Colab is running. Reports DISCONNECTED when no worker.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import os
import time

from aurora.compute.provider import ComputeProvider
from aurora.compute.schemas import (
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeProviderStatus,
    ComputeProviderType,
    JobStatus,
)


class ColabProvider(ComputeProvider):
    """Google Colab GPU provider.

    Status depends entirely on a real worker connection.
    NOT_CONFIGURED if AURORA_COLAB_WORKER_ENABLED != true.
    DISCONNECTED if no worker has registered/heartbeated.
    """

    WORKER_TIMEOUT_SECONDS = 120

    def __init__(self) -> None:
        self._configured = os.environ.get("AURORA_COLAB_WORKER_ENABLED", "false").lower() == "true"
        self._worker_registered = False
        self._worker_id: str | None = None
        self._worker_capabilities: ComputeCapabilities = ComputeCapabilities()
        self._last_heartbeat: float | None = None
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

    def health(self) -> ComputeProviderStatus:
        if not self._configured:
            return ComputeProviderStatus.NOT_CONFIGURED
        if not self._worker_registered:
            return ComputeProviderStatus.DISCONNECTED
        if self._is_worker_stale():
            self._worker_registered = False
            return ComputeProviderStatus.DISCONNECTED
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
        self._last_heartbeat = time.time()

    def heartbeat(
        self,
        worker_id: str,
        capabilities: ComputeCapabilities,
    ) -> None:
        """Worker heartbeat."""
        if worker_id != self._worker_id:
            return
        self._last_heartbeat = time.time()
        self._worker_capabilities = capabilities

    def disconnect_worker(self) -> None:
        """Mark worker as disconnected."""
        self._worker_registered = False
        self._worker_id = None

    def get_worker_id(self) -> str | None:
        return self._worker_id

    def get_last_heartbeat(self) -> float | None:
        return self._last_heartbeat

    def _is_worker_stale(self) -> bool:
        if self._last_heartbeat is None:
            return True
        return (time.time() - self._last_heartbeat) > self.WORKER_TIMEOUT_SECONDS

    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        if self.health() != ComputeProviderStatus.READY:
            from aurora.compute.errors import ProviderUnavailable
            raise ProviderUnavailable(f"Colab provider not ready: {self.health().value}")

        import uuid
        job_id = f"job-colab-{uuid.uuid4().hex[:12]}"
        job = ComputeJob(
            job_id=job_id,
            workload_type=request.workload_type,
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            status=JobStatus.PENDING,
        )
        self._jobs[job_id] = job
        return job

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            job = self._jobs[job_id]
            if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                return True
        return False
