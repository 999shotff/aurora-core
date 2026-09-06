"""
Evidence Graph for LLM-2 Grounded Intelligence.

Tracks relationships between evidence items:
- SUPPORTS: evidence corroborates another
- CONTRADICTS: evidence conflicts with another
- DERIVED_FROM: evidence was computed from another
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """Types of evidence relationships."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DERIVED_FROM = "DERIVED_FROM"


class EvidenceRelationship(BaseModel):
    """A directed relationship between two evidence items."""

    model_config = {"extra": "forbid"}

    source_id: str = Field(description="Evidence ID of the source")
    target_id: str = Field(description="Evidence ID of the target")
    relationship: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    description: str = Field(default="")
    created_at: float = Field(default_factory=time.time)


class EvidenceNode(BaseModel):
    """A node in the evidence graph."""

    model_config = {"extra": "forbid"}

    evidence_id: str
    tool_name: str = Field(description="Tool that produced this evidence")
    evidence_type: str = Field(default="observation")
    data_summary: str = Field(default="")
    source_refs: list[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class EvidenceGraph:
    """
    Lightweight evidence graph with relationship tracking.

    Stores nodes (evidence items) and edges (relationships).
    Provides queries for evidence chains and contradiction detection.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        self._edges: list[EvidenceRelationship] = []

    def add_node(self, node: EvidenceNode) -> None:
        """Add an evidence node to the graph."""
        self._nodes[node.evidence_id] = node

    def add_relationship(self, relationship: EvidenceRelationship) -> None:
        """Add a relationship between evidence items."""
        # Validate both nodes exist
        if relationship.source_id not in self._nodes:
            raise ValueError(f"Source evidence '{relationship.source_id}' not in graph")
        if relationship.target_id not in self._nodes:
            raise ValueError(f"Target evidence '{relationship.target_id}' not in graph")
        self._edges.append(relationship)

    def get_node(self, evidence_id: str) -> EvidenceNode | None:
        """Get an evidence node by ID."""
        return self._nodes.get(evidence_id)

    def get_relationships(
        self,
        evidence_id: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[EvidenceRelationship]:
        """Get all relationships involving an evidence item."""
        return [
            e
            for e in self._edges
            if (e.source_id == evidence_id or e.target_id == evidence_id)
            and (relationship_type is None or e.relationship == relationship_type)
        ]

    def find_contradictions(self) -> list[tuple[EvidenceRelationship, EvidenceRelationship]]:
        """
        Find evidence pairs that contradict each other.

        Returns pairs of relationships where A CONTRADICTS B and B CONTRADICTS A.
        """
        contradictions: list[tuple[EvidenceRelationship, EvidenceRelationship]] = []

        # Build lookup for contradiction edges: (source, target) -> edge
        contradiction_edges: dict[tuple[str, str], EvidenceRelationship] = {}
        for edge in self._edges:
            if edge.relationship == RelationshipType.CONTRADICTS:
                contradiction_edges[(edge.source_id, edge.target_id)] = edge

        # Check for mutual contradictions
        seen: set[tuple[str, str]] = set()
        for (src, tgt), edge1 in contradiction_edges.items():
            reverse = (tgt, src)
            if reverse in contradiction_edges and reverse not in seen:
                edge2 = contradiction_edges[reverse]
                contradictions.append((edge1, edge2))
                seen.add((src, tgt))
                seen.add(reverse)

        return contradictions

    def get_evidence_chain(
        self, evidence_id: str, max_depth: int = 5
    ) -> list[EvidenceNode]:
        """
        Get the chain of evidence that led to a given item.

        Follows DERIVED_FROM relationships backward.
        """
        chain: list[EvidenceNode] = []
        visited: set[str] = set()

        def _traverse(eid: str, depth: int) -> None:
            if depth >= max_depth or eid in visited:
                return
            visited.add(eid)

            node = self._nodes.get(eid)
            if node:
                chain.append(node)

            for edge in self._edges:
                if edge.target_id == eid and edge.relationship == RelationshipType.DERIVED_FROM:
                    _traverse(edge.source_id, depth + 1)

        _traverse(evidence_id, 0)
        return chain

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "nodes": [n.model_dump() for n in self._nodes.values()],
            "edges": [e.model_dump() for e in self._edges],
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "contradiction_count": len(self.find_contradictions()),
        }

    def summary(self) -> str:
        """Human-readable graph summary."""
        contradictions = self.find_contradictions()
        lines = [
            f"Evidence Graph: {len(self._nodes)} nodes, {len(self._edges)} edges",
            f"Contradictions: {len(contradictions)}",
        ]

        # Show relationship type breakdown
        by_type: dict[str, int] = {}
        for edge in self._edges:
            by_type[edge.relationship.value] = by_type.get(edge.relationship.value, 0) + 1
        for rtype, count in sorted(by_type.items()):
            lines.append(f"  {rtype}: {count}")

        return "\n".join(lines)
