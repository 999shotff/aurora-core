"""Tests for Phase 14: Advanced Model + Ensemble + Feature Selection + Risk Research."""

import pytest

from aurora.models.phase14 import (
    MODEL_REGISTRY,
    GradientBoostingClassifier,
    _compute_classification_metrics,
    _log_loss,
    _sigmoid,
    compute_diversity,
    create_model_phase14,
    ensemble_hard_vote,
    ensemble_soft_vote,
    ensemble_weighted_vote,
    evaluate_calibration,
    model_based_importance,
    permutation_importance,
)


class TestGradientBoosting:
    def test_fit_predict(self):
        X = [[i * 0.1, i * 0.05] for i in range(100)]
        y = [1.0 if i % 2 == 0 else 0.0 for i in range(100)]
        model = GradientBoostingClassifier(n_estimators=10, learning_rate=0.1)
        model.fit(X, y)
        probs = model.predict_proba(X)
        assert len(probs) == 100
        assert all(0 <= p <= 1 for p in probs)

    def test_predict_threshold(self):
        X = [[i * 0.1] for i in range(50)]
        y = [1.0 if i < 25 else 0.0 for i in range(50)]
        model = GradientBoostingClassifier(n_estimators=5, learning_rate=0.1)
        model.fit(X, y)
        preds = model.predict(X, threshold=0.5)
        assert len(preds) == 50
        assert all(p in (0.0, 1.0) for p in preds)

    def test_feature_importance(self):
        import random
        rng = random.Random(42)
        X = [[rng.random(), rng.random(), rng.random()] for i in range(100)]
        y = [1.0 if X[i][0] > 0.5 else 0.0 for i in range(100)]
        model = GradientBoostingClassifier(n_estimators=10, learning_rate=0.1, random_seed=42)
        model.fit(X, y)
        imp = model.feature_importance()
        assert len(imp) >= 1
        assert all(v >= 0 for v in imp)

    def test_deterministic(self):
        X = [[i * 0.1] for i in range(50)]
        y = [1.0 if i % 2 == 0 else 0.0 for i in range(50)]
        m1 = GradientBoostingClassifier(n_estimators=5, random_seed=42)
        m1.fit(X, y)
        m2 = GradientBoostingClassifier(n_estimators=5, random_seed=42)
        m2.fit(X, y)
        p1 = m1.predict_proba(X)
        p2 = m2.predict_proba(X)
        assert p1 == p2


class TestModelFactory:
    def test_logistic_regression(self):
        model = create_model_phase14("logistic_regression", {"learning_rate": 0.01, "n_iterations": 100})
        assert model is not None

    def test_decision_tree(self):
        model = create_model_phase14("decision_tree", {"max_depth": 4})
        assert model is not None

    def test_random_forest(self):
        model = create_model_phase14("random_forest", {"n_trees": 5, "max_depth": 3})
        assert model is not None

    def test_gradient_boosting(self):
        model = create_model_phase14("gradient_boosting", {"n_estimators": 10})
        assert model is not None

    def test_unknown_model(self):
        with pytest.raises(ValueError):
            create_model_phase14("unknown_model")

    def test_model_registry(self):
        assert "logistic_regression" in MODEL_REGISTRY
        assert "gradient_boosting" in MODEL_REGISTRY


class TestEnsemble:
    def test_hard_vote(self):
        preds_a = ["up", "up", "down", "down"]
        preds_b = ["up", "down", "up", "down"]
        result = ensemble_hard_vote([preds_a, preds_b])
        assert result.voting_method == "hard"
        assert result.n_models == 2
        assert len(result.predictions) == 4

    def test_soft_vote(self):
        probs_a = [0.7, 0.3, 0.6]
        probs_b = [0.6, 0.4, 0.5]
        result = ensemble_soft_vote([probs_a, probs_b])
        assert result.voting_method == "soft"
        assert len(result.probabilities) == 3
        assert all(0 <= p <= 1 for p in result.probabilities)

    def test_weighted_vote(self):
        probs_a = [0.7, 0.3]
        probs_b = [0.6, 0.4]
        result = ensemble_weighted_vote([probs_a, probs_b], [0.6, 0.4])
        assert result.voting_method == "weighted"
        assert len(result.predictions) == 2


class TestDiversity:
    def test_identical_predictions(self):
        preds = ["up", "up", "down"]
        result = compute_diversity(preds, preds, [0.6, 0.7, 0.4], [0.6, 0.7, 0.4], ["up", "up", "down"])
        assert result.prediction_agreement == 1.0
        assert result.disagreement_rate == 0.0

    def test_opposite_predictions(self):
        preds_a = ["up", "up", "up"]
        preds_b = ["down", "down", "down"]
        result = compute_diversity(preds_a, preds_b, [0.8, 0.8, 0.8], [0.2, 0.2, 0.2], ["up", "down", "up"])
        assert result.prediction_agreement == 0.0
        assert result.disagreement_rate == 1.0


class TestCalibration:
    def test_perfect_calibration(self):
        y_true = ["up", "up", "down", "down"]
        y_prob = [0.9, 0.8, 0.2, 0.1]
        result = evaluate_calibration(y_true, y_prob, n_bins=5)
        assert result.brier_score >= 0
        assert result.mean_calibration_error >= 0

    def test_empty(self):
        result = evaluate_calibration([], [], n_bins=5)
        assert result.brier_score == 0.5


class TestMetrics:
    def test_sigmoid(self):
        assert _sigmoid(0) == 0.5
        assert _sigmoid(100) > 0.99
        assert _sigmoid(-100) < 0.01

    def test_log_loss(self):
        y_true = [1.0, 0.0, 1.0]
        y_pred = [0.9, 0.1, 0.8]
        loss = _log_loss(y_true, y_pred)
        assert loss < 0.5

    def test_classification_metrics(self):
        y_true = ["up", "up", "down", "down"]
        y_pred = ["up", "down", "up", "down"]
        y_prob = [0.7, 0.3, 0.6, 0.4]
        result = _compute_classification_metrics(y_true, y_pred, y_prob)
        assert result["accuracy"] == 0.5
        assert result["balanced_accuracy"] >= 0
        assert result["precision"] >= 0
        assert result["recall"] >= 0
        assert result["f1"] >= 0


class TestFeatureSelection:
    def test_permutation_importance(self):
        X = [[i * 0.1, i * 0.05] for i in range(50)]
        y = [1.0 if i % 2 == 0 else 0.0 for i in range(50)]
        model = GradientBoostingClassifier(n_estimators=5, learning_rate=0.1)
        model.fit(X, y)
        result = permutation_importance(model, X[:20], y[:20], ["f1", "f2"], n_repeats=2)
        assert result.method == "permutation"
        assert result.n_selected > 0
        assert len(result.importance_scores) == 2

    def test_model_based_importance(self):
        X = [[i * 0.1, i * 0.05] for i in range(50)]
        y = [1.0 if i % 2 == 0 else 0.0 for i in range(50)]
        model = GradientBoostingClassifier(n_estimators=5, learning_rate=0.1)
        model.fit(X, y)
        result = model_based_importance(model, ["f1", "f2"])
        assert result.method == "model_based"
        assert result.n_selected > 0
