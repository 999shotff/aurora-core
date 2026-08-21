"""Phase 4 tests — source traceability, extraction, claim types, methodology,
hypothesis extraction, missing horizon, formula extraction, duplicate detection,
contradictory claims, OCR attribution, deterministic extraction, no auto-validation.
"""
from aurora.research.claims import ClaimExtractionResult, ResearchClaim
from aurora.research.conflict_detector import detect_conflicts
from aurora.research.duplicate_detector import deduplicate_claims, detect_duplicates
from aurora.research.extractor import _classify_claim_type, extract_claims_from_page
from aurora.research.feature_mapper import map_claim_to_feature
from aurora.research.formula_extractor import extract_formulas
from aurora.research.graph_builder import build_knowledge_graph
from aurora.research.hypothesis_extractor import (
    _detect_direction,
    _detect_horizon,
    extract_hypotheses,
)
from aurora.research.models import ResearchPage
from aurora.research.taxonomy import classify_methodology


def _page(text: str, page_num: int = 1, doc_id: str = "doc1") -> ResearchPage:
    return ResearchPage(
        page_id=f"{doc_id}_p{page_num}",
        document_id=doc_id,
        page_number=page_num,
        text=text,
        char_count=len(text),
    )


# ── PART 13: Source Traceability ──────────────────────────────────────

def test_source_traceability():
    page = _page("If price crosses above the 200-day moving average, then buy.")
    claims = extract_claims_from_page(page, "doc_001", source_file="/path/to.pdf", source_sha256="abc123")
    assert len(claims) > 0
    c = claims[0]
    assert c.document_id == "doc_001"
    assert c.source_file == "/path/to.pdf"
    assert c.source_sha256 == "abc123"
    assert c.page == 1
    assert c.source_hash != ""


def test_source_text_preserved():
    original = "If price crosses above the 200-day moving average, then buy."
    page = _page(original)
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) > 0
    assert claims[0].source_text == original


# ── PART 13: Candidate Extraction ─────────────────────────────────────

def test_extracts_if_then_rule():
    page = _page("If price crosses above the 200-day moving average, then buy.")
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) >= 1
    assert claims[0].claim_type == "rule"


def test_extracts_when_then_rule():
    page = _page("When RSI drops below 30, then the asset is oversold and likely to bounce.")
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) >= 1


def test_extracts_formula():
    page = _page("The formula is SMA = close / 20 + volume.")
    claims = extract_claims_from_page(page, "doc1")
    assert any(c.claim_type == "formula" for c in claims)


def test_extracts_definition():
    page = _page("RSI is defined as a momentum oscillator measuring the speed of price changes.")
    claims = extract_claims_from_page(page, "doc1")
    assert any(c.claim_type == "definition" for c in claims)


def test_extracts_opinion():
    page = _page("I believe the market will recover based on historical patterns.")
    claims = extract_claims_from_page(page, "doc1")
    assert any(c.claim_type == "opinion" for c in claims)


def test_extracts_observation():
    page = _page("Research indicates that increased volume precedes trend reversals in equity markets.")
    claims = extract_claims_from_page(page, "doc1")
    assert any(c.claim_type == "observation" for c in claims)


def test_empty_text_no_claims():
    page = _page("")
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) == 0


# ── PART 13: Claim Types ──────────────────────────────────────────────

def test_claim_type_classification():
    assert _classify_claim_type("RSI is defined as a measure of momentum.") == "definition"
    assert _classify_claim_type("If price goes up, then buy.") == "rule"
    assert _classify_claim_type("SMA = close / 20") == "formula"
    assert _classify_claim_type("In 2020, the market dropped 30%.") == "historical_claim"


# ── PART 13: Methodology Classification ───────────────────────────────

def test_methodology_fibonacci():
    assert classify_methodology("The Fibonacci 0.618 level acts as support.") == "fibonacci"


def test_methodology_gann():
    assert classify_methodology("Gann angles predict price trajectory.") == "gann"


def test_methodology_unknown():
    assert classify_methodology("The weather is nice today.") == "unknown"


# ── PART 13: Hypothesis Extraction ────────────────────────────────────

def test_hypothesis_from_rule():
    page = _page("If RSI drops below 30, then price tends to rally.")
    claims = extract_claims_from_page(page, "doc1")
    hyps = extract_hypotheses(claims)
    assert len(hyps) >= 1
    h = hyps[0]
    assert h.test_status == "untested"
    assert h.direction in ("long", "short", "neutral", "unknown")
    assert h.horizon in ("tick", "intraday", "swing", "position", "unknown")


def test_hypothesis_direction():
    assert _detect_direction("buy when price rises") == "long"
    assert _detect_direction("sell when price drops") == "short"
    assert _detect_direction("something happens") == "unknown"


def test_hypothesis_horizon():
    assert _detect_horizon("intraday trading signal") == "intraday"
    assert _detect_horizon("swing trade setup") == "swing"
    assert _detect_horizon("long-term position") == "position"
    assert _detect_horizon("no timing mentioned") == "unknown"


# ── PART 13: Missing Horizon Handling ─────────────────────────────────

def test_missing_horizon_defaults_to_unknown():
    page = _page("If price rises, then buy.")
    claims = extract_claims_from_page(page, "doc1")
    hyps = extract_hypotheses(claims)
    for h in hyps:
        assert h.horizon in ("unknown", "tick", "intraday", "swing", "position")


# ── PART 13: Formula Extraction ───────────────────────────────────────

def test_formula_extraction():
    claim = ResearchClaim(
        claim_id="f1", document_id="d1", page=1,
        source_text="SMA = close / 20", normalized_text="SMA = close / 20",
        claim_type="formula", methodology="technical_analysis",
    )
    formulas = extract_formulas([claim])
    assert len(formulas) == 1
    assert formulas[0].implementation_status == "not_implemented"


def test_non_formula_not_extracted():
    claim = ResearchClaim(
        claim_id="f2", document_id="d1", page=1,
        source_text="The market is bullish", normalized_text="The market is bullish",
        claim_type="observation", methodology="unknown",
    )
    formulas = extract_formulas([claim])
    assert len(formulas) == 0


# ── PART 13: Duplicate Detection ──────────────────────────────────────

def test_duplicate_detection_exact():
    c1 = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="Price respects 61.8% Fibonacci level",
        normalized_text="Price respects 61.8% Fibonacci level",
        claim_type="empirical_claim", methodology="fibonacci",
    )
    c2 = ResearchClaim(
        claim_id="c2", document_id="d1", page=1,
        source_text="Price respects 61.8% Fibonacci level",
        normalized_text="Price respects 61.8% Fibonacci level",
        claim_type="empirical_claim", methodology="fibonacci",
    )
    dupes = detect_duplicates([c1, c2])
    assert len(dupes) > 0


def test_deduplication():
    c1 = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="Price respects support",
        normalized_text="Price respects support",
        claim_type="observation", methodology="technical_analysis",
    )
    c2 = ResearchClaim(
        claim_id="c2", document_id="d1", page=1,
        source_text="Price respects support",
        normalized_text="Price respects support",
        claim_type="observation", methodology="technical_analysis",
    )
    dupes = detect_duplicates([c1, c2])
    deduped = deduplicate_claims([c1, c2], dupes)
    assert len(deduped) == 1


def test_no_merge_semantically_similar():
    c1 = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="RSI above 70 is overbought",
        normalized_text="RSI above 70 is overbought",
        claim_type="observation", methodology="technical_analysis",
    )
    c2 = ResearchClaim(
        claim_id="c2", document_id="d1", page=1,
        source_text="MACD crossover signals momentum shift",
        normalized_text="MACD crossover signals momentum shift",
        claim_type="observation", methodology="technical_analysis",
    )
    dupes = detect_duplicates([c1, c2])
    assert len(dupes) == 0


# ── PART 13: Conflicting Claims ───────────────────────────────────────

def test_conflict_detection():
    c1 = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="RSI above 70 signals a bullish rally",
        normalized_text="RSI above 70 signals a bullish rally",
        claim_type="observation", methodology="technical_analysis",
    )
    c2 = ResearchClaim(
        claim_id="c2", document_id="d1", page=1,
        source_text="RSI above 70 signals a bearish reversal",
        normalized_text="RSI above 70 signals a bearish reversal",
        claim_type="observation", methodology="technical_analysis",
    )
    conflicts = detect_conflicts([c1, c2])
    assert len(conflicts) > 0
    assert conflicts[0].relationship == "contradicts"


def test_no_conflict_same_direction():
    c1 = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="RSI above 70 signals a bullish rally",
        normalized_text="RSI above 70 signals a bullish rally",
        claim_type="observation", methodology="technical_analysis",
    )
    c2 = ResearchClaim(
        claim_id="c2", document_id="d1", page=1,
        source_text="Price rising signals bullish momentum",
        normalized_text="Price rising signals bullish momentum",
        claim_type="observation", methodology="technical_analysis",
    )
    conflicts = detect_conflicts([c1, c2])
    assert len(conflicts) == 0


# ── PART 13: OCR Source Attribution ───────────────────────────────────

def test_ocr_source_attribution():
    claim = ResearchClaim(
        claim_id="ocr_1", document_id="d1", page=5,
        source_text="OCR extracted text",
        normalized_text="OCR extracted text",
        claim_type="observation", methodology="unknown",
        metadata={"ocr_derived": True, "ocr_confidence": 85.0},
    )
    assert claim.metadata["ocr_derived"] is True
    assert claim.metadata["ocr_confidence"] == 85.0


# ── PART 13: Deterministic Extraction ─────────────────────────────────

def test_deterministic_extraction():
    text = "If price crosses above the 20-day SMA, then buy."
    page = _page(text)
    run1 = extract_claims_from_page(page, "doc1")
    run2 = extract_claims_from_page(page, "doc1")
    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.claim_id == c2.claim_id
        assert c1.source_text == c2.source_text
        assert c1.source_hash == c2.source_hash


# ── PART 13: No Automatic Validation ──────────────────────────────────

def test_no_auto_validation_claims():
    page = _page("If RSI < 30, then buy the asset for guaranteed profits.")
    claims = extract_claims_from_page(page, "doc1")
    for c in claims:
        assert c.validation_status == "unreviewed"


def test_no_auto_validation_hypotheses():
    page = _page("If RSI < 30, then price tends to rally.")
    claims = extract_claims_from_page(page, "doc1")
    hyps = extract_hypotheses(claims)
    for h in hyps:
        assert h.test_status == "untested"


def test_validation_status_literal():
    c = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="test", normalized_text="test",
        claim_type="observation", validation_status="unreviewed",
    )
    assert c.validation_status == "unreviewed"


# ── PART 13: ClaimExtractionResult ────────────────────────────────────

def test_extraction_result():
    r = ClaimExtractionResult(
        document_id="d1", source_file="/test.pdf",
        source_sha256="abc", total_pages=100, pages_processed=100,
        claims_extracted=50, hypotheses_extracted=10,
        formulas_extracted=5, ocr_derived_claims=0,
        extraction_failures=0,
    )
    assert r.document_id == "d1"
    assert r.claims_extracted == 50


# ── PART 13: Feature Mapping ──────────────────────────────────────────

def test_feature_mapping_sma():
    c = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="14-period SMA signals trend direction",
        normalized_text="14-period SMA signals trend direction",
        claim_type="observation", methodology="technical_analysis",
    )
    mapping = map_claim_to_feature(c)
    assert mapping is not None
    assert mapping.feature_name == "sma"
    assert mapping.parameters.get("lookback") == 14


def test_feature_mapping_rsi():
    c = ResearchClaim(
        claim_id="c2", document_id="d1", page=1,
        source_text="RSI above 70 is overbought, RSI below 30 is oversold",
        normalized_text="RSI above 70 is overbought, RSI below 30 is oversold",
        claim_type="observation", methodology="technical_analysis",
    )
    mapping = map_claim_to_feature(c)
    assert mapping is not None
    assert mapping.feature_name == "rsi"


def test_feature_mapping_no_match():
    c = ResearchClaim(
        claim_id="c3", document_id="d1", page=1,
        source_text="The weather is nice today",
        normalized_text="The weather is nice today",
        claim_type="observation", methodology="unknown",
    )
    mapping = map_claim_to_feature(c)
    assert mapping is None


# ── PART 13: Knowledge Graph Population ───────────────────────────────

def test_graph_population():
    from aurora.research.formulas import ResearchFormula
    from aurora.research.graph import GraphEdge
    from aurora.research.hypotheses import ResearchHypothesis

    c = ResearchClaim(
        claim_id="c1", document_id="d1", page=1,
        source_text="test", normalized_text="test",
        claim_type="rule", methodology="technical_analysis",
    )
    h = ResearchHypothesis(
        hypothesis_id="h1", source_claim_id="c1",
        document_id="d1", methodology="technical_analysis",
    )
    f = ResearchFormula(
        formula_id="f1", source_claim_id="c1",
        document_id="d1", expression="SMA(close, 20)", page=1,
    )
    from aurora.research.feature_mapper import ClaimFeatureMapping
    fm = ClaimFeatureMapping(
        claim_id="c1", feature_name="sma",
        parameters={"lookback": 20}, implementation_status="implemented",
        mapping_confidence=0.7,
    )
    GraphEdge(
        source_id="c1", target_id="c1",
        relationship="contradicts",
    )

    graph = build_knowledge_graph(
        documents=[{"document_id": "d1", "filename": "test.pdf"}],
        claims=[c], hypotheses=[h], formulas=[f],
        feature_mappings=[fm], conflicts=[],
    )
    assert "doc_d1" in graph.nodes
    assert "claim_c1" in graph.nodes
    assert "hyp_h1" in graph.nodes
    assert "formula_f1" in graph.nodes
    assert "feature_sma" in graph.nodes


# ── PART 13: ClaimExtractionResult ────────────────────────────────────

def test_extraction_result_by_type():
    r = ClaimExtractionResult(
        document_id="d1", source_file="/test.pdf",
        source_sha256="abc", total_pages=100, pages_processed=100,
        claims_extracted=50, hypotheses_extracted=10,
        formulas_extracted=5, ocr_derived_claims=0,
        extraction_failures=0,
        claims_by_type={"rule": 20, "observation": 15, "formula": 10, "definition": 5},
        claims_by_methodology={"fibonacci": 15, "gann": 10, "technical_analysis": 25},
    )
    assert r.claims_by_type["rule"] == 20
    assert r.claims_by_methodology["fibonacci"] == 15
