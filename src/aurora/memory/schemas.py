"""
LLM-3: Memory domain models.

All memory types are structured, versioned, and provenance-tracked.
MEMORY IS NOT TRUTH — every item preserves source, timestamp, status.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────


class MemoryType(str, Enum):
    """Memory classification."""

    EPISODIC = "EPISODIC"  # Investigations/events
    SEMANTIC = "SEMANTIC"  # Durable knowledge
    EVIDENCE = "EVIDENCE"  # References to existing evidence
    WORKING = "WORKING"  # Current investigation context


class MemoryStatus(str, Enum):
    """Memory lifecycle status."""

    ACTIVE = "ACTIVE"
    UPDATED = "UPDATED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class MemoryConflictState(str, Enum):
    """Conflict resolution state."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    SUPERSEDED = "SUPERSEDED"


class RelationshipType(str, Enum):
    """Memory relationship types."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DERIVED_FROM = "DERIVED_FROM"
    REFINES = "REFINES"
    SUPERSEDES = "SUPERSEDES"
    TEMPORALLY_RELATED = "TEMPORALLY_RELATED"
    SAME_ENTITY = "SAME_ENTITY"
    SAME_INVESTIGATION = "SAME_INVESTIGATION"
    RELATED_TO = "RELATED_TO"


class EntityType(str, Enum):
    """Entity reference types."""

    MARKET_ASSET = "MARKET_ASSET"
    LOCATION = "LOCATION"
    AOI = "AOI"
    RESEARCH_CLAIM = "RESEARCH_CLAIM"
    HYPOTHESIS = "HYPOTHESIS"
    DOCUMENT = "DOCUMENT"
    INVESTIGATION = "INVESTIGATION"
    SCENE = "SCENE"
    INDICATOR = "INDICATOR"


# ── Core Models ────────────────────────────────────────────────────────────


class EntityReference(BaseModel):
    """Stable entity reference."""

    model_config = {"extra": "forbid"}

    entity_id: str = Field(description="Stable entity identifier")
    entity_type: EntityType
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRecord(BaseModel):
    """Core memory record — versioned, provenance-tracked."""

    model_config = {"extra": "forbid"}

    memory_id: str = Field(description="Unique memory identifier")
    memory_type: MemoryType
    version: int = Field(default=1, ge=1)
    domain: str = Field(description="Domain: market, geo, research, general")
    title: str = Field(description="Human-readable title")
    content: str = Field(description="Memory content/text")
    source: str = Field(description="Source system or user")
    provenance: str = Field(description="Detailed provenance chain")
    created_at: float = Field(description="Creation timestamp (UTC epoch)")
    observed_at: float | None = Field(
        default=None, description="When the underlying event was observed"
    )
    updated_at: float = Field(description="Last update timestamp")
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence_refs: list[str] = Field(
        default_factory=list, description="References to evidence IDs"
    )
    entity_refs: list[str] = Field(
        default_factory=list, description="References to entity IDs"
    )
    relationship_refs: list[str] = Field(
        default_factory=list, description="References to relationship IDs"
    )
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    previous_version_id: str | None = Field(
        default=None, description="Previous version memory_id"
    )
    change_reason: str = Field(default="", description="Why this version was created")


class MemoryVersion(BaseModel):
    """Version record for memory history."""

    model_config = {"extra": "forbid"}

    version_id: str
    memory_id: str
    version: int
    snapshot: MemoryRecord
    created_at: float
    change_reason: str


class MemoryConflict(BaseModel):
    """Conflict between two memory records."""

    model_config = {"extra": "forbid"}

    conflict_id: str
    memory_id_a: str
    memory_id_b: str
    conflict_type: str = Field(description="Type of conflict")
    description: str
    state: MemoryConflictState = Field(default=MemoryConflictState.OPEN)
    created_at: float
    resolved_at: float | None = None
    resolution_notes: str = ""


class WorkingMemory(BaseModel):
    """Short-lived working memory for current investigation."""

    model_config = {"extra": "forbid"}

    session_id: str
    user_query: str = ""
    domain: str = "general"
    entities: list[EntityReference] = Field(default_factory=list)
    current_asset: str | None = None
    current_timeframe: str | None = None
    current_aoi: str | None = None
    active_evidence: list[str] = Field(default_factory=list)
    active_tool_results: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    current_plan_id: str | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class MemorySearchResult(BaseModel):
    """Search result with match explanation."""

    model_config = {"extra": "forbid"}

    memory: MemoryRecord
    score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[str] = Field(default_factory=list)


class MemoryExport(BaseModel):
    """Exportable memory data."""

    model_config = {"extra": "forbid"}

    export_id: str
    exported_at: float
    version: int
    records: list[MemoryRecord]
    versions: list[MemoryVersion]
    conflicts: list[MemoryConflict]
    relationships: list[dict[str, Any]]
    entity_references: list[EntityReference]


def generate_memory_id() -> str:
    """Generate a unique memory ID."""
    return f"mem-{uuid.uuid4().hex[:12]}"


def generate_version_id() -> str:
    """Generate a unique version ID."""
    return f"ver-{uuid.uuid4().hex[:12]}"


def generate_conflict_id() -> str:
    """Generate a unique conflict ID."""
    return f"con-{uuid.uuid4().hex[:12]}"


def compute_memory_hash(record: MemoryRecord) -> str:
    """Compute deterministic hash for memory record."""
    data = f"{record.memory_id}:{record.version}:{record.content}:{record.status.value}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]
