"""Unified Analysis — comprehensive tests.

40+ tests covering contracts, evidence classification, orchestrator,
persona adapter, cycle framework, regime detection, unified assessment.
"""

from __future__ import annotations

import pytest

from aurora.analysis.contracts import (
    AnalysisCollection,
    AnalysisInput,
    AnalysisSourceType,
    EvidenceClass,
    MethodologyType,
)
from aurora.analysis.persona import PersonaSimulationProvider
from aurora.analysis.cycles import (
    CycleAnalysisProvider,
    CycleAnalysisResult,
    CycleMethod,
    GannCycleProvider,
    HypothesisStatus,
    SeasonalityProvider,
)
from aurora.analysis.regime import RegimeType, RegimeAnalysis, detect_regime
from aurora.analysis.assessment import (
    DirectionalBias,
    AssessmentStrength,
    UnifiedAssessment,
    build_unified_assessment,
)
from aurora.analysis.orchestrator import UnifiedOrchestrator


# ============================================================
# Evidence Classification Tests
# ============================================================

class TestEvidenceClass:
    def test_evidence_class_enum(self):
        assert EvidenceClass.OBSERVED == "OBSERVED"
        assert EvidenceClass.DERIVED == "DERIVED"
        assert EvidenceClass.STATISTICAL == "STATISTICAL"
        assert EvidenceClass.SIMULATED == "SIMULATED"
        assert EvidenceClass.HYPOTHESIS == "HYPOTHESIS"
        assert EvidenceClass.UNAVAILABLE == "UNAVAILABLE"

    def test_source_type_enum(self):
        assert AnalysisSourceType.MARKET_INDICATORS == "MARKET_INDICATORS"
        assert AnalysisSourceType.PERSONA_SIMULATION == "PERSONA_SIMULATION"
        assert AnalysisSourceType.CYCLE_ANALYSIS == "CYCLE_ANALYSIS"

    def test_methodology_enum(self):
        assert MethodologyType.DETERMINISTIC == "DETERMINISTIC"
        assert MethodologyType.SIMULATION == "SIMULATION"
        assert MethodologyType.HYPOTHETICAL == "HYPOTHETICAL"


# ============================================================
# AnalysisInput Tests
# ============================================================

class TestAnalysisInput:
    def test_create_input(self):
        inp = AnalysisInput(
            source_type=AnalysisSourceType.MARKET_INDICATORS,
            source_id="ind-1",
            evidence_class=EvidenceClass.DERIVED,
            methodology=MethodologyType.DETERMINISTIC,
        )
        assert inp.source_type == AnalysisSourceType.MARKET_INDICATORS
        assert inp.evidence_class == EvidenceClass.DERIVED

    def test_input_with_observations(self):
        inp = AnalysisInput(
            source_type=AnalysisSourceType.MARKET_STRUCTURE,
            source_id="struct-1",
            evidence_class=EvidenceClass.DERIVED,
            observations={"regime": "uptrend"},
            structure={"regime": "uptrend"},
        )
        assert inp.observations["regime"] == "uptrend"

    def test_input_rejects_empty_source_id(self):
        with pytest.raises(Exception):
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="",
                evidence_class=EvidenceClass.DERIVED,
            )


# ============================================================
# AnalysisCollection Tests
# ============================================================

class TestAnalysisCollection:
    def test_empty_collection(self):
        coll = AnalysisCollection(question="Test?")
        assert coll.total_inputs == 0 if hasattr(coll, 'total_inputs') else len(coll.inputs) == 0

    def test_collection_with_inputs(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i1", evidence_class=EvidenceClass.DERIVED,
            ),
            AnalysisInput(
                source_type=AnalysisSourceType.PERSONA_SIMULATION,
                source_id="p1", evidence_class=EvidenceClass.SIMULATED,
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        assert coll.has_simulated is True
        assert coll.observed_count == 0
        assert coll.derived_count == 1

    def test_collection_evidence_classes(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i1", evidence_class=EvidenceClass.DERIVED,
            ),
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i2", evidence_class=EvidenceClass.DERIVED,
            ),
            AnalysisInput(
                source_type=AnalysisSourceType.PERSONA_SIMULATION,
                source_id="p1", evidence_class=EvidenceClass.SIMULATED,
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        classes = coll.evidence_classes
        assert classes[EvidenceClass.DERIVED] == 2
        assert classes[EvidenceClass.SIMULATED] == 1

    def test_get_by_type(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i1", evidence_class=EvidenceClass.DERIVED,
            ),
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_STRUCTURE,
                source_id="s1", evidence_class=EvidenceClass.DERIVED,
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        indicators = coll.get_by_type(AnalysisSourceType.MARKET_INDICATORS)
        assert len(indicators) == 1
        assert indicators[0].source_id == "i1"


# ============================================================
# Persona Simulation Tests
# ============================================================

class TestPersonaSimulation:
    def test_persona_not_configured(self):
        persona = PersonaSimulationProvider()
        assert persona.health() == "NOT_CONFIGURED"

    def test_persona_capabilities_when_not_configured(self):
        persona = PersonaSimulationProvider()
        caps = persona.capabilities()
        assert caps["persona_simulation"] is False

    def test_persona_configure(self):
        persona = PersonaSimulationProvider()
        persona.configure("https://example.com")
        assert persona.health() == "READY"

    def test_persona_run_scenario_not_configured(self):
        persona = PersonaSimulationProvider()
        result = persona.run_scenario("test scenario")
        assert result.evidence_class == EvidenceClass.UNAVAILABLE

    def test_persona_run_scenario_configured(self):
        persona = PersonaSimulationProvider()
        persona.configure("https://example.com")
        result = persona.run_scenario("test scenario", cohorts=["risk_averse"])
        assert result.evidence_class == EvidenceClass.SIMULATED
        assert result.methodology == MethodologyType.SIMULATION
        assert "Simulated behavior" in result.limitations[0]

    def test_persona_result_has_provenance(self):
        persona = PersonaSimulationProvider()
        persona.configure("https://example.com")
        result = persona.run_scenario("test")
        assert len(result.provenance_chain) > 0
        assert result.provenance_chain[0] == "matraix_adapter"


# ============================================================
# Cycle Analysis Tests
# ============================================================

class TestCycleAnalysis:
    def test_gann_provider(self):
        gann = GannCycleProvider()
        result = gann.analyze(CycleMethod.GANN_TIME, "BTC", {})
        assert result.method == CycleMethod.GANN_TIME
        assert result.status == HypothesisStatus.EXPLORATORY

    def test_seasonality_provider(self):
        season = SeasonalityProvider()
        result = season.analyze(CycleMethod.SEASONALITY, "ETH", {})
        assert result.method == CycleMethod.SEASONALITY

    def test_cycle_to_analysis_input(self):
        gann = GannCycleProvider()
        result = gann.analyze(CycleMethod.GANN_TIME, "BTC", {})
        inp = gann.to_analysis_input(result)
        assert inp.evidence_class == EvidenceClass.HYPOTHESIS
        assert inp.methodology == MethodologyType.HYPOTHETICAL

    def test_cycle_result_fields(self):
        result = CycleAnalysisResult(
            method=CycleMethod.GANN_TIME,
            hypothesis="Test hypothesis",
            status=HypothesisStatus.UNTESTED,
            confidence=0.3,
        )
        assert result.hypothesis == "Test hypothesis"
        assert result.confidence == 0.3


# ============================================================
# Regime Detection Tests
# ============================================================

class TestRegimeDetection:
    def test_regime_enum(self):
        assert RegimeType.TRENDING_UP == "TRENDING_UP"
        assert RegimeType.RANGE_BOUND == "RANGE_BOUND"
        assert RegimeType.HIGH_VOLATILITY == "HIGH_VOLATILITY"

    def test_detect_regime_trending_up(self):
        ctx = {
            "trend": {"direction": "bullish", "strength": 0.8},
            "volatility": {"regime": "normal"},
            "structure": {"regime": "uptrend"},
        }
        result = detect_regime(ctx)
        assert result.regime == RegimeType.TRENDING_UP

    def test_detect_regime_range_bound(self):
        ctx = {
            "trend": {"direction": "neutral", "strength": 0.3},
            "volatility": {"regime": "normal"},
            "structure": {"regime": "ranging"},
        }
        result = detect_regime(ctx)
        assert result.regime == RegimeType.RANGE_BOUND

    def test_detect_regime_high_volatility(self):
        ctx = {
            "trend": {"direction": "neutral", "strength": 0.3},
            "volatility": {"regime": "high"},
            "structure": {"regime": "ranging"},
        }
        result = detect_regime(ctx)
        assert result.regime == RegimeType.HIGH_VOLATILITY

    def test_detect_regime_expansion(self):
        ctx = {
            "trend": {"direction": "neutral", "strength": 0.3},
            "volatility": {"regime": "expansion"},
            "structure": {"regime": "ranging"},
        }
        result = detect_regime(ctx)
        assert result.regime == RegimeType.EXPANSION

    def test_detect_regime_empty(self):
        result = detect_regime({})
        # Empty context defaults to ranging (neutral)
        assert result.regime in (RegimeType.UNKNOWN, RegimeType.RANGE_BOUND)

    def test_regime_has_limitations(self):
        result = detect_regime({})
        assert len(result.limitations) > 0


# ============================================================
# Unified Assessment Tests
# ============================================================

class TestUnifiedAssessment:
    def test_assessment_fields(self):
        a = UnifiedAssessment(
            question="Test?",
            directional_bias=DirectionalBias.UP,
            strength=AssessmentStrength.MODERATE,
            confidence="LOW",
        )
        assert a.directional_bias == DirectionalBias.UP
        assert a.assessment_id.startswith("ua-")

    def test_build_assessment_empty(self):
        coll = AnalysisCollection(question="Test?")
        a = build_unified_assessment(coll)
        assert a.directional_bias == DirectionalBias.INSUFFICIENT_DATA
        assert a.total_inputs == 0

    def test_build_assessment_with_indicators(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i1", evidence_class=EvidenceClass.DERIVED,
                features={"trend_direction": "bullish"},
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert a.directional_bias == DirectionalBias.UP
        assert a.derived_count == 1

    def test_build_assessment_with_structure(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_STRUCTURE,
                source_id="s1", evidence_class=EvidenceClass.DERIVED,
                structure={"regime": "uptrend", "break_count": 2, "sr_levels_count": 3},
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert len(a.supporting_factors) > 0

    def test_build_assessment_with_simulated(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.PERSONA_SIMULATION,
                source_id="sim1", evidence_class=EvidenceClass.SIMULATED,
                observations={"scenario": "risk-off"},
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert a.simulated_count == 1
        assert len(a.limitations) > 0

    def test_build_assessment_with_hypothesis(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.CYCLE_ANALYSIS,
                source_id="cyc1", evidence_class=EvidenceClass.HYPOTHESIS,
                observations={"method": "GANN_TIME", "hypothesis": "cycle inflection"},
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert a.hypothesis_count == 1

    def test_build_assessment_with_regime(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.REGIME_DETECTION,
                source_id="reg1", evidence_class=EvidenceClass.DERIVED,
                regime="TRENDING_UP",
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert a.regime == "TRENDING_UP"

    def test_build_assessment_mixed_bias(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i1", evidence_class=EvidenceClass.DERIVED,
                features={"trend_direction": "bullish"},
            ),
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_STRUCTURE,
                source_id="s1", evidence_class=EvidenceClass.DERIVED,
                structure={"regime": "downtrend"},
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert a.directional_bias == DirectionalBias.MIXED

    def test_assessment_provenance(self):
        inputs = [
            AnalysisInput(
                source_type=AnalysisSourceType.MARKET_INDICATORS,
                source_id="i1", evidence_class=EvidenceClass.DERIVED,
            ),
        ]
        coll = AnalysisCollection(question="Test?", inputs=inputs)
        a = build_unified_assessment(coll)
        assert len(a.provenance) == 1
        assert a.provenance[0]["evidence_class"] == "DERIVED"


# ============================================================
# Orchestrator Tests
# ============================================================

class TestOrchestrator:
    def test_orchestrator_health(self):
        orch = UnifiedOrchestrator()
        h = orch.health()
        assert h["status"] == "healthy"
        assert h["persona_status"] == "NOT_CONFIGURED"

    def test_orchestrator_analyze_empty(self):
        orch = UnifiedOrchestrator()
        a = orch.analyze("What is the market outlook?")
        assert a.total_inputs == 0
        assert a.directional_bias == DirectionalBias.INSUFFICIENT_DATA

    def test_orchestrator_with_indicator_data(self):
        orch = UnifiedOrchestrator()
        a = orch.analyze(
            "Test?",
            indicator_data={"indicators": {"rsi": 65}, "summary": {"trend": "bullish"}},
            asset="BTC",
        )
        assert a.total_inputs >= 1
        assert a.observed_count + a.derived_count >= 1

    def test_orchestrator_with_structure_data(self):
        orch = UnifiedOrchestrator()
        a = orch.analyze(
            "Test?",
            structure_data={"regime": "uptrend", "breaks": [], "support_resistance": []},
        )
        assert a.total_inputs >= 1

    def test_orchestrator_with_persona(self):
        orch = UnifiedOrchestrator()
        a = orch.analyze("Test?", run_persona=True)
        # When persona not configured, returns UNAVAILABLE
        assert a.total_inputs >= 1

    def test_orchestrator_with_cycles(self):
        orch = UnifiedOrchestrator()
        a = orch.analyze("Test?", run_cycles=True)
        assert a.hypothesis_count >= 1

    def test_orchestrator_get_assessment(self):
        orch = UnifiedOrchestrator()
        a = orch.analyze("Test?")
        found = orch.get_assessment(a.assessment_id)
        assert found is not None
        assert found.assessment_id == a.assessment_id

    def test_orchestrator_get_assessment_not_found(self):
        orch = UnifiedOrchestrator()
        found = orch.get_assessment("nonexistent")
        assert found is None
