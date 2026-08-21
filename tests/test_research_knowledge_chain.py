import hashlib

from aurora.research.claims import ResearchClaim
from aurora.research.formulas import ResearchFormula
from aurora.research.graph import GraphEdge, GraphNode, ResearchKnowledgeGraph
from aurora.research.hypotheses import ResearchHypothesis
from aurora.research.models import ResearchDocument, ResearchSource


def _source() -> ResearchSource:
    return ResearchSource(
        source_path="/test/doc.pdf",
        sha256=hashlib.sha256(b"test").hexdigest(),
        source_type="pdf",
        size_bytes=1024,
        filename="doc.pdf",
    )


def test_full_knowledge_chain():
    doc = ResearchDocument(document_id="doc_001", source=_source(), page_count=5)
    claim = ResearchClaim(
        claim_id="claim_001", document_id="doc_001", page=1,
        source_text="Price respects 61.8% retracement",
        normalized_text="Price respects 61.8% retracement",
        claim_type="empirical_claim", methodology="fibonacci",
    )
    hyp = ResearchHypothesis(
        hypothesis_id="hyp_001", source_claim_id="claim_001",
        document_id="doc_001", methodology="fibonacci",
        condition="price reaches 61.8% retracement",
        expected_effect="bounce to next extension",
        target_variable="price", direction="long", horizon="swing",
    )
    formula = ResearchFormula(
        formula_id="form_001", source_claim_id="claim_001",
        document_id="doc_001", expression="retracement = (high - low) * 0.618 + low",
        page=1,
    )
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="doc_001", node_type="document", label="Fib Book"))
    g.add_node(GraphNode(node_id="claim_001", node_type="claim", label="61.8% claim"))
    g.add_node(GraphNode(node_id="hyp_001", node_type="hypothesis", label="Bounce hypothesis"))
    g.add_node(GraphNode(node_id="form_001", node_type="formula", label="Retracement formula"))
    g.add_edge(GraphEdge(source_id="doc_001", target_id="claim_001", relationship="contains"))
    g.add_edge(GraphEdge(source_id="claim_001", target_id="hyp_001", relationship="derived_from"))
    g.add_edge(GraphEdge(source_id="claim_001", target_id="form_001", relationship="defines"))

    assert doc.document_id == "doc_001"
    assert claim.document_id == "doc_001"
    assert hyp.source_claim_id == "claim_001"
    assert formula.source_claim_id == "claim_001"

    lineage = g.trace_lineage("hyp_001")
    assert len(lineage) == 2

    assert g.has_orphan_nodes() == []


def test_no_orphan_claims():
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="doc_1", node_type="document"))
    g.add_node(GraphNode(node_id="claim_1", node_type="claim"))
    g.add_edge(GraphEdge(source_id="doc_1", target_id="claim_1", relationship="contains"))
    assert g.has_orphan_nodes() == []


def test_orphan_detection():
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="doc_1", node_type="document"))
    g.add_node(GraphNode(node_id="claim_1", node_type="claim"))
    g.add_node(GraphNode(node_id="orphan_1", node_type="claim"))
    g.add_edge(GraphEdge(source_id="doc_1", target_id="claim_1", relationship="contains"))
    orphans = g.has_orphan_nodes()
    assert "orphan_1" in orphans
    assert "doc_1" not in orphans
    assert "claim_1" not in orphans


def test_claim_traceability():
    claim = ResearchClaim(
        claim_id="gann_001",
        document_id="doc_001",
        page=42,
        source_text="The Law of Vibration governs price",
        normalized_text="The Law of Vibration governs price",
        claim_type="hypothesis",
        methodology="gann",
    )
    assert claim.document_id == "doc_001"
    assert claim.page == 42
    assert claim.methodology == "gann"


def test_hypothesis_starts_untested():
    hyp = ResearchHypothesis(
        hypothesis_id="hyp_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        methodology="astrology",
    )
    assert hyp.test_status == "untested"
    assert hyp.methodology == "astrology"
