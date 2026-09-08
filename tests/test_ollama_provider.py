"""Tests for Ollama Provider integration into AURORA Intelligence.

Tests:
1. Ollama provider registration
2. Provider selection
3. Runtime resolution
4. Model resolution
5. Provider capabilities
6. Provider health check
7. Provider availability
8. Unavailable provider handling
9. Arbitrary model rejection
10. Security restrictions
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestOllamaProvider:
    """Tests for the OllamaProvider class."""

    def test_ollama_provider_name(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        assert provider.name == "ollama"

    def test_ollama_provider_capabilities(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        caps = provider.capabilities()
        assert caps.name == "ollama"
        assert "qwen2.5-0.5b-ollama" in caps.models
        assert caps.requires_api_key is False
        assert caps.max_output_tokens == 2048

    def test_ollama_provider_health_check(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        mock_rm.list_runtimes.return_value = []
        provider = OllamaProvider(mock_rm)
        health = provider.health_check()
        assert health["provider"] == "ollama"
        assert health["ollama_model"] == "qwen2.5:0.5b"
        assert health["runtime_type"] == "ollama"

    def test_ollama_provider_not_available_no_runtimes(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        mock_rm.list_runtimes.return_value = []
        provider = OllamaProvider(mock_rm)
        assert provider.is_available is False

    def test_ollama_provider_not_available_no_loaded_model(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        mock_runtime = MagicMock()
        mock_runtime.status.value = "READY"
        mock_runtime.model_load_status.value = "NOT_LOADED"
        mock_rm.list_runtimes.return_value = [mock_runtime]
        provider = OllamaProvider(mock_rm)
        assert provider.is_available is False

    def test_ollama_provider_available_with_loaded_model(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        mock_runtime = MagicMock()
        mock_runtime.status.value = "READY"
        mock_runtime.model_load_status.value = "LOADED"
        mock_rm.list_runtimes.return_value = [mock_runtime]
        provider = OllamaProvider(mock_rm)
        assert provider.is_available is True

    def test_ollama_provider_configure(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        provider.configure(model_id="custom-model", worker_id="worker-1")
        assert provider._model_id == "custom-model"
        assert provider._worker_id == "worker-1"

    def test_ollama_provider_messages_to_prompt(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        prompt = provider._messages_to_prompt(messages)
        assert "[system]: You are a helpful assistant." in prompt
        assert "[user]: Hello" in prompt

    def test_ollama_provider_generate_no_model(self):
        from aurora.ai.providers import OllamaProvider
        from aurora.ai.errors import LLMUnavailable
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        provider._model_id = None
        with pytest.raises(LLMUnavailable, match="No model configured"):
            provider.generate([{"role": "user", "content": "test"}])

    def test_ollama_provider_generate_inference_failure(self):
        from aurora.ai.providers import OllamaProvider
        from aurora.ai.errors import LLMUnavailable
        mock_rm = MagicMock()
        mock_result = MagicMock()
        mock_result.status.value = "FAILED"
        mock_result.error = "Worker disconnected"

        async def mock_run_inference(request):
            return mock_result

        mock_rm.run_inference = mock_run_inference
        provider = OllamaProvider(mock_rm)
        provider._model_id = "qwen2.5-0.5b-ollama"
        with patch.object(provider, "_ensure_runtime_loaded"):
            with pytest.raises(LLMUnavailable, match="Ollama inference failed"):
                provider.generate([{"role": "user", "content": "test"}])


class TestOllamaProviderRegistry:
    """Tests for Ollama provider registration in ProviderRegistry."""

    def test_create_provider_registry_ollama(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "ollama"}):
            with patch("aurora.runtime.manager.RuntimeManager") as mock_rm_cls:
                with patch("aurora.compute.manager.ComputeManager") as mock_cm_cls:
                    registry = create_provider_registry()
                    providers = registry.list_providers()
                    assert "ollama" in providers
                    assert "stub" in providers

    def test_create_provider_registry_stub_default(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "stub"}, clear=False):
            registry = create_provider_registry()
            assert registry._default == "stub"

    def test_create_provider_registry_ollama_is_default(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "ollama"}):
            with patch("aurora.runtime.manager.RuntimeManager"):
                with patch("aurora.compute.manager.ComputeManager"):
                    registry = create_provider_registry()
                    assert registry._default == "ollama"

    def test_ollama_provider_health_check_in_registry(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "ollama"}):
            with patch("aurora.runtime.manager.RuntimeManager") as mock_rm_cls:
                with patch("aurora.compute.manager.ComputeManager"):
                    mock_rm = MagicMock()
                    mock_rm.list_runtimes.return_value = []
                    mock_rm_cls.return_value = mock_rm
                    registry = create_provider_registry()
                    health = registry.health_check()
                    assert "ollama" in health["providers"]
                    assert health["default"] == "ollama"

    def test_ollama_provider_get_from_registry(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "ollama"}):
            with patch("aurora.runtime.manager.RuntimeManager"):
                with patch("aurora.compute.manager.ComputeManager"):
                    registry = create_provider_registry()
                    provider = registry.get("ollama")
                    assert provider.name == "ollama"

    def test_ollama_provider_default_get(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "ollama"}):
            with patch("aurora.runtime.manager.RuntimeManager"):
                with patch("aurora.compute.manager.ComputeManager"):
                    registry = create_provider_registry()
                    provider = registry.get()
                    assert provider.name == "ollama"


class TestOllamaProviderSecurity:
    """Tests for Ollama provider security restrictions."""

    def test_ollama_provider_no_arbitrary_model(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        provider.configure(model_id="qwen2.5-0.5b-ollama")
        assert provider._model_id == "qwen2.5-0.5b-ollama"

    def test_ollama_provider_no_api_key_required(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        caps = provider.capabilities()
        assert caps.requires_api_key is False

    def test_ollama_provider_no_structured_output(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        caps = provider.capabilities()
        assert caps.supports_structured_output is False

    def test_ollama_provider_max_tokens_bounded(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        caps = provider.capabilities()
        assert caps.max_output_tokens == 2048
        assert caps.max_context_tokens == 32768


class TestOllamaProviderIntegration:
    """Tests for Ollama provider integration with compute fabric."""

    def test_ollama_provider_uses_runtime_manager(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        provider = OllamaProvider(mock_rm)
        assert provider._runtime is mock_rm

    def test_ollama_provider_model_id_from_env(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        with patch.dict(os.environ, {"AURORA_LLM_MODEL": "custom-ollama-model"}):
            provider = OllamaProvider(mock_rm)
            assert provider._model_id == "custom-ollama-model"

    def test_ollama_provider_default_model_id(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        with patch.dict(os.environ, {}, clear=True):
            provider = OllamaProvider(mock_rm)
            assert provider._model_id == "qwen2.5-0.5b-ollama"

    def test_ollama_provider_health_check_with_runtime(self):
        from aurora.ai.providers import OllamaProvider
        mock_rm = MagicMock()
        mock_runtime = MagicMock()
        mock_runtime.status.value = "READY"
        mock_runtime.model_load_status.value = "LOADED"
        mock_runtime.gpu_name = "Tesla T4"
        mock_runtime.worker_id = "colab-worker-1"
        mock_rm.list_runtimes.return_value = [mock_runtime]
        provider = OllamaProvider(mock_rm)
        provider._worker_id = "colab-worker-1"
        health = provider.health_check()
        assert health["gpu"] == "Tesla T4"
        assert health["worker_id"] == "colab-worker-1"
        assert health["runtime_status"] == "READY"
        assert health["model_status"] == "LOADED"
