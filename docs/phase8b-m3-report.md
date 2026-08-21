# AURORA CORE — Phase 8B Milestone 3 Report: Classical ML Adapters + Benchmark Harness

**Date:** 2026-08-16
**Status:** COMPLETE
**Tests:** 747 passed (697 existing + 50 new)
**Ruff:** All checks passed
**Mypy:** Success: no issues found in 7 source files

---

## 1. Models Implemented

| Adapter | model_id | Underlying Model | Source |
|---------|----------|-----------------|--------|
| `LogisticRegressionAdapter` | `logistic_regression` | `interaction.models.LogisticRegressionModel` | Pure Python, no deps |
| `DecisionTreeAdapter` | `decision_tree` | `interaction.models.DecisionTreeModel` | Pure Python, no deps |
| `RandomForestAdapter` | `random_forest` | `interaction.models.BaggedEnsemble` | Pure Python, no deps |

**Decision: RandomForest implemented** — uses existing `BaggedEnsemble` from `interaction/models.py`, no new dependencies required.

---

## 2. Mathematical/Model Definitions

### 2.1 Logistic Regression

```
Model: SGD logistic regression with L2 regularization.
P(up) = sigmoid(w·x + b)
Loss: binary cross-entropy + L2 penalty
Optimization: stochastic gradient descent, n_iterations passes

Hyperparameters:
    learning_rate: 0.01 (default)
    n_iterations: 500 (default)
    l2_penalty: 0.001 (default)
    threshold: 0.5 (default)
```

### 2.2 Decision Tree

```
Model: Binary classification tree with Gini impurity.
Split criterion: Gini gain > 0
Stopping: max_depth, min_samples_split, or pure node

Hyperparameters:
    max_depth: 4 (default)
    min_samples_split: 10 (default)
    threshold: 0.5 (default)
```

### 2.3 Random Forest (Bagged Ensemble)

```
Model: Bootstrap-aggregated decision trees.
Each tree trained on random subsample with replacement.

Hyperparameters:
    n_trees: 10 (default)
    max_depth: 3 (default)
    subsample_ratio: 0.8 (default)
    seed: 42 (default)
    threshold: 0.5 (default)
```

---

## 3. Dependencies

**No new dependencies added.** All models use existing pure-Python implementations from `interaction/models.py`.

- scikit-learn: NOT installed, NOT needed
- PyTorch: NOT installed, NOT needed
- TensorFlow: NOT installed, NOT needed

---

## 4. Benchmark Architecture

```
BenchmarkHarness.run()
    ├─ Chronological split (no shuffling)
    │   ├─ Train: inputs[:n_train], labels[:n_train]
    │   ├─ Validation: inputs[n_train:n_train+n_val]
    │   └─ Test: inputs[n_train+n_val:]
    │
    ├─ For each model:
    │   ├─ fit(train_inputs, train_labels)
    │   ├─ predict(test_inputs) → test_outputs
    │   ├─ Compute metrics
    │   └─ Create ModelAuditTrail
    │
    └─ Return BenchmarkReport
```

---

## 5. Train/Validation/Test Methodology

### 5.1 Chronological Splitting

- Data is split by time index, never shuffled
- Train period → Validation period → Test period
- Each period is contiguous and non-overlapping

### 5.2 Default Ratios

- Train: 60%
- Validation: 20%
- Test: 20%

### 5.3 Validation

- Train end ≤ Validation start
- Validation end ≤ Test start
- Verified by test: `test_train_before_val_before_test`

---

## 6. Leakage Protections

### 6.1 Input Validation

All adapters inherit `validate_input()` from `ModelAdapter`:

- Test context + leakage flags → raises ValueError
- Schema version mismatch → raises ValueError

### 6.2 Temporal Safety

- Fit only on training data
- Validation data used for model selection (future milestone)
- Test data completely unseen during fitting

### 6.3 Tests Proving Leakage Protection

| Test | What it proves |
|------|----------------|
| `test_leakage_in_test_context` | Future data rejected in test context |
| `test_test_label_leakage` | Test labels cannot influence fitting |
| `test_train_before_val_before_test` | Chronological order preserved |
| `test_schema_mismatch_rejected` | Feature schema mismatch rejected |
| `test_fit_empty_raises` | Empty training data rejected |
| `test_fit_length_mismatch_raises` | Feature/label alignment enforced |

---

## 7. Metrics

### 7.1 Classification Metrics

| Metric | Formula | When Available |
|--------|---------|----------------|
| Accuracy | (TP+TN) / N | Always |
| Balanced Accuracy | (Sensitivity + Specificity) / 2 | Always |
| Precision | TP / (TP+FP) | When TP+FP > 0 |
| Recall | TP / (TP+FN) | When TP+FN > 0 |
| F1 | 2·P·R / (P+R) | When P+R > 0 |
| ROC-AUC | Mann-Whitney U statistic | When both classes present |
| Log Loss | -mean(y·log(p) + (1-y)·log(1-p)) | Always |

### 7.2 Confusion Matrix

```
[[TN, FP],
 [FN, TP]]
```

### 7.3 Timing Metrics

- `train_duration_ms`: Time to fit model
- `inference_duration_ms`: Time to predict all test samples

### 7.4 Baseline Comparison

- `majority_class_accuracy`: Dynamically computed from training labels
- `accuracy_delta`: model_accuracy - majority_class_accuracy
- `majority_class_label`: The actual majority class (not hardcoded 0.50)

---

## 8. Baseline Comparison

Every classical model is compared against:

1. **Majority class** — dynamically computed from training labels
2. **Deterministic random** — uniform predictions
3. **Buy and hold** — always "up"

The benchmark report includes:
- Absolute metric difference from majority-class baseline
- Relative improvement where mathematically meaningful
- INCONCLUSIVE status when sample size insufficient

---

## 9. Calibration Status

All models explicitly mark `calibration_status="none"` and `calibration_score=None`.

No fabricated calibration values. Raw model probabilities are presented as-is.

---

## 10. Abstention

### 10.1 Abstention Conditions

- Model not fitted → abstains with reason "model not fitted"
- Invalid input → raises ValueError (does not abstain silently)

### 10.2 Abstention Output

```python
ModelOutput(
    outcome="unknown",
    probability=0.5,
    confidence=0.0,
    uncertainty=1.0,
    abstained=True,
    abstention_reason="model not fitted",
)
```

---

## 11. Audit Trail

Every fitted model creates a `ModelAuditTrail` with:

| Field | Source |
|-------|--------|
| model_id | From adapter |
| model_version | From adapter |
| training_period | Min/max timestamps from training inputs |
| validation_period | Set by benchmark harness |
| test_period | Set by benchmark harness |
| dataset_version | From first training input |
| feature_schema_version | From first training input |
| hyperparameters | Model-specific configuration |
| random_seed | 42 (default) or user-specified |
| evaluation_metrics | Computed by benchmark |
| calibration_method | "none" |
| promotion_decision | "INCONCLUSIVE" (requires evaluation) |

---

## 12. Reproducibility

### 12.1 Deterministic Behavior

- Same data + same model + same config → same predictions
- Verified by test: `test_same_config_same_result`
- Logistic regression: deterministic SGD (no random initialization)
- Decision tree: deterministic split selection
- Random forest: seeded RNG (seed=42 default)

### 12.2 Benchmark Reproducibility

```python
harness = BenchmarkHarness()
r1 = harness.run(models=[model], all_inputs=X, all_labels=y)
r2 = harness.run(models=[model], all_inputs=X, all_labels=y)
assert r1.results[0].accuracy == r2.results[0].accuracy
```

---

## 13. Tests

### 13.1 Test Categories (50 tests)

| Category | Count | Coverage |
|----------|-------|----------|
| LogisticRegression fitting | 4 | Fit, ready, empty, mismatch |
| LogisticRegression prediction | 5 | Output, outcome, probability, abstained, unfitted |
| DecisionTree fitting | 2 | Fit, ready |
| DecisionTree prediction | 3 | Output, outcome, probability |
| RandomForest | 2 | Fit, predict |
| Registry integration | 3 | All adapters |
| Metadata | 3 | All adapters |
| Determinism | 2 | Logistic, tree |
| Probability output | 2 | Distribution sums to 1 |
| Invalid input | 2 | Schema mismatch, leakage |
| Empty dataset | 2 | Logistic, tree |
| Insufficient samples | 1 | Single sample |
| Feature schema mismatch | 1 | Mismatch rejected |
| Temporal separation | 2 | Chronological split, ordering |
| Future leakage | 1 | Test context leakage |
| Test-label leakage | 1 | Label leakage |
| Baseline comparison | 1 | Benchmark includes baselines |
| Benchmark reproducibility | 1 | Same config same result |
| Audit trail creation | 3 | All adapters |
| Abstention behavior | 3 | Unfitted, fitted |
| Metric calculation | 3 | Basic, all abstained, majority class |
| No fabricated calibration | 2 | Status is none |
| Instrument-agnostic | 1 | Multiple instruments |

---

## 14. Verification Results

### 14.1 Pytest

```
747 passed, 1 warning in 30.99s
```

- 697 existing tests: all pass
- 50 new tests: all pass
- No regressions

### 14.2 Ruff

```
All checks passed!
```

### 14.3 Mypy

```
Success: no issues found in 7 source files
```

---

## 15. Limitations

| Limitation | Severity | Mitigation |
|-----------|----------|------------|
| Logistic regression is binary only | LOW | Labels mapped to up=1, down=0 |
| No multi-class support yet | LOW | Flat/unknown treated as down |
| No hyperparameter tuning | LOW | Manual configuration |
| No feature selection | LOW | All features used |
| No regularization scheduling | LOW | Fixed L2 penalty |
| No early stopping | LOW | Fixed iterations |

---

## 16. Deferred Work

| Item | Reason | Milestone |
|------|--------|-----------|
| scikit-learn integration | Not needed — pure Python sufficient | Future if needed |
| Hyperparameter tuning | Requires validation framework | Milestone 4+ |
| Feature selection | Requires more analysis | Milestone 4+ |
| Multi-class classification | Binary sufficient for baseline | Future |

---

## 17. Files Changed

| File | Action |
|------|--------|
| `src/aurora/models/classical.py` | Created — 3 classical ML adapters |
| `src/aurora/models/benchmark.py` | Created — Benchmark harness |
| `src/aurora/models/__init__.py` | Modified — added exports |
| `tests/test_phase8b_m3.py` | Created — 50 tests |
| `docs/phase8b-m3-report.md` | Created — this report |

---

**STOP. Milestone 3 complete. Do not begin Milestone 4.**
