"""Model Registry — approved models for runtime execution.

No weights stored. Only metadata. Models downloaded at runtime.

Each model has:
  - model_id:          AURORA-internal short identifier
  - source_model_id:   Official HuggingFace repo ID or Ollama model name
  - runtime:           'transformers' or 'ollama'
  - runtime_model_id:  Model name passed to the runtime (e.g. Ollama 'qwen2.5:0.5b')
"""

from __future__ import annotations

from aurora.runtime.schemas import ModelConfig, ModelRegistry, RuntimeCapability

DEFAULT_REGISTRY = ModelRegistry(
    models=[
        ModelConfig(
            model_id="qwen2.5-0.5b-ollama",
            model_name="Qwen2.5 0.5B Instruct (Ollama)",
            source_model_id="qwen2.5:0.5b",
            runtime="ollama",
            runtime_model_id="qwen2.5:0.5b",
            framework="ollama",
            dtype="float16",
            device="cuda",
            max_input_tokens=32768,
            max_output_tokens=2048,
            required_vram_gb=1.5,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION],
            description="Qwen2.5 0.5B via Ollama. First live GPU test model.",
            source="ollama",
        ),
        ModelConfig(
            model_id="qwen2.5-0.5b-instruct",
            model_name="Qwen2.5 0.5B Instruct",
            source_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            runtime="transformers",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=32768,
            max_output_tokens=2048,
            required_vram_gb=1.5,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION],
            description="Qwen2.5 0.5B instruction-tuned via Transformers.",
            source="huggingface",
            source_url="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct",
        ),
        ModelConfig(
            model_id="smollm2-1.7b",
            model_name="SmolLM2 1.7B Instruct",
            source_model_id="HuggingFaceTB/SmolLM2-1.7B-Instruct",
            runtime="transformers",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=8192,
            max_output_tokens=2048,
            required_vram_gb=2.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION],
            description="HuggingFace SmolLM2. Ultra-lightweight. For T4/low-VRAM.",
            source="huggingface",
            source_url="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct",
        ),
        ModelConfig(
            model_id="phi-3.5-mini",
            model_name="Phi-3.5 Mini Instruct",
            source_model_id="microsoft/Phi-3.5-mini-instruct",
            runtime="transformers",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=131072,
            max_output_tokens=4096,
            required_vram_gb=4.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION,
                          RuntimeCapability.SUMMARIZATION],
            description="Microsoft Phi-3.5 Mini. Small, fast, strong reasoning.",
            source="huggingface",
            source_url="https://huggingface.co/microsoft/Phi-3.5-mini-instruct",
        ),
        ModelConfig(
            model_id="mistral-7b",
            model_name="Mistral 7B Instruct v0.3",
            source_model_id="mistralai/Mistral-7B-Instruct-v0.3",
            runtime="transformers",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=32768,
            max_output_tokens=4096,
            required_vram_gb=7.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION],
            description="Mistral 7B instruction-tuned. Strong reasoning per parameter.",
            source="huggingface",
            source_url="https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
        ),
        ModelConfig(
            model_id="qwen2.5-7b",
            model_name="Qwen 2.5 7B Instruct",
            source_model_id="Qwen/Qwen2.5-7B-Instruct",
            runtime="transformers",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=32768,
            max_output_tokens=4096,
            required_vram_gb=7.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION,
                          RuntimeCapability.SUMMARIZATION],
            description="Qwen 2.5 7B instruction-tuned. Strong multilingual and coding.",
            source="huggingface",
            source_url="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct",
        ),
        ModelConfig(
            model_id="llama-3.1-8b",
            model_name="Meta Llama 3.1 8B Instruct",
            source_model_id="meta-llama/Llama-3.1-8B-Instruct",
            runtime="transformers",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=131072,
            max_output_tokens=4096,
            required_vram_gb=8.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION],
            description="Meta Llama 3.1 8B instruction-tuned model. Good general reasoning. GATED.",
            source="huggingface",
            source_url="https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
            requires_auth=True,
        ),
    ],
    default_model_id="qwen2.5-0.5b-ollama",
)


def get_default_registry() -> ModelRegistry:
    return DEFAULT_REGISTRY


def get_model_by_id(model_id: str) -> ModelConfig | None:
    for model in DEFAULT_REGISTRY.models:
        if model.model_id == model_id:
            return model
    return None


def get_source_model_id(model_id: str) -> str | None:
    """Resolve AURORA model_id to the official source identifier."""
    model = get_model_by_id(model_id)
    return model.source_model_id if model else None


def get_runtime_model_id(model_id: str) -> str | None:
    """Resolve AURORA model_id to the runtime-specific model name."""
    model = get_model_by_id(model_id)
    if model is None:
        return None
    return model.runtime_model_id or model.source_model_id


def get_runtime_type(model_id: str) -> str | None:
    """Get the runtime type for a model (transformers or ollama)."""
    model = get_model_by_id(model_id)
    return model.runtime if model else None


def list_model_ids() -> list[str]:
    return [m.model_id for m in DEFAULT_REGISTRY.models]


def estimate_vram_needed(model_id: str) -> float | None:
    model = get_model_by_id(model_id)
    return model.required_vram_gb if model else None
