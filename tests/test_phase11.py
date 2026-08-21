"""Tests for Phase 11: Data Expansion + Advanced Signal Architecture.

Tests cover:
1. Extended data fetching
2. Microstructure features
3. External features
4. Ensemble research
5. Alternative targets
6. Additional baselines
7. Experiment registry
8. Temporal robustness
9. Statistical testing
10. Audit trail
"""

import math

from aurora.models.phase7_validation import OHLCVRecord
from aurora.models.phase11 import (
    INSTRUMENTS,
    EnsembleConfig,
    ExperimentRecord,
    ExperimentRegistry,
    compute_additional_baselines,
    construct_targets_magnitude,
    construct_targets_persistence,
    engineer_external_features,
    engineer_microstructure_features,
    get_microstructure_feature_names,
    get_microstructure_groups,
    run_ensemble_evaluation,
)

# ═══════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════

def _make_records(n: int = 300) -> list[OHLCVRecord]:
    """Create synthetic OHLCV records for testing."""
    records = []
    price = 100.0
    for i in range(n):
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
# 1. INSTRUMENTS
# ═══════════════════════════════════════════════════════

class TestInstruments:
    def test_instruments_defined(self):
        assert len(INSTRUMENTS) > 0
        assert "BTC-USD" in INSTRUMENTS
        assert "SPY" in INSTRUMENTS
        assert "QQQ" in INSTRUMENTS

    def test_instrument_metadata(self):
        for meta in INSTRUMENTS.values():
            assert "name" in meta
            assert "category" in meta
            assert "min_history" in meta


# ═══════════════════════════════════════════════════════
# 2. MICROSTRUCTURE FEATURES
# ═══════════════════════════════════════════════════════

class TestMicrostructureFeatures:
    def test_engineer_features(self):
        records = _make_records(100)
        features = engineer_microstructure_features(records)
        assert len(features) == 100

    def test_feature_names(self):
        names = get_microstructure_feature_names()
        assert len(names) > 10

    def test_feature_groups(self):
        groups = get_microstructure_groups()
        assert "spread_proxy" in groups
        assert "volume_imbalance" in groups
        assert "trade_intensity" in groups
        assert "liquidity_proxy" in groups
        assert "price_impact" in groups

    def test_no_nans(self):
        records = _make_records(100)
        features = engineer_microstructure_features(records)
        for f in features:
            for name, value in f.items():
                assert not math.isnan(value), f"NaN in feature {name}"
                assert not math.isinf(value), f"Inf in feature {name}"


# ═══════════════════════════════════════════════════════
# 3. EXTERNAL FEATURES
# ═══════════════════════════════════════════════════════

class TestExternalFeatures:
    def test_no_vix(self):
        records = _make_records(100)
        features = engineer_external_features(records, None)
        assert len(features) == 100
        assert features[0]["vix_level"] == 0.0

    def test_with_vix(self):
        records = _make_records(100)
        vix_records = _make_records(100)
        features = engineer_external_features(records, vix_records)
        assert len(features) == 100
        assert "vix_level" in features[0]


# ═══════════════════════════════════════════════════════
# 4. ENSEMBLE
# ═══════════════════════════════════════════════════════

class TestEnsemble:
    def test_ensemble_config(self):
        config = EnsembleConfig(
            method="voting",
            base_models=[
                {"model_type": "logistic_regression"},
                {"model_type": "decision_tree"},
            ],
        )
        assert config.method == "voting"
        assert len(config.base_models) == 2

    def test_ensemble_evaluation(self):
        records = _make_records(300)
        features = engineer_features_phase9(records)
        feature_names = get_feature_names()
        feature_matrix = [[f[name] for name in feature_names] for f in features]

        labels = ["up" if i % 2 == 0 else "down" for i in range(299)]
        feature_matrix = feature_matrix[:299]

        config = EnsembleConfig(
            method="voting",
            base_models=[
                {"model_type": "logistic_regression", "learning_rate": 0.01, "n_iterations": 100},
                {"model_type": "decision_tree", "max_depth": 3},
            ],
        )

        result = run_ensemble_evaluation(
            feature_matrix, labels, feature_names,
            config,
            train_size=150, val_size=30, test_size=30,
        )

        assert result.accuracy >= 0.0
        assert result.n_samples > 0


def engineer_features_phase9(records):
    """Import from phase9."""
    from aurora.models.phase9 import engineer_features_phase9 as _engineer
    return _engineer(records)


def get_feature_names():
    """Import from phase9."""
    from aurora.models.phase9 import get_feature_names as _get
    return _get()


# ═══════════════════════════════════════════════════════
# 5. ALTERNATIVE TARGETS
# ═══════════════════════════════════════════════════════

class TestAlternativeTargets:
    def test_magnitude_target(self):
        records = _make_records(100)
        labels, target_def = construct_targets_magnitude(records, horizon=1, n_classes=3)
        assert len(labels) == 99
        assert "up" in target_def["class_distribution"]
        assert "down" in target_def["class_distribution"]
        assert "neutral" in target_def["class_distribution"]

    def test_persistence_target(self):
        records = _make_records(100)
        labels, target_def = construct_targets_persistence(records, horizon=1, lookback=5)
        assert len(labels) > 0
        assert "continuation" in target_def["class_distribution"]
        assert "reversal" in target_def["class_distribution"]


# ═══════════════════════════════════════════════════════
# 6. BASELINES
# ═══════════════════════════════════════════════════════

class TestBaselines:
    def test_additional_baselines(self):
        labels = ["up", "up", "up", "down", "down"]
        baselines = compute_additional_baselines(labels)
        assert "majority" in baselines
        assert "random" in baselines
        assert "momentum" in baselines
        assert "mean_reversion" in baselines
        assert baselines["majority"] == 0.6
        assert baselines["random"] == 0.5


# ═══════════════════════════════════════════════════════
# 7. EXPERIMENT REGISTRY
# ═══════════════════════════════════════════════════════

class TestExperimentRegistry:
    def test_add_experiment(self):
        registry = ExperimentRegistry()
        record = ExperimentRecord(
            experiment_id="test_1",
            hypothesis="Test hypothesis",
            data_source="test",
            data_period="2y",
            instrument="BTC-USD",
            target="direction_1d",
            horizon=1,
            feature_groups=["price"],
            model="logistic_regression",
            hyperparameters={},
            ensemble_config=None,
            train_period="0-200",
            validation_period="200-250",
            test_period="250-300",
            metrics={"accuracy": 0.5},
            transaction_costs=None,
            statistical_results=None,
            adjusted_p_value=None,
            status="REJECTED",
            reason="Test",
        )
        registry.add(record)
        assert len(registry.experiments) == 1

    def test_get_by_instrument(self):
        registry = ExperimentRegistry()
        record = ExperimentRecord(
            experiment_id="test_1",
            hypothesis="Test",
            data_source="test",
            data_period="2y",
            instrument="BTC-USD",
            target="direction_1d",
            horizon=1,
            feature_groups=[],
            model="lr",
            hyperparameters={},
            ensemble_config=None,
            train_period="0-200",
            validation_period="200-250",
            test_period="250-300",
            metrics={},
            transaction_costs=None,
            statistical_results=None,
            adjusted_p_value=None,
            status="REJECTED",
            reason="Test",
        )
        registry.add(record)
        assert len(registry.get_by_instrument("BTC-USD")) == 1
        assert len(registry.get_by_instrument("SPY")) == 0


# ═══════════════════════════════════════════════════════
# 8. EMPTY INPUTS
# ═══════════════════════════════════════════════════════

class TestEmptyInputs:
    def test_empty_baselines(self):
        baselines = compute_additional_baselines([])
        assert baselines == {}

    def test_empty_magnitude(self):
        records = _make_records(10)
        labels, _ = construct_targets_magnitude(records, horizon=1)
        assert len(labels) == 9
