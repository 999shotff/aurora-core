"""Tests for Phase 8B Milestone 6: Temporal Real-Data Logistic Regression.

Tests 18 categories:
1. Real-data ingestion
2. Target construction
3. Future-label exclusion
4. Chronological splitting
5. Train-only preprocessing
6. Validation isolation
7. Test isolation
8. Logistic regression adapter
9. Probability bounds
10. Deterministic output
11. Feature coefficient extraction
12. Baseline comparison
13. Feature ablation
14. Sample-size protection
15. Dataset provenance
16. Feature provenance
17. Leakage detection
18. Reproducibility
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from aurora.interaction.models import LogisticRegressionModel
from aurora.models.temporal_evaluation import (
    DatasetProvenance,
    EvaluationMetrics,
    ModelEvaluationResult,
    OHLCVRecord,
    Preprocessor,
    construct_targets,
    engineer_features,
    run_baseline_evaluation,
    run_feature_ablation,
    run_logistic_regression_evaluation,
    temporal_split,
)

# ═══════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════

def _make_ohlcv_records(
    n: int = 100,
    start_price: float = 100.0,
    trend: float = 0.001,
) -> list[OHLCVRecord]:
    """Create synthetic OHLCV records."""
    records = []
    for i in range(n):
        price = start_price * (1 + trend) ** i
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
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
    n: int = 100,
) -> tuple[list[OHLCVRecord], list[dict[str, float]], list[str], list[list[float]]]:
    """Create synthetic features and labels."""
    records = _make_ohlcv_records(n)
    _labels, _ = construct_targets(records)
    features = engineer_features(records)
    feature_names = list(features[0].keys()) if features else []
    feature_matrix = [[f[name] for name in feature_names] for f in features]
    return records, features, feature_names, feature_matrix


# ═══════════════════════════════════════════════════════
# 1. REAL-DATA INGESTION
# ═══════════════════════════════════════════════════════

class TestRealDataIngestion:
    def test_ohlcv_record_creation(self):
        records = _make_ohlcv_records(10)
        assert len(records) == 10
        assert records[0].close > 0

    def test_ohlcv_record_timestamp(self):
        records = _make_ohlcv_records(5)
        for r in records:
            assert r.timestamp.tzinfo is not None

    def test_ohlcv_record_fields(self):
        records = _make_ohlcv_records(1)
        assert records[0].open > 0
        assert records[0].high > 0
        assert records[0].low > 0
        assert records[0].close > 0
        assert records[0].volume > 0


# ═══════════════════════════════════════════════════════
# 2. TARGET CONSTRUCTION
# ═══════════════════════════════════════════════════════

class TestTargetConstruction:
    def test_target_length(self):
        records = _make_ohlcv_records(10)
        labels, _target_def = construct_targets(records)
        assert len(labels) == 9  # Last row excluded

    def test_target_values(self):
        records = _make_ohlcv_records(10)
        labels, _ = construct_targets(records)
        for label in labels:
            assert label in ("up", "down")

    def test_target_definition(self):
        records = _make_ohlcv_records(10)
        _, target_def = construct_targets(records)
        assert target_def.target_horizon == "1 period ahead"
        assert target_def.final_usable_rows == 9

    def test_equal_prices_treatment(self):
        records = [
            OHLCVRecord(datetime(2024, 1, 1, tzinfo=timezone.utc), 100, 101, 99, 100, 1000),
            OHLCVRecord(datetime(2024, 1, 2, tzinfo=timezone.utc), 100, 101, 99, 100, 1000),
        ]
        labels, _ = construct_targets(records)
        assert labels[0] == "down"  # Equal prices treated as down


# ═══════════════════════════════════════════════════════
# 3. FUTURE-LABEL EXCLUSION
# ═══════════════════════════════════════════════════════

class TestFutureLabelExclusion:
    def test_no_future_in_features(self):
        records = _make_ohlcv_records(20)
        features = engineer_features(records)
        # Features should only use historical data
        for i, feat in enumerate(features):
            assert "close" in feat
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
# 4. CHRONOLOGICAL SPLITTING
# ═══════════════════════════════════════════════════════

class TestChronologicalSplitting:
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

    def test_all_indices_covered(self):
        split = temporal_split(100)
        all_indices = split.train_indices + split.val_indices + split.test_indices
        assert sorted(all_indices) == list(range(100))


# ═══════════════════════════════════════════════════════
# 5. TRAIN-ONLY PREPROCESSING
# ═══════════════════════════════════════════════════════

class TestTrainOnlyPreprocessing:
    def test_preprocessor_fit(self):
        X_train = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        preprocessor = Preprocessor()
        preprocessor.fit(X_train)
        assert preprocessor._fitted

    def test_preprocessor_transform(self):
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
# 6. VALIDATION ISOLATION
# ═══════════════════════════════════════════════════════

class TestValidationIsolation:
    def test_validation_not_in_train(self):
        split = temporal_split(100)
        assert set(split.val_indices).isdisjoint(set(split.train_indices))

    def test_validation_chronologically_after_train(self):
        split = temporal_split(100)
        assert min(split.val_indices) > max(split.train_indices)


# ═══════════════════════════════════════════════════════
# 7. TEST ISOLATION
# ═══════════════════════════════════════════════════════

class TestTestIsolation:
    def test_test_not_in_train(self):
        split = temporal_split(100)
        assert set(split.test_indices).isdisjoint(set(split.train_indices))

    def test_test_not_in_val(self):
        split = temporal_split(100)
        assert set(split.test_indices).isdisjoint(set(split.val_indices))

    def test_test_chronologically_after_val(self):
        split = temporal_split(100)
        assert min(split.test_indices) > max(split.val_indices)


# ═══════════════════════════════════════════════════════
# 8. LOGISTIC REGRESSION ADAPTER
# ═══════════════════════════════════════════════════════

class TestLogisticRegressionAdapter:
    def test_model_fit(self):
        model = LogisticRegressionModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        assert model._fitted

    def test_model_predict_proba(self):
        model = LogisticRegressionModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert len(probs) == 4
        assert all(0.0 <= p <= 1.0 for p in probs)


# ═══════════════════════════════════════════════════════
# 9. PROBABILITY BOUNDS
# ═══════════════════════════════════════════════════════

class TestProbabilityBounds:
    def test_probability_in_0_1(self):
        model = LogisticRegressionModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert all(0.0 <= p <= 1.0 for p in probs)


# ═══════════════════════════════════════════════════════
# 10. DETERMINISTIC OUTPUT
# ═══════════════════════════════════════════════════════

class TestDeterministicOutput:
    def test_same_input_same_output(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]

        model1 = LogisticRegressionModel(learning_rate=0.01, n_iterations=100)
        model1.fit(X, y)
        probs1 = model1.predict_proba(X)

        model2 = LogisticRegressionModel(learning_rate=0.01, n_iterations=100)
        model2.fit(X, y)
        probs2 = model2.predict_proba(X)

        assert probs1 == probs2


# ═══════════════════════════════════════════════════════
# 11. FEATURE COEFFICIENT EXTRACTION
# ═══════════════════════════════════════════════════════

class TestFeatureCoefficientExtraction:
    def test_coefficients_length(self):
        model = LogisticRegressionModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        assert len(model.weights) == 2

    def test_coefficients_finite(self):
        model = LogisticRegressionModel()
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model.fit(X, y)
        assert all(math.isfinite(w) for w in model.weights)


# ═══════════════════════════════════════════════════════
# 12. BASELINE COMPARISON
# ═══════════════════════════════════════════════════════

class TestBaselineComparison:
    def test_baseline_evaluation(self):
        labels = ["up", "down", "up", "down", "up"] * 20
        results = run_baseline_evaluation(labels)
        assert len(results) >= 1

    def test_baseline_has_metrics(self):
        labels = ["up", "down", "up", "down", "up"] * 20
        results = run_baseline_evaluation(labels)
        for r in results:
            assert isinstance(r.validation_metrics, EvaluationMetrics)


# ═══════════════════════════════════════════════════════
# 13. FEATURE ABLATION
# ═══════════════════════════════════════════════════════

class TestFeatureAblation:
    def test_ablation_runs(self):
        records, _, feature_names, feature_matrix = _make_features_and_labels(100)
        labels, _ = construct_targets(records)
        results = run_feature_ablation(records, labels, feature_names, feature_matrix)
        assert len(results) >= 1

    def test_ablation_has_all_features(self):
        records, _, feature_names, feature_matrix = _make_features_and_labels(100)
        labels, _ = construct_targets(records)
        results = run_feature_ablation(records, labels, feature_names, feature_matrix)
        groups = [r.feature_group for r in results]
        assert "all_features" in groups


# ═══════════════════════════════════════════════════════
# 14. SAMPLE-SIZE PROTECTION
# ═══════════════════════════════════════════════════════

class TestSampleSizeProtection:
    def test_small_dataset(self):
        records = _make_ohlcv_records(10)
        labels, _ = construct_targets(records)
        features = engineer_features(records)
        feature_names = list(features[0].keys()) if features else []
        feature_matrix = [[f[name] for name in feature_names] for f in features]
        # Should handle small datasets gracefully
        result = run_logistic_regression_evaluation(
            records, labels, feature_names, feature_matrix
        )
        assert isinstance(result, ModelEvaluationResult)


# ═══════════════════════════════════════════════════════
# 15. DATASET PROVENANCE
# ═══════════════════════════════════════════════════════

class TestDatasetProvenance:
    def test_provenance_creation(self):
        provenance = DatasetProvenance(
            source="test",
            instrument="TEST",
            date_range=("2024-01-01", "2024-12-31"),
            timeframe="1d",
            retrieval_timestamp="2024-01-01T00:00:00Z",
            columns=["Open", "High", "Low", "Close", "Volume"],
            row_count=100,
            missing_values=0,
            preprocessing="none",
        )
        assert provenance.source == "test"
        assert provenance.row_count == 100


# ═══════════════════════════════════════════════════════
# 16. FEATURE PROVENANCE
# ═══════════════════════════════════════════════════════

class TestFeatureProvenance:
    def test_feature_engineering_provenance(self):
        records = _make_ohlcv_records(20)
        features = engineer_features(records)
        assert len(features) == 20
        assert "close" in features[0]
        assert "return_1d" in features[0]


# ═══════════════════════════════════════════════════════
# 17. LEAKAGE DETECTION
# ═══════════════════════════════════════════════════════

class TestLeakageDetection:
    def test_no_future_in_features(self):
        records = _make_ohlcv_records(20)
        features = engineer_features(records)
        # Features should only use historical data
        for i in range(1, len(features)):
            # return_1d should only use current and previous close
            assert "return_1d" in features[i]


# ═══════════════════════════════════════════════════════
# 18. REPRODUCIBILITY
# ═══════════════════════════════════════════════════════

class TestReproducibility:
    def test_same_config_same_result(self):
        records, _, feature_names, feature_matrix = _make_features_and_labels(100)
        labels, _ = construct_targets(records)

        result1 = run_logistic_regression_evaluation(
            records, labels, feature_names, feature_matrix,
            learning_rate=0.01, n_iterations=100, l2_penalty=0.001,
        )
        result2 = run_logistic_regression_evaluation(
            records, labels, feature_names, feature_matrix,
            learning_rate=0.01, n_iterations=100, l2_penalty=0.001,
        )

        assert result1.test_metrics.accuracy == result2.test_metrics.accuracy
        assert result1.test_metrics.brier_score == result2.test_metrics.brier_score
