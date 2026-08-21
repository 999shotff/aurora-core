"""Tests for Phase 12: Market Prediction Architecture Research."""

import pytest

from aurora.models.phase7_validation import OHLCVRecord
from aurora.models.phase12 import (
    MarketState,
    RiskMetrics,
    TargetConfig,
    WalkForwardResult,
    aggregate_statistical_results,
    classify_market_state,
    classify_regime,
    compute_abstention_by_confidence,
    compute_risk_metrics,
    construct_target,
    create_model,
    get_regime_stats,
)


def _make_records(n: int = 300) -> list[OHLCVRecord]:
    records = []
    price = 100.0
    for i in range(n):
        import random
        rng = random.Random(i)
        change = rng.gauss(0, 0.02)
        price *= (1 + change)
        r = OHLCVRecord(
            timestamp=f"2024-01-{i+1:02d}",
            open=price * 0.99, high=price * 1.01, low=price * 0.98,
            close=price, volume=rng.randint(1000, 10000),
        )
        records.append(r)
    return records


class TestTargetFramework:
    def test_directional(self):
        records = _make_records(100)
        labels, meta = construct_target(records, TargetConfig("directional", horizon=1))
        assert len(labels) == 99
        assert meta["target_type"] == "directional"

    def test_directional_with_threshold(self):
        records = _make_records(100)
        labels, _meta = construct_target(records, TargetConfig("directional", horizon=1, threshold=0.01))
        assert len(labels) == 99

    def test_magnitude(self):
        records = _make_records(100)
        labels, meta = construct_target(records, TargetConfig("magnitude", horizon=1, n_classes=3))
        assert len(labels) == 99
        assert "class_distribution" in meta

    def test_volatility_conditioned(self):
        records = _make_records(100)
        labels, meta = construct_target(records, TargetConfig("volatility_conditioned", horizon=1))
        assert len(labels) > 0
        assert meta["target_type"] == "volatility_conditioned"

    def test_event(self):
        records = _make_records(100)
        labels, meta = construct_target(records, TargetConfig("event", horizon=5, event_threshold=0.02))
        assert len(labels) == 95
        assert "event_rate" in meta

    def test_persistence(self):
        records = _make_records(100)
        labels, meta = construct_target(records, TargetConfig("persistence", horizon=5, lookback=5))
        assert len(labels) > 0
        assert "class_distribution" in meta


class TestMarketState:
    def test_classify_market_state(self):
        records = _make_records(100)
        state = classify_market_state(records, 50)
        assert isinstance(state, MarketState)
        assert state.trend in ("bullish", "bearish", "sideways")
        assert state.volatility in ("high", "low", "normal")

    def test_classify_regime(self):
        records = _make_records(100)
        regime = classify_regime(records, 0, 50)
        assert isinstance(regime, str)

    def test_get_regime_stats(self):
        records = _make_records(100)
        stats = get_regime_stats(records, list(range(50)))
        assert isinstance(stats, dict)


class TestRiskMetrics:
    def test_perfect_prediction(self):
        y_true = ["up", "up", "down", "down"]
        y_pred = ["up", "up", "down", "down"]
        y_prob = [0.9, 0.8, 0.2, 0.1]
        returns = [0.01, 0.01, -0.01, -0.01]
        metrics = compute_risk_metrics(y_true, y_pred, y_prob, returns)
        assert metrics.accuracy == 1.0

    def test_with_abstentions(self):
        y_true = ["up", "up", "down", "down"]
        y_pred = ["up", "up", "down", "down"]
        y_prob = [0.9, 0.8, 0.2, 0.1]
        returns = [0.01, 0.01, -0.01, -0.01]
        abstentions = [False, True, False, False]
        metrics = compute_risk_metrics(y_true, y_pred, y_prob, returns, abstentions)
        assert metrics.n_abstentions == 1
        assert metrics.coverage == 0.75

    def test_empty(self):
        metrics = compute_risk_metrics([], [], [], [])
        assert metrics.n_samples == 0


class TestAbstention:
    def test_compute_abstention(self):
        y_true = ["up"] * 50 + ["down"] * 50
        y_pred = ["up"] * 50 + ["down"] * 50
        y_prob = [0.6] * 50 + [0.4] * 50
        results = compute_abstention_by_confidence(y_true, y_pred, y_prob)
        assert len(results) == 6
        for r in results:
            assert "threshold" in r
            assert "coverage" in r
            assert "accuracy" in r


class TestModelFactory:
    def test_logistic_regression(self):
        model = create_model("logistic_regression", {"learning_rate": 0.01, "n_iterations": 100})
        assert model is not None

    def test_decision_tree(self):
        model = create_model("decision_tree", {"max_depth": 3})
        assert model is not None

    def test_random_forest(self):
        model = create_model("random_forest", {"n_trees": 5, "max_depth": 3})
        assert model is not None

    def test_unknown_model(self):
        with pytest.raises(ValueError):
            create_model("unknown")


class TestStatisticalSummary:
    def test_aggregate(self):
        results = []
        for i in range(5):
            rm = RiskMetrics(
                accuracy=0.5 + i * 0.01, balanced_accuracy=0.5, precision=0.5,
                recall=0.5, f1=0.5, log_loss=0.5, brier_score=0.25,
                expected_return=0.0, return_volatility=0.01, max_drawdown=0.0,
                sharpe_ratio=0.0, turnover=0.0, coverage=1.0, n_samples=50,
                n_predictions=50, n_abstentions=0,
            )
            wr = WalkForwardResult(
                window_id=i, model_type="lr", hyperparameters={},
                target_config={"type": "directional", "horizon": 1},
                risk_metrics=rm, regime="sideways_normal",
                y_true=["up"] * 50, y_pred=["up"] * 50, y_prob=[0.6] * 50,
                actual_returns=[0.01] * 50,
            )
            results.append(wr)

        stat = aggregate_statistical_results(results, 0.5)
        assert stat.n_windows == 5
        assert stat.mean_accuracy > 0.5
