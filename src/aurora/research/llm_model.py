"""Local LLM model adapter using transformers.

Attempts to import transformers/torch.
Falls back to MODEL_UNAVAILABLE if not present.
"""
from __future__ import annotations

import json
import time
from typing import Literal

from aurora.research.llm_schema import LLMExtractionResponse
from aurora.research.model_adapter import (
    ExtractionRequest,
    ExtractionResult,
    ModelConfig,
    ResearchExtractionModel,
)
from aurora.research.model_config import get_model_config

_SYSTEM_PROMPT = (
    "You are a financial research extraction system. "
    "Extract claims from the provided text ONLY. "
    "Return valid JSON matching the LLMExtractionResponse schema. "
    "Never use outside knowledge. "
    "Every claim must have an exact source-text span. "
    "Missing information must be null, never invented."
)


def _build_prompt(text: str, context: str = "") -> str:
    user_msg = f"Extract financial research claims from this text:\n\n{text}"
    if context:
        user_msg = f"Context: {context}\n\n{user_msg}"
    return f"<|system|>\n{_SYSTEM_PROMPT}\n<|user|>\n{user_msg}\n<|assistant|>\n"


class LocalLLMModel(ResearchExtractionModel):
    def __init__(self, model_id: str = "", **kwargs: str | float) -> None:
        self._model_id = model_id
        self._config: ModelConfig | None = get_model_config(model_id)
        self._pipeline = None
        self._loaded = False
        try:
            import transformers  # noqa: F401
            self._transformers_available = True
        except ImportError:
            self._transformers_available = False

    def is_available(self) -> bool:
        if not self._transformers_available:
            return False
        if self._config and self._config.backend == "stub":
            return True
        return self._transformers_available and self._config is not None

    def model_id(self) -> str:
        return self._model_id

    def model_status(self) -> Literal['available', 'unavailable', 'error']:
        if not self._transformers_available:
            return "unavailable"
        if self._loaded:
            return "available"
        return "available" if self._transformers_available else "unavailable"

    def _load_model(self) -> None:
        if self._loaded or not self._transformers_available:
            return
        if self._config is None:
            return
        try:
            import transformers
            self._pipeline = transformers.pipeline(
                "text-generation",
                model=self._config.model_path,
                max_new_tokens=self._config.max_tokens,
                do_sample=False,
            )
            self._loaded = True
        except (ImportError, OSError, ValueError):
            self._loaded = False

    def extract_claims(self, request: ExtractionRequest) -> ExtractionResult:
        start = time.time()
        if not self.is_available():
            return ExtractionResult(
                claims=[],
                model_id=self._model_id,
                status="unavailable",
                error=f"MODEL_UNAVAILABLE: {self._model_id}",
            )
        self._load_model()
        if not self._loaded:
            return ExtractionResult(
                claims=[],
                model_id=self._model_id,
                status="unavailable",
                error=f"MODEL_UNAVAILABLE: failed to load {self._model_id}",
            )
        prompt = _build_prompt(request.text)
        try:
            output = self._pipeline(prompt, max_new_tokens=self._config.max_tokens if self._config else 4096)  # type: ignore[misc]
            raw_text = output[0]["generated_text"] if output else ""
        except (RuntimeError, ValueError, KeyError) as e:
            latency = (time.time() - start) * 1000
            return ExtractionResult(
                claims=[],
                model_id=self._model_id,
                status="error",
                error=str(e),
                latency_ms=latency,
            )
        latency = (time.time() - start) * 1000
        try:
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = raw_text[json_start:json_end]
                response = LLMExtractionResponse(**json.loads(json_str))
                claims = [c.model_dump() for c in response.candidate_claims]
            else:
                claims = []
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            claims = []
        return ExtractionResult(
            claims=claims,
            model_id=self._model_id,
            status="available",
            latency_ms=latency,
            raw_output=raw_text,
        )
