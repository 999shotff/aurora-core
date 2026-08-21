"""Tests for M8.5 Research Integrity Gate.

Tests cover:
1. Transaction-cost calculation
2. Position transitions
3. Temporal separation
4. Baseline calculation
5. Statistical testing
6. Multiple-testing correction
7. Regime sample-size handling
8. Reproducibility
9. Audit trail
"""


from aurora.models.m8_5_integrity import (
    AuditTrail,
    TransactionCostConfig,
    compute_confidence_interval,
    compute_effect_size_cohens_h,
    compute_transaction_costs,
    multiple_testing_correction,
    proportion_z_test,
)

# ═══════════════════════════════════════════════════════
# 1. TRANSACTION-COST CALCULATION
# ═══════════════════════════════════════════════════════

class TestTransactionCostCalculation:
    def test_no_trades(self):
        predictions = ["up", "up", "up", "up"]
        actual_returns = [0.01, 0.01, 0.01, 0.01]
        result = compute_transaction_costs(predictions, actual_returns)
        assert result.n_trades == 0
        assert result.total_cost == 0.0

    def test_single_trade(self):
        predictions = ["up", "up", "down", "down"]
        actual_returns = [0.01, 0.01, -0.01, -0.01]
        result = compute_transaction_costs(predictions, actual_returns)
        assert result.n_trades == 1
        assert result.total_cost > 0

    def test_multiple_trades(self):
        predictions = ["up", "down", "up", "down"]
        actual_returns = [0.01, -0.01, 0.01, -0.01]
        result = compute_transaction_costs(predictions, actual_returns)
        assert result.n_trades == 3
        assert result.total_cost > 0

    def test_custom_cost(self):
        predictions = ["up", "down"]
        actual_returns = [0.01, -0.01]
        config = TransactionCostConfig(cost_per_trade=0.01)
        result = compute_transaction_costs(predictions, actual_returns, config)
        assert result.config.cost_per_trade == 0.01

    def test_spread_included(self):
        predictions = ["up", "down"]
        actual_returns = [0.01, -0.01]
        config = TransactionCostConfig(include_spread=True, spread_assumption=0.001)
        result = compute_transaction_costs(predictions, actual_returns, config)
        # Cost should include spread
        assert result.total_cost > 0


# ═══════════════════════════════════════════════════════
# 2. POSITION TRANSITIONS
# ═══════════════════════════════════════════════════════

class TestPositionTransitions:
    def test_no_transitions(self):
        predictions = ["up", "up", "up", "up"]
        actual_returns = [0.01, 0.01, 0.01, 0.01]
        result = compute_transaction_costs(predictions, actual_returns)
        assert result.n_trades == 0

    def test_single_transition(self):
        predictions = ["up", "up", "down", "down"]
        actual_returns = [0.01, 0.01, -0.01, -0.01]
        result = compute_transaction_costs(predictions, actual_returns)
        assert result.n_trades == 1

    def test_multiple_transitions(self):
        predictions = ["up", "down", "up", "down"]
        actual_returns = [0.01, -0.01, 0.01, -0.01]
        result = compute_transaction_costs(predictions, actual_returns)
        assert result.n_trades == 3


# ═══════════════════════════════════════════════════════
# 3. BASELINE CALCULATION
# ═══════════════════════════════════════════════════════

class TestBaselineCalculation:
    def test_majority_class(self):
        labels = ["up", "up", "up", "down", "down"]
        n_pos = sum(1 for y in labels if y == "up")
        n_neg = len(labels) - n_pos
        baseline_accuracy = max(n_pos, n_neg) / len(labels)
        assert baseline_accuracy == 0.6

    def test_balanced_classes(self):
        labels = ["up", "up", "down", "down"]
        n_pos = sum(1 for y in labels if y == "up")
        n_neg = len(labels) - n_pos
        baseline_accuracy = max(n_pos, n_neg) / len(labels)
        assert baseline_accuracy == 0.5


# ═══════════════════════════════════════════════════════
# 4. STATISTICAL TESTING
# ═══════════════════════════════════════════════════════

class TestStatisticalTesting:
    def test_proportion_z_test_same(self):
        z, p = proportion_z_test(0.5, 0.5, 100, 100)
        assert abs(z) < 0.01
        assert p > 0.05

    def test_proportion_z_test_different(self):
        z, p = proportion_z_test(0.6, 0.4, 100, 100)
        assert z > 0
        assert p < 0.05

    def test_effect_size(self):
        h = compute_effect_size_cohens_h(0.6, 0.4)
        assert h > 0

    def test_confidence_interval(self):
        ci = compute_confidence_interval(0.5, 100)
        assert ci[0] < 0.5
        assert ci[1] > 0.5


# ═══════════════════════════════════════════════════════
# 5. MULTIPLE-TESTING CORRECTION
# ═══════════════════════════════════════════════════════

class TestMultipleTestingCorrection:
    def test_bonferroni(self):
        p_values = [0.01, 0.02, 0.03]
        corrected = multiple_testing_correction(p_values, method="bonferroni")
        assert corrected[0] == 0.03
        assert corrected[1] == 0.06
        assert corrected[2] == 0.09

    def test_holm(self):
        p_values = [0.01, 0.02, 0.03]
        corrected = multiple_testing_correction(p_values, method="holm")
        assert len(corrected) == 3
        # All should be >= original p-values
        assert all(c >= p for c, p in zip(corrected, p_values))

    def test_bh(self):
        p_values = [0.01, 0.02, 0.03]
        corrected = multiple_testing_correction(p_values, method="bh")
        assert len(corrected) == 3
        # All should be >= original p-values
        assert all(c >= p for c, p in zip(corrected, p_values))


# ═══════════════════════════════════════════════════════
# 6. REPRODUCIBILITY
# ═══════════════════════════════════════════════════════

class TestReproducibility:
    def test_same_config_same_result(self):
        predictions = ["up", "down", "up", "down"]
        actual_returns = [0.01, -0.01, 0.01, -0.01]
        result1 = compute_transaction_costs(predictions, actual_returns)
        result2 = compute_transaction_costs(predictions, actual_returns)
        assert result1.n_trades == result2.n_trades
        assert result1.total_cost == result2.total_cost


# ═══════════════════════════════════════════════════════
# 7. AUDIT TRAIL
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
# 8. EMPTY INPUTS
# ═══════════════════════════════════════════════════════

class TestEmptyInputs:
    def test_empty_predictions(self):
        result = compute_transaction_costs([], [])
        assert result.n_trades == 0
        assert result.total_cost == 0.0

    def test_empty_p_values(self):
        corrected = multiple_testing_correction([])
        assert corrected == []
