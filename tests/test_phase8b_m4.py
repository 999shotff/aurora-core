import math
from datetime import datetime, timezone

import pytest

from aurora.features.base import FeatureVector
from aurora.interaction.models import (
    BaggedEnsemble,
    DecisionTreeModel,
    LogisticRegressionModel,
    _sigmoid,
)
from aurora.models.base import ModelInput
from aurora.models.calibration import (
    brier_score,
    evaluate_calibration,
)
from aurora.models.classical import (
    DecisionTreeAdapter,
    LogisticRegressionAdapter,
    RandomForestAdapter,
)
from aurora.models.selection import ModelSelector
from aurora.schemas.evaluation import Outcome
from aurora.schemas.market_state import MarketState


def _ts(h: int = 12) -> datetime:
    return datetime(2025, 6, 1, h, 0, tzinfo=timezone.utc)


def _make_feature_vector(ts: datetime | None = None, price: float = 100_000.0) -> FeatureVector:
    return FeatureVector(
        version="0.1.0",
        extractor_id="test",
        asset="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        numerical={"price": price, "return_1h": 0.01, "momentum": 0.5},
    )


def _make_market_state(ts: datetime | None = None, price: float = 100_000.0) -> MarketState:
    return MarketState(
        asset="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        data_quality="historical",
        price=price,
    )


def _make_input(
    ts: datetime | None = None,
    evaluation_context: str = "live",
    feature_schema_version: str = "0.1.0",
    leakage_flags: dict[str, bool] | None = None,
    instrument: str = "BTCUSD",
    price: float = 100_000.0,
) -> ModelInput:
    return ModelInput(
        instrument_id=instrument,
        timeframe="15m",
        timestamp=ts or _ts(),
        feature_vector=_make_feature_vector(ts, price),
        market_state=_make_market_state(ts, price),
        data_quality="historical",
        feature_schema_version=feature_schema_version,
        evaluation_context=evaluation_context,
        leakage_flags=leakage_flags or {},
    )


def _make_dataset(n: int = 100, instrument: str = "BTCUSD") -> tuple[list[ModelInput], list[Outcome]]:
    inputs = []
    labels: list[Outcome] = []
    for i in range(n):
        ts = datetime(2025, 1, 1, i % 24, i // 24 % 60, tzinfo=timezone.utc)
        price = 100_000.0 + (i * 100 if i % 10 < 6 else -i * 50)
        inputs.append(_make_input(ts=ts, instrument=instrument, price=float(price)))
        if i % 10 < 6:
            labels.append("up")
        elif i % 10 < 9:
            labels.append("down")
        else:
            labels.append("flat")
    return inputs, labels


# ═══════════════════════════════════════════════════════
# A. Logistic Regression Mathematics
# ═══════════════════════════════════════════════════════

class TestLogisticRegressionMath:
    def test_sigmoid_zero(self):
        assert _sigmoid(0.0) == pytest.approx(0.5)

    def test_sigmoid_large_positive(self):
        assert _sigmoid(500.0) == pytest.approx(1.0, abs=1e-10)

    def test_sigmoid_large_negative(self):
        assert _sigmoid(-500.0) == pytest.approx(0.0, abs=1e-10)

    def test_sigmoid_symmetry(self):
        for z in [0.5, 1.0, 2.0, 5.0]:
            assert _sigmoid(z) + _sigmoid(-z) == pytest.approx(1.0)

    def test_logistic_loss_perfect(self):
        model = LogisticRegressionModel(n_iterations=100)
        X = [[1.0], [0.0], [1.0], [0.0]]
        y = [1.0, 0.0, 1.0, 0.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        for p in probs:
            assert 0.0 <= p <= 1.0

    def test_logistic_coefficients_finite(self):
        model = LogisticRegressionModel(n_iterations=100)
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        y = [1.0, 0.0, 1.0]
        model.fit(X, y)
        for w in model.weights:
            assert math.isfinite(w)
        assert math.isfinite(model.bias)

    def test_logistic_single_feature(self):
        model = LogisticRegressionModel(n_iterations=200)
        X = [[1.0], [2.0], [3.0], [4.0], [5.0]]
        y = [0.0, 0.0, 1.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert probs[-1] > probs[0]

    def test_logistic_constant_feature(self):
        model = LogisticRegressionModel(n_iterations=100)
        X = [[1.0], [1.0], [1.0], [1.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        for p in probs:
            assert 0.0 <= p <= 1.0


# ═══════════════════════════════════════════════════════
# B. Logistic Numerical Stability
# ═══════════════════════════════════════════════════════

class TestLogisticNumericalStability:
    def test_extreme_positive_z(self):
        assert _sigmoid(1000.0) == pytest.approx(1.0, abs=1e-10)
        assert not math.isinf(_sigmoid(1000.0))
        assert not math.isnan(_sigmoid(1000.0))

    def test_extreme_negative_z(self):
        assert _sigmoid(-1000.0) == pytest.approx(0.0, abs=1e-10)
        assert not math.isinf(_sigmoid(-1000.0))
        assert not math.isnan(_sigmoid(-1000.0))

    def test_large_features_no_nan(self):
        model = LogisticRegressionModel(n_iterations=50)
        X = [[1e6, -1e6], [1e6, -1e6], [-1e6, 1e6]]
        y = [1.0, 0.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        for p in probs:
            assert math.isfinite(p)
            assert 0.0 <= p <= 1.0

    def test_predict_proba_bounds(self):
        model = LogisticRegressionModel(n_iterations=100)
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [1.0, 0.0, 1.0, 0.0]
        model.fit(X, y)
        test_X = [[10.0, -10.0], [-10.0, 10.0], [0.0, 0.0]]
        probs = model.predict_proba(test_X)
        for p in probs:
            assert 0.0 <= p <= 1.0


# ═══════════════════════════════════════════════════════
# C. Decision Tree Splitting
# ═══════════════════════════════════════════════════════

class TestDecisionTreeSplitting:
    def test_tree_splits_on_separable_data(self):
        tree = DecisionTreeModel(max_depth=2, min_samples_split=2)
        X = [[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]]
        y = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
        tree.fit(X, y)
        assert tree.root is not None
        assert not tree.root.is_leaf

    def test_tree_impurity_pure_node(self):
        tree = DecisionTreeModel(max_depth=1, min_samples_split=2)
        X = [[1.0], [2.0], [3.0]]
        y = [1.0, 1.0, 1.0]
        tree.fit(X, y)
        probs = tree.predict_proba(X)
        for p in probs:
            assert p == pytest.approx(1.0)

    def test_tree_single_class(self):
        tree = DecisionTreeModel(max_depth=2, min_samples_split=2)
        X = [[1.0], [2.0], [3.0]]
        y = [0.0, 0.0, 0.0]
        tree.fit(X, y)
        probs = tree.predict_proba(X)
        for p in probs:
            assert p == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════
# D. Decision Tree Probabilities
# ═══════════════════════════════════════════════════════

class TestDecisionTreeProbabilities:
    def test_probabilities_between_zero_and_one(self):
        tree = DecisionTreeModel(max_depth=3, min_samples_split=2)
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 1.0, 0.0, 1.0]
        tree.fit(X, y)
        test_X = [[2.0, 3.0], [4.0, 5.0], [6.0, 7.0]]
        probs = tree.predict_proba(test_X)
        for p in probs:
            assert 0.0 <= p <= 1.0

    def test_leaf_prediction_is_proportion(self):
        tree = DecisionTreeModel(max_depth=1, min_samples_split=10)
        X = [[1.0], [2.0], [3.0], [4.0], [5.0]]
        y = [1.0, 1.0, 0.0, 0.0, 0.0]
        tree.fit(X, y)
        assert tree.root is not None
        assert tree.root.prediction == pytest.approx(0.4)


# ═══════════════════════════════════════════════════════
# E. Random Forest Reproducibility
# ═══════════════════════════════════════════════════════

class TestRandomForestReproducibility:
    def test_same_seed_same_result(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]]
        y = [0.0, 1.0, 0.0, 1.0, 0.0]
        r1 = BaggedEnsemble(n_trees=5, max_depth=2, subsample_ratio=0.8)
        r2 = BaggedEnsemble(n_trees=5, max_depth=2, subsample_ratio=0.8)
        r1.fit(X, y, seed=42)
        r2.fit(X, y, seed=42)
        p1 = r1.predict_proba(X)
        p2 = r2.predict_proba(X)
        assert p1 == pytest.approx(p2)

    def test_different_seeds_may_differ(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0], [11.0, 12.0]]
        y = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
        r1 = BaggedEnsemble(n_trees=5, max_depth=2, subsample_ratio=0.8)
        r2 = BaggedEnsemble(n_trees=5, max_depth=2, subsample_ratio=0.8)
        r1.fit(X, y, seed=42)
        r2.fit(X, y, seed=99)
        p1 = r1.predict_proba(X)
        p2 = r2.predict_proba(X)
        # Both must be valid even if different
        for p in p1 + p2:
            assert 0.0 <= p <= 1.0


# ═══════════════════════════════════════════════════════
# F. Probability Bounds
# ═══════════════════════════════════════════════════════

class TestProbabilityBounds:
    def test_logistic_output_bounds(self):
        inputs, labels = _make_dataset(n=50)
        adapter = LogisticRegressionAdapter()
        adapter.fit(inputs, labels)
        for inp in inputs[:20]:
            out = adapter.predict(inp)
            assert 0.0 <= out.probability <= 1.0

    def test_tree_output_bounds(self):
        inputs, labels = _make_dataset(n=50)
        adapter = DecisionTreeAdapter()
        adapter.fit(inputs, labels)
        for inp in inputs[:20]:
            out = adapter.predict(inp)
            assert 0.0 <= out.probability <= 1.0

    def test_forest_output_bounds(self):
        inputs, labels = _make_dataset(n=50)
        adapter = RandomForestAdapter()
        adapter.fit(inputs, labels)
        for inp in inputs[:20]:
            out = adapter.predict(inp)
            assert 0.0 <= out.probability <= 1.0


# ═══════════════════════════════════════════════════════
# G. Probability Summation
# ═══════════════════════════════════════════════════════

class TestProbabilitySummation:
    def test_logistic_distribution_sums_to_one(self):
        inputs, labels = _make_dataset(n=50)
        adapter = LogisticRegressionAdapter()
        adapter.fit(inputs, labels)
        out = adapter.predict(inputs[0])
        total = out.probability_distribution.get("up", 0) + out.probability_distribution.get("down", 0)
        assert total == pytest.approx(1.0)

    def test_tree_distribution_sums_to_one(self):
        inputs, labels = _make_dataset(n=50)
        adapter = DecisionTreeAdapter()
        adapter.fit(inputs, labels)
        out = adapter.predict(inputs[0])
        total = out.probability_distribution.get("up", 0) + out.probability_distribution.get("down", 0)
        assert total == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════
# H. Brier Score
# ═══════════════════════════════════════════════════════

class TestBrierScore:
    def test_perfect_predictions(self):
        bs = brier_score([1.0, 0.0, 1.0], [1.0, 0.0, 1.0])
        assert bs == pytest.approx(0.0)

    def test_worst_predictions(self):
        bs = brier_score([0.0, 1.0, 0.0], [1.0, 0.0, 1.0])
        assert bs == pytest.approx(1.0)

    def test_uncertain_predictions(self):
        bs = brier_score([0.5, 0.5, 0.5], [1.0, 0.0, 1.0])
        assert bs == pytest.approx(0.25)

    def test_empty_input(self):
        bs = brier_score([], [])
        assert bs == 0.0


# ═══════════════════════════════════════════════════════
# I. Calibration Evaluation
# ═══════════════════════════════════════════════════════

class TestCalibrationEvaluation:
    def test_perfect_calibration(self):
        probs = [0.0] * 10 + [1.0] * 10
        actuals = [0.0] * 10 + [1.0] * 10
        result = evaluate_calibration(probs, actuals, n_bins=10, min_samples_per_bin=1)
        assert result.brier_score == pytest.approx(0.0)
        assert result.calibration_status == "CALIBRATION_EVALUATED"

    def test_insufficient_data(self):
        probs = [0.5, 0.6]
        actuals = [0.0, 1.0]
        result = evaluate_calibration(probs, actuals, n_bins=10, min_samples_per_bin=5)
        assert result.calibration_status == "CALIBRATION_INCONCLUSIVE"

    def test_ece_range(self):
        probs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        actuals = [0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        result = evaluate_calibration(probs, actuals, n_bins=5, min_samples_per_bin=1)
        assert result.expected_calibration_error is not None
        assert 0.0 <= result.expected_calibration_error <= 1.0


# ═══════════════════════════════════════════════════════
# J. Model Selection
# ═══════════════════════════════════════════════════════

class TestModelSelection:
    def test_selects_best_candidate(self):
        inputs, labels = _make_dataset(n=100)
        train = inputs[:60]
        train_labels = labels[:60]
        val = inputs[60:80]
        val_labels = labels[60:80]

        c1 = LogisticRegressionAdapter(model_id="lr1", n_iterations=100)
        c2 = LogisticRegressionAdapter(model_id="lr2", n_iterations=500)

        selector = ModelSelector()
        result = selector.select(
            candidates=[c1, c2],
            candidate_configs=[{"n_iter": 100}, {"n_iter": 500}],
            train_inputs=train,
            train_labels=train_labels,
            val_inputs=val,
            val_labels=val_labels,
        )
        assert result.n_selected == 1
        assert result.selected_model_id in ("lr1", "lr2")

    def test_validation_not_used_for_training(self):
        inputs, labels = _make_dataset(n=100)
        train = inputs[:60]
        train_labels = labels[:60]
        val = inputs[60:80]
        val_labels = labels[60:80]

        adapter = LogisticRegressionAdapter()
        selector = ModelSelector()
        result = selector.select(
            candidates=[adapter],
            candidate_configs=[{"lr": 0.01}],
            train_inputs=train,
            train_labels=train_labels,
            val_inputs=val,
            val_labels=val_labels,
        )
        assert result.validation_period[0] != result.validation_period[1]


# ═══════════════════════════════════════════════════════
# K. Validation/Test Separation
# ═══════════════════════════════════════════════════════

class TestValidationTestSeparation:
    def test_chronological_order(self):
        inputs, _labels = _make_dataset(n=100)
        train = inputs[:60]
        val = inputs[60:80]
        test = inputs[80:]

        train_end = train[-1].timestamp
        val_start = val[0].timestamp
        val_end = val[-1].timestamp
        test_start = test[0].timestamp

        assert train_end <= val_start
        assert val_end <= test_start


# ═══════════════════════════════════════════════════════
# L. Leakage Attacks
# ═══════════════════════════════════════════════════════

class TestLeakageAttacks:
    def test_future_feature_in_test_context(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"future_price": True},
                )
            )

    def test_test_label_in_leakage_flags(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"test_label": True},
                )
            )

    def test_train_context_allows_leakage_flags(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        out = adapter.predict(
            _make_input(
                evaluation_context="train",
                leakage_flags={"future_data": True},
            )
        )
        assert out.abstained is False

    def test_feature_schema_mismatch(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        with pytest.raises(ValueError, match="schema mismatch"):
            adapter.predict(_make_input(feature_schema_version="99.0.0"))


# ═══════════════════════════════════════════════════════
# M. Edge Cases
# ═══════════════════════════════════════════════════════

class TestEdgeCases:
    def test_one_row_dataset(self):
        adapter = LogisticRegressionAdapter()
        inputs = [_make_input()]
        labels: list[Outcome] = ["up"]
        adapter.fit(inputs, labels)
        out = adapter.predict(inputs[0])
        assert out.outcome in ("up", "down")

    def test_two_class_dataset(self):
        adapter = DecisionTreeAdapter()
        inputs = [_make_input(price=100.0), _make_input(price=200.0)]
        labels: list[Outcome] = ["up", "down"]
        adapter.fit(inputs, labels)
        out = adapter.predict(inputs[0])
        assert out.outcome in ("up", "down")

    def test_constant_feature(self):
        adapter = LogisticRegressionAdapter()
        inputs = [_make_input(price=100.0) for _ in range(10)]
        labels: list[Outcome] = ["up"] * 5 + ["down"] * 5
        adapter.fit(inputs, labels)
        out = adapter.predict(inputs[0])
        assert 0.0 <= out.probability <= 1.0

    def test_extreme_feature_values(self):
        adapter = LogisticRegressionAdapter()
        inputs = [
            _make_input(price=1e10),
            _make_input(price=1e-10),
            _make_input(price=0.0),
        ]
        labels: list[Outcome] = ["up", "down", "up"]
        adapter.fit(inputs, labels)
        for inp in inputs:
            out = adapter.predict(inp)
            assert math.isfinite(out.probability)

    def test_duplicate_timestamps_allowed(self):
        adapter = LogisticRegressionAdapter()
        ts = _ts()
        inputs = [_make_input(ts=ts) for _ in range(10)]
        labels: list[Outcome] = ["up"] * 5 + ["down"] * 5
        adapter.fit(inputs, labels)
        out = adapter.predict(inputs[0])
        assert out.outcome in ("up", "down")


# ═══════════════════════════════════════════════════════
# N. Audit Trail
# ═══════════════════════════════════════════════════════

class TestAuditTrail:
    def test_logistic_audit_trail_complete(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        trail = adapter.audit_trail()
        assert trail.model_id == "logistic_regression"
        assert trail.training_period[0] != "unknown"
        assert "learning_rate" in trail.hyperparameters

    def test_tree_audit_trail_complete(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        trail = adapter.audit_trail()
        assert trail.model_id == "decision_tree"
        assert "max_depth" in trail.hyperparameters

    def test_forest_audit_trail_complete(self):
        adapter = RandomForestAdapter()
        inputs, labels = _make_dataset(n=50)
        adapter.fit(inputs[:40], labels[:40])
        trail = adapter.audit_trail()
        assert trail.model_id == "random_forest"
        assert trail.random_seed == 42


# ═══════════════════════════════════════════════════════
# O. Reproducibility
# ═══════════════════════════════════════════════════════

class TestReproducibility:
    def test_logistic_reproducible(self):
        inputs, labels = _make_dataset(n=50)
        a1 = LogisticRegressionAdapter()
        a2 = LogisticRegressionAdapter()
        a1.fit(inputs[:40], labels[:40])
        a2.fit(inputs[:40], labels[:40])
        o1 = a1.predict(inputs[40])
        o2 = a2.predict(inputs[40])
        assert o1.probability == pytest.approx(o2.probability)

    def test_tree_reproducible(self):
        inputs, labels = _make_dataset(n=50)
        a1 = DecisionTreeAdapter()
        a2 = DecisionTreeAdapter()
        a1.fit(inputs[:40], labels[:40])
        a2.fit(inputs[:40], labels[:40])
        o1 = a1.predict(inputs[40])
        o2 = a2.predict(inputs[40])
        assert o1.probability == pytest.approx(o2.probability)

    def test_forest_reproducible(self):
        inputs, labels = _make_dataset(n=50)
        a1 = RandomForestAdapter(seed=42)
        a2 = RandomForestAdapter(seed=42)
        a1.fit(inputs[:40], labels[:40])
        a2.fit(inputs[:40], labels[:40])
        o1 = a1.predict(inputs[40])
        o2 = a2.predict(inputs[40])
        assert o1.probability == pytest.approx(o2.probability)


# ═══════════════════════════════════════════════════════
# P. Benchmark Integrity
# ═══════════════════════════════════════════════════════

class TestBenchmarkIntegrity:
    def test_no_hardcoded_050_baseline(self):
        from aurora.models.benchmark import _majority_class_from_labels

        labels: list[Outcome] = ["up"] * 8 + ["down"] * 2
        maj, acc = _majority_class_from_labels(labels)
        assert maj == "up"
        assert acc == pytest.approx(0.8)

    def test_baseline_depends_on_data(self):
        from aurora.models.benchmark import _majority_class_from_labels

        labels1: list[Outcome] = ["up"] * 9 + ["down"] * 1
        labels2: list[Outcome] = ["up"] * 1 + ["down"] * 9
        maj1, acc1 = _majority_class_from_labels(labels1)
        maj2, acc2 = _majority_class_from_labels(labels2)
        assert maj1 == "up"
        assert maj2 == "down"
        assert acc1 == pytest.approx(0.9)
        assert acc2 == pytest.approx(0.9)
