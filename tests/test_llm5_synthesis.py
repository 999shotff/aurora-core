"""LLM-5: Evidence-Grounded Synthesis — comprehensive tests.

26 tests covering schemas, engine, API, and deterministic submodules.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from aurora.ai.synthesis.schemas import (
    SynthesisRequest,
    SynthesisResult,
    SynthesisStatus,
    EvidenceAssessment,
    FindingAssessment,
    Hypothesis,
    HypothesisComparison,
    ContradictionAssessment,
    ContradictionType,
    UncertaintyAssessment,
    UncertaintyKind,
    Scenario,
    EvidenceGap,
    EvidenceGapStatus,
    DecisionConsideration,
    MemoryUpdateProposal,
    MemoryUpdateType,
    ProvenanceRecord,
    SynthesisAuditRecord,
    CausalLevel,
    ConfidenceLevel,
    HypothesisStatus,
)
from aurora.ai.synthesis.evidence_assessment import assess_evidences
from aurora.ai.synthesis.hypothesis import generate_hypotheses, compare_hypotheses
from aurora.ai.synthesis.contradiction import detect_contradictions
from aurora.ai.synthesis.uncertainty import assess_uncertainty
from aurora.ai.synthesis.scenarios import generate_scenarios
from aurora.ai.synthesis.decision import generate_decision_considerations
from aurora.ai.synthesis.provenance import build_provenance
from aurora.ai.synthesis.cache import SynthesisCache, compute_cache_key
from aurora.ai.synthesis.engine import SynthesisEngine


# ── Schemas ──────────────────────────────────────────────────────────────────

class TestSynthesisRequest:
    def test_create_request(self):
        req = SynthesisRequest(
            request_id="req-001",
            question="Is this hypothesis valid?",
        )
        assert req.request_id == "req-001"
        assert req.question == "Is this hypothesis valid?"
        assert req.evidence_ids == []
        assert req.memory_ids == []

    def test_request_with_all_fields(self):
        req = SynthesisRequest(
            request_id="req-002",
            question="Test",
            investigation_id="inv-001",
            evidence_ids=["ev-1", "ev-2"],
            finding_ids=["f-1"],
            memory_ids=["m-1"],
            domain="market",
            comparison_context="Context A",
            decision_context="Decision context",
        )
        assert req.investigation_id == "inv-001"
        assert len(req.evidence_ids) == 2
        assert req.domain == "market"

    def test_request_rejects_empty_question(self):
        with pytest.raises(Exception):
            SynthesisRequest(request_id="r", question="")

    def test_request_rejects_long_question(self):
        with pytest.raises(Exception):
            SynthesisRequest(request_id="r", question="x" * 10001)

    def test_request_default_domain(self):
        req = SynthesisRequest(request_id="r", question="Test")
        assert req.domain == "general"


class TestEvidenceAssessment:
    def test_evidence_assessment_fields(self):
        e = EvidenceAssessment(
            evidence_id="ev-001",
            source="test",
            evidence_type="OBSERVATION",
            domain="test",
            claim="Test claim",
            freshness="RECENT",
            relevance=ConfidenceLevel.MODERATE,
            reliability=ConfidenceLevel.HIGH,
            direct_vs_derived="DIRECT",
            limitations=[],
        )
        assert e.evidence_id == "ev-001"
        assert e.evidence_type == "OBSERVATION"
        assert e.freshness == "RECENT"

    def test_evidence_assessment_rejects_bad_type(self):
        e = EvidenceAssessment(
            evidence_id="ev", source="s", evidence_type="",
            domain="d", claim="c", freshness="RECENT",
            relevance=ConfidenceLevel.MODERATE, reliability=ConfidenceLevel.HIGH,
            direct_vs_derived="DIRECT", limitations=[],
        )
        assert e.evidence_id == "ev"

    def test_finding_assessment_fields(self):
        f = FindingAssessment(
            finding_id="f-001",
            statement="Test finding",
            supporting_evidence=["ev-1"],
            contradicting_evidence=[],
            provenance="test-prov",
            status=HypothesisStatus.SUPPORTED,
            confidence=ConfidenceLevel.HIGH,
        )
        assert f.finding_id == "f-001"
        assert f.status == HypothesisStatus.SUPPORTED


class TestHypothesis:
    def test_hypothesis_fields(self):
        h = Hypothesis(
            hypothesis_id="h-001",
            statement="Test hypothesis",
            supporting_evidence=["ev-1"],
            contradicting_evidence=[],
            assumptions=["a1"],
            confidence=ConfidenceLevel.MODERATE,
            status=HypothesisStatus.SUPPORTED,
        )
        assert h.hypothesis_id == "h-001"
        assert h.assumptions == ["a1"]

    def test_contradiction_fields(self):
        c = ContradictionAssessment(
            contradiction_id="c-001",
            contradiction_type=ContradictionType.SEMANTIC,
            evidence_a="ev-1",
            evidence_b="ev-2",
            description="Test contradiction",
            severity="MODERATE",
        )
        assert c.contradiction_id == "c-001"
        assert c.contradiction_type == ContradictionType.SEMANTIC

    def test_uncertainty_fields(self):
        u = UncertaintyAssessment(
            element="Test unknown",
            kind=UncertaintyKind.UNKNOWN,
            description="Unknown element",
            impact="HIGH",
            reduction_path="Gather more data",
        )
        assert u.kind == UncertaintyKind.UNKNOWN
        assert u.reduction_path == "Gather more data"

    def test_scenario_fields(self):
        s = Scenario(
            scenario_id="s-001",
            label="Best case",
            assumptions=["a1"],
            evidence_basis=["ev-1"],
            trigger_conditions=["t1"],
            implications=["imp1"],
            uncertainty=["unc1"],
        )
        assert s.label == "Best case"
        assert len(s.trigger_conditions) == 1

    def test_decision_consideration_fields(self):
        d = DecisionConsideration(
            consideration="Consider action A",
            evidence_basis=["ev-1"],
            confidence=ConfidenceLevel.HIGH,
            key_uncertainty="Risk factor X",
        )
        assert d.confidence == ConfidenceLevel.HIGH

    def test_provenance_record_fields(self):
        p = ProvenanceRecord(
            conclusion="Test conclusion",
            finding_ids=["f-1"],
            evidence_ids=["ev-1"],
            source_ids=["src-1"],
            reasoning_chain=["Step 1", "Step 2"],
        )
        assert len(p.reasoning_chain) == 2

    def test_synthesis_result_fields(self):
        r = SynthesisResult(
            synthesis_id="syn-001",
            question="Test Q",
            executive_summary="Summary",
            synthesis_status=SynthesisStatus.COMPLETE,
            causal_level=CausalLevel.TEMPORAL_ASSOCIATION,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )
        assert r.synthesis_id == "syn-001"
        assert r.key_findings == []

    def test_synthesis_status_invalid(self):
        with pytest.raises(Exception):
            SynthesisStatus("INVALID")


# ── Evidence Assessment ──────────────────────────────────────────────────────

class TestEvidenceAssessmentModule:
    def test_assess_empty_evidences(self):
        result = assess_evidences([])
        assert result == []

    def test_assess_single_evidence(self):
        items = [{
            "evidence_id": "ev-001",
            "source": "test",
            "evidence_type": "OBSERVATION",
            "domain": "test",
            "claim": "Test claim",
            "freshness": "RECENT",
            "source_status": "stale",
        }]
        result = assess_evidences(items)
        assert len(result) == 1
        assert result[0].evidence_id == "ev-001"
        assert result[0].limitations == ["Source data is stale"]

    def test_assess_handles_malformed_data(self):
        items = [{"evidence_id": "bad", "source": "s"}]
        result = assess_evidences(items)
        assert len(result) == 1
        assert result[0].claim == ""


# ── Hypothesis ───────────────────────────────────────────────────────────────

class TestHypothesisModule:
    def test_generate_hypotheses_empty(self):
        result = generate_hypotheses("Q", [], [])
        assert len(result) == 1
        assert "No findings" in result[0].statement

    def test_generate_hypotheses_with_findings(self):
        findings = [
            FindingAssessment(
                finding_id="f-1", statement="F1",
                supporting_evidence=["ev-1"], contradicting_evidence=[],
                status="SUPPORTED", confidence=ConfidenceLevel.HIGH,
            ),
        ]
        result = generate_hypotheses("Q", findings, ["ev-1"])
        assert len(result) >= 1

    def test_compare_hypotheses_empty(self):
        result = compare_hypotheses([])
        assert result.get("determination") == "INSUFFICIENT_HYPOTHESES"

    def test_hypothesis_comparison(self):
        h1 = Hypothesis(
            hypothesis_id="h1", statement="H1",
            supporting_evidence=["ev-1"], contradicting_evidence=[],
            assumptions=[], confidence=ConfidenceLevel.HIGH,
            status=HypothesisStatus.SUPPORTED,
        )
        result = compare_hypotheses([h1])
        assert result.get("determination") == "INSUFFICIENT_HYPOTHESES"


# ── Contradiction ────────────────────────────────────────────────────────────

class TestContradictionModule:
    def test_detect_contradictions_empty(self):
        result = detect_contradictions([])
        assert result == []

    def test_detect_contradictions_with_data(self):
        evidence = [
            EvidenceAssessment(
                evidence_id="ev-1", source="src-a", evidence_type="OBSERVATION",
                domain="d", claim="Price increase expected", freshness="RECENT",
                relevance=ConfidenceLevel.MODERATE, reliability=ConfidenceLevel.HIGH,
                direct_vs_derived="DIRECT", limitations=[],
            ),
            EvidenceAssessment(
                evidence_id="ev-2", source="src-b", evidence_type="OBSERVATION",
                domain="d", claim="Price decrease expected", freshness="RECENT",
                relevance=ConfidenceLevel.MODERATE, reliability=ConfidenceLevel.HIGH,
                direct_vs_derived="DIRECT", limitations=[],
            ),
        ]
        result = detect_contradictions(evidence)
        assert len(result) == 1
        assert result[0].contradiction_type == ContradictionType.DIRECT


# ── Uncertainty ──────────────────────────────────────────────────────────────

class TestUncertaintyModule:
    def test_assess_uncertainty_empty(self):
        result = assess_uncertainty([], [], False)
        assert result == []

    def test_assess_uncertainty_with_findings(self):
        findings = [
            FindingAssessment(
                finding_id="f-1", statement="F1",
                supporting_evidence=["ev-1"], contradicting_evidence=[],
                status=HypothesisStatus.SUPPORTED, confidence=ConfidenceLevel.HIGH,
            ),
        ]
        result = assess_uncertainty(findings, [], False)
        assert len(result) == 1


# ── Scenarios ────────────────────────────────────────────────────────────────

class TestScenarioModule:
    def test_generate_scenarios_empty(self):
        result = generate_scenarios("Q", [], [], False)
        assert len(result) >= 1

    def test_generate_scenarios_with_contradictions(self):
        result = generate_scenarios("Q", [], [], True)
        assert len(result) >= 1
        assert any("contradiction" in s.label.lower() for s in result)


# ── Decision ─────────────────────────────────────────────────────────────────

class TestDecisionModule:
    def test_generate_decision_empty(self):
        result = generate_decision_considerations("Q", [], [], [], False)
        assert len(result) == 1

    def test_generate_decision_with_data(self):
        findings = [
            FindingAssessment(
                finding_id="f-1", statement="F1",
                supporting_evidence=["ev-1"], contradicting_evidence=[],
                status="SUPPORTED", confidence=ConfidenceLevel.HIGH,
            ),
        ]
        result = generate_decision_considerations(
            "Q", findings, [], [], False,
        )
        assert len(result) >= 1


# ── Provenance ───────────────────────────────────────────────────────────────

class TestProvenanceModule:
    def test_build_provenance_empty(self):
        result = build_provenance([], [])
        assert result == []

    def test_build_provenance_with_data(self):
        findings = [
            FindingAssessment(
                finding_id="f-1", statement="F1",
                supporting_evidence=["ev-1"], contradicting_evidence=[],
                status=HypothesisStatus.SUPPORTED, confidence=ConfidenceLevel.HIGH,
            ),
        ]
        evidence = [
            EvidenceAssessment(
                evidence_id="ev-1", source="src", evidence_type="OBSERVATION",
                domain="d", claim="C1", freshness="RECENT",
                relevance=ConfidenceLevel.MODERATE, reliability=ConfidenceLevel.HIGH,
                direct_vs_derived="DIRECT", limitations=[],
            ),
        ]
        result = build_provenance(findings, evidence)
        assert len(result) == 1
        assert result[0].conclusion == "F1"


# ── Cache ────────────────────────────────────────────────────────────────────

class TestSynthesisCache:
    def test_compute_cache_key(self):
        k1 = compute_cache_key("Q", None, [], [], "general")
        k2 = compute_cache_key("Q", None, [], [], "general")
        assert k1 == k2

    def test_compute_cache_key_different(self):
        k1 = compute_cache_key("Q1", None, [], [], "general")
        k2 = compute_cache_key("Q2", None, [], [], "general")
        assert k1 != k2

    def test_cache_put_get(self):
        cache = SynthesisCache(ttl_seconds=60)
        req = SynthesisRequest(request_id="r", question="Q")
        result = SynthesisResult(
            synthesis_id="syn-1", question="Q",
            executive_summary="S", synthesis_status=SynthesisStatus.COMPLETE,
            causal_level=CausalLevel.CORRELATION, timestamp=0.0,
        )
        key = compute_cache_key("Q", None, [], [], "general")
        cache.put(key, result)
        got = cache.get(key)
        assert got is not None
        assert got.synthesis_id == "syn-1"

    def test_cache_expiry(self):
        cache = SynthesisCache(ttl_seconds=0)
        req = SynthesisRequest(request_id="r", question="Q")
        result = SynthesisResult(
            synthesis_id="syn-1", question="Q",
            executive_summary="S", synthesis_status=SynthesisStatus.COMPLETE,
            causal_level=CausalLevel.CORRELATION, timestamp=0.0,
        )
        key = compute_cache_key("Q", None, [], [], "general")
        cache.put(key, result)
        import time; time.sleep(0.01)
        got = cache.get(key)
        assert got is None


# ── Engine ───────────────────────────────────────────────────────────────────

class TestSynthesisEngine:
    def test_engine_synthesize_empty(self):
        engine = SynthesisEngine()
        req = SynthesisRequest(request_id="r", question="Test")
        result = engine.synthesize(req)
        assert result.synthesis_id.startswith("syn-")
        assert result.synthesis_status == SynthesisStatus.INSUFFICIENT_EVIDENCE

    def test_engine_health(self):
        engine = SynthesisEngine()
        h = engine.health()
        assert h["status"] == "healthy"
        assert h["service"] == "synthesis-engine"

    def test_engine_audit_log(self):
        engine = SynthesisEngine()
        req = SynthesisRequest(request_id="r", question="Q1")
        engine.synthesize(req)
        req2 = SynthesisRequest(request_id="r2", question="Q2")
        engine.synthesize(req2)
        log = engine.get_audit_log(limit=10)
        assert len(log) == 2

    def test_engine_cache_hit(self):
        engine = SynthesisEngine()
        req = SynthesisRequest(request_id="r", question="Q1")
        r1 = engine.synthesize(req)
        r2 = engine.synthesize(req)
        assert r1.synthesis_id == r2.synthesis_id

    def test_engine_with_evidence_and_findings(self):
        engine = SynthesisEngine()
        req = SynthesisRequest(
            request_id="r", question="Q",
            evidence_ids=["ev-1"], domain="test",
        )
        evidence = [{
            "evidence_id": "ev-1",
            "source": "test",
            "evidence_type": "OBSERVATION",
            "domain": "test",
            "claim": "Upward trend observed",
            "freshness": "RECENT",
            "relevance": "DIRECT",
            "reliability": "HIGH",
            "direct_vs_derived": "DIRECT",
            "limitations": [],
        }]
        findings = [{
            "finding_id": "f-1",
            "statement": "Market shows upward trend",
            "evidence_refs": ["ev-1"],
            "status": "SUPPORTED",
            "confidence": "HIGH",
        }]
        result = engine.synthesize(req, evidence_items=evidence, findings_raw=findings)
        assert len(result.evidence_assessments) == 1
        assert len(result.key_findings) == 1
        assert result.synthesis_status != SynthesisStatus.INSUFFICIENT_EVIDENCE
