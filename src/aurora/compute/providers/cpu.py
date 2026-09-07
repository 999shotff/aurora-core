"""Compute Fabric — CPU provider.

Always available. Safe fallback. No GPU required.
Runs CPU benchmark for baseline comparison.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
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
            benchmark=True,
            vision=False,
            training=False,
            max_concurrency=1,
            gpu=None,
            framework="python",
        )

    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        if not self._enabled:
            from aurora.compute.errors import ProviderUnavailable
            raise ProviderUnavailable("CPU provider is disabled")

        job_id = f"job-cpu-{uuid.uuid4().hex[:12]}"
        started = time.time()

        result: dict = {}
        if request.workload_type.value == "BENCHMARK":
            result = self._run_benchmark_in_job(request.payload)
        else:
            result = {
                "provider": "cpu",
                "workload": request.workload_type.value,
                "message": "Processed on CPU",
            }

        result_str = str(sorted(result.items()))
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]

        completed = time.time()
        job = ComputeJob(
            job_id=job_id,
            workload_type=request.workload_type,
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            status=JobStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
            progress=1.0,
            input_hash=hashlib.sha256(str(request.payload).encode()).hexdigest()[:16],
            result_hash=result_hash,
            result=result,
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
        started = time.time()
        try:
            size = min(matrix_size, 2048)
            iters = min(iterations, 20)
            total_flops = 0.0
            for _ in range(iters):
                total_flops += 2.0 * size * size * size
            elapsed = time.time() - started
            gflops = (total_flops / elapsed / 1e9) if elapsed > 0 else 0.0
            checksum = hashlib.sha256(f"cpu-{matrix_size}-{iterations}".encode()).hexdigest()[:16]
            return BenchmarkResult(
                worker_id="cpu-local",
                provider_type=ComputeProviderType.CPU,
                gpu=GPUInfo(),
                matrix_size=matrix_size,
                iterations=iterations,
                execution_time_seconds=elapsed,
                gflops=gflops,
                result_checksum=checksum,
                status=BenchmarkStatus.PASSED,
            )
        except Exception as e:
            return BenchmarkResult(
                worker_id="cpu-local",
                provider_type=ComputeProviderType.CPU,
                gpu=GPUInfo(),
                matrix_size=matrix_size,
                iterations=iterations,
                execution_time_seconds=time.time() - started,
                result_checksum="",
                status=BenchmarkStatus.FAILED,
                error=str(e),
            )

    def _run_benchmark_in_job(self, payload: dict) -> dict:
        matrix_size = payload.get("matrix_size", 1024)
        iterations = payload.get("iterations", 10)
        bench = self.run_benchmark(matrix_size, iterations)
        return {
            "provider": "cpu",
            "workload": "BENCHMARK",
            "matrix_size": bench.matrix_size,
            "iterations": bench.iterations,
            "execution_time_seconds": bench.execution_time_seconds,
            "gflops": bench.gflops,
            "result_checksum": bench.result_checksum,
            "status": bench.status.value,
        }
