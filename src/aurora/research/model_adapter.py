"""Provider-independent model adapter interface for research extraction.

Supports local models, API-based models, and future implementations.
Models are interchangeable candidates — no hard-coding.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

ModelStatus = Literal["available", "unavailable", "error"]


@dataclass
class ModelConfig:
    model_id: str
    model_path: str = ""
    backend: str = "unknown"
    max_tokens: int = 4096
    temperature: float = 0.0
    timeout_seconds: float = 60.0
    gpu_layers: int = 0
    context_window: int = 4096
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass
class ExtractionRequest:
    text: str
    document_id: str = ""
    page_number: int = 0
    context: str = ""
    source_file: str = ""
    source_sha256: str = ""
    is_ocr: bool = False
    max_claims: int = 50


@dataclass
class ExtractionResult:
    claims: list[dict]
    model_id: str
    status: ModelStatus = "available"
    error: str | None = None
    latency_ms: float = 0.0
    token_count: int = 0
    raw_output: str = ""


class ResearchExtractionModel(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract_claims(self, request: ExtractionRequest) -> ExtractionResult:
        raise NotImplementedError

    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def model_status(self) -> ModelStatus:
        raise NotImplementedError

    def warmup(self) -> bool:
        return True

    def health_check(self) -> dict[str, str | bool]:
        return {
            "model_id": self.model_id(),
            "available": self.is_available(),
            "status": self.model_status(),
        }


class UnavailableModel(ResearchExtractionModel):
    def __init__(self, model_id: str, reason: str = "not installed"):
        self._model_id = model_id
        self._reason = reason

    def is_available(self) -> bool:
        return False

    def extract_claims(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(
            claims=[],
            model_id=self._model_id,
            status="unavailable",
            error=f"MODEL_UNAVAILABLE: {self._reason}",
        )

    def model_id(self) -> str:
        return self._model_id

    def model_status(self) -> ModelStatus:
        return "unavailable"


def get_model(model_id: str, **kwargs: str | float) -> ResearchExtractionModel:
    try:
        from aurora.research.llm_model import LocalLLMModel
        model = LocalLLMModel(model_id=model_id, **kwargs)
        if model.is_available():
            return model
    except (ImportError, OSError):
        pass
    return UnavailableModel(model_id, reason="backend not available")
