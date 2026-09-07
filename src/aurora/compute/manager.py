"""Compute Fabric — ComputeManager (v2).

Central orchestration: providers, routing, jobs, workers, health, benchmark.
Worker Protocol v2: versioned registration, heartbeat acks, capability updates.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid

from aurora.compute.audit import ComputeAuditLog
from aurora.compute.errors import (
    FallbackRequired,
    InvalidMode,
    InvalidProvider,
    JobNotFound,
    ProviderBusy,
    ProviderUnavailable,
    UnauthorizedWorker,
    WorkerNotFound,
)
from aurora.compute.provider import ComputeProvider
from aurora.compute.registry import ProviderRegistry
from aurora.compute.schemas import (
    AuditAction,
    BenchmarkRequest,
    BenchmarkResult,
    BenchmarkStatus,
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeMode,
    ComputeProviderInfo,
    ComputeProviderStatus,
    ComputeProviderType,
    ComputeStatus,
    GPUInfo,
    JobProgress,
    JobStatus,
    PROTOCOL_VERSION,
    WorkerHeartbeat,
    WorkerHeartbeatAck,
    WorkerRegistration,
    WorkerRegistrationAck,
    WorkerShutdown,
    WorkerStatus,
)

logger = logging.getLogger(__name__)


class ComputeManager:
    """Central compute orchestration (v2).

    Responsibilities:
    - Track provider status
    - Select providers based on mode
    - Route jobs
    - Handle fallback
    - Worker management with v2 protocol
    - Benchmark execution
    - Audit logging
    """

    def __init__(self) -> None:
        self._registry = ProviderRegistry()
        self._audit = ComputeAuditLog()
        self._enabled = False
        self._mode = ComputeMode.CPU
        self._jobs: dict[str, ComputeJob] = {}
        self._workers: dict[str, str] = {}  # worker_id -> provider_id
        self._worker_tokens: dict[str, str] = {}  # worker_id -> api_token
        self._worker_last_seen: dict[str, float] = {}
        self._total_completed = 0
        self._worker_api_token = os.environ.get("AURORA_COMPUTE_WORKER_TOKEN", "")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def mode(self) -> ComputeMode:
        return self._mode

    def enable(self) -> ComputeStatus:
        self._enabled = True
        self._audit.record(AuditAction.COMPUTE_ENABLED, detail="Compute enabled")
        self._emit_event("compute", "Compute enabled", "live")
        return self.get_status()

    def disable(self) -> ComputeStatus:
        self._enabled = False
        for provider in self._registry.list_providers():
            if provider.provider_type != ComputeProviderType.CPU:
                provider.stop()
        self._audit.record(AuditAction.COMPUTE_DISABLED, detail="Compute disabled")
        self._emit_event("compute", "Compute disabled", "live")
        return self.get_status()

    def set_mode(self, mode: ComputeMode) -> ComputeStatus:
        if mode == self._mode:
            return self.get_status()

        if mode == ComputeMode.GOOGLE_COLAB:
            provider = self._registry.get_by_type(ComputeProviderType.GOOGLE_COLAB)
            if provider is None:
                raise InvalidProvider("Colab provider not available")
        elif mode == ComputeMode.LIGHTNING:
            provider = self._registry.get_by_type(ComputeProviderType.LIGHTNING)
            if provider is None:
                raise InvalidProvider("Lightning provider not available")

        self._mode = mode
        self._audit.record(AuditAction.MODE_CHANGED, detail=f"Mode set to {mode.value}")
        self._emit_event("compute", f"Mode: {mode.value}", "live")
        return self.get_status()

    def get_status(self) -> ComputeStatus:
        providers = [p.get_info() for p in self._registry.list_providers()]
        active = self._select_active_provider()
        gpu_enabled = any(
            p.status == ComputeProviderStatus.READY
            for p in providers
            if p.provider_type != ComputeProviderType.CPU
        )
        return ComputeStatus(
            enabled=self._enabled,
            mode=self._mode,
            active_provider=active.provider_id if active else None,
            providers=providers,
            active_jobs=sum(1 for j in self._jobs.values() if j.status in (JobStatus.QUEUED, JobStatus.ASSIGNED, JobStatus.RUNNING)),
            total_jobs_completed=self._total_completed,
            gpu_enabled=gpu_enabled,
            last_updated=time.time(),
        )

    def get_providers(self) -> list[ComputeProviderInfo]:
        return [p.get_info() for p in self._registry.list_providers()]

    def health(self) -> dict:
        providers = {p.provider_id: p.health().value for p in self._registry.list_providers()}
        return {
            "status": "healthy" if self._enabled else "degraded",
            "service": "compute-fabric",
            "version": "0.2.0",
            "protocol_version": PROTOCOL_VERSION,
            "enabled": self._enabled,
            "mode": self._mode.value,
            "providers": providers,
            "active_jobs": sum(1 for j in self._jobs.values() if j.status in (JobStatus.QUEUED, JobStatus.ASSIGNED, JobStatus.RUNNING)),
            "total_completed": self._total_completed,
        }

    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        if not self._enabled:
            raise ProviderUnavailable("Compute is disabled")

        provider = self._resolve_provider(request)
        if provider is None:
            raise ProviderUnavailable("No provider available for this workload")

        status = provider.health()
        if status != ComputeProviderStatus.READY:
            if self._mode == ComputeMode.AUTO:
                fallback = self._registry.get("cpu")
                if fallback and fallback.health() == ComputeProviderStatus.READY:
                    provider = fallback
                else:
                    raise ProviderUnavailable(f"Provider {provider.provider_id} not ready and no CPU fallback")
            else:
                raise ProviderUnavailable(f"Provider {provider.provider_id} not ready: {status.value}")

        job = provider.submit_job(request)
        self._jobs[job.job_id] = job
        self._audit.record(
            AuditAction.JOB_SUBMITTED,
            provider_id=provider.provider_id,
            job_id=job.job_id,
            detail=f"Workload: {request.workload_type.value}",
        )
        self._emit_event("compute", f"Job submitted: {job.job_id}", "live")
        return job

    def get_job(self, job_id: str) -> ComputeJob:
        if job_id not in self._jobs:
            raise JobNotFound(f"Job {job_id} not found")
        return self._jobs[job_id]

    def list_jobs(self, limit: int = 50) -> list[ComputeJob]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        provider = self._registry.get(job.provider_id)
        if provider:
            ok = provider.cancel_job(job_id)
            if ok:
                job.status = JobStatus.CANCELLED
                job.completed_at = time.time()
                self._audit.record(
                    AuditAction.JOB_CANCELLED,
                    provider_id=job.provider_id,
                    job_id=job_id,
                )
                self._emit_event("compute", f"Job cancelled: {job_id}", "live")
            return ok
        return False

    def update_job_progress(self, job_id: str, progress: JobProgress) -> ComputeJob:
        job = self.get_job(job_id)
        job.progress = progress.progress
        if progress.message:
            job.logs.append(progress.message)
        return job

    def complete_job(self, job_id: str, result: dict, result_hash: str | None = None) -> ComputeJob:
        job = self.get_job(job_id)
        job.status = JobStatus.COMPLETED
        job.completed_at = time.time()
        job.progress = 1.0
        job.result = result
        job.result_hash = result_hash
        self._total_completed += 1
        self._audit.record(
            AuditAction.JOB_COMPLETED,
            provider_id=job.provider_id,
            job_id=job_id,
        )
        self._emit_event("compute", f"Job completed: {job_id}", "live")
        return job

    def fail_job(self, job_id: str, error: str) -> ComputeJob:
        job = self.get_job(job_id)
        job.status = JobStatus.FAILED
        job.completed_at = time.time()
        job.error = error
        self._audit.record(
            AuditAction.JOB_FAILED,
            provider_id=job.provider_id,
            job_id=job_id,
            detail=error,
            success=False,
        )
        self._emit_event("compute", f"Job failed: {job_id}", "live")
        return job

    # ── Benchmark ──────────────────────────────────────────────

    def run_benchmark(self, request: BenchmarkRequest) -> BenchmarkResult:
        provider = self._registry.get_by_type(request.provider_type)
        if provider is None:
            return BenchmarkResult(
                worker_id="none",
                provider_type=request.provider_type,
                gpu=GPUInfo(),
                matrix_size=request.matrix_size,
                iterations=request.iterations,
                execution_time_seconds=0.0,
                result_checksum="",
                status=BenchmarkStatus.FAILED,
                error=f"Provider {request.provider_type.value} not available",
            )

        result = provider.run_benchmark(request.matrix_size, request.iterations)
        self._audit.record(
            AuditAction.BENCHMARK_COMPLETED,
            provider_id=provider.provider_id,
            detail=f"Status: {result.status.value}, GFLOPS: {result.gflops}",
            success=result.status == BenchmarkStatus.PASSED,
        )
        self._emit_event("compute", f"Benchmark: {result.status.value}", "live")
        return result

    # ── Worker Management (v2) ────────────────────────────────

    def register_worker(self, registration: WorkerRegistration) -> WorkerRegistrationAck:
        if self._worker_api_token and registration.api_token != self._worker_api_token:
            self._audit.record(
                AuditAction.WORKER_AUTH_FAILED,
                worker_id=registration.worker_id,
                detail="Invalid token",
                success=False,
            )
            raise UnauthorizedWorker("Invalid worker API token")

        if registration.protocol_version != PROTOCOL_VERSION:
            return WorkerRegistrationAck(
                accepted=False,
                worker_id=registration.worker_id,
                error=f"Protocol mismatch: expected {PROTOCOL_VERSION}, got {registration.protocol_version}",
            )

        provider = self._registry.get_by_type(registration.provider_type)
        if provider is None:
            raise InvalidProvider(f"Provider {registration.provider_type.value} not available")

        if hasattr(provider, "register_worker"):
            provider.register_worker(registration.worker_id, registration.capabilities)

        self._workers[registration.worker_id] = provider.provider_id
        self._worker_tokens[registration.worker_id] = registration.api_token
        self._worker_last_seen[registration.worker_id] = time.time()

        self._audit.record(
            AuditAction.WORKER_REGISTERED,
            provider_id=provider.provider_id,
            worker_id=registration.worker_id,
            detail=f"Protocol: {registration.protocol_version}, GPU: {registration.capabilities.gpu.name if registration.capabilities.gpu else 'none'}",
        )
        self._emit_event("compute", f"Worker registered: {registration.worker_id}", "live")

        if registration.capabilities.gpu:
            self._audit.record(
                AuditAction.GPU_DETECTED,
                provider_id=provider.provider_id,
                worker_id=registration.worker_id,
                detail=f"GPU: {registration.capabilities.gpu.name}, VRAM: {registration.capabilities.gpu.vram_mb}MB",
            )

        return WorkerRegistrationAck(
            accepted=True,
            worker_id=registration.worker_id,
            protocol_version=PROTOCOL_VERSION,
        )

    def worker_heartbeat(self, worker_id: str, heartbeat: WorkerHeartbeat) -> WorkerHeartbeatAck:
        if self._worker_api_token and heartbeat.api_token != self._worker_api_token:
            raise UnauthorizedWorker("Invalid worker API token")

        if worker_id not in self._workers:
            raise WorkerNotFound(f"Worker {worker_id} not registered")

        provider_id = self._workers[worker_id]
        provider = self._registry.get(provider_id)
        if provider and hasattr(provider, "heartbeat"):
            provider.heartbeat(worker_id, heartbeat.capabilities, heartbeat.status)

        self._worker_last_seen[worker_id] = time.time()

        self._audit.record(
            AuditAction.WORKER_HEARTBEAT,
            provider_id=provider_id,
            worker_id=worker_id,
        )

        pending = sum(
            1 for j in self._jobs.values()
            if j.worker_id == worker_id and j.status in (JobStatus.QUEUED, JobStatus.ASSIGNED)
        )

        return WorkerHeartbeatAck(
            accepted=True,
            pending_jobs=pending,
            shutdown_requested=False,
        )

    def update_worker_capabilities(self, worker_id: str, capabilities: ComputeCapabilities) -> bool:
        if worker_id not in self._workers:
            return False
        provider_id = self._workers[worker_id]
        provider = self._registry.get(provider_id)
        if provider and hasattr(provider, "update_capabilities"):
            provider.update_capabilities(capabilities)
            return True
        return False

    def get_worker_health(self, worker_id: str) -> WorkerHealth | None:
        if worker_id not in self._workers:
            return None
        provider_id = self._workers[worker_id]
        provider = self._registry.get(provider_id)
        if provider and hasattr(provider, "get_worker_health"):
            return provider.get_worker_health()
        return None

    def shutdown_worker(self, shutdown: WorkerShutdown) -> bool:
        if self._worker_api_token and shutdown.api_token != self._worker_api_token:
            raise UnauthorizedWorker("Invalid worker API token")

        if shutdown.worker_id not in self._workers:
            return False

        provider_id = self._workers.pop(shutdown.worker_id)
        self._worker_tokens.pop(shutdown.worker_id, None)
        self._worker_last_seen.pop(shutdown.worker_id, None)
        provider = self._registry.get(provider_id)
        if provider and hasattr(provider, "disconnect_worker"):
            provider.disconnect_worker()

        self._audit.record(
            AuditAction.WORKER_SHUTDOWN,
            provider_id=provider_id,
            worker_id=shutdown.worker_id,
            detail=f"Reason: {shutdown.reason}",
        )
        self._emit_event("compute", f"Worker shutdown: {shutdown.worker_id}", "live")
        return True

    def check_stale_workers(self) -> list[str]:
        stale = []
        for worker_id, last_seen in list(self._worker_last_seen.items()):
            if (time.time() - last_seen) > 150:
                stale.append(worker_id)
                provider_id = self._workers.pop(worker_id, None)
                self._worker_tokens.pop(worker_id, None)
                self._worker_last_seen.pop(worker_id, None)
                if provider_id:
                    provider = self._registry.get(provider_id)
                    if provider and hasattr(provider, "disconnect_worker"):
                        provider.disconnect_worker()
                    self._audit.record(
                        AuditAction.WORKER_DISCONNECTED,
                        provider_id=provider_id,
                        worker_id=worker_id,
                        detail="Heartbeat timeout",
                    )
        return stale

    # ── Routing ────────────────────────────────────────────────

    def _resolve_provider(self, request: ComputeJobRequest) -> ComputeProvider | None:
        if request.provider_preference:
            p = self._registry.get_by_type(request.provider_preference)
            if p:
                return p
            return None

        if self._mode == ComputeMode.CPU:
            return self._registry.get("cpu")
        if self._mode == ComputeMode.GOOGLE_COLAB:
            return self._registry.get_by_type(ComputeProviderType.GOOGLE_COLAB)
        if self._mode == ComputeMode.LIGHTNING:
            return self._registry.get_by_type(ComputeProviderType.LIGHTNING)

        return self._select_active_provider()

    def _select_active_provider(self) -> ComputeProvider | None:
        if self._mode == ComputeMode.CPU:
            return self._registry.get("cpu")

        for ptype in (ComputeProviderType.LIGHTNING, ComputeProviderType.GOOGLE_COLAB):
            p = self._registry.get_by_type(ptype)
            if p and p.health() == ComputeProviderStatus.READY:
                return p

        return self._registry.get("cpu")

    # ── Events ─────────────────────────────────────────────────

    def _emit_event(self, kind: str, label: str, origin: str) -> None:
        try:
            from aurora.product.websocket import broadcast_event
            broadcast_event({
                "kind": kind,
                "label": label,
                "origin": origin,
                "timestamp": time.time(),
            })
        except Exception:
            pass

    # ── Audit ──────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 50) -> list:
        return self._audit.get_entries(limit)
