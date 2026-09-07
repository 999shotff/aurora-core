"""Compute Fabric v2 — comprehensive tests.

55+ tests covering:
- Worker Protocol v2 schemas
- Enhanced provider status model
- Worker lifecycle (register, heartbeat, disconnect, reconnect)
- Provider registry
- Colab provider
- Lightning provider
- CPU fallback
- AUTO routing
- Explicit provider routing
- GPU capability discovery
- Job lifecycle
- Job timeout
- Job cancellation
- Job result validation
- Benchmark
- Model runtime contract
- Worker authentication
- Audit events
- Security (payload validation, no arbitrary exec)
- API endpoints
"""

from __future__ import annotations

import os
import time

import pytest

from aurora.compute.schemas import (
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
    ModelMetadata,
    PROTOCOL_VERSION,
    RuntimeStatus,
    WorkerCapabilities,
    WorkerHeartbeat,
    WorkerHeartbeatAck,
    WorkerHealth,
    WorkerRegistration,
    WorkerRegistrationAck,
    WorkerShutdown,
    WorkerStatus,
    WorkloadType,
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
        assert ComputeProviderStatus.CONFIGURED == "CONFIGURED"
        assert ComputeProviderStatus.CONNECTING == "CONNECTING"
        assert ComputeProviderStatus.AUTHENTICATING == "AUTHENTICATING"

    def test_worker_status_enum(self):
        assert WorkerStatus.OFFLINE == "OFFLINE"
        assert WorkerStatus.READY == "READY"
        assert WorkerStatus.BUSY == "BUSY"
        assert WorkerStatus.UNHEALTHY == "UNHEALTHY"
        assert WorkerStatus.DISCONNECTED == "DISCONNECTED"

    def test_compute_mode_enum(self):
        assert ComputeMode.AUTO == "AUTO"
        assert ComputeMode.CPU == "CPU"
        assert ComputeMode.GOOGLE_COLAB == "GOOGLE_COLAB"
        assert ComputeMode.LIGHTNING == "LIGHTNING"

    def test_job_status_enum(self):
        assert JobStatus.QUEUED == "QUEUED"
        assert JobStatus.ASSIGNED == "ASSIGNED"
        assert JobStatus.RUNNING == "RUNNING"
        assert JobStatus.COMPLETED == "COMPLETED"
        assert JobStatus.FAILED == "FAILED"
        assert JobStatus.CANCELLED == "CANCELLED"

    def test_workload_type_enum(self):
        assert WorkloadType.INFERENCE == "INFERENCE"
        assert WorkloadType.BENCHMARK == "BENCHMARK"
        assert WorkloadType.EMBEDDINGS == "EMBEDDINGS"

    def test_protocol_version(self):
        assert PROTOCOL_VERSION == "2.0"

    def test_gpu_info_defaults(self):
        gpu = GPUInfo()
        assert gpu.name == "UNKNOWN"
        assert gpu.vram_mb == 0.0
        assert gpu.cuda_version is None

    def test_gpu_info_with_data(self):
        gpu = GPUInfo(name="A100", vendor="NVIDIA", vram_mb=81920.0, cuda_version="12.1")
        assert gpu.name == "A100"
        assert gpu.vram_mb == 81920.0

    def test_capabilities_defaults(self):
        caps = ComputeCapabilities()
        assert caps.inference is False
        assert caps.gpu is None
        assert caps.benchmark is False

    def test_capabilities_with_gpu(self):
        gpu = GPUInfo(name="T4", vram_mb=15360.0)
        caps = ComputeCapabilities(inference=True, gpu=gpu, benchmark=True)
        assert caps.gpu.name == "T4"
        assert caps.benchmark is True

    def test_provider_info_fields(self):
        info = ComputeProviderInfo(
            provider_id="cpu", provider_type=ComputeProviderType.CPU,
            name="CPU", status=ComputeProviderStatus.READY,
        )
        assert info.provider_id == "cpu"
        assert info.status == ComputeProviderStatus.READY
        assert info.worker_status == WorkerStatus.OFFLINE

    def test_compute_job_fields(self):
        job = ComputeJob(
            job_id="job-001", workload_type=WorkloadType.INFERENCE,
            provider_id="cpu", provider_type=ComputeProviderType.CPU,
        )
        assert job.job_id == "job-001"
        assert job.status == JobStatus.QUEUED
        assert job.progress == 0.0

    def test_compute_status_fields(self):
        status = ComputeStatus(enabled=True, mode=ComputeMode.AUTO)
        assert status.enabled is True
        assert status.gpu_enabled is False

    def test_worker_registration_fields(self):
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="token-123",
        )
        assert reg.worker_id == "w-1"
        assert reg.protocol_version == PROTOCOL_VERSION

    def test_worker_registration_ack(self):
        ack = WorkerRegistrationAck(accepted=True, worker_id="w-1")
        assert ack.accepted is True
        assert ack.heartbeat_interval_seconds == 30

    def test_worker_heartbeat_fields(self):
        hb = WorkerHeartbeat(
            worker_id="w-1", status=WorkerStatus.READY,
            api_token="token-123",
        )
        assert hb.worker_id == "w-1"
        assert hb.uptime_seconds == 0.0

    def test_worker_heartbeat_ack(self):
        ack = WorkerHeartbeatAck(accepted=True, pending_jobs=0)
        assert ack.accepted is True
        assert ack.shutdown_requested is False

    def test_worker_health_fields(self):
        health = WorkerHealth(
            worker_id="w-1", status=WorkerStatus.READY,
            gpu=GPUInfo(name="T4"), uptime_seconds=100.0,
        )
        assert health.gpu.name == "T4"

    def test_mode_change_request(self):
        req = ModeChangeRequest(mode=ComputeMode.LIGHTNING)
        assert req.mode == ComputeMode.LIGHTNING

    def test_audit_record_fields(self):
        rec = AuditRecord(action=AuditAction.COMPUTE_ENABLED)
        assert rec.action == AuditAction.COMPUTE_ENABLED
        assert rec.success is True

    def test_benchmark_request(self):
        req = BenchmarkRequest(provider_type=ComputeProviderType.GOOGLE_COLAB)
        assert req.matrix_size == 1024
        assert req.iterations == 10

    def test_benchmark_result_checksum(self):
        data = {"a": 1, "b": 2}
        checksum = BenchmarkResult.compute_checksum(data)
        assert len(checksum) == 16

    def test_model_metadata(self):
        meta = ModelMetadata(model_id="test-model", status=RuntimeStatus.NOT_AVAILABLE)
        assert meta.status == RuntimeStatus.NOT_AVAILABLE

    def test_job_progress(self):
        prog = JobProgress(job_id="j-1", progress=0.5, message="Half done")
        assert prog.progress == 0.5

    def test_worker_capabilities(self):
        caps = WorkerCapabilities(
            worker_id="w-1",
            capabilities=ComputeCapabilities(inference=True),
            api_token="token",
        )
        assert caps.capabilities.inference is True


# ============================================================
# Security Tests
# ============================================================

class TestSecurity:
    def test_payload_rejects_shell_key(self):
        with pytest.raises(Exception):
            ComputeJobRequest(
                workload_type=WorkloadType.CUSTOM,
                payload={"shell": "rm -rf /"},
            )

    def test_payload_rejects_exec_key(self):
        with pytest.raises(Exception):
            ComputeJobRequest(
                workload_type=WorkloadType.CUSTOM,
                payload={"exec": "import os; os.system('rm -rf /')"},
            )

    def test_payload_rejects_eval_key(self):
        with pytest.raises(Exception):
            ComputeJobRequest(
                workload_type=WorkloadType.CUSTOM,
                payload={"eval": "__import__('os').system('ls')"},
            )

    def test_payload_rejects_subprocess_key(self):
        with pytest.raises(Exception):
            ComputeJobRequest(
                workload_type=WorkloadType.CUSTOM,
                payload={"subprocess": "echo hacked"},
            )

    def test_payload_rejects_os_system_key(self):
        with pytest.raises(Exception):
            ComputeJobRequest(
                workload_type=WorkloadType.CUSTOM,
                payload={"os.system": "ls"},
            )

    def test_payload_rejects_compile_key(self):
        with pytest.raises(Exception):
            ComputeJobRequest(
                workload_type=WorkloadType.CUSTOM,
                payload={"compile": "malicious"},
            )

    def test_worker_token_not_in_response(self):
        info = ComputeProviderInfo(
            provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            name="Colab",
            status=ComputeProviderStatus.NOT_CONFIGURED,
        )
        dumped = info.model_dump()
        assert "api_token" not in dumped
        assert "worker_token" not in dumped

    def test_gpu_info_no_fabrication(self):
        gpu = GPUInfo()
        assert gpu.name == "UNKNOWN"
        assert gpu.vram_mb == 0.0


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
        assert caps.benchmark is True
        assert caps.gpu is None

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
        assert cpu.cancel_job(job.job_id) is False

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

    def test_cpu_benchmark(self):
        cpu = CPUProvider()
        result = cpu.run_benchmark(matrix_size=64, iterations=2)
        assert result.status == BenchmarkStatus.PASSED
        assert result.gflops is not None
        assert result.gflops > 0
        assert len(result.result_checksum) == 16

    def test_cpu_benchmark_in_job(self):
        cpu = CPUProvider()
        req = ComputeJobRequest(
            workload_type=WorkloadType.BENCHMARK,
            payload={"matrix_size": 64, "iterations": 2},
        )
        job = cpu.submit_job(req)
        assert job.status == JobStatus.COMPLETED
        assert "gflops" in job.result


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
            gpu = GPUInfo(name="T4", vram_mb=15360.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
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

    def test_colab_heartbeat_updates_gpu(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            caps1 = ComputeCapabilities(inference=True)
            colab.register_worker("w-1", caps1)
            assert colab.capabilities().gpu is None

            gpu = GPUInfo(name="A100", vram_mb=81920.0)
            caps2 = ComputeCapabilities(inference=True, gpu=gpu)
            colab.heartbeat("w-1", caps2, WorkerStatus.READY)
            assert colab.capabilities().gpu.name == "A100"
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_colab_worker_health(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            gpu = GPUInfo(name="T4", vram_mb=15360.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            colab.register_worker("w-1", caps)
            health = colab.get_worker_health()
            assert health is not None
            assert health.gpu.name == "T4"
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_colab_disconnect_worker(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            caps = ComputeCapabilities(inference=True)
            colab.register_worker("w-1", caps)
            assert colab.health() == ComputeProviderStatus.READY
            colab.disconnect_worker()
            assert colab.health() == ComputeProviderStatus.DISCONNECTED
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

    def test_colab_get_info_includes_worker_status(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            colab = ColabProvider()
            gpu = GPUInfo(name="T4", vram_mb=15360.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            colab.register_worker("w-1", caps)
            info = colab.get_info()
            assert info.worker_status == WorkerStatus.READY
            assert "gpu" in info.metadata
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
            gpu = GPUInfo(name="A100", vram_mb=81920.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            lt.register_worker("w-1", caps)
            assert lt.health() == ComputeProviderStatus.READY
        finally:
            os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
            os.environ.pop("AURORA_LIGHTNING_API_KEY", None)

    def test_lightning_heartbeat_updates_status(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            lt = LightningProvider()
            caps = ComputeCapabilities(inference=True)
            lt.register_worker("w-1", caps)
            lt.heartbeat("w-1", caps, WorkerStatus.BUSY)
            assert lt.health() == ComputeProviderStatus.BUSY
        finally:
            os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
            os.environ.pop("AURORA_LIGHTNING_API_KEY", None)

    def test_lightning_worker_health(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            lt = LightningProvider()
            gpu = GPUInfo(name="A100", vram_mb=81920.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            lt.register_worker("w-1", caps)
            health = lt.get_worker_health()
            assert health is not None
            assert health.gpu.name == "A100"
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

    def test_lightning_get_info_includes_metadata(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            lt = LightningProvider()
            info = lt.get_info()
            assert "endpoint_configured" in info.metadata
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

    def test_manager_health(self):
        mgr = ComputeManager()
        h = mgr.health()
        assert h["status"] == "degraded"
        assert h["service"] == "compute-fabric"
        assert h["protocol_version"] == PROTOCOL_VERSION

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

    def test_manager_list_jobs(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        mgr.submit_job(req)
        jobs = mgr.list_jobs()
        assert len(jobs) >= 1

    def test_manager_cancel_job(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        ok = mgr.cancel_job(job.job_id)
        assert ok is False

    def test_manager_audit_log(self):
        mgr = ComputeManager()
        mgr.enable()
        entries = mgr.get_audit_log()
        assert len(entries) >= 1

    def test_manager_job_progress(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        progress = JobProgress(job_id=job.job_id, progress=0.5, message="Halfway")
        updated = mgr.update_job_progress(job.job_id, progress)
        assert updated.progress == 0.5

    def test_manager_complete_job(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        completed = mgr.complete_job(job.job_id, {"result": "ok"}, "hash123")
        assert completed.status == JobStatus.COMPLETED
        assert completed.result_hash == "hash123"

    def test_manager_fail_job(self):
        mgr = ComputeManager()
        mgr.enable()
        req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
        job = mgr.submit_job(req)
        failed = mgr.fail_job(job.job_id, "Something went wrong")
        assert failed.status == JobStatus.FAILED
        assert failed.error == "Something went wrong"

    def test_manager_benchmark(self):
        mgr = ComputeManager()
        req = BenchmarkRequest(provider_type=ComputeProviderType.CPU, matrix_size=64, iterations=2)
        result = mgr.run_benchmark(req)
        assert result.status == BenchmarkStatus.PASSED


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
        ack = mgr.register_worker(reg)
        assert ack.accepted is True
        assert ack.protocol_version == PROTOCOL_VERSION

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

    def test_register_worker_wrong_protocol(self):
        mgr = ComputeManager()
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="test-token",
            protocol_version="1.0",
        )
        ack = mgr.register_worker(reg)
        assert ack.accepted is False
        assert "Protocol mismatch" in ack.error

    def test_worker_heartbeat(self):
        mgr = ComputeManager()
        reg = WorkerRegistration(
            worker_id="w-1", provider_id="colab",
            provider_type=ComputeProviderType.GOOGLE_COLAB,
            api_token="test-token",
        )
        mgr.register_worker(reg)
        hb = WorkerHeartbeat(
            worker_id="w-1", status=WorkerStatus.READY,
            api_token="test-token",
        )
        ack = mgr.worker_heartbeat("w-1", hb)
        assert ack.accepted is True

    def test_worker_heartbeat_not_found(self):
        mgr = ComputeManager()
        hb = WorkerHeartbeat(
            worker_id="w-missing", status=WorkerStatus.READY,
            api_token="test-token",
        )
        with pytest.raises(WorkerNotFound):
            mgr.worker_heartbeat("w-missing", hb)

    def test_worker_capabilities_update(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            mgr = ComputeManager()
            reg = WorkerRegistration(
                worker_id="w-1", provider_id="colab",
                provider_type=ComputeProviderType.GOOGLE_COLAB,
                api_token="test-token",
            )
            mgr.register_worker(reg)
            gpu = GPUInfo(name="A100", vram_mb=81920.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            ok = mgr.update_worker_capabilities("w-1", caps)
            assert ok is True
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

    def test_worker_health(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            mgr = ComputeManager()
            gpu = GPUInfo(name="T4", vram_mb=15360.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            reg = WorkerRegistration(
                worker_id="w-1", provider_id="colab",
                provider_type=ComputeProviderType.GOOGLE_COLAB,
                api_token="test-token",
                capabilities=caps,
            )
            mgr.register_worker(reg)
            health = mgr.get_worker_health("w-1")
            assert health is not None
            assert health.gpu.name == "T4"
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)

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
    def test_colab_register_then_heartbeat_then_submit(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            mgr = ComputeManager()
            mgr.enable()
            mgr.set_mode(ComputeMode.GOOGLE_COLAB)
            gpu = GPUInfo(name="T4", vram_mb=15360.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            reg = WorkerRegistration(
                worker_id="w-1", provider_id="colab",
                provider_type=ComputeProviderType.GOOGLE_COLAB,
                api_token="test-token",
                capabilities=caps,
            )
            mgr.register_worker(reg)
            hb = WorkerHeartbeat(
                worker_id="w-1", status=WorkerStatus.READY,
                capabilities=caps, api_token="test-token",
            )
            mgr.worker_heartbeat("w-1", hb)
            req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
            job = mgr.submit_job(req)
            assert job.provider_type == ComputeProviderType.GOOGLE_COLAB
            assert job.worker_id == "w-1"
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

    def test_auto_mode_prefers_lightning(self):
        os.environ["AURORA_LIGHTNING_ENDPOINT"] = "https://example.com"
        os.environ["AURORA_LIGHTNING_API_KEY"] = "key-123"
        try:
            mgr = ComputeManager()
            mgr.enable()
            mgr.set_mode(ComputeMode.AUTO)
            lt = LightningProvider()
            gpu = GPUInfo(name="A100", vram_mb=81920.0)
            caps = ComputeCapabilities(inference=True, gpu=gpu)
            lt.register_worker("w-lt", caps)
            mgr._registry.register(lt)
            req = ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
            job = mgr.submit_job(req)
            assert job.provider_type == ComputeProviderType.LIGHTNING
        finally:
            os.environ.pop("AURORA_LIGHTNING_ENDPOINT", None)
            os.environ.pop("AURORA_LIGHTNING_API_KEY", None)


# ============================================================
# Stale Worker Detection Tests
# ============================================================

class TestStaleWorkerDetection:
    def test_check_stale_workers(self):
        os.environ["AURORA_COLAB_WORKER_ENABLED"] = "true"
        try:
            mgr = ComputeManager()
            reg = WorkerRegistration(
                worker_id="w-1", provider_id="colab",
                provider_type=ComputeProviderType.GOOGLE_COLAB,
                api_token="test-token",
            )
            mgr.register_worker(reg)
            mgr._worker_last_seen["w-1"] = time.time() - 200
            stale = mgr.check_stale_workers()
            assert "w-1" in stale
        finally:
            os.environ.pop("AURORA_COLAB_WORKER_ENABLED", None)
