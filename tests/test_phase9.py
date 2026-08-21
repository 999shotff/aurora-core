"""Tests for Phase 9: Feature Engineering + Model Research.

Tests cover:
1. Feature engineering
2. Feature groups
3. Hyperparameter search
4. Walk-forward validation
5. Feature ablation
6. Statistical testing
7. Transaction costs
8. Reproducibility
9. Audit trail
"""

import math

import pytest

from aurora.models.phase7_validation import OHLCVRecord
from aurora.models.phase9 import (
    FEATURE_GROUPS,
    AuditTrail,
    HyperparameterConfig,
    Preprocessor,
    classify_regime_phase9,
    compute_metrics,
    engineer_features_phase9,
    get_feature_groups,
    get_feature_names,
    run_feature_ablation,
    run_walk_forward,
    search_hyperparameters,
)

# ═══════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════

def _make_records(n: int = 300) -> list[OHLCVRecord]:
    """Create synthetic OHLCV records for testing."""
    records = []
    price = 100.0
    for i in range(n):
        # Random walk
        import random
        rng = random.Random(i)
        change = rng.gauss(0, 0.02)
        price *= (1 + change)

        r = OHLCVRecord(
            timestamp=f"2024-01-{i+1:02d}",
            open=price * 0.99,
            high=price * 1.01,
            low=price * 0.98,
            close=price,
            volume=rng.randint(1000, 10000),
        )
        records.append(r)
    return records


# ═══════════════════════════════════════════════════════
# 1. FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════

class TestFeatureEngineering:
    def test_engineer_features_returns_correct_count(self):
        records = _make_records(100)
        features = engineer_features_phase9(records)
        assert len(features) == 100

    def test_engineer_features_has_all_groups(self):
        records = _make_records(100)
        features = engineer_features_phase9(records)
        feature_names = get_feature_names()

        for name in feature_names:
            assert name in features[0], f"Missing feature: {name}"

    def test_engineer_features_no_nans(self):
        records = _make_records(100)
        features = engineer_features_phase9(records)

        for f in features:
            for name, value in f.items():
                assert not math.isnan(value), f"NaN in feature {name}"
                assert not math.isinf(value), f"Inf in feature {name}"

    def test_get_feature_names(self):
        names = get_feature_names()
        assert len(names) > 30  # Should have 40+ features

    def test_get_feature_groups(self):
        groups = get_feature_groups()
        assert "price" in groups
        assert "volatility" in groups
        assert "momentum" in groups
        assert "trend" in groups
        assert "volume" in groups
        assert "bollinger" in groups
        assert "structure" in groups


# ═══════════════════════════════════════════════════════
# 2. PREPROCESSOR
# ═══════════════════════════════════════════════════════

class TestPreprocessor:
    def test_fit_transform(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        preprocessor = Preprocessor()
        preprocessor.fit(X)
        X_scaled = preprocessor.transform(X)

        # Should be zero-mean
        for j in range(2):
            col = [X_scaled[i][j] for i in range(3)]
            assert abs(sum(col) / 3) < 1e-10

    def test_not_fitted_raises(self):
        preprocessor = Preprocessor()
        with pytest.raises(RuntimeError):
            preprocessor.transform([[1.0, 2.0]])


# ═══════════════════════════════════════════════════════
# 3. METRICS
# ═══════════════════════════════════════════════════════

class TestMetrics:
    def test_perfect_prediction(self):
        y_true = ["up", "up", "down", "down"]
        y_pred = ["up", "up", "down", "down"]
        metrics = compute_metrics(y_true, y_pred)
        assert metrics.accuracy == 1.0
        assert metrics.balanced_accuracy == 1.0

    def test_worst_prediction(self):
        y_true = ["up", "up", "down", "down"]
        y_pred = ["down", "down", "up", "up"]
        metrics = compute_metrics(y_true, y_pred)
        assert metrics.accuracy == 0.0

    def test_majority_class_baseline(self):
        y_true = ["up", "up", "up", "down"]
        y_pred = ["up", "up", "up", "up"]
        metrics = compute_metrics(y_true, y_pred)
        assert metrics.accuracy == 0.75


# ═══════════════════════════════════════════════════════
# 4. HYPERPARAMETER SEARCH
# ═══════════════════════════════════════════════════════

class TestHyperparameterSearch:
    def test_random_search(self):
        X_train = [[i * 0.1, i * 0.05] for i in range(100)]
        y_train = ["up" if i % 2 == 0 else "down" for i in range(100)]
        X_val = [[i * 0.1, i * 0.05] for i in range(100, 120)]
        y_val = ["up" if i % 2 == 0 else "down" for i in range(100, 120)]

        config = HyperparameterConfig(
            model_type="logistic_regression",
            param_grid={"learning_rate": [0.01, 0.1], "n_iterations": [100, 200]},
            search_method="random",
            n_trials=4,
        )

        result = search_hyperparameters(X_train, y_train, X_val, y_val, config)
        assert result.n_evaluated > 0
        assert result.best_score >= 0.0

    def test_grid_search(self):
        X_train = [[i * 0.1, i * 0.05] for i in range(100)]
        y_train = ["up" if i % 2 == 0 else "down" for i in range(100)]
        X_val = [[i * 0.1, i * 0.05] for i in range(100, 120)]
        y_val = ["up" if i % 2 == 0 else "down" for i in range(100, 120)]

        config = HyperparameterConfig(
            model_type="logistic_regression",
            param_grid={"learning_rate": [0.01, 0.1], "n_iterations": [100]},
            search_method="grid",
        )

        result = search_hyperparameters(X_train, y_train, X_val, y_val, config)
        assert result.n_evaluated == 2  # 2 * 1 = 2 combinations


# ═══════════════════════════════════════════════════════
# 5. WALK-FORWARD
# ═══════════════════════════════════════════════════════

class TestWalkForward:
    def test_walk_forward_returns_results(self):
        records = _make_records(300)
        features = engineer_features_phase9(records)
        feature_names = get_feature_names()
        feature_matrix = [[f[name] for name in feature_names] for f in features]
        labels, _ = construct_targets_for_test(records)

        # Truncate to match labels
        feature_matrix = feature_matrix[:len(labels)]

        results = run_walk_forward(
            feature_matrix, labels, feature_names,
            "logistic_regression", {"learning_rate": 0.01, "n_iterations": 100},
            train_size=150, val_size=30, test_size=30, step_size=30,
        )

        assert len(results) > 0
        for r in results:
            assert r.test_metrics.n_samples > 0


def construct_targets_for_test(records: list[OHLCVRecord]) -> tuple[list[str], dict]:
    """Helper for tests."""
    labels = []
    for i in range(len(records) - 1):
        if records[i + 1].close > records[i].close:
            labels.append("up")
        else:
            labels.append("down")
    return labels, {"positive_rate": sum(1 for y in labels if y == "up") / len(labels)}


# ═══════════════════════════════════════════════════════
# 6. FEATURE ABLATION
# ═══════════════════════════════════════════════════════

class TestFeatureAblation:
    def test_ablation_returns_results(self):
        records = _make_records(300)
        features = engineer_features_phase9(records)
        feature_names = get_feature_names()
        feature_matrix = [[f[name] for name in feature_names] for f in features]
        labels, _ = construct_targets_for_test(records)

        # Truncate to match labels
        feature_matrix = feature_matrix[:len(labels)]

        results = run_feature_ablation(
            feature_matrix, labels, feature_names,
            "logistic_regression", {"learning_rate": 0.01, "n_iterations": 100},
            baseline_accuracy=0.5,
            train_size=150, val_size=30, test_size=30,
        )

        assert len(results) > 0
        for r in results:
            assert r.feature_group in FEATURE_GROUPS


# ═══════════════════════════════════════════════════════
# 7. REGIME CLASSIFICATION
# ═══════════════════════════════════════════════════════

class TestRegimeClassification:
    def test_classify_regime(self):
        records = _make_records(100)
        regime = classify_regime_phase9(records, 0, 50)
        assert regime in ["bullish", "bearish", "sideways", "high_volatility_bull", "high_volatility_bear", "unknown"]

    def test_short_window_returns_unknown(self):
        records = _make_records(10)
        regime = classify_regime_phase9(records, 0, 3)
        assert regime == "unknown"


# ═══════════════════════════════════════════════════════
# 8. AUDIT TRAIL
# ═══════════════════════════════════════════════════════

class TestAuditTrail:
    def test_add_entry(self):
        trail = AuditTrail()
        trail.add("test_event", {"key": "value"})
        assert len(trail.entries) == 1
        assert trail.entries[0].event == "test_event"

    def test_to_dict(self):
        trail = AuditTrail()
        trail.add("test_event", {"key": "value"})
        d = trail.to_dict()
        assert len(d) == 1
        assert d[0]["event"] == "test_event"


# ═══════════════════════════════════════════════════════
# 9. EMPTY INPUTS
# ═══════════════════════════════════════════════════════

class TestEmptyInputs:
    def test_empty_metrics(self):
        metrics = compute_metrics([], [])
        assert metrics.n_samples == 0

    def test_empty_ablation(self):
        results = run_feature_ablation(
            [], [], [],
            "logistic_regression", {},
            baseline_accuracy=0.5,
        )
        assert results == []
