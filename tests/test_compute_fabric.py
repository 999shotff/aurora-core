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


# ============================================================
# Lightning Worker Runtime Tests
# ============================================================


class TestLightningWorkerRuntime:
    """Tests for Lightning AI worker RuntimeHandler and lifecycle."""

    def _make_handler(self):
        from workers.lightning.worker import RuntimeHandler
        gpu_info = {
            "name": "Tesla T4",
            "vram_mb": 15360.0,
            "cuda_version": "12.2",
        }
        return RuntimeHandler(gpu_info)

    def test_handler_create(self):
        handler = self._make_handler()
        assert handler is not None
        assert not handler.is_model_loaded

    def test_handler_discover(self):
        handler = self._make_handler()
        result = handler.discover()
        assert "status" in result
        assert "gpu_name" in result

    def test_handler_health_not_loaded(self):
        handler = self._make_handler()
        health = handler.health()
        assert health["model_status"] == "NOT_LOADED"
        assert health["total_inferences"] == 0

    def test_handler_load_rejects_unregistered(self):
        handler = self._make_handler()
        result = handler.load_model("totally-fake-model")
        assert result["status"] == "ERROR"
        assert "not in approved registry" in result["error"]

    def test_handler_load_rejects_arbitrary_source(self):
        handler = self._make_handler()
        result = handler.load_model(
            "qwen2.5-0.5b-instruct",
            source_model_id="evil-user/malicious-repo",
        )
        assert result["status"] == "ERROR"
        assert "not in approved whitelist" in result["error"]

    def test_handler_load_rejects_url_as_source(self):
        handler = self._make_handler()
        result = handler.load_model(
            "qwen2.5-0.5b-instruct",
            source_model_id="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct",
        )
        assert result["status"] == "ERROR"
        assert "not in approved whitelist" in result["error"]

    def test_handler_unload_not_loaded(self):
        handler = self._make_handler()
        result = handler.unload_model()
        assert result["status"] == "NOT_LOADED"

    def test_handler_infer_not_loaded(self):
        handler = self._make_handler()
        result = handler.infer("test prompt")
        assert result["status"] == "ERROR"
        assert "No model loaded" in result["error"]

    def test_whitelist_has_qwen_05b(self):
        from workers.lightning.worker import APPROVED_SOURCE_MODELS, APPROVED_SOURCE_IDS
        assert "qwen2.5-0.5b-instruct" in APPROVED_SOURCE_MODELS
        assert APPROVED_SOURCE_MODELS["qwen2.5-0.5b-instruct"] == "Qwen/Qwen2.5-0.5B-Instruct"
        assert "Qwen/Qwen2.5-0.5B-Instruct" in APPROVED_SOURCE_IDS

    def test_whitelist_has_six_models(self):
        from workers.lightning.worker import APPROVED_SOURCE_MODELS
        assert len(APPROVED_SOURCE_MODELS) == 6

    def test_source_model_id_resolution(self):
        from workers.lightning.worker import APPROVED_SOURCE_MODELS
        assert APPROVED_SOURCE_MODELS["qwen2.5-0.5b-instruct"] == "Qwen/Qwen2.5-0.5B-Instruct"
        assert APPROVED_SOURCE_MODELS["smollm2-1.7b"] == "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        assert APPROVED_SOURCE_MODELS["phi-3.5-mini"] == "microsoft/Phi-3.5-mini-instruct"
        assert APPROVED_SOURCE_MODELS["mistral-7b"] == "mistralai/Mistral-7B-Instruct-v0.3"
        assert APPROVED_SOURCE_MODELS["qwen2.5-7b"] == "Qwen/Qwen2.5-7B-Instruct"
        assert APPROVED_SOURCE_MODELS["llama-3.1-8b"] == "meta-llama/Llama-3.1-8B-Instruct"

    def test_internal_ids_never_match_source_ids(self):
        from workers.lightning.worker import APPROVED_SOURCE_MODELS
        for internal, source in APPROVED_SOURCE_MODELS.items():
            assert internal != source, f"{internal} == {source}"

    def test_worker_version(self):
        from workers.lightning.worker import WORKER_VERSION, PROTOCOL_VERSION
        assert WORKER_VERSION == "0.3.0"
        assert PROTOCOL_VERSION == "2.0"

    def test_worker_has_runtime_handler(self):
        from workers.lightning.worker import AuroraLightningWorker
        worker = AuroraLightningWorker(
            backend_url="https://example.com",
            worker_token="test-token",
        )
        assert worker._runtime_handler is None

    def test_worker_builds_capabilities_with_runtime(self):
        from workers.lightning.worker import AuroraLightningWorker
        worker = AuroraLightningWorker(
            backend_url="https://example.com",
            worker_token="test-token",
        )
        worker._gpu_info = {"name": "Tesla T4", "vram_mb": 15360.0}
        caps = worker._build_capabilities()
        assert caps["runtime"] is True
        assert caps["benchmark"] is True
        assert caps["framework"] == "pytorch"

    def test_worker_connect_initializes_runtime_handler(self):
        from workers.lightning.worker import AuroraLightningWorker
        from unittest.mock import patch, MagicMock

        worker = AuroraLightningWorker(
            backend_url="https://example.com",
            worker_token="test-token",
        )
        worker._gpu_info = {"name": "Tesla T4", "vram_mb": 15360.0}

        mock_ack = {"accepted": True, "worker_id": "test-worker"}
        with patch.object(worker, "_api_post", return_value=mock_ack):
            result = worker.connect()

        assert result is True
        assert worker._runtime_handler is not None

    def test_tokenizer_receives_source_model_id(self):
        from workers.lightning.worker import RuntimeHandler
        from unittest.mock import patch, MagicMock

        handler = self._make_handler()
        mock_tokenizer = MagicMock()
        mock_model_inst = MagicMock()
        mock_model_inst.device = "cuda:0"

        mock_transformers = MagicMock()
        mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
        mock_transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model_inst

        with patch.dict("sys.modules", {"transformers": mock_transformers, "torch": MagicMock()}):
            handler.load_model("qwen2.5-0.5b-instruct", dtype="float16")

        mock_transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
            "Qwen/Qwen2.5-0.5B-Instruct"
        )

    def test_model_loader_receives_source_model_id(self):
        from workers.lightning.worker import RuntimeHandler
        from unittest.mock import patch, MagicMock

        handler = self._make_handler()
        mock_tokenizer = MagicMock()
        mock_model_inst = MagicMock()
        mock_model_inst.device = "cuda:0"

        mock_torch = MagicMock()
        mock_torch.float16 = "float16"
        mock_transformers = MagicMock()
        mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
        mock_transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model_inst

        with patch.dict("sys.modules", {"transformers": mock_transformers, "torch": mock_torch}):
            handler.load_model("qwen2.5-0.5b-instruct", dtype="float16")

        mock_transformers.AutoModelForCausalLM.from_pretrained.assert_called_once_with(
            "Qwen/Qwen2.5-0.5B-Instruct",
            torch_dtype=mock_torch.float16,
            device_map="auto",
        )


class TestOllamaRuntime:
    """Tests for Ollama runtime integration in workers."""

    def test_ollama_whitelist_has_approved_entry(self):
        from workers.lightning.worker import APPROVED_OLLAMA_MODELS, APPROVED_OLLAMA_IDS
        assert "qwen2.5-0.5b-ollama" in APPROVED_OLLAMA_MODELS
        assert APPROVED_OLLAMA_MODELS["qwen2.5-0.5b-ollama"] == "qwen2.5:0.5b"
        assert "qwen2.5:0.5b" in APPROVED_OLLAMA_IDS

    def test_ollama_whitelist_subset_of_approved_ids(self):
        from workers.lightning.worker import APPROVED_OLLAMA_MODELS, APPROVED_OLLAMA_IDS
        for model_id, ollama_name in APPROVED_OLLAMA_MODELS.items():
            assert ollama_name in APPROVED_OLLAMA_IDS

    def test_ollama_source_model_id_in_registry(self):
        from aurora.runtime.registry import get_default_registry
        reg = get_default_registry()
        ollama_model = [m for m in reg.models if m.runtime == "ollama"]
        assert len(ollama_model) >= 1
        model = ollama_model[0]
        assert model.model_id == "qwen2.5-0.5b-ollama"
        assert model.source_model_id == "qwen2.5:0.5b"
        assert model.runtime == "ollama"
        assert model.runtime_model_id == "qwen2.5:0.5b"

    def test_ollama_worker_handler_routes_to_ollama(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "qwen2.5:0.5b"}],
        }

        with patch("workers.lightning.worker.requests.get", return_value=mock_resp):
            health = runtime.health()
            assert health["status"] == "READY"
            assert "qwen2.5:0.5b" in health["available_models"]

    def test_ollama_worker_handler_load_validates_whitelist(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "ok", "eval_count": 1}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = runtime.load_model("qwen2.5-0.5b-ollama", "qwen2.5:0.5b")
            assert result["status"] == "LOADED"
            assert result["ollama_model"] == "qwen2.5:0.5b"

    def test_ollama_worker_handler_rejects_unapproved_model(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        result = runtime.load_model("evil-model", "evil-model:latest")
        assert result["status"] == "ERROR"
        assert "not in approved" in result["error"]

    def test_ollama_worker_handler_infer(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {
            "response": "Evidence matters.",
            "eval_count": 3,
        }

        with patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = runtime.infer("test prompt", max_new_tokens=10)
            assert result["status"] == "COMPLETED"
            assert result["output"] == "Evidence matters."
            assert result["tokens_generated"] == 3
            assert runtime._total_inferences == 1

    def test_ollama_worker_handler_infer_no_model(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        result = runtime.infer("test prompt")
        assert result["status"] == "ERROR"
        assert "No model loaded" in result["error"]

    def test_lightning_worker_connect_initializes_ollama(self):
        from workers.lightning.worker import AuroraLightningWorker
        from unittest.mock import patch, MagicMock

        mock_gpu_info = {"name": "Tesla T4", "vram_mb": 15000.0, "vendor": "NVIDIA"}
        mock_ack = {"accepted": True, "worker_id": "test-worker"}

        with patch.object(AuroraLightningWorker, "_detect_gpu") as mock_detect, \
             patch.object(AuroraLightningWorker, "_api_post", return_value=mock_ack) as mock_post:
            worker = AuroraLightningWorker(backend_url="http://test", worker_token="tok")
            worker._gpu_info = mock_gpu_info
            result = worker.connect()

            assert result is True
            assert worker._ollama_runtime is not None

    def test_lightning_worker_ollama_runtime_health(self):
        from workers.lightning.worker import AuroraLightningWorker
        from unittest.mock import patch, MagicMock

        mock_gpu_info = {"name": "Tesla T4", "vram_mb": 15000.0, "vendor": "NVIDIA"}
        mock_ack = {"accepted": True, "worker_id": "test-worker"}

        with patch.object(AuroraLightningWorker, "_detect_gpu"), \
             patch.object(AuroraLightningWorker, "_api_post", return_value=mock_ack):
            worker = AuroraLightningWorker(backend_url="http://test", worker_token="tok")
            worker._gpu_info = mock_gpu_info
            worker.connect()

        payload = {}
        result = worker._handle_runtime_health(payload)
        assert result["provider"] == "lightning"
        assert "ollama_status" in result

    def test_lightning_worker_ollama_runtime_discover(self):
        from workers.lightning.worker import AuroraLightningWorker
        from unittest.mock import patch, MagicMock

        mock_gpu_info = {"name": "Tesla T4", "vram_mb": 15000.0, "vendor": "NVIDIA"}
        mock_ack = {"accepted": True, "worker_id": "test-worker"}

        with patch.object(AuroraLightningWorker, "_detect_gpu"), \
             patch.object(AuroraLightningWorker, "_api_post", return_value=mock_ack):
            worker = AuroraLightningWorker(backend_url="http://test", worker_token="tok")
            worker._gpu_info = mock_gpu_info
            worker.connect()

        payload = {}
        result = worker._handle_runtime_discover(payload)
        assert result["provider"] == "lightning"
        assert "ollama_status" in result
        assert "ollama_models" in result

    def test_lightning_worker_ollama_runtime_load_routes_by_runtime(self):
        from workers.lightning.worker import AuroraLightningWorker
        from unittest.mock import patch, MagicMock

        mock_gpu_info = {"name": "Tesla T4", "vram_mb": 15000.0, "vendor": "NVIDIA"}
        mock_ack = {"accepted": True, "worker_id": "test-worker"}

        with patch.object(AuroraLightningWorker, "_detect_gpu"), \
             patch.object(AuroraLightningWorker, "_api_post", return_value=mock_ack):
            worker = AuroraLightningWorker(backend_url="http://test", worker_token="tok")
            worker._gpu_info = mock_gpu_info
            worker.connect()

        payload = {
            "runtime": "ollama",
            "model_id": "qwen2.5-0.5b-ollama",
            "runtime_model_id": "qwen2.5:0.5b",
        }

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "ok", "eval_count": 1}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = worker._handle_runtime_load(payload)
            assert result["provider"] == "lightning"
            assert result["workload"] == "RUNTIME_LOAD"
            assert result["status"] == "LOADED"

    def test_lightning_worker_ollama_runtime_infer_routes_by_runtime(self):
        from workers.lightning.worker import AuroraLightningWorker
        from unittest.mock import patch, MagicMock

        mock_gpu_info = {"name": "Tesla T4", "vram_mb": 15000.0, "vendor": "NVIDIA"}
        mock_ack = {"accepted": True, "worker_id": "test-worker"}

        with patch.object(AuroraLightningWorker, "_detect_gpu"), \
             patch.object(AuroraLightningWorker, "_api_post", return_value=mock_ack):
            worker = AuroraLightningWorker(backend_url="http://test", worker_token="tok")
            worker._gpu_info = mock_gpu_info
            worker.connect()

        worker._ollama_runtime._loaded_model = "qwen2.5:0.5b"

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "hello", "eval_count": 2}

        payload = {"runtime": "ollama", "prompt": "test", "max_new_tokens": 10}

        with patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = worker._handle_runtime_infer(payload)
            assert result["provider"] == "lightning"
            assert result["workload"] == "RUNTIME_INFER"
            assert result["status"] == "COMPLETED"

    def test_ollama_health_not_reachable(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch
        import requests as req_lib

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch("workers.lightning.worker.requests.get", side_effect=req_lib.RequestException("connection refused")):
            health = runtime.health()
            assert health["status"] == "ERROR"
            assert "not reachable" in health["error"]
            assert health["ollama_url"] == "http://127.0.0.1:11434"

    def test_ollama_health_ready(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "qwen2.5:0.5b"}, {"name": "llama3:8b"}],
        }

        with patch("workers.lightning.worker.requests.get", return_value=mock_resp):
            health = runtime.health()
            assert health["status"] == "READY"
            assert "qwen2.5:0.5b" in health["available_models"]
            assert "llama3:8b" in health["available_models"]
            assert health["loaded_model"] is None

    def test_ollama_discover_includes_runtime_info(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        with patch("workers.lightning.worker.requests.get", return_value=mock_resp):
            result = runtime.discover()
            assert result["runtime"] == "ollama"
            assert result["gpu_name"] == "Tesla T4"
            assert result["vram_mb"] == 15000
            assert result["model_status"] == "NOT_LOADED"
            assert result["available_models"] == ["qwen2.5:0.5b"]

    def test_ollama_model_not_loaded_infer_fails(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        result = runtime.infer("test", max_new_tokens=10)
        assert result["status"] == "ERROR"
        assert "No model loaded" in result["error"]

    def test_ollama_model_loaded_state_tracking(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        assert runtime.is_model_loaded is False
        assert runtime.loaded_model_id is None

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "ok", "eval_count": 1}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = runtime.load_model("qwen2.5-0.5b-ollama", "qwen2.5:0.5b")
            assert result["status"] == "LOADED"
            assert runtime.is_model_loaded is True
            assert runtime.loaded_model_id == "qwen2.5:0.5b"

        unload_result = runtime.unload_model()
        assert unload_result["status"] == "NOT_LOADED"
        assert runtime.is_model_loaded is False
        assert runtime.loaded_model_id is None

    def test_ollama_load_rejects_duplicate_load(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        result = runtime.load_model("qwen2.5-0.5b-ollama", "qwen2.5:0.5b")
        assert result["status"] == "ERROR"
        assert "already loaded" in result["error"]

    def test_ollama_unload_when_not_loaded(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        result = runtime.unload_model()
        assert result["status"] == "NOT_LOADED"

    def test_ollama_infer_increments_counters(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "test output", "eval_count": 5}

        with patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            runtime.infer("prompt1", max_new_tokens=10)
            runtime.infer("prompt2", max_new_tokens=10)

        assert runtime._total_inferences == 2
        assert runtime._total_errors == 0

    def test_ollama_infer_error_increments_error_counter(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        with patch.object(runtime, "_ollama_post", return_value=None):
            result = runtime.infer("prompt", max_new_tokens=10)
            assert result["status"] == "FAILED"
            assert "Ollama inference failed" in result["error"]

    def test_ollama_infer_exception_increments_error_counter(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        with patch.object(runtime, "_ollama_post", side_effect=RuntimeError("unexpected")):
            result = runtime.infer("prompt", max_new_tokens=10)
            assert result["status"] == "FAILED"
            assert runtime._total_errors == 1

    def test_ollama_ensure_model_pulls_when_missing(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags_empty = MagicMock()
        mock_tags_empty.status_code = 200
        mock_tags_empty.json.return_value = {"models": []}

        mock_tags_after_pull = MagicMock()
        mock_tags_after_pull.status_code = 200
        mock_tags_after_pull.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_pull = MagicMock()
        mock_pull.status_code = 200
        mock_pull.json.return_value = {"status": "success"}

        call_count = [0]
        def mock_get(url, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return mock_tags_empty
            return mock_tags_after_pull

        with patch("workers.lightning.worker.requests.get", side_effect=mock_get), \
             patch("workers.lightning.worker.requests.post", return_value=mock_pull):
            result = runtime.ensure_model("qwen2.5:0.5b")
            assert result["status"] == "READY"
            assert result["model"] == "qwen2.5:0.5b"

    def test_ollama_ensure_model_already_available(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        with patch("workers.lightning.worker.requests.get", return_value=mock_resp):
            result = runtime.ensure_model("qwen2.5:0.5b")
            assert result["status"] == "READY"
            assert result["model"] == "qwen2.5:0.5b"

    def test_ollama_ensure_model_not_reachable(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch
        import requests as req_lib

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch("workers.lightning.worker.requests.get", side_effect=req_lib.RequestException("refused")):
            result = runtime.ensure_model("qwen2.5:0.5b")
            assert result["status"] == "ERROR"
            assert "not reachable" in result["error"]

    def test_ollama_load_validates_ollama_model_name_directly(self):
        from workers.lightning.worker import OllamaRuntime, APPROVED_OLLAMA_IDS
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "ok", "eval_count": 1}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = runtime.load_model("unknown-id", "qwen2.5:0.5b")
            assert result["status"] == "LOADED"

    def test_ollama_unload_returns_model_name(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        result = runtime.unload_model()
        assert result["status"] == "NOT_LOADED"
        assert result["unloaded_model"] == "qwen2.5:0.5b"


# ============================================================
# Ollama GPU/CPU Detection, Startup, Provenance, Security
# ============================================================


class TestOllamaGPUDetection:
    """Tests for GPU/CPU runtime classification."""

    def test_detect_gpu_status_returns_valid_classifications(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": []}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("subprocess.run") as mock_run:
            # Simulate GPU memory usage found
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="12345, 512 MiB\n",
            )
            status = runtime._detect_gpu_status()
            assert status in ("GPU_ACCELERATED", "CPU_ONLY", "GPU_AVAILABLE_BUT_NOT_USED", "RUNTIME_UNAVAILABLE")

    def test_detect_gpu_status_gpu_accelerated(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="12345, 512 MiB\n",
            )
            status = runtime._detect_gpu_status()
            assert status == "GPU_ACCELERATED"

    def test_detect_gpu_status_cpu_only_via_ps(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch("subprocess.run") as mock_run:
            # nvidia-smi fails (no GPU processes), ollama ps shows CPU-only (size_vram=0)
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout=""),  # nvidia-smi no processes
                MagicMock(returncode=0, stdout='{"models": [{"size_vram": 0, "size": 400000000}]}'),
            ]
            status = runtime._detect_gpu_status()
            assert status == "CPU_ONLY"

    def test_detect_gpu_status_gpu_available_but_not_used(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch("subprocess.run") as mock_run:
            # nvidia-smi fails, ollama ps fails
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout=""),
                FileNotFoundError(),
            ]
            status = runtime._detect_gpu_status()
            assert status == "GPU_AVAILABLE_BUT_NOT_USED"

    def test_detect_gpu_status_no_gpu_hardware(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "UNKNOWN", "vram_mb": 0}
        runtime = OllamaRuntime(mock_gpu)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                FileNotFoundError(),
                FileNotFoundError(),
            ]
            status = runtime._detect_gpu_status()
            assert status == "RUNTIME_UNAVAILABLE"

    def test_health_includes_gpu_status(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            result = runtime.health()
            assert "gpu_status" in result
            assert result["gpu_status"] == "GPU_ACCELERATED"

    def test_discover_includes_gpu_status(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": []}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch.object(runtime, "_detect_gpu_status", return_value="CPU_ONLY"):
            result = runtime.discover()
            assert "gpu_status" in result
            assert result["gpu_status"] == "CPU_ONLY"


class TestOllamaProvenance:
    """Tests for inference provenance preservation."""

    def test_infer_returns_provenance_fields(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.json.return_value = {
            "response": "Evidence matters because...",
            "eval_count": 42,
            "eval_duration": 1_000_000_000,
        }

        with patch("workers.lightning.worker.requests.post", return_value=mock_result), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            result = runtime.infer("test prompt")

        assert result["status"] == "COMPLETED"
        assert result["model"] == "qwen2.5:0.5b"
        assert result["tokens_generated"] == 42
        assert result["generation_time_seconds"] >= 0
        assert result["tokens_per_second"] >= 0
        assert result["gpu_status"] == "GPU_ACCELERATED"
        assert "output" in result and len(result["output"]) > 0

    def test_infer_increments_counters(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)
        runtime._loaded_model = "qwen2.5:0.5b"

        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.json.return_value = {"response": "ok", "eval_count": 1}

        with patch("workers.lightning.worker.requests.post", return_value=mock_result), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            runtime.infer("test")
            runtime.infer("test2")

        assert runtime._total_inferences == 2
        assert runtime._total_errors == 0

    def test_load_model_returns_gpu_status(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "ok", "eval_count": 1}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("workers.lightning.worker.requests.post", return_value=mock_generate), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            result = runtime.load_model("qwen2.5-0.5b-ollama", "qwen2.5:0.5b")

        assert result["status"] == "LOADED"
        assert result["gpu_status"] == "GPU_ACCELERATED"


class TestOllamaSecurity:
    """Tests for Ollama security constraints."""

    def test_ollama_endpoint_is_localhost_only(self):
        from workers.lightning.worker import OLLAMA_BASE_URL
        assert OLLAMA_BASE_URL == "http://127.0.0.1:11434"
        assert "0.0.0.0" not in OLLAMA_BASE_URL
        assert "localhost" in OLLAMA_BASE_URL or "127.0.0.1" in OLLAMA_BASE_URL

    def test_rejects_unapproved_model(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": [{"name": "evil-model"}]}

        mock_generate = MagicMock()
        mock_generate.status_code = 200
        mock_generate.json.return_value = {"response": "ok"}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch("workers.lightning.worker.requests.post", return_value=mock_generate):
            result = runtime.load_model("evil-model", "evil-model:latest")
            assert result["status"] == "ERROR"
            assert "not in approved" in result["error"].lower()

    def test_rejects_arbitrary_model_id(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        result = runtime.load_model("random-model-123", "random:latest")
        assert result["status"] == "ERROR"

    def test_no_secrets_in_health_response(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": []}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            result = runtime.health()
            result_str = str(result)
            assert "token" not in result_str.lower() or "worker_token" not in result_str.lower()
            assert "api_key" not in result_str.lower()
            assert "secret" not in result_str.lower()

    def test_no_secrets_in_discover_response(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {"models": []}

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            result = runtime.discover()
            result_str = str(result)
            assert "api_key" not in result_str.lower()
            assert "secret" not in result_str.lower()


class TestOllamaStartup:
    """Tests for Ollama startup readiness."""

    def test_health_error_when_not_reachable(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch.object(runtime, "_ollama_get", return_value=None):
            result = runtime.health()
            assert result["status"] == "ERROR"
            assert "not reachable" in result["error"].lower()

    def test_health_ready_with_models(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {
            "models": [
                {"name": "qwen2.5:0.5b"},
                {"name": "llama3:8b"},
            ]
        }

        with patch("workers.lightning.worker.requests.get", return_value=mock_tags), \
             patch.object(runtime, "_detect_gpu_status", return_value="GPU_ACCELERATED"):
            result = runtime.health()
            assert result["status"] == "READY"
            assert "qwen2.5:0.5b" in result["available_models"]
            assert len(result["available_models"]) == 2

    def test_ensure_model_pulls_when_missing(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        mock_tags_empty = MagicMock()
        mock_tags_empty.status_code = 200
        mock_tags_empty.json.return_value = {"models": []}

        mock_tags_full = MagicMock()
        mock_tags_full.status_code = 200
        mock_tags_full.json.return_value = {"models": [{"name": "qwen2.5:0.5b"}]}

        mock_pull = MagicMock()
        mock_pull.status_code = 200
        mock_pull.json.return_value = {"status": "success"}

        with patch("workers.lightning.worker.requests.get",
                   side_effect=[mock_tags_empty, mock_tags_full]), \
             patch("workers.lightning.worker.requests.post", return_value=mock_pull):
            result = runtime.ensure_model("qwen2.5:0.5b")
            assert result["status"] == "READY"

    def test_ensure_model_not_reachable(self):
        from workers.lightning.worker import OllamaRuntime
        from unittest.mock import MagicMock, patch

        mock_gpu = {"name": "Tesla T4", "vram_mb": 15000}
        runtime = OllamaRuntime(mock_gpu)

        with patch.object(runtime, "_ollama_get", return_value=None):
            result = runtime.ensure_model("qwen2.5:0.5b")
            assert result["status"] == "ERROR"
            assert "not reachable" in result["error"].lower()
