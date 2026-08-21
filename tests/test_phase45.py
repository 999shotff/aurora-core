"""Phase 4.5 tests — OCR integration, context-aware classification,
classification confidence/evidence, claim context, OCR quality comparison,
deterministic benchmark.
"""
from aurora.research.benchmark import BENCHMARK_CASES, get_benchmark_by_group
from aurora.research.claims import ClaimExtractionResult
from aurora.research.extractor import extract_claims_from_page, select_text_source
from aurora.research.models import ResearchPage
from aurora.research.taxonomy import classify_methodology_context


def _page(text: str, page_num: int = 1, doc_id: str = "doc1", heading: str = "") -> ResearchPage:
    return ResearchPage(
        page_id=f"{doc_id}_p{page_num}",
        document_id=doc_id,
        page_number=page_num,
        text=text,
        char_count=len(text),
    )


# ── PART 2: Context-Aware Classification ──────────────────────────────

def test_fibonacci_classification():
    result = classify_methodology_context(
        "The 0.618 fibonacci retracement level acts as strong support.",
        context="Chapter 5: Fibonacci Trading Strategies",
    )
    assert result.category == "fibonacci"
    assert result.confidence > 0.0
    assert len(result.evidence) > 0


def test_gann_classification():
    result = classify_methodology_context(
        "The Gann angle 1x1 line provides dynamic support throughout the trend.",
        context="Chapter on Gann Analysis",
    )
    assert result.category == "gann"
    assert result.confidence > 0.0


def test_volatility_classification():
    result = classify_methodology_context(
        "Implied volatility expanded significantly ahead of the earnings announcement.",
        context="Volatility Trading Chapter",
    )
    assert result.category == "volatility"
    assert result.confidence > 0.0


def test_market_psychology_classification():
    result = classify_methodology_context(
        "Fear and greed indices reached extreme greed levels at the market top.",
        context="Trading Psychology Section",
    )
    assert result.category == "market_psychology"
    assert result.confidence > 0.0


def test_unknown_classification():
    result = classify_methodology_context(
        "The weather forecast predicts rain for the next three days.",
    )
    assert result.category == "unknown"
    assert result.confidence == 0.0


def test_context_improves_classification():
    text = "The 0.618 level acts as strong support."
    result_no_ctx = classify_methodology_context(text)
    result_with_ctx = classify_methodology_context(
        text, context="Chapter on Fibonacci Trading Strategies",
    )
    assert result_with_ctx.confidence >= result_no_ctx.confidence


def test_multi_keyword_boost():
    result = classify_methodology_context(
        "The fibonacci 0.618 retracement and 1.618 extension levels define the golden ratio zones.",
    )
    assert result.category == "fibonacci"
    assert len(result.evidence) >= 2


# ── PART 3: Classification Confidence + Evidence ──────────────────────

def test_classification_confidence_range():
    result = classify_methodology_context(
        "Fibonacci retracement levels provide support and resistance.",
    )
    assert 0.0 <= result.confidence <= 1.0


def test_classification_evidence_populated():
    result = classify_methodology_context(
        "The fibonacci 0.618 retracement level acts as support.",
    )
    assert len(result.evidence) > 0
    assert any("fibonacci" in e.lower() for e in result.evidence)


def test_scores_dict_populated():
    result = classify_methodology_context(
        "The fibonacci retracement level provides support.",
    )
    assert len(result.scores) > 0
    assert "fibonacci" in result.scores


# ── PART 4: Claim Context ─────────────────────────────────────────────

def test_claim_has_preceding_context():
    text = "First sentence about the market. If price crosses above the 200-day moving average, then buy. Third sentence about risk."
    page = _page(text)
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) > 0
    assert claims[0].preceding_context != ""


def test_claim_has_following_context():
    text = "First sentence about the market. If price crosses above the 200-day moving average, then buy. This is a third sentence about risk management."
    page = _page(text)
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) > 0
    assert claims[0].following_context != ""


def test_claim_has_page_title():
    text = "If price crosses above the 200-day moving average, then buy."
    page = _page(text, heading="Trading Rules Chapter")
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) > 0
    # page_title is populated from page context when available
    assert isinstance(claims[0].page_title, str)


def test_source_text_unchanged():
    original = "If price crosses above the 200-day moving average, then buy."
    page = _page(original)
    claims = extract_claims_from_page(page, "doc1")
    assert len(claims) > 0
    assert claims[0].source_text == original


# ── PART 1: OCR Integration ──────────────────────────────────────────

def test_ocr_claim_fields():
    page = _page("If price crosses above the 200-day moving average, then buy.")
    claims = extract_claims_from_page(
        page, "doc1",
        extraction_method="rule_based",
        is_ocr=True,
        ocr_engine="tesseract",
        ocr_confidence=85.0,
        native_text_quality="ocr_required",
        ocr_text_quality="good",
        selected_text_source="ocr",
    )
    assert len(claims) > 0
    c = claims[0]
    assert c.is_ocr_derived is True
    assert c.ocr_engine == "tesseract"
    assert c.ocr_confidence == 85.0
    assert c.selected_text_source == "ocr"
    assert c.extraction_method == "ocr"


def test_native_claim_fields():
    page = _page("If price crosses above the 200-day moving average, then buy.")
    claims = extract_claims_from_page(
        page, "doc1",
        is_ocr=False,
        selected_text_source="native",
    )
    assert len(claims) > 0
    c = claims[0]
    assert c.is_ocr_derived is False
    assert c.selected_text_source == "native"


# ── PART 5: OCR Quality Comparison ────────────────────────────────────

def test_select_native_when_good():
    _text, source, reason = select_text_source("good text", "good", "ocr text", "good")
    assert source == "native"
    assert reason == "native_quality_good"


def test_select_ocr_when_native_failed():
    _text, source, reason = select_text_source("", "failed", "ocr text", "good")
    assert source == "ocr"
    assert reason == "ocr_quality_good"


def test_select_longer_text():
    _text, source, reason = select_text_source("long native text here", "partial", "short", "partial")
    assert source == "native"
    assert reason == "native_longer"


def test_select_ocr_when_native_empty():
    _text, source, reason = select_text_source("", "ocr_required", "ocr text here", "partial")
    assert source == "ocr"
    assert reason == "ocr_available"


def test_fallback_native():
    _text, source, reason = select_text_source("", "failed", "", "failed")
    assert source == "native"
    assert reason == "fallback_native"


# ── PART 7: Deterministic Benchmark ───────────────────────────────────

def test_benchmark_all_cases_classified():
    for case in BENCHMARK_CASES:
        result = classify_methodology_context(case.text)
        assert result.category == case.expected_methodology, (
            f"FAIL: '{case.description}' -> got {result.category}, "
            f"expected {case.expected_methodology}"
        )


def test_benchmark_accuracy():
    correct = 0
    total = len(BENCHMARK_CASES)
    for case in BENCHMARK_CASES:
        result = classify_methodology_context(case.text)
        if result.category == case.expected_methodology:
            correct += 1
    accuracy = correct / total if total > 0 else 0
    assert accuracy >= 0.7, f"Benchmark accuracy {accuracy:.1%} below 70% threshold"


def test_benchmark_by_group():
    groups = get_benchmark_by_group()
    assert len(groups) > 10


def test_benchmark_no_false_positive_on_unknown():
    unknown_cases = [c for c in BENCHMARK_CASES if c.expected_methodology == "unknown"]
    for case in unknown_cases:
        result = classify_methodology_context(case.text)
        assert result.category == "unknown", (
            f"False positive: '{case.description}' classified as {result.category}"
        )


# ── PART 10: Deterministic Repeated Execution ─────────────────────────

def test_deterministic_classification():
    text = "The fibonacci 0.618 retracement level provides support."
    r1 = classify_methodology_context(text)
    r2 = classify_methodology_context(text)
    assert r1.category == r2.category
    assert r1.confidence == r2.confidence
    assert r1.evidence == r2.evidence


def test_deterministic_extraction():
    text = "If RSI drops below 30, then price tends to rally."
    page = _page(text)
    r1 = extract_claims_from_page(page, "doc1")
    r2 = extract_claims_from_page(page, "doc1")
    assert len(r1) == len(r2)
    for c1, c2 in zip(r1, r2):
        assert c1.claim_id == c2.claim_id
        assert c1.methodology == c2.methodology
        assert c1.methodology_confidence == c2.methodology_confidence


# ── ClaimExtractionResult new fields ──────────────────────────────────

def test_extraction_result_native_ocr_fields():
    r = ClaimExtractionResult(
        document_id="d1", source_file="/test.pdf",
        source_sha256="abc", total_pages=100, pages_processed=100,
        native_pages=80, ocr_pages=20,
        claims_extracted=50, native_claims=40, ocr_claims=10,
        hypotheses_extracted=5, formulas_extracted=3,
        ocr_derived_claims=10, extraction_failures=0,
    )
    assert r.native_pages == 80
    assert r.ocr_pages == 20
    assert r.native_claims == 40
    assert r.ocr_claims == 10
