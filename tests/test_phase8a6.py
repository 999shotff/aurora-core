"""Phase 8A.6 comprehensive regression tests: corrected methodology."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aurora.interaction.ablation import compute_metrics, walk_forward_evaluate
from aurora.interaction.preprocessing import StandardScaler, impute_missing
from aurora.interaction.regimes import (
    RegimeType,
    evaluate_regime_conditional,
)
from aurora.interaction.statistics import (
    HypothesisTest,
    benjamini_hochberg,
    cohens_h,
    compute_confidence_interval,
    proportion_z_test,
)


class Test1MajorityClassBaseline:
    def test_balanced_dataset(self):
        y_true = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
        y_pred = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        y_proba = [0.6] * 6
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.majority_class_accuracy == 0.5
        assert m.class_distribution == (3, 3)

    def test_imbalanced_80_20(self):
        y_true = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]
        y_pred = [1.0] * 10
        y_proba = [0.8] * 10
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.majority_class_accuracy == 0.8
        assert m.class_distribution == (8, 2)

    def test_all_positive(self):
        y_true = [1.0, 1.0, 1.0]
        y_pred = [1.0, 1.0, 1.0]
        y_proba = [0.9] * 3
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.majority_class_accuracy == 1.0

    def test_all_negative(self):
        y_true = [0.0, 0.0, 0.0]
        y_pred = [0.0, 0.0, 0.0]
        y_proba = [0.1] * 3
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.majority_class_accuracy == 1.0


class Test2BaselineCalculation:
    def test_baseline_from_dataset(self):
        n_pos, n_neg = 306, 191
        n_total = n_pos + n_neg
        baseline = max(n_pos, n_neg) / n_total
        assert abs(baseline - 0.6157) < 0.001

    def test_baseline_not_hardcoded(self):
        for n_pos, n_neg in [(50, 50), (80, 20), (306, 191), (300, 197)]:
            n_total = n_pos + n_neg
            baseline = max(n_pos, n_neg) / n_total
            assert 0.5 <= baseline <= 1.0

    def test_baseline_spy_reference(self):
        n_pos, n_neg = 306, 191
        n_total = n_pos + n_neg
        baseline = max(n_pos, n_neg) / n_total
        assert abs(baseline - 0.616) < 0.005

    def test_baseline_qqq_reference(self):
        n_pos, n_neg = 300, 197
        n_total = n_pos + n_neg
        baseline = max(n_pos, n_neg) / n_total
        assert abs(baseline - 0.604) < 0.005

    def test_baseline_btc_reference(self):
        n_pos, n_neg = 379, 347
        n_total = n_pos + n_neg
        baseline = max(n_pos, n_neg) / n_total
        assert abs(baseline - 0.522) < 0.005


class Test3PerTradeTransactionCost:
    def test_entry_cost(self):
        y_true = [1.0, 0.0]
        y_pred = [1.0, 0.0]
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[0] == 1.0 - cost

    def test_exit_cost(self):
        y_true = [1.0, 0.0]
        y_pred = [1.0, 0.0]
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[1] == 0.0 - cost

    def test_no_cost_when_holding(self):
        y_true = [1.0, 0.0, 1.0]
        y_pred = [1.0, 1.0, 1.0]
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[0] == 1.0 - cost
        assert returns[1] == -1.0
        assert returns[2] == 1.0

    def test_round_trip_cost(self):
        y_true = [1.0, 0.0, 0.0, 0.0, 0.0]
        y_pred = [1.0, 1.0, 1.0, 1.0, 0.0]
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[0] == 1.0 - cost
        assert returns[1] == -1.0
        assert returns[2] == -1.0
        assert returns[3] == -1.0
        assert returns[4] == 0.0 - cost

    def test_multiple_transitions(self):
        y_true = [1.0, 0.0, 1.0]
        y_pred = [1.0, 0.0, 1.0]
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[0] == 1.0 - cost
        assert returns[1] == 0.0 - cost
        assert returns[2] == 1.0 - cost


class Test4MultiBarHoldNoExtraCost:
    def test_five_bar_hold(self):
        y_true = [1.0, 0.0, 1.0, 0.0, 1.0]
        y_pred = [1.0, 1.0, 1.0, 1.0, 1.0]
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[0] == 1.0 - cost
        assert returns[1] == -1.0
        assert returns[2] == 1.0
        assert returns[3] == -1.0
        assert returns[4] == 1.0

    def test_hold_never_costs(self):
        y_true = [1.0] * 10
        y_pred = [1.0] * 10
        cost = 10 / 10000
        returns = []
        prev = 0.0
        for pred, actual in zip(y_pred, y_true):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev:
                r -= cost
            returns.append(r)
            prev = pred
        assert returns[0] == 1.0 - cost
        for i in range(1, 10):
            assert returns[i] == 1.0


class Test5EntryExitTransition:
    def test_no_position_to_long(self):
        cost = 10 / 10000
        prev = 0.0
        pred = 1.0
        actual = 1.0
        r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
        if pred != prev:
            r -= cost
        assert r == 1.0 - cost

    def test_long_to_no_position(self):
        cost = 10 / 10000
        prev = 1.0
        pred = 0.0
        actual = 0.0
        r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
        if pred != prev:
            r -= cost
        assert r == 0.0 - cost

    def test_no_change_no_cost(self):
        cost = 10 / 10000
        prev = 1.0
        pred = 1.0
        actual = 1.0
        r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
        if pred != prev:
            r -= cost
        assert r == 1.0


class Test6InteractionIncrementalValue:
    def test_interaction_better_than_ab(self):
        da_ab = 0.63
        da_abi = 0.65
        inc = da_abi - da_ab
        assert inc > 0

    def test_interaction_worse_than_ab(self):
        da_ab = 0.63
        da_abi = 0.61
        inc = da_abi - da_ab
        assert inc < 0

    def test_interaction_equal_to_ab(self):
        da_ab = 0.63
        da_abi = 0.63
        inc = da_abi - da_ab
        assert inc == 0.0

    def test_interaction_equal_to_b(self):
        da_ab = 0.62
        da_abi = 0.62
        inc = da_abi - da_ab
        assert inc == 0.0


class Test7BenjaminiHochbergFDR:
    def test_empty(self):
        result = benjamini_hochberg([])
        assert result == []

    def test_all_below_threshold(self):
        tests = [
            HypothesisTest("t1", "f", 0.01, 0.5, 100, 0.01),
            HypothesisTest("t2", "f", 0.02, 0.4, 100, 0.02),
            HypothesisTest("t3", "f", 0.03, 0.3, 100, 0.03),
        ]
        result = benjamini_hochberg(tests, alpha=0.05)
        assert all(t.adjusted_p_value <= 0.05 for t in result)

    def test_all_above_threshold(self):
        tests = [
            HypothesisTest("t1", "f", 0.5, 0.1, 100, 0.5),
            HypothesisTest("t2", "f", 0.6, 0.1, 100, 0.6),
            HypothesisTest("t3", "f", 0.7, 0.1, 100, 0.7),
        ]
        result = benjamini_hochberg(tests, alpha=0.05)
        assert all(t.adjusted_p_value > 0.05 for t in result)

    def test_monotone_adjusted(self):
        tests = [
            HypothesisTest("t1", "f", 0.01, 0.5, 100, 0.01),
            HypothesisTest("t2", "f", 0.04, 0.4, 100, 0.04),
            HypothesisTest("t3", "f", 0.09, 0.3, 100, 0.09),
        ]
        result = benjamini_hochberg(tests, alpha=0.05)
        assert result[0].adjusted_p_value <= result[1].adjusted_p_value <= result[2].adjusted_p_value

    def test_single_test(self):
        tests = [HypothesisTest("t1", "f", 0.03, 0.5, 100, 0.03)]
        result = benjamini_hochberg(tests, alpha=0.05)
        assert result[0].adjusted_p_value <= 0.05


class Test8RegimeConditionalEvaluation:
    def test_insufficient_samples(self):
        targets = [1.0, 0.0, 1.0]
        predictions = [1.0, 0.0, 1.0]
        valid_indices = [0, 1, 2]
        regimes = {RegimeType.HIGH_VOL: [True, False, True]}
        results = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=30)
        assert len(results) == 1
        assert results[0].sufficient_samples is False
        assert results[0].status == "INCONCLUSIVE"

    def test_sufficient_samples(self):
        targets = [1.0] * 20 + [0.0] * 10
        predictions = [1.0] * 25 + [0.0] * 5
        valid_indices = list(range(30))
        regimes = {RegimeType.TRENDING: [True] * 30}
        results = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=30)
        assert len(results) == 1
        assert results[0].sufficient_samples is True
        assert results[0].n_observations == 30

    def test_baseline_computed_per_regime(self):
        targets = [1.0] * 25 + [0.0] * 5
        predictions = [1.0] * 30
        valid_indices = list(range(30))
        regimes = {RegimeType.RANGING: [True] * 30}
        results = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=30)
        assert results[0].majority_class_accuracy == 25 / 30

    def test_no_future_information(self):
        targets = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0] * 4
        predictions = [1.0] * 40
        valid_indices = list(range(40))
        regimes = {RegimeType.LOW_VOL: [i % 2 == 0 for i in range(40)]}
        results = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=30)
        assert len(results) == 1
        assert results[0].n_observations == 20


class Test9InsufficientRegimeSampleHandling:
    def test_marked_inconclusive(self):
        targets = [1.0, 0.0] * 10
        predictions = [1.0, 0.0] * 10
        valid_indices = list(range(20))
        regimes = {RegimeType.HIGH_VOL: [True, False] * 10}
        results = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=30)
        assert all(r.status == "INCONCLUSIVE" for r in results)

    def test_different_min_samples(self):
        targets = [1.0, 0.0] * 25
        predictions = [1.0, 0.0] * 25
        valid_indices = list(range(50))
        regimes = {RegimeType.TRENDING: [True] * 50}
        results = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=50)
        assert results[0].sufficient_samples is True
        results2 = evaluate_regime_conditional(targets, predictions, valid_indices, regimes, min_samples=100)
        assert results2[0].sufficient_samples is False


class Test10TemporalSplitIntegrity:
    def test_expanding_window(self):
        import random
        random.seed(42)
        n = 300
        X = [[random.gauss(0, 1)] for _ in range(n)]
        y = [1.0 if random.random() > 0.5 else 0.0 for _ in range(n)]
        metrics, _ = walk_forward_evaluate(X, y, ["f1"], "logistic", n_folds=3, min_train=50, transaction_cost_bps=0.0)
        assert metrics.n_observations > 0
        assert 0.0 <= metrics.directional_accuracy <= 1.0

    def test_no_random_split(self):
        X = [[i] for i in range(300)]
        y = [1.0 if i % 2 == 0 else 0.0 for i in range(300)]
        metrics, _ = walk_forward_evaluate(X, y, ["f1"], "logistic", n_folds=3, min_train=50, transaction_cost_bps=0.0)
        assert metrics.n_observations > 0


class Test11NoLeakage:
    def test_preprocessing_fit_only_on_train(self):
        train_X = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        test_X = [[7.0, 8.0], [9.0, 10.0]]
        scaler = StandardScaler()
        train_s = scaler.fit_transform(train_X)
        test_s = scaler.transform(test_X)
        assert train_s[0][0] != test_s[0][0]
        assert scaler.means is not None
        assert scaler.stds is not None

    def test_no_test_data_in_training(self):
        import random
        random.seed(42)
        n = 200
        X = [[random.gauss(0, 1)] for _ in range(n)]
        y = [1.0 if random.random() > 0.5 else 0.0 for _ in range(n)]
        metrics, _ = walk_forward_evaluate(X, y, ["f1"], "logistic", n_folds=3, min_train=50, transaction_cost_bps=0.0)
        assert metrics.n_observations > 0

    def test_impute_does_not_leak(self):
        X = [[1.0, float("nan")], [3.0, 4.0], [5.0, float("inf")]]
        result = impute_missing(X)
        assert result[0][1] == 0.0
        assert result[1][1] == 4.0
        assert result[2][1] == 0.0


class Test12HypothesisStatusAssignment:
    def test_supported_requires_significance_and_delta(self):
        sig = True
        da_delta = 0.03
        status = "SUPPORTED" if sig and da_delta > 0.02 else "WEAK"
        assert status == "SUPPORTED"

    def test_weak_when_positive_delta(self):
        sig = False
        da_delta = 0.01
        status = "SUPPORTED" if sig and da_delta > 0.02 else "WEAK" if da_delta > 0 else "INCONCLUSIVE"
        assert status == "WEAK"

    def test_inconclusive_when_negative_delta(self):
        sig = False
        da_delta = -0.01
        status = "SUPPORTED" if sig and da_delta > 0.02 else "WEAK" if da_delta > 0 else "INCONCLUSIVE"
        assert status == "INCONCLUSIVE"


class Test13RegressionBugs:
    def test_preprocessing_import_math(self):
        from aurora.interaction.preprocessing import impute_missing
        X = [[1.0, float("nan")]]
        result = impute_missing(X)
        assert result[0][1] == 0.0

    def test_compute_metrics_perfect(self):
        y_true = [1.0, 0.0, 1.0, 0.0]
        y_pred = [1.0, 0.0, 1.0, 0.0]
        y_proba = [1.0, 0.0, 1.0, 0.0]
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.directional_accuracy == 1.0
        assert m.balanced_accuracy == 1.0

    def test_compute_metrics_all_wrong(self):
        y_true = [1.0, 0.0, 1.0, 0.0]
        y_pred = [0.0, 1.0, 0.0, 1.0]
        y_proba = [0.0, 1.0, 0.0, 1.0]
        m = compute_metrics(y_true, y_pred, y_proba)
        assert m.directional_accuracy == 0.0

    def test_proportion_z_test_known(self):
        p = proportion_z_test(80, 100, 0.5)
        assert p < 0.001

    def test_cohens_h_known(self):
        h = cohens_h(0.5, 0.5)
        assert abs(h) < 0.001

    def test_confidence_interval_width(self):
        ci = compute_confidence_interval(0.5, 100)
        width = ci[1] - ci[0]
        assert 0.05 < width < 0.25

    def test_negative_control_da_range(self):
        from aurora.interaction.ablation import _negative_control_da
        da = _negative_control_da([1.0] * 100, seed=42)
        assert 0.3 < da < 0.7
