"""
LLM-3: Memory Manager — orchestrates all memory operations.

Integrates store, index, retrieval, relationships, and lifecycle.
"""

from __future__ import annotations

import time
from typing import Any

from aurora.memory.schemas import (
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    MemoryVersion,
    MemorySearchResult,
    WorkingMemory,
    RelationshipType,
    generate_memory_id,
)
from aurora.memory.store import MemoryStore
from aurora.memory.index import MemoryIndex
from aurora.memory.retrieval import MemoryRetriever
from aurora.memory.relationships import MemoryRelationshipGraph, MemoryRelationship


class MemoryManager:
    """
    Orchestrates all memory operations.

    Provides:
    - Create/update/archive memory records
    - Build and maintain index
    - Retrieve with ranking
    - Manage relationships
    - Working memory for current session
    - Export for reproducibility
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store
        self._index = MemoryIndex()
        self._retriever = MemoryRetriever(self._index)
        self._relationships = MemoryRelationshipGraph()
        self._working: WorkingMemory | None = None
        self._build_index()

    def _build_index(self) -> None:
        """Build index from store on initialization."""
        for record in self._store.list_all(limit=10000):
            self._index.add(record)

    # ── CRUD ───────────────────────────────────────────────────────────────

    def create(
        self,
        memory_type: MemoryType,
        domain: str,
        title: str,
        content: str,
        source: str,
        provenance: str,
        observed_at: float | None = None,
        confidence: float = 0.5,
        evidence_refs: list[str] | None = None,
        entity_refs: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """Create a new memory record."""
        now = time.time()
        record = MemoryRecord(
            memory_id=generate_memory_id(),
            memory_type=memory_type,
            domain=domain,
            title=title,
            content=content,
            source=source,
            provenance=provenance,
            created_at=now,
            observed_at=observed_at,
            updated_at=now,
            status=MemoryStatus.ACTIVE,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            entity_refs=entity_refs or [],
            tags=tags or [],
            metadata=metadata or {},
        )
        self._store.create(record)
        self._index.add(record)
        return record

    def get(self, memory_id: str) -> MemoryRecord | None:
        """Get a memory record by ID."""
        return self._store.get(memory_id)

    def update(self, record: MemoryRecord, change_reason: str = "") -> MemoryRecord:
        """Update a memory record (creates new version)."""
        record.change_reason = change_reason
        updated = self._store.update(record)
        self._index.remove(record.memory_id)
        self._index.add(updated)
        return updated

    def archive(self, memory_id: str) -> MemoryRecord | None:
        """Archive a memory record."""
        record = self._store.archive(memory_id)
        if record:
            self._index.remove(memory_id)
            self._index.add(record)
        return record

    def list_all(
        self,
        memory_type: MemoryType | None = None,
        domain: str | None = None,
        status: MemoryStatus | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """List memory records."""
        return self._store.list_all(
            memory_type=memory_type, domain=domain, status=status, limit=limit
        )

    # ── Retrieval ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        entity_id: str | None = None,
        domain: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 10,
    ) -> list[MemorySearchResult]:
        """Search and rank memory records."""
        results = self._retriever.retrieve(
            query=query, entity_id=entity_id, domain=domain, top_k=top_k
        )
        if memory_type:
            results = [r for r in results if r.memory.memory_type == memory_type]
        return results

    def retrieve_for_reasoning(
        self,
        query: str,
        domain: str = "general",
        entity_id: str | None = None,
        top_k: int = 5,
    ) -> list[MemoryRecord]:
        """Retrieve memory for LLM reasoning context."""
        results = self._retriever.retrieve(
            query=query, entity_id=entity_id, domain=domain, top_k=top_k
        )
        return [r.memory for r in results]

    # ── Relationships ──────────────────────────────────────────────────────

    def link(
        self,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
        description: str = "",
    ) -> None:
        """Create a relationship between two memories."""
        import uuid
        rel = MemoryRelationship(
            relationship_id=f"rel-{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            description=description,
        )
        self._relationships.add(rel)

    def get_relationships(self, memory_id: str) -> list[MemoryRelationship]:
        """Get all relationships for a memory."""
        return self._relationships.get_all(memory_id)

    def find_conflicts(self) -> list[tuple[MemoryRelationship, MemoryRelationship]]:
        """Find contradictory relationships."""
        return self._relationships.find_contradictions()

    # ── Versions ───────────────────────────────────────────────────────────

    def get_versions(self, memory_id: str) -> list[MemoryVersion]:
        """Get version history for a memory."""
        return self._store.get_versions(memory_id)

    # ── Working Memory ─────────────────────────────────────────────────────

    def start_session(self, query: str = "", domain: str = "general") -> WorkingMemory:
        """Start a new working memory session."""
        import uuid
        self._working = WorkingMemory(
            session_id=f"ws-{uuid.uuid4().hex[:8]}",
            user_query=query,
            domain=domain,
        )
        return self._working

    def get_working(self) -> WorkingMemory | None:
        """Get current working memory."""
        return self._working

    def update_working(self, **kwargs: Any) -> WorkingMemory:
        """Update current working memory."""
        if self._working is None:
            self.start_session()
        for key, value in kwargs.items():
            if hasattr(self._working, key):
                setattr(self._working, key, value)
        self._working.updated_at = time.time()
        return self._working

    def promote_working(self, memory_type: MemoryType = MemoryType.EPISODIC) -> MemoryRecord | None:
        """Promote working memory to permanent memory."""
        if self._working is None:
            return None

        content_parts = []
        if self._working.user_query:
            content_parts.append(f"Query: {self._working.user_query}")
        if self._working.unresolved_questions:
            content_parts.append(f"Unresolved: {'; '.join(self._working.unresolved_questions)}")

        if not content_parts:
            return None

        return self.create(
            memory_type=memory_type,
            domain=self._working.domain,
            title=f"Session: {self._working.user_query[:50] or 'Investigation'}",
            content="\n".join(content_parts),
            source="working_memory_promotion",
            provenance=f"session:{self._working.session_id}",
            entity_refs=[e.entity_id for e in self._working.entities],
            tags=["promoted_from_working"],
        )

    # ── Export ─────────────────────────────────────────────────────────────

    def export(self) -> dict[str, Any]:
        """Export all memory data."""
        return self._store.export_all()

    # ── Stats ──────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        all_records = self.list_all(limit=10000)
        by_type = {}
        by_domain = {}
        by_status = {}
        for r in all_records:
            by_type[r.memory_type.value] = by_type.get(r.memory_type.value, 0) + 1
            by_domain[r.domain] = by_domain.get(r.domain, 0) + 1
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        return {
            "total": len(all_records),
            "by_type": by_type,
            "by_domain": by_domain,
            "by_status": by_status,
            "index_size": self._index.size(),
            "relationship_count": len(self._relationships._edges),
        }
