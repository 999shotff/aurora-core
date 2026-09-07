"""Model Registry — approved models for runtime execution.

No weights stored. Only metadata. Models downloaded at runtime.
"""

from __future__ import annotations

from aurora.runtime.schemas import ModelConfig, ModelRegistry, RuntimeCapability

DEFAULT_REGISTRY = ModelRegistry(
    models=[
        ModelConfig(
            model_id="llama-3.1-8b",
            model_name="Meta Llama 3.1 8B Instruct",
            framework="transformers",
            dtype="float16",
            device="cuda",
            max_input_tokens=131072,
            max_output_tokens=4096,
            required_vram_gb=8.0,
            capabilities=[RuntimeCapability.INFERENCE, RuntimeCapability.TEXT_GENERATION],
            description="Meta Llama 3.1 8B instruction-tuned model. Good general reasoning.",
            source="huggingface",
            source_url="https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        ),
        ModelConfig(
            model_id="mistral-7b",
            model_name="Mistral 7B Instruct v0.3",
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
            model_id="phi-3.5-mini",
            model_name="Phi-3.5 Mini Instruct",
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
            model_id="smollm2-1.7b",
            model_name="SmolLM2 1.7B Instruct",
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
    ],
    default_model_id="smollm2-1.7b",
)


def get_default_registry() -> ModelRegistry:
    return DEFAULT_REGISTRY


def get_model_by_id(model_id: str) -> ModelConfig | None:
    for model in DEFAULT_REGISTRY.models:
        if model.model_id == model_id:
            return model
    return None


def list_model_ids() -> list[str]:
    return [m.model_id for m in DEFAULT_REGISTRY.models]


def estimate_vram_needed(model_id: str) -> float | None:
    model = get_model_by_id(model_id)
    return model.required_vram_gb if model else None
