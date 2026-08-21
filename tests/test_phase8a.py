"""Phase 8A: Feature Interaction Research tests."""

from __future__ import annotations

from aurora.benchmark.data import OHLCVBar, OHLCVDataset
from aurora.interaction.ablation import (
    compute_metrics,
    run_ablation,
    walk_forward_evaluate,
)
from aurora.interaction.compute import compute_all_features, compute_interactions, compute_targets
from aurora.interaction.models import BaggedEnsemble, DecisionTreeModel, LogisticRegressionModel
from aurora.interaction.preprocessing import StandardScaler, impute_missing
from aurora.interaction.regimes import RegimeType, detect_regimes
from aurora.interaction.registry import (
    FeatureFamily,
    InteractionType,
    build_feature_registry,
)


def _make_dataset(n: int = 300) -> OHLCVDataset:
    from datetime import datetime, timedelta, timezone
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = 100.0
    import random
    rng = random.Random(42)
    for i in range(n):
        ts = base + timedelta(days=i)
        ret = rng.gauss(0.0001, 0.02)
        price *= 1 + ret
        h = price * (1 + abs(rng.gauss(0, 0.01)))
        l = price * (1 - abs(rng.gauss(0, 0.01)))
        v = rng.uniform(1e6, 1e7)
        bars.append(OHLCVBar(ts, price, h, l, price, v))
    return OHLCVDataset(instrument="TEST", timeframe="1d", bars=tuple(bars))


class TestModels:
    def test_logistic_regression(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model = LogisticRegressionModel(learning_rate=0.1, n_iterations=200)
        model.fit(X, y)
        pred = model.predict(X)
        assert len(pred) == 4
        assert model.feature_importance() == [abs(w) for w in model.weights]

    def test_decision_tree(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
        y = [0.0, 0.0, 1.0, 1.0]
        model = DecisionTreeModel(max_depth=2, min_samples_split=2)
        model.fit(X, y)
        pred = model.predict(X)
        assert len(pred) == 4
        assert all(p in (0.0, 1.0) for p in pred)

    def test_bagged_ensemble(self):
        X = [[float(i), float(i * 2)] for i in range(50)]
        y = [0.0] * 25 + [1.0] * 25
        model = BaggedEnsemble(n_trees=5, max_depth=3, subsample_ratio=0.8)
        model.fit(X, y, seed=42)
        pred = model.predict(X)
        assert len(pred) == 50
        assert all(p in (0.0, 1.0) for p in pred)


class TestPreprocessing:
    def test_standard_scaler(self):
        X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X)
        assert len(X_s) == 3
        assert len(X_s[0]) == 2
        mean_0 = sum(row[0] for row in X_s) / len(X_s)
        assert abs(mean_0) < 0.01

    def test_impute_missing(self):
        X = [[1.0, None], [None, 2.0]]
        result = impute_missing(X, fill_value=0.0)
        assert result == [[1.0, 0.0], [0.0, 2.0]]


class TestRegistry:
    def test_build_registry(self):
        reg = build_feature_registry()
        assert reg.version == "1.0.0"
        assert len(reg.features) == 8
        assert len(reg.interactions) == 5
        assert all(isinstance(f.family, FeatureFamily) for f in reg.features)
        assert all(isinstance(i.interaction_type, InteractionType) for i in reg.interactions)

    def test_feature_ids(self):
        reg = build_feature_registry()
        ids = reg.feature_ids()
        assert "liquidity_sweep" in ids
        assert "rsi_signal" in ids


class TestCompute:
    def test_compute_all_features(self):
        ds = _make_dataset(300)
        features = compute_all_features(ds)
        assert len(features) == 8
        for vals in features.values():
            assert len(vals) == ds.count
            assert any(v is not None for v in vals)

    def test_compute_interactions(self):
        ds = _make_dataset(300)
        features = compute_all_features(ds)
        interactions = compute_interactions(features)
        assert len(interactions) == 5
        for vals in interactions.values():
            assert len(vals) == ds.count

    def test_compute_targets(self):
        ds = _make_dataset(300)
        targets = compute_targets(ds.closes(), horizon=4)
        assert len(targets) == 300
        assert targets[-5] is not None
        assert targets[-1] is None


class TestMetrics:
    def test_compute_metrics(self):
        y_true = [1.0, 0.0, 1.0, 1.0, 0.0]
        y_pred = [1.0, 0.0, 0.0, 1.0, 1.0]
        y_proba = [0.8, 0.2, 0.4, 0.9, 0.6]
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.directional_accuracy == 0.6
        assert m.n_observations == 5
        assert m.f1 > 0

    def test_perfect_prediction(self):
        y_true = [1.0, 0.0, 1.0, 0.0]
        y_pred = [1.0, 0.0, 1.0, 0.0]
        y_proba = [0.9, 0.1, 0.9, 0.1]
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.directional_accuracy == 1.0
        assert m.brier_score < 0.01


class TestAblation:
    def test_walk_forward_evaluate(self):
        import random
        rng = random.Random(42)
        X = [[rng.gauss(0, 1), rng.gauss(0, 1)] for _ in range(300)]
        y = [1.0 if x[0] + x[1] > 0 else 0.0 for x in X]
        m, imp = walk_forward_evaluate(X, y, ["f1", "f2"], "logistic", n_folds=2, min_train=100)
        assert m.n_observations > 0
        assert len(imp) == 2

    def test_run_ablation(self):
        ds = _make_dataset(300)
        features = compute_all_features(ds)
        interactions = compute_interactions(features)
        all_features = {**features, **interactions}
        targets = compute_targets(ds.closes(), horizon=4)
        valid_mask = [targets[i] is not None for i in range(ds.count)]
        groups = {"liquidity": ["liquidity_sweep"], "rsi": ["rsi_signal"]}
        results = run_ablation(all_features, targets, valid_mask, groups, model_type="logistic")
        assert len(results) >= 2


class TestRegimes:
    def test_detect_regimes(self):
        ds = _make_dataset(300)
        regimes = detect_regimes(ds)
        assert RegimeType.HIGH_VOL in regimes
        assert RegimeType.TRENDING in regimes
        assert len(regimes[RegimeType.HIGH_VOL]) == 300
