"""Model Runtime — comprehensive tests.

50+ tests covering schemas, registry, manager, provider, security, API.
"""

from __future__ import annotations

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aurora.runtime.schemas import (
    InferenceProvenance,
    InferenceRequest,
    InferenceResult,
    InferenceStatus,
    ModelConfig,
    ModelLoadStatus,
    ModelRegistry,
    RuntimeCapability,
    RuntimeDiscoverRequest,
    RuntimeDiscoverResult,
    RuntimeHealthRequest,
    RuntimeInfo,
    RuntimeLoadRequest,
    RuntimeLoadResult,
    RuntimeStatus,
    RuntimeUnloadRequest,
)
from aurora.runtime.registry import (
    get_default_registry,
    get_model_by_id,
    list_model_ids,
    estimate_vram_needed,
    DEFAULT_REGISTRY,
)
from aurora.runtime.security import (
    validate_inference_prompt,
    validate_model_id,
    validate_worker_id,
)


# ============================================================
# Schema Tests
# ============================================================


class TestModelConfig:
    def test_create_minimal(self):
        config = ModelConfig(model_id="test", model_name="Test Model")
        assert config.model_id == "test"
        assert config.framework == "transformers"
        assert config.dtype == "float16"
        assert config.device == "cuda"

    def test_create_full(self):
        config = ModelConfig(
            model_id="llama-3.1-8b",
            model_name="Llama 3.1 8B",
            model_revision="main",
            framework="transformers",
            dtype="bfloat16",
            device="cuda",
            max_input_tokens=131072,
            max_output_tokens=4096,
            required_vram_gb=8.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.VISION],
            description="Test model",
            source="huggingface",
            source_url="https://huggingface.co/test",
        )
        assert config.model_id == "llama-3.1-8b"
        assert config.max_input_tokens == 131072
        assert config.required_vram_gb == 8.0
        assert len(config.capabilities) == 2

    def test_empty_model_id_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="", model_name="Test")

    def test_long_model_id_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="x" * 200, model_name="Test")

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="test", model_name="Test", extra_field="bad")

    def test_vram_bounds(self):
        config = ModelConfig(model_id="test", model_name="Test", required_vram_gb=0.1)
        assert config.required_vram_gb == 0.1
        config2 = ModelConfig(model_id="test2", model_name="Test2", required_vram_gb=80.0)
        assert config2.required_vram_gb == 80.0
        with pytest.raises(Exception):
            ModelConfig(model_id="test3", model_name="Test3", required_vram_gb=0.0)
        with pytest.raises(Exception):
            ModelConfig(model_id="test4", model_name="Test4", required_vram_gb=100.0)


class TestModelRegistry:
    def test_create_empty(self):
        reg = ModelRegistry()
        assert len(reg.models) == 0
        assert reg.default_model_id is None

    def test_create_with_models(self):
        reg = ModelRegistry(
            models=[
                ModelConfig(model_id="m1", model_name="Model 1"),
                ModelConfig(model_id="m2", model_name="Model 2"),
            ],
            default_model_id="m1",
        )
        assert len(reg.models) == 2
        assert reg.default_model_id == "m1"


class TestRuntimeInfo:
    def test_create_minimal(self):
        info = RuntimeInfo(runtime_id="rt-1", status=RuntimeStatus.READY)
        assert info.runtime_id == "rt-1"
        assert info.status == RuntimeStatus.READY
        assert info.model is None
        assert info.total_inferences == 0
        assert info.total_errors == 0

    def test_create_full(self):
        info = RuntimeInfo(
            runtime_id="rt-1",
            status=RuntimeStatus.READY,
            model=ModelConfig(model_id="test", model_name="Test"),
            model_load_status=ModelLoadStatus.LOADED,
            worker_id="worker-1",
            provider_type="GOOGLE_COLAB",
            gpu_name="Tesla T4",
            vram_mb=15360.0,
            cuda_version="12.2",
            framework="pytorch",
            pytorch_version="2.1.0",
            model_memory_mb=8192.0,
            loaded_at=time.time(),
            last_inference_at=time.time(),
            total_inferences=42,
            total_errors=1,
        )
        assert info.gpu_name == "Tesla T4"
        assert info.total_inferences == 42


class TestInferenceRequest:
    def test_create(self):
        req = InferenceRequest(model_id="test", prompt="Hello")
        assert req.model_id == "test"
        assert req.prompt == "Hello"
        assert req.max_new_tokens == 256
        assert req.temperature == 0.7

    def test_empty_prompt_rejected(self):
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="")

    def test_long_prompt_rejected(self):
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="x" * 10000)

    def test_code_exec_rejected(self):
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="import os; os.system('rm -rf /')")

    def test_eval_rejected(self):
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="eval('malicious')")

    def test_shell_rejected(self):
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="subprocess.run(['ls'])")

    def test_shell_rejected(self):
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="subprocess.run(['ls'])")

    def test_bounds_checking(self):
        req = InferenceRequest(model_id="test", prompt="Hi", max_new_tokens=1)
        assert req.max_new_tokens == 1
        req2 = InferenceRequest(model_id="test", prompt="Hi", max_new_tokens=4096)
        assert req2.max_new_tokens == 4096
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="Hi", max_new_tokens=0)
        with pytest.raises(Exception):
            InferenceRequest(model_id="test", prompt="Hi", max_new_tokens=5000)


class TestInferenceResult:
    def test_create(self):
        result = InferenceResult(
            job_id="ij-1",
            inference_id="inf-1",
            model_id="test",
            worker_id="w1",
            runtime_id="rt-1",
            status=InferenceStatus.COMPLETED,
            prompt_hash="abc123",
            output="Hello world",
        )
        assert result.status == InferenceStatus.COMPLETED
        assert result.tokens_generated == 0

    def test_compute_hash(self):
        h = InferenceResult.compute_hash("test input")
        assert len(h) == 16
        assert h == InferenceResult.compute_hash("test input")
        assert h != InferenceResult.compute_hash("different input")


class TestInferenceProvenance:
    def test_create(self):
        prov = InferenceProvenance(
            job_id="ij-1",
            inference_id="inf-1",
            worker_id="w1",
            runtime_id="rt-1",
            model_id="test",
            prompt_hash="abc123",
            status=InferenceStatus.COMPLETED,
        )
        assert prov.evidence_class == "MODEL_INFERENCE"
        assert prov.status == InferenceStatus.COMPLETED


class TestRuntimeStatus:
    def test_all_values(self):
        values = [s.value for s in RuntimeStatus]
        assert "UNAVAILABLE" in values
        assert "READY" in values
        assert "BUSY" in values
        assert "ERROR" in values


class TestModelLoadStatus:
    def test_all_values(self):
        values = [s.value for s in ModelLoadStatus]
        assert "NOT_LOADED" in values
        assert "LOADED" in values
        assert "ERROR" in values


class TestInferenceStatus:
    def test_all_values(self):
        values = [s.value for s in InferenceStatus]
        assert "PENDING" in values
        assert "RUNNING" in values
        assert "COMPLETED" in values
        assert "FAILED" in values
        assert "TIMEOUT" in values
        assert "CANCELLED" in values


# ============================================================
# Registry Tests
# ============================================================


class TestRegistry:
    def test_default_registry_has_models(self):
        reg = get_default_registry()
        assert len(reg.models) >= 3

    def test_default_model_exists(self):
        reg = get_default_registry()
        assert reg.default_model_id is not None
        model = get_model_by_id(reg.default_model_id)
        assert model is not None

    def test_list_model_ids(self):
        ids = list_model_ids()
        assert len(ids) >= 3
        assert all(isinstance(mid, str) for mid in ids)

    def test_get_model_by_id_found(self):
        model = get_model_by_id("smollm2-1.7b")
        assert model is not None
        assert model.model_name == "SmolLM2 1.7B Instruct"

    def test_get_model_by_id_not_found(self):
        model = get_model_by_id("nonexistent-model")
        assert model is None

    def test_estimate_vram(self):
        vram = estimate_vram_needed("smollm2-1.7b")
        assert vram is not None
        assert vram == 2.0

    def test_estimate_vram_unknown(self):
        vram = estimate_vram_needed("nonexistent")
        assert vram is None


# ============================================================
# Security Tests
# ============================================================


class TestSecurity:
    def test_valid_prompt(self):
        result = validate_inference_prompt("What is the capital of France?")
        assert result == "What is the capital of France?"

    def test_empty_prompt_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_inference_prompt("")

    def test_whitespace_prompt_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_inference_prompt("   ")

    def test_long_prompt_rejected(self):
        with pytest.raises(ValueError, match="length"):
            validate_inference_prompt("x" * 9000)

    def test_code_exec_rejected(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_inference_prompt("import os; os.system('ls')")

    def test_eval_rejected(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_inference_prompt("eval('malicious code')")

    def test_shell_rejected(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_inference_prompt("subprocess.run(['ls'])")

    def test_exec_rejected(self):
        with pytest.raises(ValueError, match="forbidden"):
            validate_inference_prompt("exec('print(1)')")

    def test_model_id_valid(self):
        assert validate_model_id("llama-3.1-8b") == "llama-3.1-8b"
        assert validate_model_id("smollm2_1.7b") == "smollm2_1.7b"

    def test_model_id_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_model_id("")

    def test_model_id_special_chars_rejected(self):
        with pytest.raises(ValueError, match="invalid"):
            validate_model_id("model; rm -rf /")

    def test_worker_id_valid(self):
        assert validate_worker_id("worker-123") == "worker-123"

    def test_worker_id_empty_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            validate_worker_id("")


# ============================================================
# Manager Tests
# ============================================================


class TestRuntimeManager:
    def _make_manager(self):
        from aurora.runtime.manager import RuntimeManager
        from aurora.compute.manager import ComputeManager
        cm = ComputeManager()
        return RuntimeManager(cm)

    def test_create_manager(self):
        mgr = self._make_manager()
        assert mgr is not None
        assert len(mgr.list_runtimes()) == 0

    def test_list_runtimes_empty(self):
        mgr = self._make_manager()
        assert mgr.list_runtimes() == []

    def test_get_runtime_none(self):
        mgr = self._make_manager()
        assert mgr.get_runtime("nonexistent") is None

    def test_list_inference_jobs_empty(self):
        mgr = self._make_manager()
        assert mgr.list_inference_jobs() == []

    def test_get_inference_job_none(self):
        mgr = self._make_manager()
        assert mgr.get_inference_job("nonexistent") is None

    def test_build_provenance(self):
        mgr = self._make_manager()
        result = InferenceResult(
            job_id="ij-1",
            inference_id="inf-1",
            model_id="test",
            worker_id="w1",
            runtime_id="rt-1",
            status=InferenceStatus.COMPLETED,
            prompt_hash="abc",
            output="Hello",
            tokens_generated=10,
            generation_time_seconds=1.5,
            tokens_per_second=6.67,
            gpu_name="Tesla T4",
        )
        prov = mgr.build_provenance(result)
        assert prov.job_id == "ij-1"
        assert prov.evidence_class == "MODEL_INFERENCE"
        assert len(prov.limitations) == 0

    def test_build_provenance_with_errors(self):
        mgr = self._make_manager()
        result = InferenceResult(
            job_id="ij-1",
            inference_id="inf-1",
            model_id="test",
            worker_id="w1",
            runtime_id="rt-1",
            status=InferenceStatus.FAILED,
            prompt_hash="abc",
            error="Model not found",
        )
        prov = mgr.build_provenance(result)
        assert len(prov.limitations) > 0


# ============================================================
# Provider Tests
# ============================================================


class TestComputeRuntimeProvider:
    def _make_provider(self):
        from aurora.runtime.manager import RuntimeManager
        from aurora.runtime.provider import ComputeRuntimeProvider
        from aurora.compute.manager import ComputeManager
        cm = ComputeManager()
        mgr = RuntimeManager(cm)
        return ComputeRuntimeProvider(mgr)

    def test_create_provider(self):
        prov = self._make_provider()
        assert prov.name == "compute-runtime"
        assert not prov.is_available

    def test_configure(self):
        prov = self._make_provider()
        prov.configure(model_id="test-model", worker_id="w1")
        assert prov._model_id == "test-model"
        assert prov._worker_id == "w1"

    def test_capabilities(self):
        prov = self._make_provider()
        caps = prov.capabilities()
        assert caps.name == "compute-runtime"
        assert caps.requires_api_key is False

    def test_health_check(self):
        prov = self._make_provider()
        health = prov.health_check()
        assert health["provider"] == "compute-runtime"
        assert health["available"] is False


# ============================================================
# API Tests
# ============================================================


class TestRuntimeAPI:
    def _create_app(self):
        from fastapi import FastAPI
        from aurora.runtime.api import router, set_runtime_manager
        from aurora.runtime.manager import RuntimeManager
        from aurora.compute.manager import ComputeManager

        app = FastAPI()
        app.include_router(router)

        cm = ComputeManager()
        mgr = RuntimeManager(cm)
        set_runtime_manager(mgr)

        return app, mgr

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["runtimes"] == 0

    def test_list_runtimes_empty(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/runtimes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_get_runtime_not_found(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/runtimes/nonexistent")
        assert resp.status_code == 404

    def test_list_inference_jobs_empty(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/inference")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_get_inference_job_not_found(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/inference/nonexistent")
        assert resp.status_code == 404

    def test_registry_endpoint(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/registry")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["models"]) >= 3

    def test_registry_models_endpoint(self):
        from fastapi.testclient import TestClient
        app, _ = self._create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/runtime/registry/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3
        assert "model_id" in data[0]


# ============================================================
# Worker Runtime Handler Tests
# ============================================================


class TestWorkerRuntimeHandler:
    def _make_handler(self):
        from workers.google_colab.worker import RuntimeHandler
        gpu_info = {
            "name": "Tesla T4",
            "vram_mb": 15360.0,
            "cuda_version": "12.2",
        }
        return RuntimeHandler(gpu_info)

    def test_create_handler(self):
        handler = self._make_handler()
        assert handler is not None
        assert not handler.is_model_loaded

    def test_discover(self):
        handler = self._make_handler()
        result = handler.discover()
        assert "status" in result
        assert "gpu_name" in result

    def test_health_not_loaded(self):
        handler = self._make_handler()
        health = handler.health()
        assert health["model_status"] == "NOT_LOADED"
        assert health["total_inferences"] == 0

    def test_load_model_not_available(self):
        handler = self._make_handler()
        result = handler.load_model("nonexistent-model")
        assert result["status"] == "ERROR"

    def test_unload_not_loaded(self):
        handler = self._make_handler()
        result = handler.unload_model()
        assert result["status"] == "NOT_LOADED"

    def test_infer_not_loaded(self):
        handler = self._make_handler()
        result = handler.infer("test prompt")
        assert result["status"] == "ERROR"
        assert "No model loaded" in result["error"]


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    def test_runtime_info_defaults(self):
        info = RuntimeInfo(runtime_id="rt-1", status=RuntimeStatus.UNAVAILABLE)
        assert info.gpu_name is None
        assert info.vram_mb is None
        assert info.framework is None
        assert info.loaded_at is None
        assert info.uptime_seconds == 0.0
        assert info.metadata == {}

    def test_inference_result_defaults(self):
        result = InferenceResult(
            job_id="ij-1",
            inference_id="inf-1",
            model_id="test",
            worker_id="w1",
            runtime_id="rt-1",
            status=InferenceStatus.PENDING,
            prompt_hash="abc",
        )
        assert result.output is None
        assert result.tokens_generated == 0
        assert result.generation_time_seconds == 0.0
        assert result.error is None

    def test_model_config_defaults(self):
        config = ModelConfig(model_id="test", model_name="Test")
        assert config.model_revision is None
        assert config.source_url is None
        assert config.description == ""
        assert len(config.capabilities) == 1
        assert config.capabilities[0] == RuntimeCapability.INFERENCE

    def test_provenance_limitations_populated(self):
        result = InferenceResult(
            job_id="ij-1",
            inference_id="inf-1",
            model_id="test",
            worker_id="w1",
            runtime_id="rt-1",
            status=InferenceStatus.TIMEOUT,
            prompt_hash="abc",
        )
        prov = InferenceProvenance(
            job_id="ij-1",
            inference_id="inf-1",
            worker_id="w1",
            runtime_id="rt-1",
            model_id="test",
            prompt_hash="abc",
            status=InferenceStatus.TIMEOUT,
            limitations=["Inference did not complete: TIMEOUT"],
        )
        assert len(prov.limitations) == 1
        assert "TIMEOUT" in prov.limitations[0]

    def test_discover_request(self):
        req = RuntimeDiscoverRequest(worker_id="w1")
        assert req.timeout_seconds == 30

    def test_load_request(self):
        req = RuntimeLoadRequest(model_id="test", worker_id="w1")
        assert req.dtype is None
        assert req.timeout_seconds == 120

    def test_unload_request(self):
        req = RuntimeUnloadRequest(worker_id="w1", runtime_id="rt-1")
        assert req.worker_id == "w1"
