
from aurora.research.claims import ResearchClaim


def test_claim_basic():
    claim = ResearchClaim(
        claim_id="claim_001",
        document_id="doc_001",
        page=1,
        source_text="Price respects support levels",
        normalized_text="Price respects support levels",
        claim_type="observation",
        methodology="market_structure",
    )
    assert claim.claim_id == "claim_001"
    assert claim.claim_type == "observation"
    assert claim.validation_status == "unreviewed"


def test_claim_all_types():
    for ct in ["definition", "observation", "hypothesis", "rule", "formula", "empirical_claim", "opinion", "historical_claim"]:
        claim = ResearchClaim(
            claim_id=f"c_{ct}",
            document_id="doc_001",
            page=1,
            source_text="test",
            normalized_text="test",
            claim_type=ct,  # type: ignore[arg-type]
        )
        assert claim.claim_type == ct


def test_claim_source_traceability():
    claim = ResearchClaim(
        claim_id="gann_001",
        document_id="doc_001",
        page=42,
        source_text="The Law of Vibration governs price movement",
        normalized_text="The Law of Vibration governs price movement",
        claim_type="hypothesis",
        methodology="gann",
        char_offset_start=100,
        char_offset_end=200,
    )
    assert claim.page == 42
    assert claim.char_offset_start == 100
    assert claim.char_offset_end == 200
    assert claim.document_id == "doc_001"


def test_claim_serialization_round_trip():
    claim = ResearchClaim(
        claim_id="claim_001",
        document_id="doc_001",
        page=1,
        source_text="test",
        normalized_text="test",
        claim_type="definition",
    )
    data = claim.model_dump()
    restored = ResearchClaim.model_validate(data)
    assert restored.claim_id == claim.claim_id
    assert restored.source_text == claim.source_text


def test_claim_no_orphan():
    claim = ResearchClaim(
        claim_id="claim_001",
        document_id="doc_001",
        page=1,
        source_text="test",
        normalized_text="test",
        claim_type="observation",
    )
    assert claim.document_id != ""
    assert claim.claim_id != ""
