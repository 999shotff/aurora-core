"""Model configuration for multi-model support.

Models are interchangeable candidates.
No model is assumed to be the best.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from aurora.research.model_adapter import ModelConfig

DEFAULT_MODEL_CONFIGS: dict[str, ModelConfig] = {
    "deepseek-r1-distill-qwen-1.5b": ModelConfig(
        model_id="deepseek-r1-distill-qwen-1.5b",
        model_path="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        backend="transformers",
        max_tokens=4096,
        temperature=0.0,
        timeout_seconds=120.0,
        context_window=4096,
    ),
    "qwen2.5-1.5b": ModelConfig(
        model_id="qwen2.5-1.5b",
        model_path="Qwen/Qwen2.5-1.5B",
        backend="transformers",
        max_tokens=4096,
        temperature=0.0,
        timeout_seconds=120.0,
        context_window=4096,
    ),
    "gemma-2-2b": ModelConfig(
        model_id="gemma-2-2b",
        model_path="google/gemma-2-2b",
        backend="transformers",
        max_tokens=4096,
        temperature=0.0,
        timeout_seconds=120.0,
        context_window=4096,
    ),
    "stub": ModelConfig(
        model_id="stub",
        model_path="",
        backend="stub",
        max_tokens=4096,
        temperature=0.0,
        timeout_seconds=10.0,
        context_window=4096,
    ),
}


@dataclass
class ExperimentConfig:
    models: list[str] = field(default_factory=lambda: ["stub"])
    benchmark_ids: list[str] = field(default_factory=list)
    max_claims_per_page: int = 50
    require_source_grounding: bool = True
    confidence_threshold: float = 0.3
    timeout_seconds: float = 60.0


def get_model_config(model_id: str) -> ModelConfig | None:
    return DEFAULT_MODEL_CONFIGS.get(model_id)


def list_available_models() -> list[str]:
    return sorted(DEFAULT_MODEL_CONFIGS.keys())
