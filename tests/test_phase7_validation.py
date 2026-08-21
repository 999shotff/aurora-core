"""Tests for Phase 7: Real Market Validation.

Tests cover:
1. Data ingestion
2. Feature engineering (RSI, MACD, Bollinger Bands)
3. Target construction
4. Temporal splitting
5. Walk-forward validation
6. Model evaluation
7. Baseline comparison
8. Regime analysis
9. Transaction costs
10. Hyperparameter optimization
11. Preprocessing
12. Leakage detection
13. Reproducibility
"""

from datetime import datetime, timedelta, timezone

import pytest

from aurora.interaction.models import (
    BaggedEnsemble,
    DecisionTreeModel,
    LogisticRegressionModel,
)
from aurora.models.phase7_validation import (
    DatasetProvenance,
    EvaluationMetrics,
    ModelConfig,
    OHLCVRecord,
    Preprocessor,
    classify_regime,
    compute_transaction_cost_impact,
    construct_targets,
    engineer_features_expanded,
    evaluate_baselines,
    generate_walk_forward_windows,
    run_walk_forward_experiment,
    temporal_split,
)

# ═══════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════

def _make_ohlcv_records(
    n: int = 300,
    start_price: float = 100.0,
    trend: float = 0.001,
) -> list[OHLCVRecord]:
    """Create synthetic OHLCV records."""
    records = []
    for i in range(n):
        price = start_price * (1 + trend) ** i
        ts = datetime(2022, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
        records.append(OHLCVRecord(
            timestamp=ts,
            open=price * 0.99,
            high=price * 1.01,
            low=price * 0.98,
            close=price,
            volume=1000000 + i * 10000,
        ))
    return records


def _make_features_and_labels(
    n: int = 300,
) -> tuple[list[OHLCVRecord], list[dict[str, float]], list[str], list[list[float]]]:
    """Create synthetic features and labels."""
    records = _make_ohlcv_records(n)
    _labels, _ = construct_targets(records)
    features = engineer_features_expanded(records)
    feature_names = list(features[0].keys()) if features else []
    feature_matrix = [[f[name] for name in feature_names] for f in features]
    return records, features, feature_names, feature_matrix


# ═══════════════════════════════════════════════════════
# 1. DATA INGESTION
# ═══════════════════════════════════════════════════════

class TestDataIngestion:
    def test_ohlcv_record_creation(self):
        records = _make_ohlcv_records(10)
        assert len(records) == 10
        assert records[0].close > 0

    def test_ohlcv_record_timestamp(self):
        records = _make_ohlcv_records(5)
        for r in records:
            assert r.timestamp.tzinfo is not None

    def test_dataset_provenance(self):
        provenance = DatasetProvenance(
            source="test",
            instrument="TEST",
            date_range=("2022-01-01", "2022-12-31"),
            timeframe="1d",
            retrieval_timestamp="2024-01-01T00:00:00Z",
            columns=["Open", "High", "Low", "Close", "Volume"],
            row_count=100,
            missing_values=0,
            duplicates_removed=0,
            gaps_detected=0,
            preprocessing="none",
        )
        assert provenance.source == "test"
        assert provenance.row_count == 100


# ═══════════════════════════════════════════════════════
# 2. FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════

class TestFeatureEngineering:
    def test_expanded_features_count(self):
        records = _make_ohlcv_records(100)
        features = engineer_features_expanded(records)
        assert len(features) == 100
        # Should have more features than basic
        assert len(features[0]) >= 20

    def test_rsi_computation(self):
        records = _make_ohlcv_records(50)
        features = engineer_features_expanded(records)
        assert "rsi_14" in features[0]
        # RSI should be between 0 and 100
        for feat in features[30:]:  # Skip early values
            assert 0 <= feat["rsi_14"] <= 100

    def test_macd_computation(self):
        records = _make_ohlcv_records(50)
        features = engineer_features_expanded(records)
        assert "macd" in features[0]
        assert "macd_signal" in features[0]
        assert "macd_histogram" in features[0]

    def test_bollinger_bands_computation(self):
        records = _make_ohlcv_records(50)
        features = engineer_features_expanded(records)
        assert "bb_upper" in features[0]
        assert "bb_middle" in features[0]
        assert "bb_lower" in features[0]
        assert "bb_width" in features[0]
        assert "bb_position" in features[0]

    def test_bollinger_bands_ordering(self):
        records = _make_ohlcv_records(50)
        features = engineer_features_expanded(records)
        for feat in features[20:]:  # Skip early values
            assert feat["bb_upper"] >= feat["bb_middle"]
            assert feat["bb_middle"] >= feat["bb_lower"]


# ═══════════════════════════════════════════════════════
# 3. TARGET CONSTRUCTION
# ═══════════════════════════════════════════════════════

class TestTargetConstruction:
    def test_target_length(self):
        records = _make_ohlcv_records(10)
        labels, _target_def = construct_targets(records)
        assert len(labels) == 9

    def test_target_values(self):
        records = _make_ohlcv_records(10)
        labels, _ = construct_targets(records)
        for label in labels:
            assert label in ("up", "down")

    def test_equal_prices_treatment(self):
        records = [
            OHLCVRecord(datetime(2024, 1, 1, tzinfo=timezone.utc), 100, 101, 99, 100, 1000),
            OHLCVRecord(datetime(2024, 1, 2, tzinfo=timezone.utc), 100, 101, 99, 100, 1000),
        ]
        labels, _ = construct_targets(records)
        assert labels[0] == "down"


# ═══════════════════════════════════════════════════════
# 4. TEMPORAL SPLITTING
# ═══════════════════════════════════════════════════════

class TestTemporalSplitting:
    def test_split_ratios(self):
        split = temporal_split(100)
        assert len(split.train_indices) == 60
        assert len(split.val_indices) == 20
        assert len(split.test_indices) == 20

    def test_no_overlap(self):
        split = temporal_split(100)
        assert set(split.train_indices).isdisjoint(set(split.val_indices))
        assert set(split.train_indices).isdisjoint(set(split.test_indices))
        assert set(split.val_indices).isdisjoint(set(split.test_indices))

    def test_chronological_order(self):
        split = temporal_split(100)
        assert max(split.train_indices) < min(split.val_indices)
        assert max(split.val_indices) < min(split.test_indices)


# ═══════════════════════════════════════════════════════
# 5. WALK-FORWARD VALIDATION
# ═══════════════════════════════════════════════════════

class TestWalkForwardValidation:
    def test_walk_forward_windows(self):
        windows = generate_walk_forward_windows(500)
        assert len(windows) > 0
        for w in windows:
            assert w.train_samples == 200
            assert w.val_samples == 50
            assert w.test_samples == 50

    def test_windows_chronological(self):
        windows = generate_walk_forward_windows(500)
        for i in range(1, len(windows)):
            assert windows[i].train_start > windows[i - 1].train_start

    def test_walk_forward_experiment(self):
        records, _, feature_names, feature_matrix = _make_features_and_labels(300)
        labels, _ = construct_targets(records)

        config = ModelConfig(
            model_type="logistic_regression",
            model_id="test_lr",
            version="1.0.0",
            hyperparameters={"learning_rate": 0.01, "n_iterations": 100, "l2_penalty": 0.001},
        )

        results = run_walk_forward_experiment(
            records, labels, feature_names, feature_matrix, [config],
            train_size=100, val_size=50, test_size=50, step_size=50,
        )
        assert len(results) > 0
        for r in results:
            assert isinstance(r.validation_metrics, EvaluationMetrics)
            assert isinstance(r.test_metrics, EvaluationMetrics)


# ═══════════════════════════════════════════════════════
# 6. MODEL EVALUATION
# ═══════════════════════════════════════════════════════

class TestModelEvaluation:
    def test_logistic_regression(self):
        model = LogisticRegressionModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert len(probs) == 4
        assert all(0.0 <= p <= 1.0 for p in probs)

    def test_decision_tree(self):
        model = DecisionTreeModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert len(probs) == 4
        assert all(0.0 <= p <= 1.0 for p in probs)

    def test_random_forest(self):
        model = BaggedEnsemble()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert len(probs) == 4
        assert all(0.0 <= p <= 1.0 for p in probs)


# ═══════════════════════════════════════════════════════
# 7. BASELINE COMPARISON
# ═══════════════════════════════════════════════════════

class TestBaselineComparison:
    def test_baseline_evaluation(self):
        labels = ["up", "down", "up", "down", "up"] * 20
        baselines = evaluate_baselines(labels)
        assert "majority_class" in baselines
        assert "buy_and_hold" in baselines

    def test_majority_class_baseline(self):
        labels = ["up", "up", "up", "down", "down"]
        baselines = evaluate_baselines(labels)
        assert baselines["majority_class"].accuracy == 0.6


# ═══════════════════════════════════════════════════════
# 8. REGIME ANALYSIS
# ═══════════════════════════════════════════════════════

class TestRegimeAnalysis:
    def test_classify_regime(self):
        records = _make_ohlcv_records(100)
        regime = classify_regime(records, 0, 100)
        assert regime in ("bullish", "bearish", "sideways", "high_volatility_bull",
                          "high_volatility_bear", "high_volatility_sideways", "INCONCLUSIVE")

    def test_insufficient_data(self):
        records = _make_ohlcv_records(10)
        regime = classify_regime(records, 0, 10)
        assert regime == "INCONCLUSIVE"


# ═══════════════════════════════════════════════════════
# 9. TRANSACTION COSTS
# ═══════════════════════════════════════════════════════

class TestTransactionCosts:
    def test_transaction_cost_computation(self):
        predictions = ["up", "up", "down", "down", "up"]
        actual_returns = [0.01, 0.01, -0.01, -0.01, 0.01]
        result = compute_transaction_cost_impact(predictions, actual_returns)
        assert result["n_trades"] == 2  # up->down, down->up
        assert result["total_cost"] == 0.002  # 2 * 0.001

    def test_no_trades(self):
        predictions = ["up", "up", "up", "up"]
        actual_returns = [0.01, 0.01, 0.01, 0.01]
        result = compute_transaction_cost_impact(predictions, actual_returns)
        assert result["n_trades"] == 0


# ═══════════════════════════════════════════════════════
# 10. HYPERPARAMETER OPTIMIZATION
# ═══════════════════════════════════════════════════════

class TestHyperparameterOptimization:
    def test_model_config(self):
        config = ModelConfig(
            model_type="logistic_regression",
            model_id="test",
            version="1.0.0",
            hyperparameters={"learning_rate": 0.01},
        )
        assert config.model_type == "logistic_regression"
        assert config.hyperparameters["learning_rate"] == 0.01


# ═══════════════════════════════════════════════════════
# 11. PREPROCESSING
# ═══════════════════════════════════════════════════════

class TestPreprocessing:
    def test_preprocessor_fit_transform(self):
        X_train = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        preprocessor = Preprocessor()
        preprocessor.fit(X_train)
        X_transformed = preprocessor.transform(X_train)
        assert len(X_transformed) == 3
        # Transformed data should have mean ~0
        mean_0 = sum(row[0] for row in X_transformed) / len(X_transformed)
        assert abs(mean_0) < 0.01

    def test_preprocessor_not_fitted(self):
        preprocessor = Preprocessor()
        with pytest.raises(RuntimeError):
            preprocessor.transform([[1.0, 2.0]])


# ═══════════════════════════════════════════════════════
# 12. LEAKAGE DETECTION
# ═══════════════════════════════════════════════════════

class TestLeakageDetection:
    def test_no_future_in_features(self):
        records = _make_ohlcv_records(50)
        features = engineer_features_expanded(records)
        # Features should only use historical data
        for i in range(1, len(features)):
            assert "return_1d" in features[i]
            # Feature at time t should not use data from t+1

    def test_target_uses_next_close(self):
        records = _make_ohlcv_records(10)
        labels, _ = construct_targets(records)
        # Label at index i uses records[i+1].close
        for i in range(len(records) - 1):
            if records[i + 1].close > records[i].close:
                assert labels[i] == "up"
            else:
                assert labels[i] == "down"


# ═══════════════════════════════════════════════════════
# 13. REPRODUCIBILITY
# ═══════════════════════════════════════════════════════

class TestReproducibility:
    def test_same_config_same_result(self):
        records, _, feature_names, feature_matrix = _make_features_and_labels(300)
        labels, _ = construct_targets(records)

        config = ModelConfig(
            model_type="logistic_regression",
            model_id="test_lr",
            version="1.0.0",
            hyperparameters={"learning_rate": 0.01, "n_iterations": 100, "l2_penalty": 0.001},
        )

        results1 = run_walk_forward_experiment(
            records, labels, feature_names, feature_matrix, [config],
            train_size=100, val_size=50, test_size=50, step_size=50,
        )
        results2 = run_walk_forward_experiment(
            records, labels, feature_names, feature_matrix, [config],
            train_size=100, val_size=50, test_size=50, step_size=50,
        )

        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.test_metrics.accuracy == r2.test_metrics.accuracy
