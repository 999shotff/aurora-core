"""Local model runtime adapter using ctransformers (GGUF models).

Supports CPU-only operation without PyTorch.
Falls back to MODEL_RUNTIME_UNAVAILABLE if no model can load.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from aurora.research.llm_schema import (
    LLMExtractionResponse,
)
from aurora.research.model_adapter import (
    ExtractionResult,
    ResearchExtractionModel,
)


@dataclass
class RuntimeConfig:
    max_model_memory_mb: int = 2048
    max_input_tokens: int = 2048
    max_output_tokens: int = 1024
    timeout_seconds: float = 60.0
    temperature: float = 0.0
    top_p: float = 0.9
    repetition_penalty: float = 1.1
    context_length: int = 2048
    gpu_layers: int = 0
    threads: int = 4


_SYSTEM_PROMPT = (
    "You are a financial research extraction system. "
    "Extract claims from the provided text ONLY. "
    "Return valid JSON. "
    "Never use outside knowledge. "
    "Every claim must have an exact source-text span. "
    "Missing information must be null, never invented."
)


def _build_prompt(text, context=""):
    user_msg = "Extract financial research claims from this text:\n\n" + text
    if context:
        user_msg = "Context: " + context + "\n\n" + user_msg
    return "<|system|>\n" + _SYSTEM_PROMPT + "\n<|user|>\n" + user_msg + "\n<|assistant|>\n"


def _parse_llm_output(raw_text):
    try:
        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = raw_text[json_start:json_end]
            data = json.loads(json_str)
            response = LLMExtractionResponse(**data)
            return response, raw_text
    except Exception:
        pass
    return LLMExtractionResponse(candidate_claims=[]), raw_text


class LocalGGUFModel(ResearchExtractionModel):
    def __init__(self, model_path="", model_id="local-gguf", config=None):
        self._model_path = model_path
        self._model_id = model_id
        self._config = config or RuntimeConfig()
        self._llm = None
        self._loaded = False
        self._ctransformers_available = False
        try:
            import ctransformers
            self._ctransformers_available = True
            self._ct = ctransformers
        except ImportError:
            self._ct = None

    def is_available(self):
        if not self._ctransformers_available:
            return False
        if self._loaded:
            return True
        return os.path.isfile(self._model_path) if self._model_path else False

    def model_id(self):
        return self._model_id

    def model_status(self):
        if not self._ctransformers_available:
            return "unavailable"
        if self._loaded:
            return "available"
        if self._model_path and os.path.isfile(self._model_path):
            return "available"
        return "unavailable"

    def load(self):
        if self._loaded:
            return True
        if not self._ctransformers_available:
            return False
        if not self._model_path or not os.path.isfile(self._model_path):
            return False
        try:
            self._llm = self._ct.AutoModelForCausalLM.from_pretrained(
                self._model_path,
                model_type="llama",
                max_new_tokens=self._config.max_output_tokens,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                repetition_penalty=self._config.repetition_penalty,
                context_length=self._config.context_length,
                gpu_layers=self._config.gpu_layers,
                threads=self._config.threads,
            )
            self._loaded = True
            return True
        except Exception:
            self._loaded = False
            return False

    def unload(self):
        self._llm = None
        self._loaded = False

    def generate(self, prompt, max_tokens=None):
        if not self._loaded or self._llm is None:
            return ""
        tokens = max_tokens or self._config.max_output_tokens
        try:
            output = self._llm(prompt, max_new_tokens=tokens)
            if isinstance(output, str):
                return output
            if isinstance(output, list) and len(output) > 0:
                return output[0].get("generated_text", str(output[0]))
            return str(output)
        except Exception:
            return ""

    def extract_structured_claims(self, request):
        start = time.time()
        if not self._loaded:
            loaded = self.load()
            if not loaded:
                return ExtractionResult(
                    claims=[], model_id=self._model_id,
                    status="unavailable", error="MODEL_RUNTIME_UNAVAILABLE",
                )
        prompt = _build_prompt(request.text)
        raw_text = self.generate(prompt)
        latency = (time.time() - start) * 1000
        response, _ = _parse_llm_output(raw_text)
        claims = [c.model_dump() for c in response.candidate_claims]
        return ExtractionResult(
            claims=claims, model_id=self._model_id,
            status="available", latency_ms=latency,
            raw_output=raw_text,
        )

    def extract_claims(self, request):
        return self.extract_structured_claims(request)

    def health_check(self):
        return {
            "model_id": self._model_id,
            "available": self.is_available(),
            "status": self.model_status(),
            "loaded": self._loaded,
            "model_path": self._model_path,
        }
