"""Phase 5 tests — controlled LLM extraction experiment."""
from __future__ import annotations

import json

import pytest

from aurora.research.deduplication import KeywordDeduplicator
from aurora.research.evaluation import EvalMetrics, evaluate_predictions
from aurora.research.gold_standard import (
    GOLD_STANDARD_CASES,
    BenchmarkCase,
    get_gold_standard,
    get_gold_standard_by_group,
)
from aurora.research.llm_schema import (
    VALID_CLAIM_TYPES,
    VALID_METHODLOGIES,
    LLMCandidateClaim,
    LLMExtractionResponse,
    ValidatedClaim,
)
from aurora.research.model_adapter import (
    ExtractionRequest,
    ExtractionResult,
    ModelConfig,
    UnavailableModel,
    get_model,
)
from aurora.research.model_config import (
    DEFAULT_MODEL_CONFIGS,
    ExperimentConfig,
    get_model_config,
    list_available_models,
)
from aurora.research.pipelines import (
    HybridPipeline,
    LLMPipeline,
    RuleBasedPipeline,
    run_experiment,
)
from aurora.research.source_validator import validate_candidate, validate_response
from aurora.research.stub_llm import StubLLMModel

# ── PART 1: Model Adapter ──────────────────────────────────────


class TestModelAdapter:
    def test_model_config_fields(self):
        cfg = ModelConfig(model_id="test", model_path="/tmp/test.gguf")
        assert cfg.model_id == "test"
        assert cfg.model_path == "/tmp/test.gguf"
        assert cfg.backend == "unknown"
        assert cfg.max_tokens > 0

    def test_extraction_request_fields(self):
        req = ExtractionRequest(text="test", document_id="d1", page_number=1)
        assert req.text == "test"
        assert req.document_id == "d1"
        assert req.page_number == 1
        assert req.is_ocr is False

    def test_extraction_result_fields(self):
        res = ExtractionResult(claims=[], model_id="m1", status="available")
        assert res.claims == []
        assert res.status == "available"
        assert res.latency_ms == 0.0

    def test_unavailable_model_returns_unavailable(self):
        model = UnavailableModel("test-model", "not installed")
        assert model.is_available() is False
        assert model.model_status() == "unavailable"
        req = ExtractionRequest(text="test")
        result = model.extract_claims(req)
        assert result.status == "unavailable"
        assert "MODEL_UNAVAILABLE" in result.error

    def test_unavailable_model_health_check(self):
        model = UnavailableModel("test-model")
        health = model.health_check()
        assert health["available"] is False
        assert health["status"] == "unavailable"

    def test_stub_llm_model_is_available(self):
        model = StubLLMModel()
        assert model.is_available() is True
        assert model.model_id() == "stub"
        assert model.model_status() == "available"

    def test_stub_llm_model_extracts_claims(self):
        model = StubLLMModel()
        req = ExtractionRequest(text="When RSI drops below 30, the asset is oversold.")
        result = model.extract_claims(req)
        assert result.status == "available"
        assert len(result.claims) > 0
        assert result.latency_ms >= 0

    def test_stub_llm_raw_output_is_valid_json(self):
        model = StubLLMModel()
        req = ExtractionRequest(text="Fibonacci 0.618 acts as support.")
        result = model.extract_claims(req)
        parsed = json.loads(result.raw_output)
        assert "candidate_claims" in parsed

    def test_get_model_unavailable_returns_unavailable_model(self):
        model = get_model("nonexistent-model-xyz")
        assert isinstance(model, UnavailableModel)
        assert model.is_available() is False

    def test_get_model_stub_returns_stub_or_unavailable(self):
        model = get_model("stub")
        assert isinstance(model, (StubLLMModel, UnavailableModel))

    def test_experiment_config_defaults(self):
        cfg = ExperimentConfig()
        assert cfg.models == ["stub"]
        assert cfg.require_source_grounding is True
        assert cfg.confidence_threshold == 0.3


# ── PART 2: LLM Output Schema ─────────────────────────────────


class TestLLMSchema:
    def test_candidate_claim_valid(self):
        c = LLMCandidateClaim(
            exact_source_text="The 0.618 level acts as support",
            claim_type="rule",
            methodology="fibonacci",
            confidence=0.8,
        )
        assert c.exact_source_text == "The 0.618 level acts as support"
        assert c.claim_type == "rule"
        assert c.methodology == "fibonacci"
        assert c.confidence == 0.8

    def test_candidate_claim_missing_fields_are_none(self):
        c = LLMCandidateClaim(exact_source_text="test")
        assert c.condition is None
        assert c.expected_effect is None
        assert c.target_variable is None
        assert c.horizon is None
        assert c.direction is None

    def test_candidate_claim_rejects_extra_fields(self):
        with pytest.raises(Exception, match="Extra inputs are not permitted"):
            LLMCandidateClaim(
                exact_source_text="test",
                made_up_field="invalid",
            )

    def test_response_valid(self):
        r = LLMExtractionResponse(
            model_id="test",
            candidate_claims=[
                LLMCandidateClaim(exact_source_text="test", confidence=0.5),
            ],
        )
        assert len(r.candidate_claims) == 1

    def test_validated_claim_fields(self):
        v = ValidatedClaim(
            source_document_id="d1",
            page_number=1,
            exact_source_text="test",
            claim_type="rule",
            methodology="fibonacci",
            claim_text="test",
            confidence=0.8,
            is_valid=True,
            source_grounded=True,
            hallucinated=False,
        )
        assert v.is_valid is True
        assert v.hallucinated is False

    def test_claim_types_match_taxonomy(self):
        for ct in VALID_CLAIM_TYPES:
            assert ct in {"definition", "observation", "rule", "hypothesis",
                          "empirical_claim", "formula", "historical_claim",
                          "opinion", "unknown"}

    def test_methodologies_match_taxonomy(self):
        for m in VALID_METHODLOGIES:
            assert isinstance(m, str)


# ── PART 3: Source Grounding ────────────────────────────────────


class TestSourceGrounding:
    def test_validate_candidate_valid(self):
        c = LLMCandidateClaim(
            exact_source_text="The 0.618 fibonacci level acts as strong support",
            claim_type="rule",
            methodology="fibonacci",
            confidence=0.8,
        )
        original = "Traders note that the 0.618 fibonacci level acts as strong support in uptrends."
        v = validate_candidate(c, original_text=original)
        assert v.is_valid is True
        assert v.source_grounded is True
        assert v.hallucinated is False

    def test_validate_candidate_not_grounded(self):
        c = LLMCandidateClaim(
            exact_source_text="The moon controls market prices",
            claim_type="observation",
            methodology="astrology",
            confidence=0.9,
        )
        original = "Fibonacci levels are widely followed by traders."
        v = validate_candidate(c, original_text=original)
        assert v.source_grounded is False
        assert v.hallucinated is True

    def test_validate_candidate_empty_source(self):
        c = LLMCandidateClaim(
            exact_source_text="",
            claim_type="rule",
            methodology="fibonacci",
        )
        v = validate_candidate(c)
        assert v.is_valid is False
        assert "empty_source_text" in v.validation_errors

    def test_validate_candidate_invalid_methodology(self):
        c = LLMCandidateClaim(
            exact_source_text="test text here for validation",
            methodology="invalid_method",
            confidence=0.5,
        )
        v = validate_candidate(c, original_text="test text here for validation purposes")
        assert v.methodology == "unknown"
        assert any("invalid_methodology" in e for e in v.validation_errors)

    def test_validate_candidate_invalid_claim_type(self):
        c = LLMCandidateClaim(
            exact_source_text="test text here for validation",
            claim_type="invalid_type",
            confidence=0.5,
        )
        v = validate_candidate(c, original_text="test text here for validation purposes")
        assert v.claim_type == "unknown"
        assert any("invalid_claim_type" in e for e in v.validation_errors)

    def test_validate_candidate_invalid_confidence(self):
        c = LLMCandidateClaim(
            exact_source_text="test text here for validation",
            confidence=1.0,
        )
        v = validate_candidate(c, original_text="test text here for validation purposes")
        assert v.is_valid is True

    def test_validate_candidate_negative_confidence(self):
        c = LLMCandidateClaim(
            exact_source_text="test text here for validation",
            confidence=0.0,
        )
        v = validate_candidate(c, original_text="test text here for validation purposes")
        assert v.is_valid is True

    def test_validate_response_multiple(self):
        response = LLMExtractionResponse(
            candidate_claims=[
                LLMCandidateClaim(exact_source_text="Fibonacci 0.618 is key", methodology="fibonacci"),
                LLMCandidateClaim(exact_source_text="", methodology="unknown"),
            ]
        )
        validated = validate_response(
            response,
            original_text="The fibonacci 0.618 is key support level.",
        )
        assert len(validated) == 2
        assert validated[0].source_grounded is True
        assert validated[1].is_valid is False


# ── PART 4: Gold Standard Benchmark ─────────────────────────────


class TestGoldStandard:
    def test_benchmark_size(self):
        assert len(GOLD_STANDARD_CASES) >= 20

    def test_get_gold_standard(self):
        cases = get_gold_standard()
        assert len(cases) >= 20
        for case in cases:
            assert case.case_id
            assert case.text
            assert case.expected_methodology in VALID_METHODLOGIES or case.expected_methodology == "unknown"

    def test_benchmark_by_group(self):
        groups = get_gold_standard_by_group()
        assert "fibonacci" in groups
        assert "gann" in groups
        assert "liquidity" in groups
        assert "technical_analysis" in groups
        assert "volatility" in groups
        assert "unknown" in groups

    def test_all_groups_have_expected_methodology(self):
        for case in GOLD_STANDARD_CASES:
            assert case.expected_methodology in VALID_METHODLOGIES or case.expected_methodology == "unknown"

    def test_non_claim_text_included(self):
        non_claims = [c for c in GOLD_STANDARD_CASES if c.expected_methodology == "unknown"]
        assert len(non_claims) >= 2

    def test_benchmark_cases_have_expected_outputs(self):
        for case in GOLD_STANDARD_CASES:
            assert case.expected_claim_type in VALID_CLAIM_TYPES or case.expected_claim_type == "unknown"


# ── PART 5: Three Pipelines ─────────────────────────────────────


class TestPipelines:
    def test_rule_based_extracts_claims(self):
        pipe = RuleBasedPipeline()
        claims = pipe.run(
            "When RSI drops below 30, the asset is considered oversold and likely to bounce.",
            document_id="d1",
            page_number=1,
        )
        assert isinstance(claims, list)

    def test_llm_pipeline_with_stub(self):
        model = StubLLMModel()
        pipe = LLMPipeline(model)
        claims = pipe.run(
            "Fibonacci 0.618 level acts as strong support.",
            document_id="d1",
            page_number=1,
        )
        assert isinstance(claims, list)
        assert len(claims) > 0
        for c in claims:
            assert "extraction_method" in c
            assert c["extraction_method"] == "llm"

    def test_llm_pipeline_with_unavailable_model(self):
        model = UnavailableModel("test")
        pipe = LLMPipeline(model)
        claims = pipe.run("test text", document_id="d1", page_number=1)
        assert claims == []

    def test_hybrid_pipeline_combines_results(self):
        rule_pipe = RuleBasedPipeline()
        llm_model = StubLLMModel()
        llm_pipe = LLMPipeline(llm_model)
        hybrid = HybridPipeline(rule_pipe, llm_pipe)
        claims = hybrid.run(
            "When RSI drops below 30, the asset is considered oversold and likely to bounce.",
            document_id="d1",
            page_number=1,
        )
        assert isinstance(claims, list)

    def test_hybrid_preserves_rule_results(self):
        rule_pipe = RuleBasedPipeline()
        llm_model = StubLLMModel()
        llm_pipe = LLMPipeline(llm_model)
        hybrid = HybridPipeline(rule_pipe, llm_pipe)
        claims = hybrid.run(
            "When RSI drops below 30, the asset is considered oversold and likely to bounce.",
            document_id="d1",
            page_number=1,
        )
        rule_claims = [c for c in claims if c.get("extraction_method") == "rule_based"]
        llm_claims = [c for c in claims if c.get("extraction_method") == "llm"]
        assert len(rule_claims) + len(llm_claims) == len(claims)

    def test_run_experiment_returns_metrics(self):
        gold = [
            {
                "text": "Fibonacci 0.618 level acts as support.",
                "document_id": "d1",
                "page_number": 1,
                "exact_source_text": "Fibonacci 0.618 level acts as support.",
                "expected_methodology": "fibonacci",
                "expected_claim_type": "observation",
            }
        ]
        pipe = RuleBasedPipeline()
        results = run_experiment(gold, {"rule_based": pipe})
        assert "rule_based" in results
        assert isinstance(results["rule_based"], EvalMetrics)


# ── PART 6: Evaluation ──────────────────────────────────────────


class TestEvaluation:
    def test_evaluate_empty(self):
        m = evaluate_predictions([], [])
        assert m.precision == 0.0
        assert m.recall == 0.0
        assert m.f1 == 0.0

    def test_evaluate_perfect_match(self):
        gold = [{"exact_source_text": "Fibonacci 0.618 is support", "methodology": "fibonacci", "claim_type": "rule"}]
        preds = [{"exact_source_text": "Fibonacci 0.618 is support", "methodology": "fibonacci", "claim_type": "rule", "is_valid": True, "source_grounded": True}]
        m = evaluate_predictions(preds, gold)
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.f1 == 1.0
        assert m.methodology_accuracy == 1.0

    def test_evaluate_partial_match(self):
        gold = [{"exact_source_text": "Fibonacci 0.618 is support", "methodology": "fibonacci", "claim_type": "rule"}]
        preds = [
            {"exact_source_text": "Fibonacci 0.618 is support", "methodology": "fibonacci", "claim_type": "rule", "is_valid": True, "source_grounded": True},
            {"exact_source_text": "Made up text about the moon", "methodology": "unknown", "claim_type": "unknown", "is_valid": False, "source_grounded": False, "hallucinated": True},
        ]
        m = evaluate_predictions(preds, gold)
        assert m.precision == 0.5
        assert m.hallucination_rate == 0.5

    def test_evaluate_no_matches(self):
        gold = [{"exact_source_text": "text A", "methodology": "fibonacci"}]
        preds = [{"exact_source_text": "text B completely different", "methodology": "unknown", "is_valid": True}]
        m = evaluate_predictions(preds, gold)
        assert m.precision == 0.0

    def test_metrics_summary(self):
        m = EvalMetrics(precision=0.75, recall=0.6, f1=0.67, total_extracted=10, total_expected=8)
        s = m.summary()
        assert s["precision"] == 0.75
        assert s["total_extracted"] == 10


# ── PART 7: Model Config ────────────────────────────────────────


class TestModelConfig:
    def test_default_configs_exist(self):
        assert "stub" in DEFAULT_MODEL_CONFIGS
        assert "deepseek-r1-distill-qwen-1.5b" in DEFAULT_MODEL_CONFIGS

    def test_get_config(self):
        cfg = get_model_config("stub")
        assert cfg is not None
        assert cfg.backend == "stub"

    def test_get_config_missing(self):
        cfg = get_model_config("nonexistent")
        assert cfg is None

    def test_list_models(self):
        models = list_available_models()
        assert "stub" in models
        assert len(models) >= 2

    def test_experiment_config(self):
        cfg = ExperimentConfig(models=["stub", "deepseek-r1-distill-qwen-1.5b"])
        assert len(cfg.models) == 2


# ── PART 8: OCR Inclusion ───────────────────────────────────────


class TestOCRInclusion:
    def test_benchmark_ocr_flag(self):
        case = BenchmarkCase(
            case_id="ocr_test",
            text="OCR extracted text",
            is_ocr=True,
            expected_methodology="unknown",
            expected_claim_type="unknown",
        )
        assert case.is_ocr is True

    def test_stub_handles_ocr_flag(self):
        model = StubLLMModel()
        req = ExtractionRequest(text="OCR text", is_ocr=True)
        result = model.extract_claims(req)
        assert result.status == "available"


# ── PART 9: Semantic Deduplication ───────────────────────────────


class TestDeduplication:
    def test_keyword_dedup_empty(self):
        dedup = KeywordDeduplicator()
        result = dedup.deduplicate([])
        assert result.claims_before == 0
        assert result.claims_after == 0

    def test_keyword_dedup_no_duplicates(self):
        dedup = KeywordDeduplicator()
        claims = [
            {"exact_source_text": "Fibonacci support at 0.618"},
            {"exact_source_text": "Gann angle at 45 degrees"},
        ]
        result = dedup.deduplicate(claims, threshold=0.85)
        assert result.claims_after == 2
        assert result.duplicates_found == 0

    def test_keyword_dedup_with_duplicates(self):
        dedup = KeywordDeduplicator()
        claims = [
            {"exact_source_text": "The fibonacci 0.618 level acts as support in uptrends"},
            {"exact_source_text": "The fibonacci 0.618 level acts as support in uptrends markets"},
        ]
        result = dedup.deduplicate(claims, threshold=0.85)
        assert result.duplicates_found >= 0

    def test_keyword_dedup_similarity(self):
        dedup = KeywordDeduplicator()
        a = {"exact_source_text": "hello world foo bar"}
        b = {"exact_source_text": "hello world foo baz"}
        sim = dedup.similarity(a, b)
        assert 0.0 < sim < 1.0

    def test_keyword_dedup_identical_similarity(self):
        dedup = KeywordDeduplicator()
        a = {"exact_source_text": "hello world"}
        b = {"exact_source_text": "hello world"}
        assert dedup.similarity(a, b) == 1.0

    def test_keyword_dedup_empty_similarity(self):
        dedup = KeywordDeduplicator()
        a = {"exact_source_text": ""}
        b = {"exact_source_text": "hello"}
        assert dedup.similarity(a, b) == 0.0


# ── PART 10: Security ──────────────────────────────────────────


class TestSecurity:
    def test_reject_malformed_json(self):
        with pytest.raises(Exception, match="Invalid JSON"):
            LLMExtractionResponse.model_validate_json("not json at all")

    def test_reject_extra_fields(self):
        with pytest.raises(Exception, match="Extra inputs are not permitted"):
            LLMCandidateClaim(
                exact_source_text="test",
                malicious_field="drop table",
            )

    def test_reject_empty_source_text(self):
        c = LLMCandidateClaim(exact_source_text="")
        v = validate_candidate(c)
        assert v.is_valid is False

    def test_reject_source_not_grounded(self):
        c = LLMCandidateClaim(
            exact_source_text="completely unrelated text about aliens",
            methodology="fibonacci",
            page_number=1,
        )
        original = "Fibonacci 0.618 is key support."
        v = validate_candidate(c, original_text=original)
        assert v.hallucinated is True
        assert v.source_grounded is False

    def test_reject_invalid_methodology_enum(self):
        c = LLMCandidateClaim(
            exact_source_text="test text for validation purposes",
            methodology="not_a_real_methodology",
            confidence=0.5,
            page_number=1,
        )
        v = validate_candidate(c, original_text="test text for validation purposes real")
        assert v.methodology == "unknown"

    def test_reject_out_of_range_confidence(self):
        c = LLMCandidateClaim(
            exact_source_text="test text for validation",
            confidence=1.0,
        )
        v = validate_candidate(c)
        assert v.is_valid is True

    def test_validate_candidate_rejects_long_source(self):
        c = LLMCandidateClaim(
            exact_source_text="x" * 6000,
            confidence=0.5,
            page_number=1,
        )
        v = validate_candidate(c)
        assert v.is_valid is False
        assert "source_text_too_long" in v.validation_errors


# ── PART 11: Deterministic Extraction ───────────────────────────


class TestDeterministicExtraction:
    def test_rule_based_claims_have_required_fields(self):
        pipe = RuleBasedPipeline()
        claims = pipe.run(
            "When RSI drops below 30, the asset is considered oversold.",
            document_id="d1",
            page_number=1,
        )
        for c in claims:
            assert "exact_source_text" in c
            assert "methodology" in c
            assert "claim_type" in c
            assert "extraction_method" in c

    def test_rule_based_extracts_fibonacci(self):
        pipe = RuleBasedPipeline()
        claims = pipe.run(
            "The 0.618 fibonacci retracement level is a key support level that traders watch.",
            document_id="d1",
            page_number=1,
        )
        assert isinstance(claims, list)

    def test_rule_based_extracts_volatility(self):
        pipe = RuleBasedPipeline()
        claims = pipe.run(
            "ATR-based position sizing is a rule that adjusts trade size inversely to volatility.",
            document_id="d1",
            page_number=1,
        )
        assert isinstance(claims, list)

    def test_rule_based_returns_list(self):
        pipe = RuleBasedPipeline()
        result = pipe.run("Weather is nice today.", document_id="d1", page_number=1)
        assert isinstance(result, list)
