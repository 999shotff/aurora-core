"""Tests for Phase 15: Research Decision Gate + Prediction-Formulation Audit."""


from aurora.models.phase15 import (
    analyze_failure_modes,
    assess_production_readiness,
    audit_architecture,
    audit_baselines,
    audit_data_sufficiency,
    audit_economic_value,
    audit_features,
    audit_non_stationarity,
    audit_prediction_targets,
    audit_temporal_resolution,
    create_decision_matrix,
    evaluate_research_directions,
    make_final_decision,
)


class TestArchitectureAudit:
    def test_returns_all_layers(self):
        result = audit_architecture()
        assert len(result.layers) >= 8

    def test_identifies_bottlenecks(self):
        result = audit_architecture()
        assert len(result.bottlenecks) > 0

    def test_data_flow_string(self):
        result = audit_architecture()
        assert "DATA" in result.data_flow
        assert "FINAL DECISION" in result.data_flow

    def test_bottleneck_layer_flagged(self):
        result = audit_architecture()
        bottleneck_layers = [l for l in result.layers if l.bottleneck]
        assert len(bottleneck_layers) > 0


class TestTargetAudit:
    def test_all_targets_audited(self):
        result = audit_prediction_targets()
        assert len(result) >= 6

    def test_directional_included(self):
        result = audit_prediction_targets()
        types = [t.target_type for t in result]
        assert "directional_h1" in types

    def test_each_has_limitations(self):
        result = audit_prediction_targets()
        for t in result:
            assert len(t.limitations) > 0


class TestBaselineAudit:
    def test_majority_class_included(self):
        result = audit_baselines()
        types = [b.baseline_type for b in result]
        assert "majority_class" in types

    def test_all_have_reasoning(self):
        result = audit_baselines()
        for b in result:
            assert len(b.reasoning) > 0


class TestDataSufficiency:
    def test_returns_metrics(self):
        result = audit_data_sufficiency()
        assert len(result) >= 5

    def test_each_has_assessment(self):
        result = audit_data_sufficiency()
        valid = ("MARGINAL", "INSUFFICIENT", "ADEQUATE", "HIGH RISK")
        for d in result:
            assert any(v in d.assessment for v in valid), f"Bad assessment: {d.assessment}"


class TestNonStationarity:
    def test_returns_aspects(self):
        result = audit_non_stationarity()
        assert len(result) >= 3

    def test_each_has_implication(self):
        result = audit_non_stationarity()
        for n in result:
            assert len(n.implication) > 0


class TestFeatureAudit:
    def test_returns_groups(self):
        result = audit_features()
        assert len(result) >= 5

    def test_all_assessed(self):
        result = audit_features()
        valid = ("NO PREDICTIVE VALUE", "NO STATISTICALLY SIGNIFICANT VALUE", "INCONCLUSIVE")
        for f in result:
            assert any(v in f.assessment for v in valid), f"Bad assessment: {f.assessment}"


class TestTemporalResolution:
    def test_returns_resolutions(self):
        result = audit_temporal_resolution()
        assert len(result) >= 3

    def test_daily_included(self):
        result = audit_temporal_resolution()
        resolutions = [t.resolution for t in result]
        assert "Daily (current)" in resolutions


class TestEconomicValue:
    def test_returns_aspects(self):
        result = audit_economic_value()
        assert len(result) >= 3

    def test_transaction_costs_audited(self):
        result = audit_economic_value()
        aspects = [e.aspect for e in result]
        assert "Transaction costs" in aspects


class TestFailureModes:
    def test_returns_modes(self):
        result = analyze_failure_modes()
        assert len(result) >= 3

    def test_has_primary(self):
        result = analyze_failure_modes()
        codes = [f.code for f in result]
        assert "A" in codes

    def test_each_has_evidence(self):
        result = analyze_failure_modes()
        for f in result:
            assert len(f.evidence) > 0


class TestResearchDirections:
    def test_returns_directions(self):
        result = evaluate_research_directions()
        assert len(result) >= 5

    def test_each_has_score(self):
        result = evaluate_research_directions()
        for r in result:
            assert 1 <= r.score <= 5


class TestDecisionMatrix:
    def test_returns_options(self):
        result = create_decision_matrix()
        assert len(result) >= 4

    def test_has_stop(self):
        result = create_decision_matrix()
        options = [d.option for d in result]
        assert "STOP_PREDICTIVE_RESEARCH" in options

    def test_each_has_recommendation(self):
        result = create_decision_matrix()
        for d in result:
            assert d.recommendation in ("ADOPT", "CONSIDER", "REJECT")


class TestProductionReadiness:
    def test_returns_requirements(self):
        result = assess_production_readiness()
        assert len(result) >= 5

    def test_predictive_model_not_met(self):
        result = assess_production_readiness()
        pred = [r for r in result if r.requirement == "Validated predictive model"]
        assert len(pred) == 1
        assert pred[0].status == "NOT_MET"

    def test_reproducibility_met(self):
        result = assess_production_readiness()
        repro = [r for r in result if r.requirement == "Reproducible model"]
        assert len(repro) == 1
        assert repro[0].status == "MET"


class TestFinalDecision:
    def test_returns_decision(self):
        result = make_final_decision()
        assert result.primary_decision == "STOP_PREDICTIVE_RESEARCH"

    def test_production_blocked(self):
        result = make_final_decision()
        assert result.production_readiness == "NOT JUSTIFIED"
        assert result.tradingview_readiness == "BLOCKED"
        assert result.website_readiness == "BLOCKED"
        assert result.live_trading_readiness == "BLOCKED"

    def test_has_secondary(self):
        result = make_final_decision()
        assert len(result.secondary_recommendations) > 0

    def test_has_reasoning(self):
        result = make_final_decision()
        assert len(result.reasoning) > 100

    def test_has_what_was_learned(self):
        result = make_final_decision()
        assert len(result.what_was_learned) > 100
