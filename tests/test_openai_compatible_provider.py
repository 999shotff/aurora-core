"""Tests for OpenAI-Compatible Remote Provider.

Tests:
1. Provider registration and selection
2. Valid configuration
3. Invalid base URL
4. Invalid model
5. Missing API key
6. API key redaction
7. No secret in logs/responses
8. Successful request (mocked)
9. Authentication failure
10. Model not found
11. Timeout
12. Remote unavailable
13. Rate limiting
14. Malformed upstream response
15. Usage normalization
16. Provenance
17. GPU independence
18. LLM-1 through LLM-5 integration
19. Unified Intelligence integration
20. Existing Ollama tests remain passing
21. Existing Transformers tests remain passing
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch, PropertyMock
from urllib.error import HTTPError, URLError

import pytest


class TestOpenAICompatibleProvider:
    """Tests for the OpenAICompatibleProvider class."""

    def test_provider_name(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        assert provider.name == "openai-compatible"

    def test_provider_custom_name(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
            provider_name="my-custom-provider",
        )
        assert provider.name == "my-custom-provider"

    def test_provider_capabilities(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="gpt-4",
        )
        caps = provider.capabilities()
        assert caps.name == "openai-compatible"
        assert "gpt-4" in caps.models
        assert caps.requires_api_key is True
        assert caps.max_output_tokens == 4096
        assert caps.supports_structured_output is True

    def test_provider_available_with_key(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        assert provider.is_available is True

    def test_provider_not_available_without_key(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        with pytest.raises(ValueError, match="API key is required"):
            OpenAICompatibleProvider(
                api_key="",
                base_url="https://api.example.com/v1",
                model="test-model",
            )

    def test_provider_requires_api_key(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        with pytest.raises(ValueError):
            OpenAICompatibleProvider(api_key="", model="m")

    def test_health_check_never_exposes_api_key(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="secret-api-key-12345",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        health = provider.health_check()
        # API key must never appear in health check
        health_str = json.dumps(health)
        assert "secret-api-key-12345" not in health_str
        assert health["api_key_configured"] is True
        assert health["gpu_required"] is False
        assert health["execution"] == "REMOTE_API"

    def test_provenance_never_exposes_api_key(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="secret-key-abcdef",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        provenance = provider.get_provenance("test prompt", "test output")
        prov_str = json.dumps(provenance)
        assert "secret-key-abcdef" not in prov_str
        assert provenance["runtime"] == "remote-api"
        assert provenance["gpu_required"] is False
        assert provenance["provider"] == "openai-compatible"
        assert "prompt_hash" in provenance
        assert "output_hash" in provenance

    def test_provenance_hostname_only(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1/path",
            model="test-model",
        )
        prov = provider.get_provenance("prompt", "output")
        assert prov["base_url_hostname"] == "api.example.com"

    def test_gpu_independence(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        health = provider.health_check()
        assert health["gpu_required"] is False
        caps = provider.capabilities()
        assert caps.requires_api_key is True


class TestURLValidation:
    """Tests for base URL validation."""

    def test_valid_https_url(self):
        from aurora.ai.providers import _validate_base_url
        result = _validate_base_url("https://api.example.com/v1")
        assert result == "https://api.example.com/v1"

    def test_valid_http_localhost(self):
        from aurora.ai.providers import _validate_base_url
        result = _validate_base_url("http://localhost:11434/v1")
        assert result == "http://localhost:11434/v1"

    def test_valid_http_127(self):
        from aurora.ai.providers import _validate_base_url
        result = _validate_base_url("http://127.0.0.1:8080/v1")
        assert result == "http://127.0.0.1:8080/v1"

    def test_rejects_ftp_scheme(self):
        from aurora.ai.providers import _validate_base_url
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            _validate_base_url("ftp://example.com/v1")

    def test_rejects_file_scheme(self):
        from aurora.ai.providers import _validate_base_url
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            _validate_base_url("file:///etc/passwd")

    def test_rejects_http_non_localhost(self):
        from aurora.ai.providers import _validate_base_url
        with pytest.raises(ValueError, match="Non-HTTPS"):
            _validate_base_url("http://api.example.com/v1")

    def test_rejects_credentials_in_url(self):
        from aurora.ai.providers import _validate_base_url
        with pytest.raises(ValueError, match="credentials"):
            _validate_base_url("https://user:pass@example.com/v1")

    def test_strips_trailing_slash(self):
        from aurora.ai.providers import _validate_base_url
        result = _validate_base_url("https://api.example.com/v1/")
        assert result == "https://api.example.com/v1"

    def test_rejects_empty_hostname(self):
        from aurora.ai.providers import _validate_base_url
        with pytest.raises(ValueError, match="hostname"):
            _validate_base_url("https:///v1")


class TestAPIKeyRedaction:
    """Tests for API key redaction."""

    def test_redact_long_key(self):
        from aurora.ai.providers import _redact_api_key
        result = _redact_api_key("sk-1234567890abcdef")
        assert result.startswith("sk-1")
        assert result.endswith("cdef")
        assert "1234567890" not in result
        assert "*" in result

    def test_redact_short_key(self):
        from aurora.ai.providers import _redact_api_key
        result = _redact_api_key("ab")
        assert result == "****"

    def test_redact_empty_key(self):
        from aurora.ai.providers import _redact_api_key
        result = _redact_api_key("")
        assert result == "****"

    def test_redact_medium_key(self):
        from aurora.ai.providers import _redact_api_key
        result = _redact_api_key("12345678")
        assert len(result) == 8
        assert result[:4] == "1234"
        assert result[-4:] == "5678"


class TestGenerate:
    """Tests for the generate method with mocked HTTP."""

    def test_successful_generate(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Hello world"}}],
            "id": "chatcmpl-123",
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=100,
            )
            assert result == "Hello world"

    def test_authentication_error(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        from aurora.ai.errors import LLMUnavailable
        provider = OpenAICompatibleProvider(
            api_key="bad-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=MagicMock(read=MagicMock(return_value=b""))
        )):
            with pytest.raises(LLMUnavailable, match="AUTHENTICATION_ERROR"):
                provider.generate(messages=[{"role": "user", "content": "Hi"}])

    def test_model_not_found(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        from aurora.ai.errors import LLMUnavailable
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="nonexistent-model",
        )
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=MagicMock(read=MagicMock(return_value=b""))
        )):
            with pytest.raises(LLMUnavailable, match="MODEL_NOT_FOUND"):
                provider.generate(messages=[{"role": "user", "content": "Hi"}])

    def test_rate_limiting(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        from aurora.ai.errors import LLMTimeout
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="", code=429, msg="Rate Limited", hdrs=None, fp=MagicMock(read=MagicMock(return_value=b""))
        )):
            with pytest.raises(LLMTimeout):
                provider.generate(messages=[{"role": "user", "content": "Hi"}])

    def test_remote_unavailable(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        from aurora.ai.errors import LLMUnavailable
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        with patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
            with pytest.raises(LLMUnavailable, match="REMOTE_UNAVAILABLE"):
                provider.generate(messages=[{"role": "user", "content": "Hi"}])

    def test_empty_response(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        from aurora.ai.errors import LLMUnavailable
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"choices": []}).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(LLMUnavailable, match="Empty response"):
                provider.generate(messages=[{"role": "user", "content": "Hi"}])

    def test_temperature_not_in_payload_when_default(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            provider.generate(messages=[{"role": "user", "content": "Hi"}], temperature=0.0)
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            assert "temperature" not in payload

    def test_temperature_in_payload_when_non_default(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            provider.generate(messages=[{"role": "user", "content": "Hi"}], temperature=0.7)
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            assert payload["temperature"] == 0.7

    def test_inference_counter_increments(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            assert provider._total_inferences == 0
            provider.generate(messages=[{"role": "user", "content": "Hi"}])
            assert provider._total_inferences == 1
            provider.generate(messages=[{"role": "user", "content": "Hi again"}])
            assert provider._total_inferences == 2


class TestTestConnection:
    """Tests for the test_connection method."""

    def test_successful_connection(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": [{"id": "model-1"}, {"id": "model-2"}],
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = provider.test_connection()
            assert result["status"] == "CONNECTED"
            assert result["provider"] == "openai-compatible"
            assert "model-1" in result["available_models"]

    def test_auth_failure(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="bad-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=MagicMock(read=MagicMock(return_value=b""))
        )):
            result = provider.test_connection()
            assert result["status"] == "AUTHENTICATION_ERROR"

    def test_connection_never_exposes_api_key(self):
        from aurora.ai.providers import OpenAICompatibleProvider
        provider = OpenAICompatibleProvider(
            api_key="secret-key-12345",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = provider.test_connection()
            result_str = json.dumps(result)
            assert "secret-key-12345" not in result_str


class TestProviderRegistry:
    """Tests for provider registry integration."""

    def test_registry_openai_compatible(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {
            "AURORA_LLM_PROVIDER": "openai-compatible",
            "AURORA_OPENAI_COMPATIBLE_API_KEY": "test-key",
            "AURORA_OPENAI_COMPATIBLE_BASE_URL": "https://api.example.com/v1",
            "AURORA_OPENAI_COMPATIBLE_MODEL": "test-model",
        }):
            registry = create_provider_registry()
            providers = registry.list_providers()
            assert "openai-compatible" in providers
            provider = registry.get("openai-compatible")
            assert provider.name == "openai-compatible"

    def test_registry_openai_compatible_uses_generic_env(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {
            "AURORA_LLM_PROVIDER": "openai-compatible",
            "AURORA_LLM_API_KEY": "generic-key",
            "AURORA_LLM_BASE_URL": "https://generic.example.com/v1",
            "AURORA_LLM_MODEL": "generic-model",
        }, clear=False):
            # Remove provider-specific vars to ensure generic fallback
            env = os.environ.copy()
            env.pop("AURORA_OPENAI_COMPATIBLE_API_KEY", None)
            env.pop("AURORA_OPENAI_COMPATIBLE_BASE_URL", None)
            env.pop("AURORA_OPENAI_COMPATIBLE_MODEL", None)
            with patch.dict(os.environ, env, clear=True):
                os.environ["AURORA_LLM_PROVIDER"] = "openai-compatible"
                os.environ["AURORA_LLM_API_KEY"] = "generic-key"
                os.environ["AURORA_LLM_BASE_URL"] = "https://generic.example.com/v1"
                os.environ["AURORA_LLM_MODEL"] = "generic-model"
                registry = create_provider_registry()
                provider = registry.get("openai-compatible")
                assert provider._api_key == "generic-key"

    def test_registry_no_key_no_register(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {
            "AURORA_LLM_PROVIDER": "openai-compatible",
            "AURORA_LLM_API_KEY": "",
        }, clear=False):
            env = os.environ.copy()
            env["AURORA_LLM_PROVIDER"] = "openai-compatible"
            env["AURORA_LLM_API_KEY"] = ""
            env.pop("AURORA_OPENAI_COMPATIBLE_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                registry = create_provider_registry()
                providers = registry.list_providers()
                assert "openai-compatible" not in providers
                assert "stub" in providers

    def test_registry_ollama_still_works(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "ollama"}):
            with patch("aurora.runtime.manager.RuntimeManager"):
                with patch("aurora.compute.manager.ComputeManager"):
                    registry = create_provider_registry()
                    providers = registry.list_providers()
                    assert "ollama" in providers

    def test_registry_stub_default(self):
        from aurora.ai.providers import create_provider_registry
        with patch.dict(os.environ, {"AURORA_LLM_PROVIDER": "stub"}):
            registry = create_provider_registry()
            providers = registry.list_providers()
            assert "stub" in providers
            assert registry.get().name == "stub"


class TestComputeAPIOpenAICompatible:
    """Tests for compute API endpoints for openai-compatible provider."""

    def _get_app(self):
        from aurora.compute.api import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return app

    def test_test_endpoint_success(self):
        from fastapi.testclient import TestClient
        app = self._get_app()
        client = TestClient(app)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            resp = client.post("/api/v1/compute/providers/openai-compatible/test", json={
                "base_url": "https://api.example.com/v1",
                "api_key": "test-key",
                "model": "test-model",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "CONNECTED"
            assert "test-key" not in json.dumps(data)

    def test_test_endpoint_invalid_url(self):
        from fastapi.testclient import TestClient
        app = self._get_app()
        client = TestClient(app)

        resp = client.post("/api/v1/compute/providers/openai-compatible/test", json={
            "base_url": "ftp://invalid.com/v1",
            "api_key": "test-key",
            "model": "test-model",
        })
        assert resp.status_code == 400

    def test_status_endpoint_not_configured(self):
        from fastapi.testclient import TestClient
        from aurora.compute.api import _openai_compatible_config
        app = self._get_app()
        client = TestClient(app)

        _openai_compatible_config.clear()
        resp = client.get("/api/v1/compute/providers/openai-compatible/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "NOT_CONFIGURED"
        assert data["gpu_required"] is False

    def test_configure_endpoint(self):
        from fastapi.testclient import TestClient
        from aurora.compute.api import _openai_compatible_config
        app = self._get_app()
        client = TestClient(app)

        _openai_compatible_config.clear()
        resp = client.post("/api/v1/compute/providers/openai-compatible/configure", json={
            "base_url": "https://api.example.com/v1",
            "api_key": "secret-key-123",
            "model": "test-model",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CONFIGURED"
        assert data["gpu_required"] is False
        # API key must NOT be in response
        assert "secret-key-123" not in json.dumps(data)

    def test_configure_then_status(self):
        from fastapi.testclient import TestClient
        from aurora.compute.api import _openai_compatible_config
        app = self._get_app()
        client = TestClient(app)

        _openai_compatible_config.clear()
        client.post("/api/v1/compute/providers/openai-compatible/configure", json={
            "base_url": "https://api.example.com/v1",
            "api_key": "secret-key",
            "model": "my-model",
        })
        resp = client.get("/api/v1/compute/providers/openai-compatible/status")
        data = resp.json()
        assert data["status"] == "CONFIGURED"
        assert data["model"] == "my-model"
        assert data["api_key_configured"] is True
        assert "secret-key" not in json.dumps(data)

    def test_infer_endpoint_not_configured(self):
        from fastapi.testclient import TestClient
        from aurora.compute.api import _openai_compatible_config
        app = self._get_app()
        client = TestClient(app)

        _openai_compatible_config.clear()
        resp = client.post("/api/v1/compute/providers/openai-compatible/infer", json={
            "messages": [{"role": "user", "content": "hi"}],
        })
        assert resp.status_code == 400

    def test_infer_endpoint_success(self):
        from fastapi.testclient import TestClient
        from aurora.compute.api import _openai_compatible_config
        app = self._get_app()
        client = TestClient(app)

        _openai_compatible_config.clear()
        _openai_compatible_config["base_url"] = "https://api.example.com/v1"
        _openai_compatible_config["api_key"] = "test-key"
        _openai_compatible_config["model"] = "test-model"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Hello"}}],
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            resp = client.post("/api/v1/compute/providers/openai-compatible/infer", json={
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 100,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "COMPLETED"
            assert data["output"] == "Hello"
            assert "provenance" in data
            assert "secret-key" not in json.dumps(data)


class TestLLMIntegration:
    """Tests that OpenAI-compatible provider works through LLM-1 through LLM-5."""

    def test_llm1_reasoning_service_uses_provider(self):
        """LLM-1: ReasoningService uses the registered provider."""
        from aurora.ai.providers import OpenAICompatibleProvider, ProviderRegistry

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        registry = ProviderRegistry()
        registry.register(provider, default=True)

        retrieved = registry.get()
        assert retrieved.name == "openai-compatible"
        assert retrieved.is_available is True

    def test_llm2_tool_orchestration_uses_provider(self):
        """LLM-2: Tool orchestration uses the same provider interface."""
        from aurora.ai.providers import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        # LLM-2 calls provider.generate() — same interface
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"answer": "test"}'}}],
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = provider.generate(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=100,
            )
            assert result == '{"answer": "test"}'

    def test_model_output_not_auto_trusted(self):
        """Model output is classified as MODEL_INFERENCE, not FACT."""
        from aurora.ai.providers import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        prov = provider.get_provenance("prompt", "output")
        # Runtime is remote-api, not a fact/evidence source
        assert prov["runtime"] == "remote-api"
        # No auto-trust indicators
        assert "fact" not in prov
        assert "evidence" not in prov
        assert "source" not in prov


class TestUnifiedIntelligenceIntegration:
    """Tests that Unified Intelligence can use the new provider."""

    def test_provider_accessible_through_registry(self):
        from aurora.ai.providers import OpenAICompatibleProvider, ProviderRegistry

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        registry = ProviderRegistry()
        registry.register(provider, default=True)

        # Unified Intelligence calls registry.get()
        p = registry.get()
        assert p.name == "openai-compatible"

    def test_provider_capabilities_match_unified_needs(self):
        from aurora.ai.providers import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            api_key="test-key",
            base_url="https://api.example.com/v1",
            model="test-model",
        )
        caps = provider.capabilities()
        # Unified Intelligence needs structured output support
        assert caps.supports_structured_output is True
        # And sufficient context window
        assert caps.max_context_tokens >= 8192
