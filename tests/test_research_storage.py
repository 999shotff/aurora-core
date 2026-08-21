import hashlib
import json
from pathlib import Path

from aurora.research.claims import ResearchClaim
from aurora.research.formulas import ResearchFormula
from aurora.research.graph import GraphNode, ResearchKnowledgeGraph
from aurora.research.hypotheses import ResearchHypothesis
from aurora.research.models import ResearchDocument, ResearchSource
from aurora.research.storage import ResearchStorage


def _source() -> ResearchSource:
    return ResearchSource(
        source_path="/test/doc.pdf",
        sha256=hashlib.sha256(b"test").hexdigest(),
        source_type="pdf",
        size_bytes=1024,
        filename="doc.pdf",
    )


def test_storage_save_load_document(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    doc = ResearchDocument(document_id="doc_001", source=_source(), page_count=2)
    store.save_document(doc)
    loaded = store.load_document("doc_001")
    assert loaded is not None
    assert loaded.document_id == "doc_001"


def test_storage_load_missing_document(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    assert store.load_document("missing") is None


def test_storage_save_load_claim(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    claim = ResearchClaim(
        claim_id="claim_001", document_id="doc_001", page=1,
        source_text="test", normalized_text="test", claim_type="definition",
    )
    store.save_claim(claim)
    loaded = store.load_claim("claim_001")
    assert loaded is not None
    assert loaded.claim_id == "claim_001"


def test_storage_list_claims(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    for i in range(3):
        store.save_claim(ResearchClaim(
            claim_id=f"claim_{i:03d}", document_id="doc_001", page=1,
            source_text="test", normalized_text="test", claim_type="observation",
        ))
    assert store.list_claims() == ["claim_000", "claim_001", "claim_002"]


def test_storage_save_load_hypothesis(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    hyp = ResearchHypothesis(
        hypothesis_id="hyp_001", source_claim_id="claim_001",
        document_id="doc_001", methodology="gann",
    )
    store.save_hypothesis(hyp)
    loaded = store.load_hypothesis("hyp_001")
    assert loaded is not None
    assert loaded.methodology == "gann"


def test_storage_list_hypotheses(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    store.save_hypothesis(ResearchHypothesis(
        hypothesis_id="hyp_a", source_claim_id="c", document_id="d", methodology="x",
    ))
    assert store.list_hypotheses() == ["hyp_a"]


def test_storage_save_load_formula(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    f = ResearchFormula(
        formula_id="form_001", source_claim_id="claim_001",
        document_id="doc_001", expression="SMA(close, 20)", page=1,
    )
    store.save_formula(f)
    loaded = store.load_formula("form_001")
    assert loaded is not None
    assert loaded.expression == "SMA(close, 20)"


def test_storage_list_formulas(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    store.save_formula(ResearchFormula(
        formula_id="f1", source_claim_id="c", document_id="d", expression="x", page=1,
    ))
    assert store.list_formulas() == ["f1"]


def test_storage_save_load_graph(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    g = ResearchKnowledgeGraph()
    g.add_node(GraphNode(node_id="n1", node_type="document"))
    store.save_graph(g)
    loaded = store.load_graph()
    assert "n1" in loaded.nodes


def test_storage_load_empty_graph(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    g = store.load_graph()
    assert len(g.nodes) == 0


def test_storage_save_load_index(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    store.save_index({"version": "1.0", "count": 5})
    loaded = store.load_index()
    assert loaded["version"] == "1.0"
    assert loaded["count"] == 5


def test_storage_deterministic_json(tmp_path: Path):
    store = ResearchStorage(tmp_path)
    doc = ResearchDocument(document_id="doc_001", source=_source(), page_count=1)
    store.save_document(doc)
    path = tmp_path / "documents" / "doc_001.json"
    data = json.loads(path.read_text())
    assert data["document_id"] == "doc_001"
    assert "sha256" in data["source"]
