"""Compute Fabric — strict Pydantic schemas (v2).

Worker Protocol v2: versioned, structured, validated.
Enhanced provider/worker status models.
GPU info from real runtime only. No fabrication.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


PROTOCOL_VERSION = "2.0"
WORKER_VERSION = "0.2.0"


# ============================================================
# Enums
# ============================================================


class ComputeProviderType(str, Enum):
    CPU = "CPU"
    GOOGLE_COLAB = "GOOGLE_COLAB"
    LIGHTNING = "LIGHTNING"


class ComputeProviderStatus(str, Enum):
    DISABLED = "DISABLED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    HEALTH_CHECK = "HEALTH_CHECK"
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class WorkerStatus(str, Enum):
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    READY = "READY"
    BUSY = "BUSY"
    UNHEALTHY = "UNHEALTHY"
    DISCONNECTED = "DISCONNECTED"
    SHUTTING_DOWN = "SHUTTING_DOWN"


class ComputeMode(str, Enum):
    AUTO = "AUTO"
    CPU = "CPU"
    GOOGLE_COLAB = "GOOGLE_COLAB"
    LIGHTNING = "LIGHTNING"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class WorkloadType(str, Enum):
    INFERENCE = "INFERENCE"
    EMBEDDINGS = "EMBEDDINGS"
    VISION = "VISION"
    TRAINING = "TRAINING"
    BENCHMARK = "BENCHMARK"
    CUSTOM = "CUSTOM"


class ProtocolMessageType(str, Enum):
    REGISTER = "REGISTER"
    REGISTER_ACK = "REGISTER_ACK"
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    CAPABILITIES = "CAPABILITIES"
    HEALTH = "HEALTH"
    JOB_SUBMIT = "JOB_SUBMIT"
    JOB_ACCEPTED = "JOB_ACCEPTED"
    JOB_STARTED = "JOB_STARTED"
    JOB_PROGRESS = "JOB_PROGRESS"
    JOB_LOG = "JOB_LOG"
    JOB_RESULT = "JOB_RESULT"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCEL = "JOB_CANCEL"
    SHUTDOWN = "SHUTDOWN"


class AuditAction(str, Enum):
    COMPUTE_ENABLED = "COMPUTE_ENABLED"
    COMPUTE_DISABLED = "COMPUTE_DISABLED"
    MODE_CHANGED = "MODE_CHANGED"
    PROVIDER_SELECTED = "PROVIDER_SELECTED"
    PROVIDER_STARTING = "PROVIDER_STARTING"
    PROVIDER_READY = "PROVIDER_READY"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    WORKER_REGISTERED = "WORKER_REGISTERED"
    WORKER_AUTHENTICATED = "WORKER_AUTHENTICATED"
    WORKER_AUTH_FAILED = "WORKER_AUTH_FAILED"
    WORKER_HEARTBEAT = "WORKER_HEARTBEAT"
    WORKER_DISCONNECTED = "WORKER_DISCONNECTED"
    WORKER_RECONNECTED = "WORKER_RECONNECTED"
    WORKER_SHUTDOWN = "WORKER_SHUTDOWN"
    GPU_DETECTED = "GPU_DETECTED"
    JOB_SUBMITTED = "JOB_SUBMITTED"
    JOB_ASSIGNED = "JOB_ASSIGNED"
    JOB_STARTED = "JOB_STARTED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_TIMEOUT = "JOB_TIMEOUT"
    BENCHMARK_COMPLETED = "BENCHMARK_COMPLETED"


class BenchmarkStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


# ============================================================
# GPU Info — only from real runtime
# ============================================================


class GPUInfo(BaseModel):
    """GPU information. Only from real runtime reporting. Never fabricated."""

    model_config = ConfigDict(extra="forbid")

    name: str = "UNKNOWN"
    vendor: str = "UNKNOWN"
    vram_mb: float = 0.0
    cuda_version: str | None = None
    driver_version: str | None = None
    compute_capability: str | None = None
    available_memory_mb: float = 0.0
    runtime_info: str | None = None


# ============================================================
# Compute Capabilities
# ============================================================


class ComputeCapabilities(BaseModel):
    """What a provider can do. Never fabricate."""

    model_config = ConfigDict(extra="forbid")

    inference: bool = False
    embeddings: bool = False
    vision: bool = False
    training: bool = False
    benchmark: bool = False
    max_concurrency: int = 1
    gpu: GPUInfo | None = None
    framework: str | None = None
    python_version: str | None = None


# ============================================================
# Provider Info
# ============================================================


class ComputeProviderInfo(BaseModel):
    """Public provider state. No secrets."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    provider_type: ComputeProviderType
    name: str
    status: ComputeProviderStatus
    capabilities: ComputeCapabilities = Field(default_factory=ComputeCapabilities)
    last_health_check: float | None = None
    last_heartbeat: float | None = None
    worker_id: str | None = None
    worker_status: WorkerStatus = WorkerStatus.OFFLINE
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Worker Protocol v2
# ============================================================


class WorkerRegistration(BaseModel):
    """Worker registers itself with the compute backend."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    provider_id: str = Field(..., min_length=1, max_length=128)
    provider_type: ComputeProviderType
    capabilities: ComputeCapabilities = Field(default_factory=ComputeCapabilities)
    protocol_version: str = PROTOCOL_VERSION
    worker_version: str = WORKER_VERSION
    started_at: float = Field(default_factory=time.time)
    api_token: str = Field(..., min_length=1, max_length=256)


class WorkerRegistrationAck(BaseModel):
    """Server acknowledges worker registration."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    worker_id: str
    protocol_version: str = PROTOCOL_VERSION
    heartbeat_interval_seconds: int = 30
    error: str | None = None


class WorkerHeartbeat(BaseModel):
    """Worker periodic heartbeat with runtime state."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    status: WorkerStatus
    capabilities: ComputeCapabilities = Field(default_factory=ComputeCapabilities)
    current_job_id: str | None = None
    uptime_seconds: float = 0.0
    api_token: str = Field(..., min_length=1, max_length=256)


class WorkerHeartbeatAck(BaseModel):
    """Server acknowledges heartbeat."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    pending_jobs: int = 0
    shutdown_requested: bool = False


class WorkerCapabilities(BaseModel):
    """Worker sends updated capabilities."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    capabilities: ComputeCapabilities
    api_token: str = Field(..., min_length=1, max_length=256)


class WorkerHealth(BaseModel):
    """Worker health check response."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str
    status: WorkerStatus
    gpu: GPUInfo | None = None
    uptime_seconds: float = 0.0
    memory_usage_mb: float | None = None
    cpu_usage_percent: float | None = None


class WorkerShutdown(BaseModel):
    """Worker graceful shutdown."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    reason: str = ""
    api_token: str = Field(..., min_length=1, max_length=256)


# ============================================================
# Job Models
# ============================================================


class ComputeJobRequest(BaseModel):
    """Request to submit a compute job."""

    model_config = ConfigDict(extra="forbid")

    workload_type: WorkloadType
    provider_preference: ComputeProviderType | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def validate_payload_no_arbitrary_exec(cls, v: dict[str, Any]) -> dict[str, Any]:
        forbidden_keys = {"shell", "exec", "eval", "subprocess", "os.system", "compile"}
        for key in v:
            if key.lower() in forbidden_keys:
                raise ValueError(f"Payload key '{key}' is not permitted")
        return v


class ComputeJob(BaseModel):
    """A compute job record."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    workload_type: WorkloadType
    provider_id: str
    provider_type: ComputeProviderType
    worker_id: str | None = None
    status: JobStatus = JobStatus.QUEUED
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: float = Field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    timeout_seconds: int = 300
    input_hash: str | None = None
    result_hash: str | None = None
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobProgress(BaseModel):
    """Worker reports job progress."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    progress: float = Field(ge=0.0, le=1.0)
    message: str = ""


class JobResult(BaseModel):
    """Worker reports job completion."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    result_hash: str | None = None
    logs: list[str] = Field(default_factory=list)


class JobFailed(BaseModel):
    """Worker reports job failure."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    error: str
    logs: list[str] = Field(default_factory=list)


class JobLog(BaseModel):
    """Worker sends a log line for a job."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    message: str
    level: str = "INFO"


# ============================================================
# Benchmark
# ============================================================


class BenchmarkRequest(BaseModel):
    """Request to run GPU benchmark on a specific provider."""

    model_config = ConfigDict(extra="forbid")

    provider_type: ComputeProviderType
    matrix_size: int = Field(default=1024, ge=64, le=8192)
    iterations: int = Field(default=10, ge=1, le=100)


class BenchmarkResult(BaseModel):
    """Result of a GPU benchmark."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str
    provider_type: ComputeProviderType
    gpu: GPUInfo
    matrix_size: int
    iterations: int
    execution_time_seconds: float
    gflops: float | None = None
    result_checksum: str
    status: BenchmarkStatus
    timestamp: float = Field(default_factory=time.time)
    error: str | None = None

    @staticmethod
    def compute_checksum(data: dict[str, Any]) -> str:
        raw = str(sorted(data.items()))
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ============================================================
# Model Runtime
# ============================================================


class RuntimeStatus(str, Enum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    LOADING = "LOADING"
    READY = "READY"
    UNLOADING = "UNLOADING"
    ERROR = "ERROR"


class ModelMetadata(BaseModel):
    """Metadata about a model. No weights stored in repo."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    provider: str | None = None
    runtime: str | None = None
    parameter_count: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    required_vram_gb: float | None = None
    status: RuntimeStatus = RuntimeStatus.NOT_AVAILABLE


class EmbeddingRequest(BaseModel):
    """Structured embedding workload request."""

    model_config = ConfigDict(extra="forbid")

    texts: list[str] = Field(..., min_length=1, max_length=1000)
    model: str = "default"
    batch_size: int = Field(default=32, ge=1, le=256)


class EmbeddingResult(BaseModel):
    """Result of embedding workload."""

    model_config = ConfigDict(extra="forbid")

    embedding_model: str
    dimensions: int
    count: int
    input_hash: str
    result_hash: str
    worker_id: str
    provider_type: ComputeProviderType


# ============================================================
# Compute Status
# ============================================================


class ComputeStatus(BaseModel):
    """Overall compute fabric status."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: ComputeMode = ComputeMode.CPU
    active_provider: str | None = None
    providers: list[ComputeProviderInfo] = Field(default_factory=list)
    active_jobs: int = 0
    total_jobs_completed: int = 0
    gpu_enabled: bool = False
    last_updated: float = Field(default_factory=time.time)


# ============================================================
# API Request/Response
# ============================================================


class ModeChangeRequest(BaseModel):
    """Request to change compute mode."""

    model_config = ConfigDict(extra="forbid")

    mode: ComputeMode


class AuditRecord(BaseModel):
    """Audit log entry."""

    model_config = ConfigDict(extra="forbid")

    action: AuditAction
    timestamp: float = Field(default_factory=time.time)
    provider_id: str | None = None
    worker_id: str | None = None
    job_id: str | None = None
    detail: str = ""
    success: bool = True
