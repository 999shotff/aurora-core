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
    get_source_model_id,
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
        config = ModelConfig(model_id="test", model_name="Test Model",
                             source_model_id="org/test-model")
        assert config.model_id == "test"
        assert config.source_model_id == "org/test-model"
        assert config.framework == "transformers"
        assert config.dtype == "float16"
        assert config.device == "cuda"

    def test_create_full(self):
        config = ModelConfig(
            model_id="llama-3.1-8b",
            model_name="Llama 3.1 8B",
            source_model_id="meta-llama/Llama-3.1-8B-Instruct",
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
            requires_auth=True,
        )
        assert config.model_id == "llama-3.1-8b"
        assert config.source_model_id == "meta-llama/Llama-3.1-8B-Instruct"
        assert config.requires_auth is True
        assert config.max_input_tokens == 131072
        assert config.required_vram_gb == 8.0
        assert len(config.capabilities) == 2

    def test_empty_model_id_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="", model_name="Test", source_model_id="org/test")

    def test_empty_source_model_id_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="test", model_name="Test", source_model_id="")

    def test_long_model_id_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="x" * 200, model_name="Test", source_model_id="org/test")

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            ModelConfig(model_id="test", model_name="Test", source_model_id="org/test",
                        extra_field="bad")

    def test_requires_auth_default_false(self):
        config = ModelConfig(model_id="test", model_name="Test",
                             source_model_id="org/test")
        assert config.requires_auth is False

    def test_vram_bounds(self):
        config = ModelConfig(model_id="test", model_name="Test",
                             source_model_id="org/test", required_vram_gb=0.1)
        assert config.required_vram_gb == 0.1
        config2 = ModelConfig(model_id="test2", model_name="Test2",
                              source_model_id="org/test2", required_vram_gb=80.0)
        assert config2.required_vram_gb == 80.0
        with pytest.raises(Exception):
            ModelConfig(model_id="test3", model_name="Test3",
                        source_model_id="org/test3", required_vram_gb=0.0)
        with pytest.raises(Exception):
            ModelConfig(model_id="test4", model_name="Test4",
                        source_model_id="org/test4", required_vram_gb=100.0)


class TestModelRegistry:
    def test_create_empty(self):
        reg = ModelRegistry()
        assert len(reg.models) == 0
        assert reg.default_model_id is None

    def test_create_with_models(self):
        reg = ModelRegistry(
            models=[
                ModelConfig(model_id="m1", model_name="Model 1",
                            source_model_id="org/m1"),
                ModelConfig(model_id="m2", model_name="Model 2",
                            source_model_id="org/m2"),
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
            model=ModelConfig(model_id="test", model_name="Test",
                              source_model_id="org/test"),
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

    def test_source_model_id_resolution(self):
        assert get_source_model_id("smollm2-1.7b") == "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        assert get_source_model_id("phi-3.5-mini") == "microsoft/Phi-3.5-mini-instruct"
        assert get_source_model_id("mistral-7b") == "mistralai/Mistral-7B-Instruct-v0.3"
        assert get_source_model_id("qwen2.5-7b") == "Qwen/Qwen2.5-7B-Instruct"
        assert get_source_model_id("llama-3.1-8b") == "meta-llama/Llama-3.1-8B-Instruct"

    def test_source_model_id_not_found(self):
        assert get_source_model_id("nonexistent") is None

    def test_all_models_have_source_model_id(self):
        reg = get_default_registry()
        for model in reg.models:
            assert model.source_model_id, f"{model.model_id} missing source_model_id"

    def test_all_models_have_distinct_ids(self):
        reg = get_default_registry()
        internal_ids = [m.model_id for m in reg.models]
        source_ids = [m.source_model_id for m in reg.models]
        assert len(set(internal_ids)) == len(internal_ids)
        assert len(set(source_ids)) == len(source_ids)
        for iid, sid in zip(internal_ids, source_ids):
            assert iid != sid, f"{iid} == {sid} — internal and source IDs must differ"

    def test_llama_requires_auth(self):
        model = get_model_by_id("llama-3.1-8b")
        assert model is not None
        assert model.requires_auth is True

    def test_other_models_do_not_require_auth(self):
        for mid in ["smollm2-1.7b", "phi-3.5-mini", "mistral-7b", "qwen2.5-7b"]:
            model = get_model_by_id(mid)
            assert model is not None
            assert model.requires_auth is False, f"{mid} should not require auth"


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

    def test_load_rejects_unregistered_model_id(self):
        handler = self._make_handler()
        result = handler.load_model("totally-fake-model")
        assert result["status"] == "ERROR"
        assert "not in approved registry" in result["error"]

    def test_load_rejects_arbitrary_source_model_id(self):
        handler = self._make_handler()
        result = handler.load_model(
            "smollm2-1.7b",
            source_model_id="evil-user/malicious-repo",
        )
        assert result["status"] == "ERROR"
        assert "not in approved whitelist" in result["error"]

    def test_load_rejects_internal_id_as_source(self):
        handler = self._make_handler()
        result = handler.load_model(
            "smollm2-1.7b",
            source_model_id="smollm2-1.7b",
        )
        assert result["status"] == "ERROR"
        assert "not in approved whitelist" in result["error"]

    def test_load_rejects_empty_source_model_id(self):
        handler = self._make_handler()
        result = handler.load_model(
            "nonexistent-model",
            source_model_id="",
        )
        assert result["status"] == "ERROR"

    def test_load_rejects_hf_url_as_source(self):
        handler = self._make_handler()
        result = handler.load_model(
            "smollm2-1.7b",
            source_model_id="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct",
        )
        assert result["status"] == "ERROR"
        assert "not in approved whitelist" in result["error"]

    def test_approved_models_whitelist_complete(self):
        from workers.google_colab.worker import APPROVED_SOURCE_MODELS, APPROVED_SOURCE_IDS
        assert len(APPROVED_SOURCE_MODELS) == 5
        assert "HuggingFaceTB/SmolLM2-1.7B-Instruct" in APPROVED_SOURCE_IDS
        assert "microsoft/Phi-3.5-mini-instruct" in APPROVED_SOURCE_IDS
        assert "mistralai/Mistral-7B-Instruct-v0.3" in APPROVED_SOURCE_IDS
        assert "Qwen/Qwen2.5-7B-Instruct" in APPROVED_SOURCE_IDS
        assert "meta-llama/Llama-3.1-8B-Instruct" in APPROVED_SOURCE_IDS

    def test_internal_ids_never_match_source_ids(self):
        from workers.google_colab.worker import APPROVED_SOURCE_MODELS
        for internal, source in APPROVED_SOURCE_MODELS.items():
            assert internal != source, f"{internal} == {source}"


# ============================================================
# Source Model ID Provenance Tests
# ============================================================


class TestSourceModelProvenance:
    def test_provenance_contains_source_model_id(self):
        model = get_model_by_id("smollm2-1.7b")
        assert model is not None
        assert model.source_model_id == "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        assert model.model_id == "smollm2-1.7b"
        assert model.model_id != model.source_model_id

    def test_provenance_contains_both_ids_for_all_models(self):
        reg = get_default_registry()
        for model in reg.models:
            assert model.model_id, f"{model.model_name} missing model_id"
            assert model.source_model_id, f"{model.model_name} missing source_model_id"
            assert model.model_id != model.source_model_id, \
                f"{model.model_name}: model_id == source_model_id"

    def test_manager_load_includes_source_model_id(self):
        from aurora.runtime.manager import RuntimeManager
        from aurora.compute.manager import ComputeManager
        cm = ComputeManager()
        mgr = RuntimeManager(cm)
        model = mgr.registry.models[0]
        assert hasattr(model, "source_model_id")
        assert model.source_model_id.startswith("HuggingFaceTB/") or \
               model.source_model_id.startswith("microsoft/") or \
               model.source_model_id.startswith("mistralai/") or \
               model.source_model_id.startswith("Qwen/") or \
               model.source_model_id.startswith("meta-llama/")

    def test_registry_models_endpoint_includes_source_model_id(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from aurora.runtime.api import router, set_runtime_manager
        from aurora.runtime.manager import RuntimeManager
        from aurora.compute.manager import ComputeManager

        app = FastAPI()
        app.include_router(router)
        cm = ComputeManager()
        mgr = RuntimeManager(cm)
        set_runtime_manager(mgr)

        client = TestClient(app)
        resp = client.get("/api/v1/runtime/registry/models")
        assert resp.status_code == 200
        data = resp.json()
        for entry in data:
            assert "source_model_id" in entry, f"{entry.get('model_id')} missing source_model_id"
            assert "model_id" in entry


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
        config = ModelConfig(model_id="test", model_name="Test",
                             source_model_id="org/test")
        assert config.model_revision is None
        assert config.source_url is None
        assert config.description == ""
        assert config.requires_auth is False
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
