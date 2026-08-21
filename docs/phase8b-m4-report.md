# AURORA CORE — Phase 8B Milestone 4 Report: ML Correctness, Calibration & Model-Selection Validation

**Date:** 2026-08-16
**Status:** COMPLETE
**Tests:** 798 passed (747 existing + 51 new)
**Ruff:** All checks passed
**Mypy:** Success: no issues found in 9 source files

---

## 1. Mathematical Verification

### 1.1 Sigmoid Function

```
sigmoid(z) = 1 / (1 + exp(-z))
```

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| `test_sigmoid_zero` | z=0.0 | 0.5 | ✅ PASS |
| `test_sigmoid_large_positive` | z=500.0 | 1.0 | ✅ PASS |
| `test_sigmoid_large_negative` | z=-500.0 | 0.0 | ✅ PASS |
| `test_sigmoid_symmetry` | z, -z | sigmoid(z) + sigmoid(-z) = 1.0 | ✅ PASS |

### 1.2 Numerical Stability

| Test | Condition | Result |
|------|-----------|--------|
| `test_extreme_positive_z` | z=1000.0 | No NaN/Inf, p≈1.0 |
| `test_extreme_negative_z` | z=-1000.0 | No NaN/Inf, p≈0.0 |
| `test_large_features_no_nan` | Features ±1e6 | All probabilities finite |
| `test_predict_proba_bounds` | Various inputs | All p ∈ [0,1] |

### 1.3 Logistic Regression Properties

| Property | Verified |
|----------|----------|
| Coefficients are finite | ✅ |
| Intercept handled correctly | ✅ |
| Single-feature behavior | ✅ |
| Constant-feature behavior | ✅ |
| Probabilities in [0,1] | ✅ |

---

## 2. Decision Tree Verification

### 2.1 Split Selection

| Test | Condition | Result |
|------|-----------|--------|
| `test_tree_splits_on_separable_data` | Linearly separable | Root is not leaf |
| `test_tree_impurity_pure_node` | All same class | Prediction = 1.0 |
| `test_tree_single_class` | All zeros | Prediction = 0.0 |

### 2.2 Probabilities

| Test | Condition | Result |
|------|-----------|--------|
| `test_probabilities_between_zero_and_one` | Various inputs | All p ∈ [0,1] |
| `test_leaf_prediction_is_proportion` | 2/5 positive | Prediction = 0.4 |

### 2.3 Edge Cases

- Empty partitions → handled (prediction = 0.5)
- Constant features → no split (leaf node)
- Single class → pure leaf
- No infinite recursion (depth limit enforced)

---

## 3. Random Forest Verification

### 3.1 Determinism

| Test | Condition | Result |
|------|-----------|--------|
| `test_same_seed_same_result` | seed=42, same data | Identical probabilities |
| `test_different_seeds_may_differ` | seed=42 vs seed=99 | Both valid, may differ |

### 3.2 Bootstrap

- Subsampling with replacement via `random.Random(seed)`
- Subsample ratio configurable (default 0.8)
- Each tree trained on independent bootstrap sample

### 3.3 Aggregation

- Probability = mean of tree predictions
- Valid for any number of trees ≥ 1

---

## 4. Probability Integrity

### 4.1 Bounds

| Model | Test | Result |
|-------|------|--------|
| Logistic Regression | `test_logistic_output_bounds` | All p ∈ [0,1] ✅ |
| Decision Tree | `test_tree_output_bounds` | All p ∈ [0,1] ✅ |
| Random Forest | `test_forest_output_bounds` | All p ∈ [0,1] ✅ |

### 4.2 Summation

| Model | Test | Result |
|-------|------|--------|
| Logistic Regression | `test_logistic_distribution_sums_to_one` | P(up) + P(down) = 1.0 ✅ |
| Decision Tree | `test_tree_distribution_sums_to_one` | P(up) + P(down) = 1.0 ✅ |

---

## 5. Calibration Methodology

### 5.1 Implemented Metrics

| Metric | Formula | Range |
|--------|---------|-------|
| Brier Score | mean((p-y)²) | [0,1], lower better |
| Expected Calibration Error (ECE) | Σ\|bin_acc - bin_conf\| × bin_fraction | [0,1], lower better |
| Max Calibration Error (MaxCE) | max\|bin_acc - bin_conf\| | [0,1], lower better |

### 5.2 Calibration Status

| Status | Condition |
|--------|-----------|
| `UNCALIBRATED` | No calibration performed |
| `CALIBRATION_EVALUATED` | ECE computed, sufficient data |
| `CALIBRATED` | ECE < 0.05 (future milestone) |
| `CALIBRATION_INCONCLUSIVE` | Insufficient samples |

### 5.3 Important Disclaimer

**Calibration evaluation does NOT imply calibrated probabilities.**
A model producing probabilities does NOT automatically become calibrated.
All models currently have `calibration_status="none"` in their output.

---

## 6. Model-Selection Methodology

### 6.1 Correct Flow

```
TRAIN → fit candidates
VALIDATION → select best
TEST → final evaluation only
```

### 6.2 Selection Criteria

- Default: maximize validation accuracy
- Alternative: minimize validation Brier score
- Selection occurs on VALIDATION data only
- TEST data is NEVER used for selection

### 6.3 Safety Guarantees

| Guarantee | Implementation |
|-----------|---------------|
| Test data not used for selection | Enforced by `ModelSelector.select()` |
| Validation data not used for training | Separate `fit()` and `predict()` calls |
| Training data not contaminated | Chronological splitting |
| Selection is deterministic | Same data + same config = same selection |

---

## 7. Temporal Separation

### 7.1 Chronological Splitting

```
Time ─────────────────────────────────────────────►
│◄── TRAIN ──►│◄── VALIDATION ──►│◄── TEST ──►
```

### 7.2 Verified Properties

| Property | Test | Result |
|----------|------|--------|
| Train end ≤ Val start | `test_chronological_order` | ✅ |
| Val end ≤ Test start | `test_chronological_order` | ✅ |
| No shuffling | Implementation review | ✅ |
| Contiguous periods | Implementation review | ✅ |

---

## 8. Leakage Tests

### 8.1 Attack Vectors Tested

| Attack | Test | Result |
|--------|------|--------|
| Future feature in test context | `test_future_feature_in_test_context` | Rejected ✅ |
| Test label in leakage flags | `test_test_label_in_leakage_flags` | Rejected ✅ |
| Feature schema mismatch | `test_feature_schema_mismatch` | Rejected ✅ |
| Train context allows flags | `test_train_context_allows_leakage_flags` | Allowed ✅ |

### 8.2 Protection Mechanism

- `ModelAdapter.validate_input()` checks:
  - Test context + any leakage flag True → ValueError
  - Schema version mismatch → ValueError
- Train/validation contexts allow flags (for flexibility)

---

## 9. Edge Cases

### 9.1 Tested Scenarios

| Scenario | Test | Result |
|----------|------|--------|
| One-row dataset | `test_one_row_dataset` | Works ✅ |
| Two-class dataset | `test_two_class_dataset` | Works ✅ |
| Constant feature | `test_constant_feature` | Works ✅ |
| Extreme feature values | `test_extreme_feature_values` | No NaN/Inf ✅ |
| Duplicate timestamps | `test_duplicate_timestamps_allowed` | Works ✅ |

---

## 10. Benchmark Integrity

### 10.1 Baseline Calculation

- Majority class computed from TRAINING labels
- No hardcoded 0.50 baseline
- Dynamic per-dataset baseline

### 10.2 Verified Properties

| Property | Test | Result |
|----------|------|--------|
| No hardcoded 0.50 | `test_no_hardcoded_050_baseline` | ✅ |
| Baseline depends on data | `test_baseline_depends_on_data` | ✅ |
| Majority class correct | Manual verification | ✅ |

---

## 11. Tests

### 11.1 Test Categories (51 tests)

| Category | Count | Coverage |
|----------|-------|----------|
| A. Logistic regression math | 8 | Sigmoid, loss, coefficients |
| B. Numerical stability | 4 | Extreme values, NaN/Inf |
| C. Decision tree splitting | 3 | Separable, pure, single class |
| D. Decision tree probabilities | 2 | Bounds, leaf prediction |
| E. Random forest reproducibility | 2 | Same seed, different seeds |
| F. Probability bounds | 3 | All models |
| G. Probability summation | 2 | Distribution sums to 1 |
| H. Brier score | 4 | Perfect, worst, uncertain, empty |
| I. Calibration evaluation | 3 | Perfect, insufficient, ECE range |
| J. Model selection | 2 | Best candidate, validation separation |
| K. Validation/test separation | 1 | Chronological order |
| L. Leakage attacks | 4 | Future feature, test label, schema |
| M. Edge cases | 5 | One-row, two-class, constant, extreme, duplicates |
| N. Audit trail | 3 | All adapters complete |
| O. Reproducibility | 3 | All models deterministic |
| P. Benchmark integrity | 2 | No hardcoded baseline |

---

## 12. Verification Results

### 12.1 Pytest

```
798 passed, 1 warning in 45.87s
```

- 747 existing tests: all pass
- 51 new tests: all pass
- No regressions

### 12.2 Ruff

```
All checks passed!
```

### 12.3 Mypy

```
Success: no issues found in 9 source files
```

---

## 13. Limitations

| Limitation | Severity | Mitigation |
|-----------|----------|------------|
| No automatic calibration | LOW | Status explicitly "none" |
| No hyperparameter tuning | LOW | Manual configuration |
| Binary classification only | LOW | Labels mapped to up/down |
| No feature selection | LOW | All features used |
| No multi-class support | LOW | Flat/unknown treated as down |

---

## 14. Deferred Work

| Item | Reason | Milestone |
|------|--------|-----------|
| Automatic calibration | Requires validation framework | Future |
| Hyperparameter tuning | Requires more analysis | Future |
| Feature selection | Requires domain knowledge | Future |
| Multi-class classification | Binary sufficient for baseline | Future |

---

## 15. Files Changed

| File | Action |
|------|--------|
| `src/aurora/models/calibration.py` | Created — Brier score, ECE, calibration evaluation |
| `src/aurora/models/selection.py` | Created — Model selection with temporal safety |
| `src/aurora/models/__init__.py` | Modified — added exports |
| `tests/test_phase8b_m4.py` | Created — 51 tests |
| `docs/phase8b-m4-report.md` | Created — this report |

---

**IMPORTANT DISCLAIMERS:**

1. **Calibration evaluation does NOT imply calibrated probabilities.** All models currently have `calibration_status="none"`.

2. **Benchmark performance does NOT establish future trading profitability.** These are scientific evaluations of model correctness, not claims of market prediction ability.

---

**STOP. Milestone 4 complete. Do not begin Milestone 5.**
