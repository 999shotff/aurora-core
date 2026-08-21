# AURORA CORE — Phase 8B Milestone 2 Report: Statistical Baseline Adapter

**Date:** 2026-08-16
**Status:** COMPLETE
**Tests:** 697 passed (646 existing + 51 new)
**Ruff:** All checks passed
**Mypy:** Success: no issues found

---

## 1. Implemented Adapters

| Adapter | model_id | Version | Description |
|---------|----------|---------|-------------|
| `MajorityClassAdapter` | `majority_class` | `1.0.0` | Always predicts the most frequent class from training data |
| `DeterministicRandomAdapter` | `deterministic_random` | `1.0.0` | Predicts randomly using a seeded RNG |
| `BuyAndHoldAdapter` | `buy_and_hold` | `1.0.0` | Always predicts "up" with P=1.0 |

---

## 2. Mathematical Definitions

### 2.1 MajorityClass

```
Let C = {c_1, ..., c_k} be the set of unique outcomes in training labels.
Let n_c = |{y in training : y == c}| for each class c.
Let n_total = |training|.

P(c) = n_c / n_total  for each class c.

Prediction = argmax_c P(c).
In case of tie, predicts "down" (conservative default).

Probability = P(predicted_class) derived from training distribution.
Confidence = |P(predicted_class) - 1/n_classes| (distance from uniform).
Uncertainty = 1 - confidence.
```

### 2.2 DeterministicRandom

```
Let seed be a fixed integer.
Let rng = random.Random(seed + hash(input)).
P(outcome) = 1/n_classes for each class.
outcome = outcomes[rng.randint(0, n_classes-1)].

Same seed + same input = same output.
Different seed = different but valid output.
```

### 2.3 BuyAndHold

```
outcome = "up"  (always).
P(up) = 1.0.
P(other) = 0.0.

Reference baseline for long-only strategies.
```

---

## 3. Temporal/Leakage Protections

### 3.1 Input Validation

All adapters inherit `validate_input()` from `ModelAdapter`:

- **Test context leakage:** If `evaluation_context == "test"` and any `leakage_flags` are True, raises ValueError
- **Schema version mismatch:** If `feature_schema_version` doesn't match model's `supported_input_schema`, raises ValueError

### 3.2 MajorityClass Temporal Safety

- `fit()` records training period from input timestamps
- `fit()` records dataset version and feature schema version from inputs
- `predict()` validates input before producing prediction
- No validation/test labels leak into training (adapter only sees what `fit()` receives)

### 3.3 What's NOT Protected (by design)

- The adapter does NOT prevent a model from memorizing test data (that's the temporal validation layer's job)
- The adapter does NOT prevent a model from using future features (that's the feature engineering layer's job)

---

## 4. Probability Behavior

### 4.1 MajorityClass

| Field | Value | Source |
|-------|-------|--------|
| `probability` | `n_majority / n_total` | Computed from training labels |
| `confidence` | `|P(majority) - 1/n_classes|` | Distance from uniform distribution |
| `uncertainty` | `1 - confidence` | Inverse of confidence |
| `calibration_status` | `"none"` | No calibration performed |
| `probability_distribution` | `{cls: n_cls/n_total}` | Full class distribution |

### 4.2 DeterministicRandom

| Field | Value | Source |
|-------|-------|--------|
| `probability` | `1/n_classes` | Uniform distribution |
| `confidence` | `0.0` | No information |
| `uncertainty` | `1.0` | Maximum uncertainty |
| `calibration_status` | `"none"` | No calibration performed |
| `probability_distribution` | `{cls: 1/n_classes}` | Uniform across all outcomes |

### 4.3 BuyAndHold

| Field | Value | Source |
|-------|-------|--------|
| `probability` | `1.0` | Fixed |
| `confidence` | `1.0` | Maximum confidence (but no information) |
| `uncertainty` | `0.0` | Fixed |
| `calibration_status` | `"none"` | No calibration performed |
| `probability_distribution` | `{"up": 1.0, "down": 0.0, "flat": 0.0}` | One-hot |

---

## 5. Deterministic Random Behavior

### 5.1 Seeding Mechanism

```python
input_hash = sha256(f"{instrument}:{timeframe}:{timestamp}").hexdigest()
combined_seed = model_seed + int(input_hash[:8], 16)
rng = random.Random(combined_seed)
```

### 5.2 Deterministic Guarantees

- Same seed + same input → same output (verified by test)
- Different seeds → different outputs (verified by test)
- Seed recorded in `raw_output` field for reproducibility
- Seed stored in metadata and audit trail

---

## 6. Registry Integration

### 6.1 Registration

```python
registry = ModelRegistry()
registry.register(MajorityClassAdapter(), tags=["baseline", "statistical"])
registry.register(DeterministicRandomAdapter(seed=42), tags=["baseline", "random"])
registry.register(BuyAndHoldAdapter(), tags=["baseline", "reference"])
```

### 6.2 Duplicate Prevention

- Same (model_id, version) → raises ValueError
- Same model_id, different version → allowed
- Different model_id, same version → allowed

---

## 7. Audit Trail

Every fitted baseline produces a `ModelAuditTrail` with:

| Field | MajorityClass | DeterministicRandom | BuyAndHold |
|-------|--------------|---------------------|------------|
| `model_id` | `"majority_class"` | `"deterministic_random"` | `"buy_and_hold"` |
| `model_version` | `"1.0.0"` | `"1.0.0"` | `"1.0.0"` |
| `training_period` | From input timestamps | `("unknown", "unknown")` | `("unknown", "unknown")` |
| `dataset_version` | From input | `"unknown"` | `"unknown"` |
| `feature_schema_version` | From input | `"0.1.0"` | `"0.1.0"` |
| `hyperparameters` | Class distribution, majority class | Seed, outcomes | Fixed outcome |
| `random_seed` | `42` (default) | User-specified | `42` (default) |
| `calibration_method` | `"none"` | `"none"` | `"none"` |
| `promotion_decision` | `"BASELINE"` | `"BASELINE"` | `"BASELINE"` |
| `decision_reason` | `"Statistical baseline reference model"` | `"Deterministic random baseline reference model"` | `"Buy-and-hold reference baseline model"` |

---

## 8. Tests

### 8.1 Test Categories (51 tests)

| Category | Count | Coverage |
|----------|-------|----------|
| Majority-class calculation | 3 | Counts, majority class, probability |
| Majority-class prediction | 3 | Prediction, probability, not abstained |
| Ties in class frequency | 3 | Two-way, three-way, up-flat ties |
| Probability calculation | 3 | Fraction, distribution sum, distribution contents |
| No hardcoded baseline | 3 | Data-dependent, all-down, flat majority |
| Deterministic random seed | 3 | Same seed, different seeds, valid outcome |
| Seed validity | 3 | Uniform probability, uniform distribution, seed in output |
| Audit trail creation | 4 | All adapters, timestamp |
| Temporal input validation | 2 | Valid input, schema check |
| Future-data rejection | 1 | Leakage in test context |
| Test-label leakage | 2 | Test leakage rejected, train leakage allowed |
| Registry registration | 4 | All adapters, with tags |
| Duplicate rejection | 3 | Duplicate rejected, different versions, different IDs |
| Metadata validation | 3 | All adapters |
| Model readiness | 4 | Unfitted, fitted, random always ready, buy-and-hold always ready |
| Invalid input handling | 4 | Unfitted abstains, empty labels, buy-and-hold, random |
| BuyAndHold specific | 3 | Always up, probability one, one-hot distribution |

### 8.2 Key Test Scenarios

- **No hardcoded 0.50:** Verified that baseline depends on actual training data
- **Tie-breaking:** Verified conservative "down" preference
- **Determinism:** Same seed + same input = same output
- **Leakage:** Test context with flags rejected, train context allowed
- **Unfitted model:** MajorityClass abstains with reason
- **Empty labels:** Raises ValueError

---

## 9. Verification Results

### 9.1 Pytest

```
697 passed, 1 warning in 30.05s
```

- 646 existing tests: all pass
- 51 new tests: all pass
- No regressions

### 9.2 Ruff

```
All checks passed!
```

### 9.3 Mypy

```
Success: no issues found in 5 source files
```

---

## 10. Limitations

| Limitation | Severity | Mitigation |
|-----------|----------|------------|
| MajorityClass only predicts one class | LOW | By design — it's a baseline |
| Random baseline has no information | LOW | By design — it's a reference |
| BuyAndHold only works for long strategies | LOW | Reference baseline for comparison |
| No calibration implemented | LOW | `calibration_status="none"` explicitly |
| No online learning (batch fit only) | LOW | Baselines are static by design |

---

## 11. Files Changed

| File | Action |
|------|--------|
| `src/aurora/models/baselines.py` | Created — 3 baseline adapters |
| `src/aurora/models/__init__.py` | Modified — added exports |
| `tests/test_phase8b_m2.py` | Created — 51 tests |

---

**STOP. Milestone 2 complete. Do not begin Milestone 3.**
