"""LLM-3: Cognitive Memory — REST API Endpoints.

POST /api/v1/memory — create memory record
GET  /api/v1/memory/{memory_id} — get memory record
GET  /api/v1/memory/search — search memories
GET  /api/v1/memory/{memory_id}/history — version history
POST /api/v1/memory/{memory_id}/link — create relationship
GET  /api/v1/memory/{memory_id}/relationships — get relationships
POST /api/v1/memory/retrieve — retrieve for reasoning
GET  /api/v1/memory/stats — memory statistics
POST /api/v1/memory/export — export all memory data

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from aurora.memory.schemas import (
    MemoryType,
    RelationshipType,
)
from aurora.memory.store import MemoryStore
from aurora.memory.manager import MemoryManager

logger = logging.getLogger("aurora.memory.api")

_store: MemoryStore | None = None
_manager: MemoryManager | None = None


def _get_manager() -> MemoryManager:
    global _store, _manager
    if _manager is None:
        _store = MemoryStore("memory")
        _manager = MemoryManager(_store)
    return _manager


# ── Request/Response Models ────────────────────────────────────────────────


class CreateMemoryRequest(BaseModel):
    """Request to create a memory record."""

    model_config = {"extra": "forbid"}

    memory_type: str = Field(description="EPISODIC, SEMANTIC, EVIDENCE, WORKING")
    domain: str = Field(default="general")
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=50000)
    source: str = Field(default="user")
    provenance: str = Field(default="")
    observed_at: float | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryAPIResponse(BaseModel):
    """Response for a single memory record."""

    model_config = {"extra": "forbid"}

    memory_id: str
    memory_type: str
    version: int
    domain: str
    title: str
    content: str
    source: str
    provenance: str
    created_at: float
    observed_at: float | None
    updated_at: float
    status: str
    confidence: float
    evidence_refs: list[str]
    entity_refs: list[str]
    tags: list[str]


class SearchMemoryRequest(BaseModel):
    """Request to search memories."""

    model_config = {"extra": "forbid"}

    query: str = Field(default="")
    entity_id: str | None = None
    domain: str | None = None
    memory_type: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)


class RetrieveRequest(BaseModel):
    """Request to retrieve memory for reasoning."""

    model_config = {"extra": "forbid"}

    query: str = Field(..., min_length=1)
    domain: str = Field(default="general")
    entity_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class LinkRequest(BaseModel):
    """Request to create a relationship."""

    model_config = {"extra": "forbid"}

    target_id: str
    relationship: str
    description: str = Field(default="")


# ── FastAPI App ────────────────────────────────────────────────────────────


memory_app = FastAPI(
    title="AURORA Memory API",
    description="Cognitive memory for research intelligence. NO_DEPLOYMENT_SIGNAL.",
    version="0.1.0",
)


@memory_app.get("/api/v1/memory/stats")
def memory_stats() -> dict:
    """Get memory statistics."""
    manager = _get_manager()
    return manager.stats()


@memory_app.post("/api/v1/memory", response_model=MemoryAPIResponse)
def create_memory(body: CreateMemoryRequest) -> dict:
    """Create a new memory record."""
    manager = _get_manager()
    try:
        mem_type = MemoryType(body.memory_type)
    except ValueError:
        mem_type = MemoryType.EPISODIC

    record = manager.create(
        memory_type=mem_type,
        domain=body.domain,
        title=body.title,
        content=body.content,
        source=body.source,
        provenance=body.provenance,
        observed_at=body.observed_at,
        confidence=body.confidence,
        evidence_refs=body.evidence_refs,
        entity_refs=body.entity_refs,
        tags=body.tags,
        metadata=body.metadata,
    )

    return MemoryAPIResponse(
        memory_id=record.memory_id,
        memory_type=record.memory_type.value,
        version=record.version,
        domain=record.domain,
        title=record.title,
        content=record.content,
        source=record.source,
        provenance=record.provenance,
        created_at=record.created_at,
        observed_at=record.observed_at,
        updated_at=record.updated_at,
        status=record.status.value,
        confidence=record.confidence,
        evidence_refs=record.evidence_refs,
        entity_refs=record.entity_refs,
        tags=record.tags,
    )


@memory_app.get("/api/v1/memory/search")
def search_memory(
    query: str = Query(default=""),
    entity_id: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    top_k: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Search memory records."""
    manager = _get_manager()
    mt = None
    if memory_type:
        try:
            mt = MemoryType(memory_type)
        except ValueError:
            pass

    results = manager.search(
        query=query, entity_id=entity_id, domain=domain, memory_type=mt, top_k=top_k
    )

    return {
        "results": [
            {
                "memory": {
                    "memory_id": r.memory.memory_id,
                    "memory_type": r.memory.memory_type.value,
                    "title": r.memory.title,
                    "domain": r.memory.domain,
                    "status": r.memory.status.value,
                    "created_at": r.memory.created_at,
                },
                "score": r.score,
                "match_reasons": r.match_reasons,
            }
            for r in results
        ],
        "total": len(results),
    }


@memory_app.get("/api/v1/memory/{memory_id}")
def get_memory(memory_id: str) -> dict:
    """Get a memory record by ID."""
    manager = _get_manager()
    record = manager.get(memory_id)
    if record is None:
        return {"error": f"Memory {memory_id} not found"}
    return MemoryAPIResponse(
        memory_id=record.memory_id,
        memory_type=record.memory_type.value,
        version=record.version,
        domain=record.domain,
        title=record.title,
        content=record.content,
        source=record.source,
        provenance=record.provenance,
        created_at=record.created_at,
        observed_at=record.observed_at,
        updated_at=record.updated_at,
        status=record.status.value,
        confidence=record.confidence,
        evidence_refs=record.evidence_refs,
        entity_refs=record.entity_refs,
        tags=record.tags,
    ).model_dump()


@memory_app.get("/api/v1/memory/{memory_id}/history")
def memory_history(memory_id: str) -> dict:
    """Get version history for a memory."""
    manager = _get_manager()
    versions = manager.get_versions(memory_id)
    return {
        "memory_id": memory_id,
        "versions": [
            {
                "version_id": v.version_id,
                "version": v.version,
                "created_at": v.created_at,
                "change_reason": v.change_reason,
            }
            for v in versions
        ],
    }


@memory_app.post("/api/v1/memory/{memory_id}/link")
def link_memory(memory_id: str, body: LinkRequest) -> dict:
    """Create a relationship between memories."""
    manager = _get_manager()
    try:
        rel_type = RelationshipType(body.relationship)
    except ValueError:
        return {"error": f"Invalid relationship type: {body.relationship}"}

    manager.link(
        source_id=memory_id,
        target_id=body.target_id,
        relationship=rel_type,
        description=body.description,
    )
    return {"status": "linked", "source": memory_id, "target": body.target_id}


@memory_app.get("/api/v1/memory/{memory_id}/relationships")
def memory_relationships(memory_id: str) -> dict:
    """Get relationships for a memory."""
    manager = _get_manager()
    rels = manager.get_relationships(memory_id)
    return {
        "memory_id": memory_id,
        "relationships": [
            {
                "relationship_id": r.relationship_id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "relationship": r.relationship.value,
                "description": r.description,
                "created_at": r.created_at,
            }
            for r in rels
        ],
    }


@memory_app.post("/api/v1/memory/retrieve")
def retrieve_for_reasoning(body: RetrieveRequest) -> dict:
    """Retrieve memory for LLM reasoning context."""
    manager = _get_manager()
    records = manager.retrieve_for_reasoning(
        query=body.query, domain=body.domain, entity_id=body.entity_id, top_k=body.top_k
    )
    return {
        "records": [
            {
                "memory_id": r.memory_id,
                "memory_type": r.memory_type.value,
                "title": r.title,
                "content": r.content[:500],
                "domain": r.domain,
                "status": r.status.value,
                "confidence": r.confidence,
                "evidence_refs": r.evidence_refs,
                "created_at": r.created_at,
            }
            for r in records
        ],
        "count": len(records),
    }


@memory_app.post("/api/v1/memory/export")
def export_memory() -> dict:
    """Export all memory data."""
    manager = _get_manager()
    return manager.export()
