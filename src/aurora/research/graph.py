from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

RelationshipType = Literal[
    "supports",
    "contradicts",
    "defines",
    "depends_on",
    "derived_from",
    "tested_by",
    "contains",
    "extracted_from",
]

NodeType = Literal[
    "document",
    "page",
    "section",
    "paragraph",
    "table",
    "claim",
    "hypothesis",
    "formula",
    "feature",
    "historical_test",
    "result",
]


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    node_type: NodeType
    label: str = ""


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    target_id: str
    relationship: RelationshipType
    weight: float = 1.0
    metadata: dict[str, str | int | float | bool] = {}


class ResearchKnowledgeGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.source_id not in self.nodes:
            raise KeyError(f"source node not found: {edge.source_id}")
        if edge.target_id not in self.nodes:
            raise KeyError(f"target node not found: {edge.target_id}")
        self.edges.append(edge)

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def get_neighbors(self, node_id: str) -> list[str]:
        targets = {e.target_id for e in self.edges if e.source_id == node_id}
        sources = {e.source_id for e in self.edges if e.target_id == node_id}
        return sorted(targets | sources)

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def has_orphan_nodes(self) -> list[str]:
        connected = set()
        for e in self.edges:
            connected.add(e.source_id)
            connected.add(e.target_id)
        return sorted(nid for nid in self.nodes if nid not in connected)

    def trace_lineage(self, node_id: str) -> list[GraphEdge]:
        visited: set[str] = set()
        result: list[GraphEdge] = []
        stack = [node_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for e in self.get_edges_to(current):
                result.append(e)
                stack.append(e.source_id)
        return result
