"""Model Runtime — strict Pydantic schemas.

Runtime lifecycle, model registry, inference jobs, provenance.
All models use extra="forbid" for validation safety.
No secrets. No fabrication. No arbitrary code execution.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# Enums
# ============================================================


class RuntimeStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    DISCOVERING = "DISCOVERING"
    LOADING = "LOADING"
    READY = "READY"
    BUSY = "BUSY"
    UNLOADING = "UNLOADING"
    ERROR = "ERROR"


class ModelLoadStatus(str, Enum):
    NOT_LOADED = "NOT_LOADED"
    LOADING = "LOADING"
    LOADED = "LOADED"
    UNLOADING = "UNLOADING"
    ERROR = "ERROR"


class InferenceStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class RuntimeCapability(str, Enum):
    INFERENCE = "INFERENCE"
    EMBEDDINGS = "EMBEDDINGS"
    VISION = "VISION"
    TEXT_GENERATION = "TEXT_GENERATION"
    TEXT_CLASSIFICATION = "TEXT_CLASSIFICATION"
    SUMMARIZATION = "SUMMARIZATION"
    TRANSLATION = "TRANSLATION"


# ============================================================
# Model Configuration
# ============================================================


class ModelConfig(BaseModel):
    """Approved model configuration. No weights stored in repo."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_id: str = Field(..., min_length=1, max_length=128)
    model_name: str = Field(..., min_length=1, max_length=256)
    model_revision: str | None = None
    framework: str = "transformers"
    dtype: str = "float16"
    device: str = "cuda"
    max_input_tokens: int = Field(default=2048, ge=1, le=131072)
    max_output_tokens: int = Field(default=512, ge=1, le=32768)
    required_vram_gb: float = Field(default=1.0, ge=0.1, le=80.0)
    capabilities: list[RuntimeCapability] = Field(default_factory=lambda: [RuntimeCapability.INFERENCE])
    description: str = ""
    source: str = "huggingface"
    source_url: str | None = None


class ModelRegistry(BaseModel):
    """Registry of approved models."""

    model_config = ConfigDict(extra="forbid")

    models: list[ModelConfig] = Field(default_factory=list)
    default_model_id: str | None = None


# ============================================================
# Runtime State
# ============================================================


class RuntimeInfo(BaseModel):
    """Current runtime state. Only from real runtime reporting."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    runtime_id: str
    status: RuntimeStatus
    model: ModelConfig | None = None
    model_load_status: ModelLoadStatus = ModelLoadStatus.NOT_LOADED
    worker_id: str | None = None
    provider_type: str | None = None
    gpu_name: str | None = None
    vram_mb: float | None = None
    cuda_version: str | None = None
    framework: str | None = None
    pytorch_version: str | None = None
    model_memory_mb: float | None = None
    loaded_at: float | None = None
    last_inference_at: float | None = None
    total_inferences: int = 0
    total_errors: int = 0
    uptime_seconds: float = 0.0
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Runtime Operations
# ============================================================


class RuntimeDiscoverRequest(BaseModel):
    """Request to discover runtime capabilities on a worker."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class RuntimeDiscoverResult(BaseModel):
    """Result of runtime discovery."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str
    runtime_id: str
    status: RuntimeStatus
    gpu_name: str | None = None
    vram_mb: float | None = None
    cuda_version: str | None = None
    pytorch_version: str | None = None
    available_models: list[str] = Field(default_factory=list)
    error: str | None = None
    timestamp: float = Field(default_factory=time.time)


class RuntimeLoadRequest(BaseModel):
    """Request to load a model on a worker."""

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1, max_length=128)
    worker_id: str = Field(..., min_length=1, max_length=128)
    dtype: str | None = None
    timeout_seconds: int = Field(default=120, ge=1, le=600)


class RuntimeLoadResult(BaseModel):
    """Result of model loading."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str
    runtime_id: str
    model_id: str
    status: ModelLoadStatus
    load_time_seconds: float | None = None
    model_memory_mb: float | None = None
    error: str | None = None
    timestamp: float = Field(default_factory=time.time)


class RuntimeUnloadRequest(BaseModel):
    """Request to unload a model from a worker."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    runtime_id: str = Field(..., min_length=1, max_length=128)


class RuntimeHealthRequest(BaseModel):
    """Request to check runtime health."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)


# ============================================================
# Inference Job
# ============================================================


class InferenceRequest(BaseModel):
    """Bounded inference request. Strictly validated."""

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1, max_length=128)
    worker_id: str | None = None
    prompt: str = Field(..., min_length=1, max_length=8192)
    max_new_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int = Field(default=50, ge=1, le=500)
    do_sample: bool = True
    num_return_sequences: int = Field(default=1, ge=1, le=4)
    stop_sequences: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=60, ge=1, le=300)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt")
    @classmethod
    def validate_prompt_no_code_exec(cls, v: str) -> str:
        forbidden = ["import os", "import subprocess", "os.system(", "exec(", "eval(",
                      "__import__", "compile(", "shell=True",
                      "subprocess.run", "subprocess.call", "subprocess.Popen",
                      "import ctypes", "import signal"]
        lower = v.lower()
        for pattern in forbidden:
            if pattern.lower() in lower:
                raise ValueError(f"Prompt contains forbidden pattern: {pattern}")
        return v


class InferenceResult(BaseModel):
    """Result of an inference job with full provenance."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    job_id: str
    inference_id: str
    model_id: str
    model_name: str | None = None
    worker_id: str
    runtime_id: str
    status: InferenceStatus
    prompt_hash: str
    output: str | None = None
    output_hash: str | None = None
    tokens_generated: int = 0
    generation_time_seconds: float = 0.0
    tokens_per_second: float = 0.0
    model_version: str | None = None
    device: str | None = None
    gpu_name: str | None = None
    framework: str | None = None
    dtype: str | None = None
    created_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def compute_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]


# ============================================================
# Provenance
# ============================================================


class InferenceProvenance(BaseModel):
    """Complete provenance record for an inference result."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    job_id: str
    inference_id: str
    worker_id: str
    runtime_id: str
    model_id: str
    model_name: str | None = None
    model_version: str | None = None
    execution_device: str | None = None
    gpu_name: str | None = None
    framework: str | None = None
    dtype: str | None = None
    prompt_hash: str
    output_hash: str | None = None
    tokens_generated: int = 0
    generation_time_seconds: float = 0.0
    created_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    status: InferenceStatus
    error: str | None = None
    evidence_class: str = "MODEL_INFERENCE"
    limitations: list[str] = Field(default_factory=list)
