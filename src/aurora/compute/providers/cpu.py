"""Compute Fabric — CPU provider.

Always available. Safe fallback. No GPU required.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import time
import uuid

from aurora.compute.provider import ComputeProvider
from aurora.compute.schemas import (
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeProviderStatus,
    ComputeProviderType,
    JobStatus,
)


class CPUProvider(ComputeProvider):
    """CPU-only compute provider. Always READY when enabled."""

    def __init__(self) -> None:
        self._enabled = True
        self._jobs: dict[str, ComputeJob] = {}

    @property
    def provider_type(self) -> ComputeProviderType:
        return ComputeProviderType.CPU

    @property
    def provider_id(self) -> str:
        return "cpu"

    @property
    def name(self) -> str:
        return "CPU"

    def start(self) -> None:
        self._enabled = True

    def stop(self) -> None:
        self._enabled = False

    def health(self) -> ComputeProviderStatus:
        if not self._enabled:
            return ComputeProviderStatus.DISABLED
        return ComputeProviderStatus.READY

    def capabilities(self) -> ComputeCapabilities:
        return ComputeCapabilities(
            inference=True,
            embeddings=True,
            vision=False,
            training=False,
            max_concurrency=1,
            gpu_name=None,
            vram_gb=None,
            framework="python",
        )

    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        if not self._enabled:
            from aurora.compute.errors import ProviderUnavailable
            raise ProviderUnavailable("CPU provider is disabled")

        job_id = f"job-cpu-{uuid.uuid4().hex[:12]}"
        job = ComputeJob(
            job_id=job_id,
            workload_type=request.workload_type,
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            status=JobStatus.COMPLETED,
            started_at=time.time(),
            completed_at=time.time(),
            result={
                "provider": "cpu",
                "workload": request.workload_type.value,
                "message": "Processed on CPU",
            },
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
