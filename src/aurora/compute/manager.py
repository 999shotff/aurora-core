"""Compute Fabric — ComputeManager.

Central orchestration: providers, routing, jobs, workers, health.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

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
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeMode,
    ComputeProviderInfo,
    ComputeProviderStatus,
    ComputeProviderType,
    ComputeStatus,
    JobStatus,
    WorkerHeartbeat,
    WorkerRegistration,
    WorkerShutdown,
)

logger = logging.getLogger(__name__)


class ComputeManager:
    """Central compute orchestration.

    Responsibilities:
    - Track provider status
    - Select providers based on mode
    - Route jobs
    - Handle fallback
    - Worker management
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
        return ComputeStatus(
            enabled=self._enabled,
            mode=self._mode,
            active_provider=active.provider_id if active else None,
            providers=providers,
            active_jobs=sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING),
            total_jobs_completed=self._total_completed,
            last_updated=time.time(),
        )

    def get_providers(self) -> list[ComputeProviderInfo]:
        return [p.get_info() for p in self._registry.list_providers()]

    def health(self) -> dict:
        providers = {p.provider_id: p.health().value for p in self._registry.list_providers()}
        return {
            "status": "healthy" if self._enabled else "degraded",
            "service": "compute-fabric",
            "version": "0.1.0",
            "enabled": self._enabled,
            "mode": self._mode.value,
            "providers": providers,
            "active_jobs": sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING),
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
        return job

    def get_job(self, job_id: str) -> ComputeJob:
        if job_id not in self._jobs:
            raise JobNotFound(f"Job {job_id} not found")
        return self._jobs[job_id]

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        provider = self._registry.get(job.provider_id)
        if provider:
            ok = provider.cancel_job(job_id)
            if ok:
                self._audit.record(
                    AuditAction.JOB_CANCELLED,
                    provider_id=job.provider_id,
                    job_id=job_id,
                )
            return ok
        return False

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

    # ── Worker Management ────────────────────────────────────────

    def register_worker(self, registration: WorkerRegistration) -> ComputeProviderInfo:
        if self._worker_api_token and registration.api_token != self._worker_api_token:
            raise UnauthorizedWorker("Invalid worker API token")

        provider = self._registry.get_by_type(registration.provider_type)
        if provider is None:
            raise InvalidProvider(f"Provider {registration.provider_type.value} not available")

        if hasattr(provider, "register_worker"):
            provider.register_worker(registration.worker_id, registration.capabilities)
        self._workers[registration.worker_id] = provider.provider_id
        self._worker_tokens[registration.worker_id] = registration.api_token

        self._audit.record(
            AuditAction.WORKER_REGISTERED,
            provider_id=provider.provider_id,
            worker_id=registration.worker_id,
            detail=f"Capabilities: inference={registration.capabilities.inference}",
        )
        self._emit_event("compute", f"Worker registered: {registration.worker_id}", "live")
        return provider.get_info()

    def worker_heartbeat(self, worker_id: str, heartbeat: WorkerHeartbeat) -> ComputeProviderInfo:
        if self._worker_api_token and heartbeat.api_token != self._worker_api_token:
            raise UnauthorizedWorker("Invalid worker API token")

        if worker_id not in self._workers:
            raise WorkerNotFound(f"Worker {worker_id} not registered")

        provider_id = self._workers[worker_id]
        provider = self._registry.get(provider_id)
        if provider and hasattr(provider, "heartbeat"):
            provider.heartbeat(worker_id, heartbeat.capabilities)

        self._audit.record(
            AuditAction.WORKER_HEARTBEAT,
            provider_id=provider_id,
            worker_id=worker_id,
        )
        return provider.get_info() if provider else ComputeProviderInfo(
            provider_id=provider_id,
            provider_type=ComputeProviderType.CPU,
            name="Unknown",
            status=ComputeProviderStatus.UNKNOWN,
        )

    def shutdown_worker(self, shutdown: WorkerShutdown) -> bool:
        if self._worker_api_token and shutdown.api_token != self._worker_api_token:
            raise UnauthorizedWorker("Invalid worker API token")

        if shutdown.worker_id not in self._workers:
            return False

        provider_id = self._workers.pop(shutdown.worker_id)
        self._worker_tokens.pop(shutdown.worker_id, None)
        provider = self._registry.get(provider_id)
        if provider and hasattr(provider, "disconnect_worker"):
            provider.disconnect_worker()

        self._audit.record(
            AuditAction.WORKER_DISCONNECTED,
            provider_id=provider_id,
            worker_id=shutdown.worker_id,
            detail=f"Reason: {shutdown.reason}",
        )
        self._emit_event("compute", f"Worker disconnected: {shutdown.worker_id}", "live")
        return True

    # ── Events ───────────────────────────────────────────────────

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

    # ── Audit ────────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 50) -> list:
        return self._audit.get_entries(limit)
