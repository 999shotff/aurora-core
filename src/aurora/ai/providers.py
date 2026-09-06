"""AURORA Reasoning Core — Provider Interface.

Provider-agnostic LLM interface with registry, timeout, structured generation.
Does not expose provider API keys to the frontend.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from aurora.ai.errors import (
    LLMTimeout,
    LLMUnavailable,
)


@dataclass(frozen=True)
class ProviderCapabilities:
    """Capabilities of an LLM provider."""

    name: str
    models: list[str]
    max_context_tokens: int = 8192
    max_output_tokens: int = 2048
    supports_structured_output: bool = True
    requires_api_key: bool = False
    is_demo: bool = False


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider is configured and reachable."""

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> str:
        """Generate a response from messages.

        Returns the raw text response.
        Raises LLMTimeout, LLMUnavailable on failure.
        """

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""

    def health_check(self) -> dict:
        """Basic health check."""
        return {
            "provider": self.name,
            "available": self.is_available,
            "capabilities": {
                "models": self.capabilities().models,
                "max_context": self.capabilities().max_context_tokens,
                "requires_key": self.capabilities().requires_api_key,
            },
        }


# ============================================================
# Stub Provider
# ============================================================


class StubProvider(LLMProvider):
    """Stub provider that returns deterministic fallback responses.

    Used when no real LLM is configured.
    """

    @property
    def name(self) -> str:
        return "stub"

    @property
    def is_available(self) -> bool:
        return True

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name="stub",
            models=["stub"],
            max_context_tokens=8192,
            max_output_tokens=2048,
            supports_structured_output=True,
            requires_api_key=False,
            is_demo=True,
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> str:
        """Generate a stub response based on the last user message."""
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        return json.dumps({
            "answer": (
                f"[Deterministic analysis only — no LLM configured] "
                f"Received query: {user_msg[:200]}"
            ),
            "summary": "LLM not configured. Analysis based on deterministic engines only.",
            "reasoning_points": [
                {
                    "point": "No LLM provider is configured for this AURORA instance.",
                    "grounding": "ABSTAINED",
                    "evidence_refs": [],
                }
            ],
            "uncertainties": ["No LLM provider available — all reasoning is deterministic."],
            "conflicts": [],
            "abstention_reason": "No LLM provider configured. Deterministic analysis only.",
        })


# ============================================================
# External Provider Adapter (OpenAI-compatible)
# ============================================================


class OpenAICompatibleProvider(LLMProvider):
    """Adapter for OpenAI-compatible APIs (OpenAI, Anthropic via proxy, local servers)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        provider_name: str = "openai",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._provider_name = provider_name

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=self._provider_name,
            models=[self._model],
            max_context_tokens=128000,
            max_output_tokens=4096,
            supports_structured_output=True,
            requires_api_key=True,
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> str:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if not choices:
                    raise LLMUnavailable("Empty response from provider")
                return choices[0].get("message", {}).get("content", "")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                raise LLMTimeout(timeout) from exc
            raise LLMUnavailable(f"HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise LLMUnavailable(f"Connection failed: {exc.reason}") from exc
        except TimeoutError:
            raise LLMTimeout(timeout)


# ============================================================
# Provider Registry
# ============================================================


class ProviderRegistry:
    """Registry of available LLM providers."""

    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._default: str = "stub"

    def register(self, provider: LLMProvider, default: bool = False) -> None:
        self._providers[provider.name] = provider
        if default:
            self._default = provider.name

    def get(self, name: str | None = None) -> LLMProvider:
        key = name or self._default
        if key not in self._providers:
            raise LLMUnavailable(f"Provider '{key}' not registered")
        return self._providers[key]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def health_check(self) -> dict:
        return {
            "providers": {
                name: p.health_check()
                for name, p in self._providers.items()
            },
            "default": self._default,
        }


# ============================================================
# Factory
# ============================================================


def create_provider_registry() -> ProviderRegistry:
    """Create a provider registry from environment configuration.

    Reads:
        AURORA_LLM_PROVIDER — provider name (default: stub)
        AURORA_LLM_API_KEY — API key for external providers
        AURORA_LLM_BASE_URL — base URL for OpenAI-compatible APIs
        AURORA_LLM_MODEL — model name
    """
    registry = ProviderRegistry()

    stub = StubProvider()
    registry.register(stub, default=True)

    provider_name = os.environ.get("AURORA_LLM_PROVIDER", "stub")
    api_key = os.environ.get("AURORA_LLM_API_KEY", "")
    base_url = os.environ.get("AURORA_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("AURORA_LLM_MODEL", "gpt-4o-mini")

    if provider_name != "stub" and api_key:
        provider = OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider_name=provider_name,
        )
        registry.register(provider, default=True)

    return registry
