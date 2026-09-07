"""Compute Fabric — strict Pydantic schemas.

All models use extra="forbid" for validation safety.
No secrets exposed. No fake GPU data.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    STARTING = "STARTING"
    READY = "READY"
    BUSY = "BUSY"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class ComputeMode(str, Enum):
    AUTO = "AUTO"
    CPU = "CPU"
    GOOGLE_COLAB = "GOOGLE_COLAB"
    LIGHTNING = "LIGHTNING"


class JobStatus(str, Enum):
    PENDING = "PENDING"
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
    CUSTOM = "CUSTOM"


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
    WORKER_HEARTBEAT = "WORKER_HEARTBEAT"
    WORKER_DISCONNECTED = "WORKER_DISCONNECTED"
    JOB_SUBMITTED = "JOB_SUBMITTED"
    JOB_STARTED = "JOB_STARTED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_TIMEOUT = "JOB_TIMEOUT"


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
    max_concurrency: int = 1
    gpu_name: str | None = None
    vram_gb: float | None = None
    cuda_version: str | None = None
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
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Worker Protocol
# ============================================================


class WorkerRegistration(BaseModel):
    """Worker registers itself with the compute backend."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    provider_id: str = Field(..., min_length=1, max_length=128)
    provider_type: ComputeProviderType
    capabilities: ComputeCapabilities = Field(default_factory=ComputeCapabilities)
    protocol_version: str = "1.0"
    api_token: str = Field(..., min_length=1, max_length=256)


class WorkerHeartbeat(BaseModel):
    """Worker periodic heartbeat."""

    model_config = ConfigDict(extra="forbid")

    worker_id: str = Field(..., min_length=1, max_length=128)
    status: ComputeProviderStatus
    capabilities: ComputeCapabilities = Field(default_factory=ComputeCapabilities)
    current_job_id: str | None = None
    api_token: str = Field(..., min_length=1, max_length=256)


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


class ComputeJob(BaseModel):
    """A compute job record."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    workload_type: WorkloadType
    provider_id: str
    provider_type: ComputeProviderType
    status: JobStatus = JobStatus.PENDING
    created_at: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    started_at: float | None = None
    completed_at: float | None = None
    timeout_seconds: int = 300
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    last_updated: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


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
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    provider_id: str | None = None
    worker_id: str | None = None
    job_id: str | None = None
    detail: str = ""
    success: bool = True
