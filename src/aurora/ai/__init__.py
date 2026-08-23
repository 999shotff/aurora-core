"""AI/LLM Abstraction Layer.

The deterministic analysis engine is the source of truth.
The LLM receives structured analytical facts and cannot modify raw data.

Architecture:
  OHLCV → deterministic indicators → market context → structured JSON → OPTIONAL LLM → NL explanation

If the AI service is unavailable, the deterministic analysis continues working.
No API key is required for core functionality.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM provider."""
    text: str
    provider: str
    model: str
    success: bool
    error: str = ""


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
    def generate(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        """Generate a response from a prompt."""


class StubLLMProvider(LLMProvider):
    """Stub provider that returns a fallback message. Used when no real LLM is configured."""

    @property
    def name(self) -> str:
        return "stub"

    @property
    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        return LLMResponse(
            text="[LLM not configured — using deterministic analysis only]",
            provider="stub",
            model="none",
            success=True,
        )


def create_llm_provider() -> LLMProvider:
    """Create an LLM provider from environment configuration.

    Currently returns a stub. Real providers can be added here
    by checking for API keys in environment variables.
    """
    import os

    # Check for configured providers (future use)
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if openai_key:
        # Future: return OpenAIProvider(openai_key)
        pass
    if anthropic_key:
        # Future: return AnthropicProvider(anthropic_key)
        pass

    return StubLLMProvider()


def format_analysis_for_llm(market_context_dict: dict) -> str:
    """Format a MarketContext dict into a prompt for an LLM.

    The LLM receives structured facts only. It cannot modify any data.
    """
    lines = [
        "You are an analytical assistant. Below is structured market analysis data.",
        "Describe the market context in plain language. Do NOT make predictions.",
        "Do NOT give trading recommendations. Only describe what the data shows.",
        "",
        "=== MARKET ANALYSIS DATA ===",
        "",
    ]

    for key in ("trend", "momentum", "volatility", "volume", "structure", "liquidity", "multi_timeframe"):
        section = market_context_dict.get(key, {})
        if isinstance(section, dict):
            lines.append(f"## {key.upper()}")
            for k, v in section.items():
                if k == "evidence":
                    continue
                lines.append(f"  {k}: {v}")
            evidence = section.get("evidence", [])
            if evidence:
                lines.append("  evidence:")
                for e in evidence:
                    lines.append(f"    - {e}")
            lines.append("")

    conflicts = market_context_dict.get("conflicts", [])
    if conflicts:
        lines.append("## CONFLICTS")
        for c in conflicts:
            if isinstance(c, dict):
                lines.append(f"  - {c.get('description', '')}")
        lines.append("")

    lines.append("=== END DATA ===")
    lines.append("")
    lines.append("Respond with a structured analysis. Be factual. No predictions.")

    return "\n".join(lines)


def generate_natural_language_explanation(market_context_dict: dict) -> str:
    """Generate a natural language explanation.

    Uses the LLM if available, otherwise falls back to deterministic
    section-by-section summary.
    """
    provider = create_llm_provider()

    if provider.is_available and provider.name != "stub":
        prompt = format_analysis_for_llm(market_context_dict)
        response = provider.generate(prompt)
        if response.success:
            return response.text

    # Fallback: deterministic summary
    sections = []
    trend = market_context_dict.get("trend", {})
    direction = trend.get("direction", "unknown")
    strength = trend.get("strength", "unknown")
    sections.append(f"Trend: {direction.upper()} ({strength})")

    momentum = market_context_dict.get("momentum", {})
    sections.append(f"Momentum: {momentum.get('state', 'unknown').upper()}")

    volatility = market_context_dict.get("volatility", {})
    sections.append(f"Volatility: {volatility.get('regime', 'unknown').upper()}")

    volume = market_context_dict.get("volume", {})
    sections.append(f"Volume: {volume.get('state', 'unknown').upper()}")

    structure = market_context_dict.get("structure", {})
    sections.append(f"Structure: {structure.get('state', 'unknown').upper()}")

    conflicts = market_context_dict.get("conflicts", [])
    if conflicts:
        sections.append(f"Conflicts: {len(conflicts)} detected")
        for c in conflicts:
            desc = c.get("description", "") if isinstance(c, dict) else str(c)
            sections.append(f"  - {desc}")

    return "\n".join(sections)
