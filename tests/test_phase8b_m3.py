from datetime import datetime, timezone

import pytest

from aurora.features.base import FeatureVector
from aurora.models.base import ModelAuditTrail, ModelInput, ModelOutput
from aurora.models.baselines import MajorityClassAdapter
from aurora.models.benchmark import BenchmarkHarness, _compute_metrics, _majority_class_from_labels
from aurora.models.classical import (
    DecisionTreeAdapter,
    LogisticRegressionAdapter,
    RandomForestAdapter,
)
from aurora.models.registry import ModelRegistry
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


def _make_dataset(
    n: int = 100,
    instrument: str = "BTCUSD",
) -> tuple[list[ModelInput], list[Outcome]]:
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


# ── 1. LogisticRegressionAdapter fitting ──

class TestLogisticRegressionFitting:
    def test_fit_does_not_raise(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)

    def test_fitted_flag_set(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        assert adapter.is_ready() is False
        adapter.fit(inputs, labels)
        assert adapter.is_ready() is True

    def test_fit_empty_raises(self):
        adapter = LogisticRegressionAdapter()
        with pytest.raises(ValueError, match="empty"):
            adapter.fit([], [])

    def test_fit_length_mismatch_raises(self):
        adapter = LogisticRegressionAdapter()
        inputs = [_make_input()] * 5
        labels: list[Outcome] = ["up"] * 3
        with pytest.raises(ValueError, match="length mismatch"):
            adapter.fit(inputs, labels)


# ── 2. LogisticRegressionAdapter prediction ──

class TestLogisticRegressionPrediction:
    def test_predict_returns_model_output(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert isinstance(out, ModelOutput)

    def test_predict_valid_outcome(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.outcome in ("up", "down")

    def test_predict_probability_in_range(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert 0.0 <= out.probability <= 1.0

    def test_predict_not_abstained(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.abstained is False

    def test_unfitted_abstains(self):
        adapter = LogisticRegressionAdapter()
        out = adapter.predict(_make_input())
        assert out.abstained is True
        assert out.outcome == "unknown"


# ── 3. DecisionTreeAdapter fitting ──

class TestDecisionTreeFitting:
    def test_fit_does_not_raise(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)

    def test_fitted_flag_set(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        assert adapter.is_ready() is False
        adapter.fit(inputs, labels)
        assert adapter.is_ready() is True


# ── 4. DecisionTreeAdapter prediction ──

class TestDecisionTreePrediction:
    def test_predict_returns_model_output(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert isinstance(out, ModelOutput)

    def test_predict_valid_outcome(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.outcome in ("up", "down")

    def test_predict_probability_in_range(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert 0.0 <= out.probability <= 1.0


# ── 5. RandomForestAdapter (if implemented) ──

class TestRandomForestAdapter:
    def test_fit_does_not_raise(self):
        adapter = RandomForestAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)

    def test_predict_returns_model_output(self):
        adapter = RandomForestAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert isinstance(out, ModelOutput)
        assert out.outcome in ("up", "down")


# ── 6. Model registry integration ──

class TestRegistryIntegration:
    def test_register_logistic(self):
        reg = ModelRegistry()
        meta = reg.register(LogisticRegressionAdapter())
        assert meta.model_type == "logistic_regression"

    def test_register_decision_tree(self):
        reg = ModelRegistry()
        meta = reg.register(DecisionTreeAdapter())
        assert meta.model_type == "decision_tree"

    def test_register_random_forest(self):
        reg = ModelRegistry()
        meta = reg.register(RandomForestAdapter())
        assert meta.model_type == "random_forest"


# ── 7. Metadata ──

class TestMetadata:
    def test_logistic_metadata(self):
        adapter = LogisticRegressionAdapter()
        meta = adapter.metadata()
        assert meta.model_type == "logistic_regression"
        assert meta.framework == "custom_python"
        assert "learning_rate" in meta.configuration

    def test_tree_metadata(self):
        adapter = DecisionTreeAdapter()
        meta = adapter.metadata()
        assert meta.model_type == "decision_tree"
        assert "max_depth" in meta.configuration

    def test_forest_metadata(self):
        adapter = RandomForestAdapter()
        meta = adapter.metadata()
        assert meta.model_type == "random_forest"
        assert "n_trees" in meta.configuration


# ── 8. Deterministic random state ──

class TestDeterminism:
    def test_logistic_deterministic(self):
        inputs, labels = _make_dataset()
        r1 = LogisticRegressionAdapter()
        r2 = LogisticRegressionAdapter()
        r1.fit(inputs, labels)
        r2.fit(inputs, labels)
        o1 = r1.predict(_make_input())
        o2 = r2.predict(_make_input())
        assert o1.probability == pytest.approx(o2.probability)

    def test_tree_deterministic(self):
        inputs, labels = _make_dataset()
        r1 = DecisionTreeAdapter()
        r2 = DecisionTreeAdapter()
        r1.fit(inputs, labels)
        r2.fit(inputs, labels)
        o1 = r1.predict(_make_input())
        o2 = r2.predict(_make_input())
        assert o1.probability == pytest.approx(o2.probability)


# ── 9. Probability output ──

class TestProbabilityOutput:
    def test_logistic_probability_distribution_sums_to_one(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        total = out.probability_distribution["up"] + out.probability_distribution["down"]
        assert total == pytest.approx(1.0)

    def test_tree_probability_distribution_sums_to_one(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        total = out.probability_distribution["up"] + out.probability_distribution["down"]
        assert total == pytest.approx(1.0)


# ── 10. Invalid input ──

class TestInvalidInput:
    def test_schema_mismatch_rejected(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="schema mismatch"):
            adapter.predict(_make_input(feature_schema_version="99.0.0"))

    def test_leakage_in_test_rejected(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"future_price": True},
                )
            )


# ── 11. Empty dataset ──

class TestEmptyDataset:
    def test_fit_empty_raises_logistic(self):
        adapter = LogisticRegressionAdapter()
        with pytest.raises(ValueError, match="empty"):
            adapter.fit([], [])

    def test_fit_empty_raises_tree(self):
        adapter = DecisionTreeAdapter()
        with pytest.raises(ValueError, match="empty"):
            adapter.fit([], [])


# ── 12. Insufficient samples ──

class TestInsufficientSamples:
    def test_single_sample_fit(self):
        adapter = LogisticRegressionAdapter()
        inputs = [_make_input()]
        labels: list[Outcome] = ["up"]
        adapter.fit(inputs, labels)
        assert adapter.is_ready() is True


# ── 13. Feature schema mismatch ──

class TestFeatureSchemaMismatch:
    def test_mismatch_rejected(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="schema mismatch"):
            adapter.predict(_make_input(feature_schema_version="2.0.0"))


# ── 14. Temporal train/validation/test separation ──

class TestTemporalSeparation:
    def test_benchmark_chronological_split(self):
        harness = BenchmarkHarness()
        inputs, labels = _make_dataset(n=100)
        adapter = LogisticRegressionAdapter()
        report = harness.run(
            models=[adapter],
            all_inputs=inputs,
            all_labels=labels,
            train_ratio=0.6,
            val_ratio=0.2,
        )
        assert report.n_train == 60
        assert report.n_val == 20
        assert report.n_test == 20

    def test_train_before_val_before_test(self):
        harness = BenchmarkHarness()
        inputs, labels = _make_dataset(n=100)
        adapter = DecisionTreeAdapter()
        report = harness.run(
            models=[adapter],
            all_inputs=inputs,
            all_labels=labels,
            train_ratio=0.6,
            val_ratio=0.2,
        )
        train_end = datetime.fromisoformat(report.train_period[1])
        val_start = datetime.fromisoformat(report.val_period[0])
        val_end = datetime.fromisoformat(report.val_period[1])
        test_start = datetime.fromisoformat(report.test_period[0])
        assert train_end <= val_start
        assert val_end <= test_start


# ── 15. Future leakage rejection ──

class TestFutureLeakageRejection:
    def test_leakage_in_test_context(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"future_target": True},
                )
            )


# ── 16. Test-label leakage rejection ──

class TestLabelLeakageRejection:
    def test_test_label_leakage(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"test_label": True},
                )
            )


# ── 17. Baseline comparison ──

class TestBaselineComparison:
    def test_benchmark_includes_baseline_comparison(self):
        harness = BenchmarkHarness()
        inputs, labels = _make_dataset(n=100)
        majority = MajorityClassAdapter()
        logistic = LogisticRegressionAdapter()
        report = harness.run(
            models=[majority, logistic],
            all_inputs=inputs,
            all_labels=labels,
        )
        assert len(report.results) == 2
        for result in report.results:
            assert result.majority_class_accuracy > 0
            assert isinstance(result.accuracy_delta, float)


# ── 18. Benchmark reproducibility ──

class TestBenchmarkReproducibility:
    def test_same_config_same_result(self):
        inputs, labels = _make_dataset(n=80)
        r1 = BenchmarkHarness().run(
            models=[LogisticRegressionAdapter()],
            all_inputs=inputs,
            all_labels=labels,
            experiment_id="rep1",
        )
        r2 = BenchmarkHarness().run(
            models=[LogisticRegressionAdapter()],
            all_inputs=inputs,
            all_labels=labels,
            experiment_id="rep2",
        )
        a1 = r1.results[0].accuracy
        a2 = r2.results[0].accuracy
        assert a1 == pytest.approx(a2)


# ── 19. Audit trail creation ──

class TestAuditTrailCreation:
    def test_logistic_audit_trail(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        trail = adapter.audit_trail()
        assert isinstance(trail, ModelAuditTrail)
        assert trail.model_id == "logistic_regression"
        assert trail.training_period[0] != "unknown"

    def test_tree_audit_trail(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        trail = adapter.audit_trail()
        assert trail.model_id == "decision_tree"

    def test_forest_audit_trail(self):
        adapter = RandomForestAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        trail = adapter.audit_trail()
        assert trail.model_id == "random_forest"


# ── 20. Abstention behavior ──

class TestAbstentionBehavior:
    def test_unfitted_abstains_logistic(self):
        adapter = LogisticRegressionAdapter()
        out = adapter.predict(_make_input())
        assert out.abstained is True
        assert out.abstention_reason == "model not fitted"

    def test_unfitted_abstains_tree(self):
        adapter = DecisionTreeAdapter()
        out = adapter.predict(_make_input())
        assert out.abstained is True

    def test_fitted_does_not_abstain(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.abstained is False


# ── 21. Metric calculation ──

class TestMetricCalculation:
    def test_compute_metrics_basic(self):
        actuals: list[Outcome] = ["up", "up", "down", "down"]
        preds: list[Outcome] = ["up", "down", "down", "up"]
        probs = [0.8, 0.3, 0.4, 0.7]
        abstained = [False, False, False, False]
        m = _compute_metrics(actuals, preds, probs, abstained)
        assert m["accuracy"] == pytest.approx(0.5)
        assert m["n_correct"] == 2
        assert m["n_incorrect"] == 2

    def test_compute_metrics_all_abstained(self):
        actuals: list[Outcome] = ["up", "down"]
        preds: list[Outcome] = ["unknown", "unknown"]
        probs = [0.5, 0.5]
        abstained = [True, True]
        m = _compute_metrics(actuals, preds, probs, abstained)
        assert m["abstention_rate"] == 1.0
        assert m["accuracy"] == 0.0

    def test_majority_class_from_labels_fn(self):
        labels: list[Outcome] = ["up", "up", "up", "down"]
        maj, acc = _majority_class_from_labels(labels)
        assert maj == "up"
        assert acc == pytest.approx(0.75)


# ── 22. No fabricated calibration ──

class TestNoFabricatedCalibration:
    def test_calibration_status_is_none(self):
        adapter = LogisticRegressionAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.calibration_status == "none"
        assert out.calibration_score is None

    def test_tree_calibration_status_is_none(self):
        adapter = DecisionTreeAdapter()
        inputs, labels = _make_dataset()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.calibration_status == "none"


# ── 23. Instrument-agnostic operation ──

class TestInstrumentAgnostic:
    def test_works_with_different_instruments(self):
        for inst in ("BTCUSD", "SPY", "QQQ", "ETHUSD"):
            adapter = LogisticRegressionAdapter()
            inputs, labels = _make_dataset(n=30, instrument=inst)
            adapter.fit(inputs, labels)
            out = adapter.predict(_make_input(instrument=inst))
            assert out.outcome in ("up", "down")
            assert adapter.model_id == "logistic_regression"
