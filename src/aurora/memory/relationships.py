"""
LLM-3: Memory Relationship Graph — typed relationships between memories.

Extends the Evidence Graph pattern from src/aurora/ai/evidence_graph.py.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field

from aurora.memory.schemas import RelationshipType


class MemoryRelationship(BaseModel):
    """A typed relationship between two memory records."""

    model_config = {"extra": "forbid"}

    relationship_id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    description: str = ""
    created_at: float = Field(default_factory=time.time)


class MemoryRelationshipGraph:
    """
    Graph of typed relationships between memory records.

    Provides:
    - Add/remove relationships
    - Query by source/target
    - Contradiction detection
    - Relationship chain traversal
    """

    def __init__(self) -> None:
        self._edges: list[MemoryRelationship] = []

    def add(self, relationship: MemoryRelationship) -> None:
        """Add a relationship."""
        self._edges.append(relationship)

    def remove(self, relationship_id: str) -> bool:
        """Remove a relationship by ID."""
        for i, edge in enumerate(self._edges):
            if edge.relationship_id == relationship_id:
                self._edges.pop(i)
                return True
        return False

    def get_outgoing(
        self, source_id: str, relationship_type: RelationshipType | None = None
    ) -> list[MemoryRelationship]:
        """Get outgoing relationships from a memory."""
        return [
            e
            for e in self._edges
            if e.source_id == source_id
            and (relationship_type is None or e.relationship == relationship_type)
        ]

    def get_incoming(
        self, target_id: str, relationship_type: RelationshipType | None = None
    ) -> list[MemoryRelationship]:
        """Get incoming relationships to a memory."""
        return [
            e
            for e in self._edges
            if e.target_id == target_id
            and (relationship_type is None or e.relationship == relationship_type)
        ]

    def get_all(self, memory_id: str) -> list[MemoryRelationship]:
        """Get all relationships involving a memory."""
        return [
            e for e in self._edges
            if e.source_id == memory_id or e.target_id == memory_id
        ]

    def find_contradictions(self) -> list[tuple[MemoryRelationship, MemoryRelationship]]:
        """Find mutual contradictions."""
        contradictions: list[tuple[MemoryRelationship, MemoryRelationship]] = []
        contradiction_edges: dict[tuple[str, str], MemoryRelationship] = {}
        for edge in self._edges:
            if edge.relationship == RelationshipType.CONTRADICTS:
                contradiction_edges[(edge.source_id, edge.target_id)] = edge

        seen: set[tuple[str, str]] = set()
        for (src, tgt), edge1 in contradiction_edges.items():
            reverse = (tgt, src)
            if reverse in contradiction_edges and reverse not in seen:
                edge2 = contradiction_edges[reverse]
                contradictions.append((edge1, edge2))
                seen.add((src, tgt))
                seen.add(reverse)

        return contradictions

    def get_chain(
        self, memory_id: str, relationship_type: RelationshipType, max_depth: int = 5
    ) -> list[str]:
        """Traverse a relationship chain from a memory."""
        chain: list[str] = []
        visited: set[str] = set()

        def _traverse(mid: str, depth: int) -> None:
            if depth >= max_depth or mid in visited:
                return
            visited.add(mid)
            chain.append(mid)
            for edge in self._edges:
                if edge.source_id == mid and edge.relationship == relationship_type:
                    _traverse(edge.target_id, depth + 1)

        _traverse(memory_id, 0)
        return chain

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph."""
        return {
            "edges": [e.model_dump() for e in self._edges],
            "edge_count": len(self._edges),
        }

    def summary(self) -> str:
        """Human-readable summary."""
        by_type: dict[str, int] = {}
        for edge in self._edges:
            by_type[edge.relationship.value] = by_type.get(edge.relationship.value, 0) + 1
        lines = [f"Memory Relationships: {len(self._edges)} edges"]
        for rtype, count in sorted(by_type.items()):
            lines.append(f"  {rtype}: {count}")
        return "\n".join(lines)
