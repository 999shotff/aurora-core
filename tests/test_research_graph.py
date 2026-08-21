import pytest

from aurora.research.graph import (
    GraphEdge,
    GraphNode,
    ResearchKnowledgeGraph,
)


def _make_graph() -> ResearchKnowledgeGraph:
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="doc_1", node_type="document", label="Doc 1"))
    g.add_node(GraphNode(node_id="page_1", node_type="page", label="Page 1"))
    g.add_node(GraphNode(node_id="claim_1", node_type="claim", label="Claim 1"))
    g.add_node(GraphNode(node_id="hyp_1", node_type="hypothesis", label="Hyp 1"))
    g.add_edge(GraphEdge(source_id="doc_1", target_id="page_1", relationship="contains"))
    g.add_edge(GraphEdge(source_id="page_1", target_id="claim_1", relationship="extracted_from"))
    g.add_edge(GraphEdge(source_id="claim_1", target_id="hyp_1", relationship="derived_from"))
    return g


def test_graph_add_node():
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="n1", node_type="document"))
    assert "n1" in g.nodes


def test_graph_add_edge():
    g = _make_graph()
    assert len(g.edges) == 3


def test_graph_edge_missing_source():
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="n1", node_type="document"))
    with pytest.raises(KeyError, match="source node not found"):
        g.add_edge(GraphEdge(source_id="missing", target_id="n1", relationship="contains"))


def test_graph_edge_missing_target():
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="n1", node_type="document"))
    with pytest.raises(KeyError, match="target node not found"):
        g.add_edge(GraphEdge(source_id="n1", target_id="missing", relationship="contains"))


def test_graph_get_edges_from():
    g = _make_graph()
    edges = g.get_edges_from("doc_1")
    assert len(edges) == 1
    assert edges[0].relationship == "contains"


def test_graph_get_edges_to():
    g = _make_graph()
    edges = g.get_edges_to("claim_1")
    assert len(edges) == 1
    assert edges[0].relationship == "extracted_from"


def test_graph_neighbors():
    g = _make_graph()
    neighbors = g.get_neighbors("page_1")
    assert "doc_1" in neighbors
    assert "claim_1" in neighbors


def test_graph_nodes_by_type():
    g = _make_graph()
    claims = g.get_nodes_by_type("claim")
    assert len(claims) == 1
    assert claims[0].node_id == "claim_1"


def test_graph_no_orphans():
    g = _make_graph()
    assert g.has_orphan_nodes() == []


def test_graph_has_orphans():
    g = _make_graph()
    g.add_node(GraphNode(node_id="orphan", node_type="claim"))
    assert "orphan" in g.has_orphan_nodes()


def test_graph_trace_lineage():
    g = _make_graph()
    lineage = g.trace_lineage("hyp_1")
    assert len(lineage) == 3
    source_ids = {e.source_id for e in lineage}
    assert "claim_1" in source_ids
    assert "page_1" in source_ids
    assert "doc_1" in source_ids


def test_graph_relationship_types():
    for rel in ["supports", "contradicts", "defines", "depends_on", "derived_from", "tested_by", "contains", "extracted_from"]:
        g = ResearchKnowledgeGraph()
        g.add_node(GraphNode(node_id="a", node_type="document"))
        g.add_node(GraphNode(node_id="b", node_type="claim"))
        g.add_edge(GraphEdge(source_id="a", target_id="b", relationship=rel))  # type: ignore[arg-type]
        assert len(g.edges) == 1
