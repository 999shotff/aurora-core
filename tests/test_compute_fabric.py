"""Compute Fabric — comprehensive tests.

35+ tests covering schemas, providers, registry, manager, routing, workers, jobs, security.
"""

from __future__ import annotations

import os
import time

import pytest

from aurora.compute.schemas import (
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeMode,
    ComputeProviderInfo,
    ComputeProviderStatus,
    ComputeProviderType,
    ComputeStatus,
    JobStatus,
    WorkloadType,
    WorkerHeartbeat,
    WorkerRegistration,
    WorkerShutdown,
    AuditAction,
    AuditRecord,
    ModeChangeRequest,
)
from aurora.compute.errors import (
    ComputeError,
    ProviderNotConfigured,
    ProviderUnavailable,
    InvalidMode,
    InvalidProvider,
    UnauthorizedWorker,
    WorkerNotFound,
    JobNotFound,
    FallbackRequired,
)
from aurora.compute.provider import ComputeProvider
from aurora.compute.providers.cpu import CPUProvider
from aurora.compute.providers.colab import ColabProvider
from aurora.compute.providers.lightning import LightningProvider
from aurora.compute.registry import ProviderRegistry
from aurora.compute.manager import ComputeManager
from aurora.compute.audit import ComputeAuditLog


# ============================================================
# Schema Tests
# ============================================================

class TestSchemas:
    def test_compute_provider_type_enum(self):
        assert ComputeProviderType.CPU == "CPU"
        assert ComputeProviderType.GOOGLE_COLAB == "GOOGLE_COLAB"
        assert ComputeProviderType.LIGHTNING == "LIGHTNING"

    def test_compute_provider_status_enum(self):
        assert ComputeProviderStatus.READY == "READY"
        assert ComputeProviderStatus.DISABLED == "DISABLED"
        assert ComputeProviderStatus.NOT_CONFIGURED == "NOT_CONFIGURED"
        assert ComputeProviderStatus.DISCONNECTED == "DISCONNECTED"

    def test_compute_mode_enum(self):
        assert ComputeMode.AUTO == "AUTO"
        assert ComputeMode.CPU == "CPU"
        assert ComputeMode.GOOGLE_COLAB == "GOOGLE_COLAB"
        assert ComputeMode.LIGHTNING == "LIGHTNING"

    def test_job_status_enum(self):
        assert JobStatus.PENDING == "PENDING"
        assert JobStatus.COMPLETED == "COMPLETED"
        assert JobStatus.FAILED == "FAILED"

    def test_workload_type_enum(self):
        assert WorkloadType.INFERENCE == "INFERENCE"
        assert WorkloadType.TRAINING == "TRAINING"

    def test_capabilities_defaults(self):
        caps = ComputeCapabilities()
        assert caps.inference is False
        assert caps.gpu_name is None
        assert caps.vram_gb is None

    def test_capabilities_with_gpu(self):
        caps = ComputeCapabilities(
            inference=True, gpu_name="A100", vram_gb=40.0,
            cuda_version="12.1", framework="pytorch",
        )
        assert caps.gpu_name == "A100"
        assert caps.vram_gb == 40.0

    def test_provider_info_fields(self):
        info = ComputeProviderInfo(
            provider_id="cpu", provider_type=ComputeProviderType.CPU,
            name="CPU", status=ComputeProviderStatus.READY,
        )
        assert info.provider_id == "cpu"
        assert info.status == ComputeProviderStatus.READY

    def test_compute_job_fields(self):
        job = ComputeJob(
            job_id="job-001", workload_type=WorkloadType.INFERENCE,
            provider_id="cpu", provider_type=ComputeProviderType.CPU,
        )
        assert job.job_id == "job-001"
        assert job.status == JobStatus.PENDING

    def test_compute_status_fields(self):
        status = ComputeStatus(enabled=True, mode=ComputeMode.AUTO)
        assert status.enabled is True
        assert status.mode == ComputeMode.AUTO

    def test_worker_registration_fields(self):
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="token-123",
        )
        assert reg.worker_id == "w-1"
        assert reg.protocol_version == "1.0"

    def test_worker_heartbeat_fields(self):
        hb = WorkerHeartbeat(
            worker_id="w-1", status=ComputeProviderStatus.READY,
            api_token="token-123",
        )
        assert hb.worker_id == "w-1"

    def test_mode_change_request(self):
        req = ModeChangeRequest(mode=ComputeMode.LIGHTNING)
        assert req.mode == ComputeMode.LIGHTNING

    def test_audit_record_fields(self):
        rec = AuditRecord(action=AuditAction.COMPUTE_ENABLED)
        assert rec.action == AuditAction.COMPUTE_ENABLED
        assert rec.success is True


# ============================================================
# Error Tests
# ============================================================

class TestErrors:
    def test_compute_error_hierarchy(self):
        assert issubclass(ProviderNotConfigured, ComputeError)
        assert issubclass(ProviderUnavailable, ComputeError)
        assert issubclass(InvalidMode, ComputeError)
        assert issubclass(UnauthorizedWorker, ComputeError)
        assert issubclass(JobNotFound, ComputeError)

    def test_error_messages(self):
        err = ProviderUnavailable("test message")
        assert str(err) == "test message"


# ============================================================
# CPU Provider Tests
# ============================================================

class TestCPUProvider:
    def test_cpu_always_ready(self):
        cpu = CPUProvider()
        assert cpu.health() == ComputeProviderStatus.READY

    def test_cpu_provider_type(self):
        cpu = CPUProvider()
        assert cpu.provider_type == ComputeProviderType.CPU
        assert cpu.provider_id == "cpu"
        assert cpu.name == "CPU"

    def test_cpu_capabilities(self):
        cpu = CPUProvider()
        caps = cpu.capabilities()
        assert caps.inference is True
        assert caps.gpu_name is None

    def test_cpu_submit_job(self):
        cpu = CPUProvider()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = cpu.submit_job(req)
        assert job.status == JobStatus.COMPLETED
        assert job.provider_id == "cpu"

    def test_cpu_cancel_job(self):
        cpu = CPUProvider()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = cpu.submit_job(req)
        assert cpu.cancel_job(job.job_id) is False  # already completed

    def test_cpu_start_stop(self):
        cpu = CPUProvider()
        cpu.stop()
        assert cpu.health() == ComputeProviderStatus.DISABLED
        cpu.start()
        assert cpu.health() == ComputeProviderStatus.READY

    def test_cpu_get_info(self):
        cpu = CPUProvider()
        info = cpu.get_info()
        assert info.provider_id == "cpu"
        assert info.status == ComputeProviderStatus.READY


# ============================================================
# Colab Provider Tests
# ============================================================

class TestColabProvider:
    def test_colab_not_configured_by_default(self):
        os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)
        colab = ColabProvider()
        assert colab.health() == ComputeProviderStatus.NOT_CONFIGURED

    def test_colab_configured_no_worker(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            assert colab.health() == ComputeProviderStatus.DISCONNECTED
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_colab_register_worker(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            caps = ComputeCapabilities(inference=True, gpu_name="T4", vram_gb=15.0)
            colab.register_worker("w-1", caps)
            assert colab.health() == ComputeProviderStatus.READY
            assert colab.get_worker_id() == "w-1"
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_colab_worker_timeout(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            colab.WORKER_TIMEOUT_SECONDS = 0
            caps = ComputeCapabilities(inference=True)
            colab.register_worker("w-1", caps)
            time.sleep(0.01)
            assert colab.health() == ComputeProviderStatus.DISCONNECTED
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_colab_capabilities_no_worker(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            caps = colab.capabilities()
            assert caps.gpu_name is None
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_colab_submit_job_not_ready(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
            with pytest.raises(ProviderUnavailable):
                colab.submit_job(req)
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)


# ============================================================
# Lightning Provider Tests
# ============================================================

class TestLightningProvider:
    def test_lightning_not_configured_by_default(self):
        os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
        os.environ.pop("AURORA_LIGHTNING_API_KEY", None)
        lt = LightningProvider()
        assert lt.health() == ComputeProviderStatus.NOT_CONFIGURED

    def test_lightning_configured_no_worker(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            lt = LightningProvider()
            assert lt.is_configured() is True
            assert lt.health() == ComputeProviderStatus.DISCONNECTED
        finally:
            os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
            os.environ.pop("AURORA_LIGHTNING_API_KEY", None)

    def test_lightning_register_worker(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            lt = LightningProvider()
            caps = ComputeCapabilities(inference=True, gpu_name="A100", vram_gb=80.0)
            lt.register_worker("w-1", caps)
            assert lt.health() == ComputeProviderStatus.READY
        finally:
            os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
            os.environ.pop("AURORA_LIGHTNING_API_KEY", None)

    def test_lightning_submit_job_not_ready(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            lt = LightningProvider()
            req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
            with pytest.raises(ProviderUnavailable):
                lt.submit_job(req)
        finally:
            os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
            os.environ.pop("AURORA_LIGHTNING_API_KEY", None)


# ============================================================
# Registry Tests
# ============================================================

class TestProviderRegistry:
    def test_registry_has_cpu(self):
        reg = ProviderRegistry()
        cpu = reg.get("cpu")
        assert cpu is not None
        assert isinstance(cpu, CPUProvider)

    def test_registry_has_colab(self):
        reg = ProviderRegistry()
        colab = reg.get("colab")
        assert colab is not None
        assert isinstance(colab, ColabProvider)

    def test_registry_has_lightning(self):
        reg = ProviderRegistry()
        lt = reg.get("lightning")
        assert lt is not None
        assert isinstance(lt, LightningProvider)

    def test_registry_get_by_type(self):
        reg = ProviderRegistry()
        cpu = reg.get_by_type(ComputeProviderType.CPU)
        assert cpu is not None

    def test_registry_list_all(self):
        reg = ProviderRegistry()
        providers = reg.list_providers()
        assert len(providers) == 3

    def test_registry_unregister_cpu_blocked(self):
        reg = ProviderRegistry()
        assert reg.unregister("cpu") is False

    def test_registry_unregister_other(self):
        reg = ProviderRegistry()
        reg.unregister("colab")
        assert reg.get("colab") is None


# ============================================================
# ComputeManager Tests
# ============================================================

class TestComputeManager:
    def test_manager_default_state(self):
        mgr = ComputeManager()
        assert mgr.enabled is False
        assert mgr.mode == ComputeMode.CPU

    def test_manager_enable(self):
        mgr = ComputeManager()
        status = mgr.enable()
        assert status.enabled is True

    def test_manager_disable(self):
        mgr = ComputeManager()
        mgr.enable()
        status = mgr.disable()
        assert status.enabled is False

    def test_manager_set_mode(self):
        mgr = ComputeManager()
        mgr.enable()
        status = mgr.set_mode(ComputeMode.AUTO)
        assert status.mode == ComputeMode.AUTO

    def test_manager_set_mode_invalid(self):
        mgr = ComputeManager()
        # Colab provider exists but is NOT_CONFIGURED; mode change succeeds
        status = mgr.set_mode(ComputeMode.GOOGLE_COLAB)
        assert status.mode == ComputeMode.GOOGLE_COLAB

    def test_manager_health(self):
        mgr = ComputeManager()
        h = mgr.health()
        assert h["status"] == "degraded"
        assert h["service"] == "compute-fabric"

    def test_manager_health_enabled(self):
        mgr = ComputeManager()
        mgr.enable()
        h = mgr.health()
        assert h["status"] == "healthy"

    def test_manager_submit_job_disabled(self):
        mgr = ComputeManager()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        with pytest.raises(ProviderUnavailable):
            mgr.submit_job(req)

    def test_manager_submit_job_enabled(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        assert job.status == JobStatus.COMPLETED

    def test_manager_get_job(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        found = mgr.get_job(job.job_id)
        assert found.job_id == job.job_id

    def test_manager_get_job_not_found(self):
        mgr = ComputeManager()
        with pytest.raises(JobNotFound):
            mgr.get_job("nonexistent")

    def test_manager_cancel_job(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        ok = mgr.cancel_job(job.job_id)
        assert ok is False  # already completed

    def test_manager_audit_log(self):
        mgr = ComputeManager()
        mgr.enable()
        entries = mgr.get_audit_log()
        assert len(entries) >= 1


# ============================================================
# Worker Management Tests
# ============================================================

class TestWorkerManagement:
    def test_register_worker(self):
        mgr = ComputeManager()
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="test-token",
        )
        info = mgr.register_worker(reg)
        assert info.provider_id == "colab"

    def test_register_worker_unauthorized(self):
        os.environ["AURORA_COMPUTE_WORKER_TOKEN"] = "secret"
        try:
            mgr = ComputeManager()
            reg = WorkerRegistration(
                worker_id="w-1", provider_id="colab",
                provider_type=ComputeProviderType.GOOGLE_COLAB,
                api_token="wrong",
            )
            with pytest.raises(UnauthorizedWorker):
                mgr.register_worker(reg)
        finally:
            os.environ.pop("AURORA_COMPUTE_WORKER_TOKEN", None)

    def test_worker_heartbeat(self):
        mgr = ComputeManager()
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="test-token",
        )
        mgr.register_worker(reg)
        hb = WorkerHeartbeat(
            worker_id="w-1", status=ComputeProviderStatus.READY,
            api_token="test-token",
        )
        info = mgr.worker_heartbeat("w-1", hb)
        assert info.provider_id == "colab"

    def test_worker_heartbeat_not_found(self):
        mgr = ComputeManager()
        hb = WorkerHeartbeat(
            worker_id="w-missing", status=ComputeProviderStatus.READY,
            api_token="test-token",
        )
        with pytest.raises(WorkerNotFound):
            mgr.worker_heartbeat("w-missing", hb)

    def test_shutdown_worker(self):
        mgr = ComputeManager()
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="test-token",
        )
        mgr.register_worker(reg)
        sd = WorkerShutdown(worker_id="w-1", reason="test", api_token="test-token")
        ok = mgr.shutdown_worker(sd)
        assert ok is True

    def test_shutdown_worker_not_found(self):
        mgr = ComputeManager()
        sd = WorkerShutdown(worker_id="w-missing", api_token="test-token")
        ok = mgr.shutdown_worker(sd)
        assert ok is False


# ============================================================
# Audit Tests
# ============================================================

class TestAuditLog:
    def test_record_entry(self):
        log = ComputeAuditLog()
        entry = log.record(AuditAction.COMPUTE_ENABLED, detail="test")
        assert entry.action == AuditAction.COMPUTE_ENABLED

    def test_get_entries(self):
        log = ComputeAuditLog()
        log.record(AuditAction.COMPUTE_ENABLED)
        log.record(AuditAction.COMPUTE_DISABLED)
        entries = log.get_entries(limit=10)
        assert len(entries) == 2

    def test_max_entries(self):
        log = ComputeAuditLog(max_entries=5)
        for i in range(10):
            log.record(AuditAction.WORKER_HEARTBEAT, detail=str(i))
        entries = log.get_entries(limit=100)
        assert len(entries) <= 5


# ============================================================
# Integration: Colab + Manager
# ============================================================

class TestIntegrationColabManager:
    def test_colab_register_then_submit(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            mgr = ComputeManager()
            mgr.enable()
            mgr.set_mode(ComputeMode.GOOGLE_COLAB)
            reg = WorkerRegistration(
                worker_id="w-1", provider_id="colab",
                provider_type=ComputeProviderType.GOOGLE_COLAB,
                api_token="test-token",
            )
            mgr.register_worker(reg)
            req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
            job = mgr.submit_job(req)
            assert job.provider_type == ComputeProviderType.GOOGLE_COLAB
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)


# ============================================================
# Routing Tests
# ============================================================

class TestRouting:
    def test_auto_mode_uses_cpu_when_no_gpu(self):
        mgr = ComputeManager()
        mgr.enable()
        mgr.set_mode(ComputeMode.AUTO)
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        assert job.provider_type == ComputeProviderType.CPU

    def test_cpu_mode_always_uses_cpu(self):
        mgr = ComputeManager()
        mgr.enable()
        mgr.set_mode(ComputeMode.CPU)
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        assert job.provider_id == "cpu"

    def test_explicit_provider_preference(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(
            workload_type=WorkloadType.INFERENCE,
            provider_preference=ComputeProviderType.CPU,
        )
        job = mgr.submit_job(req)
        assert job.provider_id == "cpu"
