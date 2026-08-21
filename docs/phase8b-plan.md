# AURORA CORE — Phase 8B Engineering Plan: Model Interface Design

**Date:** 2026-08-16
**Revision:** 1 (post-review corrections)
**Status:** PLANNING ONLY — DO NOT IMPLEMENT
**Author:** Autonomous agent

---

## 1. Executive Summary

Phase 8B designs the model interface layer that allows AURORA CORE to evaluate multiple predictive models without coupling the research engine to any particular model implementation. The architecture must support statistical baselines, classical ML, small CPU-friendly local models, optional remote models, and future AURORA-specific models — all while preventing temporal leakage and ensuring reproducibility.

This plan is based on a thorough audit of the existing codebase, which reveals:
- A clean `ModelAdapter` ABC in `models/base.py` (but not used by ML models)
- Rich `MarketState` and `FeatureVector` schemas (but not connected to evaluation)
- Temporal splitters and leakage detectors (but not integrated with evaluation)
- Three ML models in `interaction/models.py` (but not implementing `ModelAdapter`)

The plan bridges these gaps without rewriting existing code.

---

## 2. Architecture

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│  schemas/market_data.py  schemas/market_state.py            │
│  OHLCVBar, OHLCVSequence, MarketState, MarketStateSequence  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 FEATURE LAYER                                │
│  features/base.py: FeatureExtractor, FeatureVector           │
│  interaction/compute.py: compute_all_features()              │
│  benchmark/features.py: deterministic feature functions      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 MODEL LAYER                                  │
│  models/base.py: ModelAdapter, ModelResponse                 │
│  models/registry.py: ModelRegistry (new)                     │
│  models/adapters/: model implementations (new)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              TEMPORAL VALIDATION LAYER                       │
│  temporal/splits.py: WalkForwardSplitter                     │
│  temporal/leakage.py: LeakageDetector                        │
│  interaction/ablation.py: walk_forward_evaluate()            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│               EVALUATION LAYER                               │
│  interaction/ablation.py: EvalMetrics, compute_metrics()     │
│  interaction/statistics.py: BH-FDR, CI, z-test               │
│  evaluation/metrics.py: brier_score, calibration_error       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│               BENCHMARK LAYER                                │
│  benchmark/harness.py: walk-forward orchestrator (new)       │
│  benchmark/comparison.py: multi-model comparison (new)       │
│  docs/reports: results                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            ENSEMBLE/FUSION LAYER (FUTURE)                    │
│  NOT IMPLEMENTED in Phase 8B                                 │
│  Interface planned for future independent validation         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Design Principles

1. **No model can bypass temporal validation.** The framework enforces chronological splitting before any model sees data.
2. **No model can see test data during training or calibration.** Preprocessing is fit on training data only.
3. **No hardcoded predictions.** Models must produce predictions from inputs, not from stored values.
4. **No fabricated confidence.** Uncertainty must be computed from model internals or calibration, not assigned arbitrarily.
5. **Deterministic reproducibility.** Same data + same model + same config = same predictions.
6. **CPU-only compatibility.** All models must run on Android ARM64 without GPU.
7. **Composition over inheritance.** Models are composed into ensembles, not subclassed.
8. **Multi-dimensional evaluation.** No single metric determines model validity.
9. **Strict temporal separation.** TRAIN → VALIDATION → FINAL TEST, never reversed.

---

## 3. Interfaces

### 3.1 Model Input: Enhanced MarketState

The existing `MarketState` from `schemas/market_state.py` is the primary model input. It already contains:
- Asset, timeframe, timestamp
- Price, returns
- Structure, liquidity, volume, volatility states
- VWAP distance, fibonacci levels
- Research features, historical analogue count

**Enhancement needed:** Add a `FeatureVector` field to `MarketState` so models can receive both raw market state and pre-computed features.

```python
# In schemas/market_state.py (planned extension)
class MarketState:
    # ... existing fields ...
    feature_vector: FeatureVector | None = None  # NEW: pre-computed features
    regime_label: str | None = None              # NEW: current regime
    data_quality_score: float = 1.0              # NEW: quality metric
```

### 3.2 Model Output: ModelResponse

The existing `ModelResponse` from `models/base.py`:

```python
@dataclass(frozen=True)
class ModelResponse:
    model_id: str
    outcome: Outcome          # "up", "down", "flat", "unknown", "abstain"
    probability: float        # P(outcome)
    reasoning: str            # human-readable explanation
    abstained: bool           # True if model declined to predict
    raw_output: str | None    # optional raw model output
```

**Enhancement needed:** Add uncertainty, calibration, and metadata fields.

```python
@dataclass(frozen=True)
class ModelResponse:
    model_id: str
    model_version: str
    outcome: Outcome
    probability: float
    confidence: float         # model's self-assessed confidence [0,1]
    uncertainty: float        # estimated prediction uncertainty [0,1]
    reasoning: str
    abstained: bool
    abstention_reason: str    # why abstained (if applicable)
    raw_output: str | None
    feature_schema_version: str
    inference_timestamp: str  # ISO timestamp of prediction
    calibration_score: float  # post-hoc calibration (if available)
    metadata: dict[str, str]  # arbitrary model-specific metadata
```

### 3.3 Model Adapter Interface

The existing `ModelAdapter` ABC from `models/base.py`:

```python
class ModelAdapter(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @abstractmethod
    def predict(self, state: MarketState) -> ModelResponse: ...

    def metadata(self) -> dict[str, Any]:
        return {"model_id": self.model_id}
```

**Enhancement needed:** Add lifecycle methods and configuration.

```python
class ModelAdapter(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    def predict(self, state: MarketState) -> ModelResponse: ...

    def fit(self, training_data: list[MarketState], labels: list[Outcome]) -> None:
        """Optional: train the model. Default is no-op for pre-trained models."""
        pass

    def calibrate(self, calibration_data: list[MarketState], labels: list[Outcome]) -> None:
        """Optional: calibrate probability outputs. Default is no-op."""
        pass

    def metadata(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "fitted": hasattr(self, "_fitted") and self._fitted,
        }

    def feature_requirements(self) -> list[str]:
        """Return list of feature names this model requires."""
        return []
```

### 3.4 Model Configuration

```python
@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    model_version: str
    hyperparameters: dict[str, Any]
    feature_ids: list[str]
    target_horizon: int
    transaction_cost_bps: float = 10.0
    abstention_threshold: float = 0.3
    calibration_method: str = "none"  # "none", "platt", "isotonic"
    random_seed: int = 42
    metadata: dict[str, str] = field(default_factory=dict)
```

---

## 4. Data Contracts

### 4.1 FeatureVector (existing in features/base.py)

```python
class FeatureVector(BaseModel):
    version: str
    extractor_id: str
    asset: str
    timeframe: str
    timestamp: datetime
    numerical: dict[str, float]
    categorical: dict[str, str]
    metadata: dict[str, Any]
```

### 4.2 TrainingData

```python
@dataclass
class TrainingData:
    market_states: list[MarketState]
    features: list[FeatureVector]
    labels: list[Outcome]
    regime_labels: list[str]
    timestamps: list[datetime]
    asset: str
    timeframe: str
    data_quality: str  # "historical", "live", "simulated"
```

### 4.3 EvaluationRecord

```python
@dataclass(frozen=True)
class EvaluationRecord:
    experiment_id: str
    model_id: str
    model_version: str
    timestamp: str
    asset: str
    timeframe: str
    predicted_outcome: Outcome
    actual_outcome: Outcome
    probability: float
    confidence: float
    uncertainty: float
    abstained: bool
    correct: bool
    brier_score: float
    regime: str
    data_split: str  # "train", "validation", "test"
    feature_schema_version: str
```

### 4.4 ExperimentResult

```python
@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    model_id: str
    model_version: str
    config: ModelConfig
    records: list[EvaluationRecord]
    summary: dict[str, float]
    baseline_accuracy: float
    majority_class_accuracy: float
    temporal_split_info: dict[str, Any]
    leakage_checks: list[dict[str, Any]]
    timestamp: str
```

### 4.5 ModelAuditTrail (NEW)

```python
@dataclass(frozen=True)
class ModelAuditTrail:
    model_id: str
    model_version: str
    training_period: tuple[str, str]     # (start_date, end_date)
    validation_period: tuple[str, str]
    test_period: tuple[str, str]
    feature_schema_version: str
    dataset_version: str
    hyperparameters: dict[str, Any]
    calibration_method: str
    random_seed: int
    metrics: dict[str, float]            # all evaluation metrics
    selection_decision: str              # BASELINE, INCONCLUSIVE, WEAK, PROMISING, SUPPORTED, REJECTED, NO_DEPLOYMENT_SIGNAL
    decision_reason: str                 # human-readable explanation
    timestamp: str
```

---

## 5. Model Registry

### 5.1 Design

```python
# models/registry.py (new file)

@dataclass
class ModelEntry:
    adapter: ModelAdapter
    config: ModelConfig
    registered_at: str
    tags: list[str]
    status: str  # "active", "deprecated", "experimental"

class ModelRegistry:
    def __init__(self):
        self._models: dict[str, ModelEntry] = {}

    def register(self, adapter: ModelAdapter, config: ModelConfig, tags: list[str] | None = None) -> None:
        """Register a model adapter with its configuration."""
        ...

    def get(self, model_id: str) -> ModelEntry | None:
        """Retrieve a registered model by ID."""
        ...

    def list_models(self, status: str | None = None, tag: str | None = None) -> list[ModelEntry]:
        """List all registered models, optionally filtered."""
        ...

    def deactivate(self, model_id: str) -> None:
        """Mark a model as deprecated."""
        ...

    def compare(self, model_ids: list[str], metric: str) -> list[tuple[str, float]]:
        """Compare models by a specific metric from their last experiment."""
        ...
```

### 5.2 Built-in Models

| Model ID | Type | Description | CPU Cost |
|----------|------|-------------|----------|
| `majority_class` | Baseline | Always predict majority class | None |
| `random` | Baseline | Random predictions | None |
| `buy_and_hold` | Baseline | Always predict "up" | None |
| `logistic_regression` | Classical ML | SGD with L2 regularization | Low |
| `decision_tree` | Classical ML | Gini-based classification tree | Low |
| `bagged_ensemble` | Classical ML | Bootstrap aggregated trees | Medium |
| `stub` | Debug | Deterministic hash-based | None |

---

## 6. Benchmark Methodology

### 6.1 Strict Temporal Evaluation

Every model evaluation MUST follow the three-phase temporal separation:

```
TRAIN → VALIDATION → FINAL TEST
```

| Phase | Purpose | Data Used For |
|-------|---------|---------------|
| TRAIN | Model fitting | Weight/parameter updates |
| VALIDATION | Calibration, threshold selection | Probability calibration, abstention threshold |
| FINAL TEST | Honest evaluation | All reported metrics |

**The final test set is NEVER used for:**
- Model selection
- Hyperparameter tuning
- Calibration
- Threshold adjustment
- Any form of optimization

### 6.2 Walk-Forward Evaluation

```
For each model M in registry:
  For each instrument I in [BTC-USD, SPY, QQQ]:
    1. Load data D for instrument I
    2. Compute features F from D
    3. Compute targets T from D
    4. Apply WalkForwardSplitter to get folds
    5. For each fold:
       a. Split into train/validation/test (chronological)
       b. Fit preprocessing on train only
       c. Transform train/validation/test
       d. If model has fit(): fit on train
       e. If model has calibrate(): calibrate on validation
       f. Predict on test
       g. Compute per-record metrics
       h. Run leakage checks
    6. Aggregate metrics across folds
    7. Compare against majority-class baseline
    8. Apply BH-FDR correction across all models
    9. Record experiment with full audit trail
```

### 6.3 Multi-Dimensional Evaluation

No single metric determines model validity. Every candidate model must be evaluated across ALL applicable dimensions:

| Dimension | Metrics | Purpose |
|-----------|---------|---------|
| **Predictive Accuracy** | Directional accuracy, Balanced accuracy | Raw predictive power |
| **Probability Quality** | Brier score, Log loss, Calibration error | Reliability of probability outputs |
| **Classification** | Precision, Recall, F1 score | Error-type analysis |
| **Risk-Adjusted Return** | Sharpe ratio, Mean return, Max drawdown | Trading viability (when applicable) |
| **Abstention** | Abstention rate, Abstention quality | Selective prediction value |
| **Stability** | Walk-forward consistency, Regime robustness | Generalization across time/regimes |
| **Statistical Significance** | p-value, Adjusted p-value, Confidence interval, Effect size | Whether results are real |
| **Cost Sensitivity** | Transaction-cost-adjusted metrics | Real-world viability |

### 6.4 Metrics Detail

| Metric | Formula | Use Case |
|--------|---------|----------|
| Directional Accuracy | correct / total | Predictive power |
| Balanced Accuracy | (sensitivity + specificity) / 2 | Imbalanced classes |
| Precision | TP / (TP + FP) | False positive cost |
| Recall | TP / (TP + FN) | False negative cost |
| F1 Score | 2 * P * R / (P + R) | Balanced P/R |
| Brier Score | mean((p - y)^2) | Probability calibration |
| Log Loss | -mean(y*log(p) + (1-y)*log(1-p)) | Probability quality |
| Calibration Error | mean(|expected - actual| per bin) | Probability reliability |
| Mean Return | mean(strategy_returns) | Profitability |
| Sharpe Ratio | mean(r) / std(r) | Risk-adjusted return |
| Max Drawdown | max(peak - trough) / peak | Downside risk |
| Abstention Rate | abstained / total | Model selectivity |
| Abstention Quality | accuracy_when_not_abstained | Selectivity value |
| Walk-Forward Stability | std(fold_da) across folds | Temporal consistency |
| Regime Robustness | min(regime_da) across regimes | Cross-regime performance |

### 6.5 Baseline Comparison

For every experiment, the model must be compared against:

1. **Majority-class baseline:** `max(n_pos, n_neg) / n_total` — computed dynamically from the evaluation dataset
2. **Random baseline:** ~0.5 (or majority-class for imbalanced)
3. **Buy-and-hold baseline:** fraction of positive returns

The majority-class baseline is the PRIMARY reference. A model that does not exceed it provides no predictive value.

### 6.6 Model Status Classification

| Status | Criteria |
|--------|----------|
| **BASELINE** | Reference model (majority_class, random, buy_and_hold) — not evaluated for predictive value |
| **INCONCLUSIVE** | Evidence insufficient or sample size inadequate |
| **WEAK** | Some evidence exists, but effect size, robustness, or practical value is insufficient |
| **PROMISING** | Shows meaningful OOS improvement across multiple criteria, but not yet robust enough for SUPPORTED |
| **SUPPORTED** | Statistically and practically significant improvement across predefined criteria after correction |
| **REJECTED** | Evidence contradicts the hypothesis or method performs materially worse than baseline |
| **NO_DEPLOYMENT_SIGNAL** | Model evaluated but does not demonstrate deployment-ready predictive value |

**Critical rules:**
- PROMISING and SUPPORTED do NOT mean profitable automatically
- SUPPORTED requires: improvement across multiple metrics, statistical significance after BH-FDR correction, robustness across regimes, and positive transaction-cost-adjusted performance
- NO_DEPLOYMENT_SIGNAL is the default status for models that are technically valid but do not add value
- A model may be PROMISING but still not meet deployment criteria

---

## 7. Leakage Controls

### 7.1 Temporal Integrity

| Control | Implementation | Enforcement |
|---------|---------------|-------------|
| Chronological splits | `WalkForwardSplitter` from `temporal/splits.py` | Mandatory for all experiments |
| No random splits | `LeakageDetector.check_random_temporal_split()` | Checked before evaluation |
| Feature timestamps | `LeakageDetector.check_feature_timestamp_leakage()` | Checked before evaluation |
| Target timestamps | `LeakageDetector.check_target_leakage()` | Checked before evaluation |
| Normalization leakage | `LeakageDetector.check_normalization_leakage()` | Checked after preprocessing |
| Test-set isolation | Final test set never used for selection | Enforced by harness |

### 7.2 Preprocessing Boundary

```python
# Pseudo-code for correct preprocessing
scaler = StandardScaler()
train_X = scaler.fit_transform(raw_train_X)  # fit on train ONLY
val_X = scaler.transform(raw_val_X)          # transform, no fit
test_X = scaler.transform(raw_test_X)        # transform, no fit
```

### 7.3 Model Training Boundary

```python
# Pseudo-code for correct training
model.fit(train_X, train_y)           # train on train ONLY
model.calibrate(val_X, val_y)         # calibrate on validation ONLY
predictions = model.predict(test_X)   # predict on test (final evaluation only)
```

### 7.4 No Future Information

| Check | Method |
|-------|--------|
| Features use only past data | All feature functions use trailing windows |
| Targets use future data | Targets are future returns, filtered for look-ahead |
| Regime labels use past data | Regime detection uses trailing ATR/momentum |
| No test-set model selection | Model selection uses validation performance only |
| No test-set calibration | Calibration uses validation data only |

---

## 8. Calibration

### 8.1 Calibration Methods

| Method | Description | When to Use |
|--------|-------------|-------------|
| None | Raw model probabilities | When model is well-calibrated by design |
| Platt Scaling | Logistic regression on log-odds | Small datasets, linear models |
| Isotonic Regression | Non-parametric monotonic mapping | Larger datasets, any model |

### 8.2 Calibration Evaluation

```python
def calibration_error(predictions: list[float], actuals: list[float], n_bins: int = 10) -> float:
    """Expected calibration error across n_bins."""
    bins = defaultdict(list)
    for p, a in zip(predictions, actuals):
        b = min(int(p * n_bins), n_bins - 1)
        bins[b].append((p, a))
    error = 0.0
    for bin_items in bins.values():
        expected = mean(p for p, _ in bin_items)
        actual = mean(a for _, a in bin_items)
        error += abs(expected - actual) * len(bin_items)
    return error / len(predictions)
```

### 8.3 Calibration Requirements

- Models must report calibration error in their results
- Calibration must be performed on validation data, not test data
- Calibration quality must be tracked across time periods

---

## 9. Abstention

### 9.1 Abstention Policy

Models may abstain from prediction when:
1. Confidence is below the abstention threshold
2. Input data quality is insufficient
3. Model is not fitted
4. Feature requirements are not met

### 9.2 Abstention Quality

```python
def abstention_quality(abstained: list[bool], correct: list[bool]) -> dict[str, float]:
    """Evaluate whether abstention improves overall accuracy."""
    n_abstained = sum(abstained)
    n_total = len(abstained)
    n_active = n_total - n_abstained
    if n_active == 0:
        return {"abstention_rate": 1.0, "active_accuracy": 0.0, "value": 0.0}
    active_correct = sum(c for a, c in zip(abstained, correct) if not a)
    active_accuracy = active_correct / n_active
    overall_accuracy = sum(correct) / n_total
    return {
        "abstention_rate": n_abstained / n_total,
        "active_accuracy": active_accuracy,
        "overall_accuracy": overall_accuracy,
        "value": active_accuracy - overall_accuracy,
    }
```

### 9.3 Abstention Requirements

- Abstention must be tracked and reported
- Abstention quality must be evaluated (does abstaining improve accuracy?)
- Models that abstain too often (>50%) are flagged as unhelpful

---

## 10. CPU-Only Constraints

### 10.1 Hard Limits

| Constraint | Value | Reason |
|-----------|-------|--------|
| Max RAM | 2 GB | Android device limit |
| Max model size | 100 MB | Storage constraint |
| Max inference time | 100 ms per prediction | Real-time requirement |
| No GPU required | All models CPU-only | No GPU on Android |
| No PyTorch | Pure Python only | musl libc incompatibility |
| No Transformers | No large language models | Storage/compute limit |

### 10.2 Supported Model Types

| Type | Max Parameters | Max Features | Expected Performance |
|------|---------------|--------------|---------------------|
| Logistic Regression | N/A | 100 | Near baseline |
| Decision Tree | depth=6 | 50 | Near baseline |
| Bagged Ensemble | 20 trees | 50 | Near baseline |
| Small MLP | 1000 params | 50 | Uncertain |
| K-Nearest Neighbors | N/A | 20 | Uncertain |

### 10.3 What NOT to Build

- Do NOT build neural networks expecting better performance
- Do NOT assume more parameters = better predictions
- Do NOT assume LLMs can predict markets
- Do NOT assume transformers can find patterns in price data

---

## 11. Future Live-Data Integration

### 11.1 Data Flow

```
TradingView/WebSocket → OHLCVBar → OHLCVSequence → MarketState → ModelAdapter → ModelResponse
```

### 11.2 Interface Stability

The `ModelAdapter.predict(state: MarketState) -> ModelResponse` interface does not change whether the data comes from:
- Historical yfinance fetch
- Live TradingView websocket
- Simulated backtest
- Paper trading feed

### 11.3 Live-Data Requirements

| Requirement | Implementation |
|-------------|---------------|
| Real-time feature computation | `FeatureExtractor.extract_single(MarketState)` |
| Inference latency < 100ms | CPU-only models, no network calls |
| Graceful degradation | Abstain if data quality insufficient |
| No state mutation | Models are immutable after fitting |
| Audit trail | Every prediction logged with timestamp |

### 11.4 Future TradingView Integration

```python
# Pseudo-code for live trading (NOT IMPLEMENTED in Phase 8B)
class LiveTradingBridge:
    def __init__(self, model: ModelAdapter, registry: ModelRegistry):
        self.model = model
        self.registry = registry

    def on_bar(self, bar: OHLCVBar) -> ModelResponse | None:
        """Called on each new bar from TradingView."""
        state = self._bar_to_state(bar)
        response = self.model.predict(state)
        if response.abstained:
            return None
        return response
```

---

## 12. Future Ensemble/Fusion Interface (PLANNED, NOT IMPLEMENTED)

### 12.1 Purpose

AURORA must eventually be able to combine independently validated evidence sources. However, no combination should be assumed to improve prediction.

### 12.2 Planned Interface

```python
# NOT IMPLEMENTED in Phase 8B — interface design only
class EnsembleAdapter(ModelAdapter):
    """Combines multiple independently validated ModelAdapters."""

    def __init__(self, adapters: list[ModelAdapter], combination_method: str = "average"):
        """
        combination_method: "average", "weighted_average", "voting", "stacking"
        Each adapter must have passed独立 validation before inclusion.
        """
        ...

    def predict(self, state: MarketState) -> ModelResponse:
        """Combine predictions from all adapters."""
        ...
```

### 12.3 Constraints for Future Implementation

- Each component adapter must be independently validated
- No component adapter may be a "black box" — all must have transparent metrics
- Ensemble performance must be compared against each component
- Ensemble must not degrade performance of best component
- No live deployment of ensemble without independent audit

---

## 13. Testing Strategy

### 13.1 Unit Tests

| Test Category | Count | Coverage |
|---------------|-------|----------|
| ModelAdapter interface compliance | 5 | All abstract methods |
| ModelResponse validation | 5 | All fields, edge cases |
| ModelRegistry CRUD | 8 | Register, get, list, deactivate |
| Walk-forward temporal integrity | 5 | No future leakage |
| Preprocessing boundary | 5 | Fit on train only |
| Calibration correctness | 5 | Known calibration curves |
| Abstention quality | 5 | Various abstention rates |
| BH-FDR correction | 5 | Monotonicity, family-wise error |
| Regime-conditional evaluation | 5 | Sample size protection |
| Transaction cost accounting | 5 | Per-transition, not per-bar |
| Audit trail completeness | 5 | All fields recorded |

### 13.2 Integration Tests

| Test | Description |
|------|-------------|
| End-to-end walk-forward | Data → Features → Model → Predict → Evaluate |
| Multi-model comparison | Compare 3+ models on same data |
| Leakage detection | Inject leakage, verify detection |
| Reproducibility | Same config → same results |
| Abstention under stress | Models abstain correctly on bad data |
| Audit trail generation | Verify complete trail for each experiment |

### 13.3 Regression Tests

| Bug | Test |
|-----|------|
| Per-bar transaction costs | Verify per-transition accounting |
| 0.50 baseline assumption | Verify dynamic majority-class baseline |
| Interaction no incremental value | Verify A+B+int comparison |
| Import order in preprocessing | Verify math import at top |
| Test-set leakage | Verify test set never used for selection |

---

## 14. Deployment Strategy

### 14.1 Phase 8B Scope

| In Scope | Out of Scope |
|----------|-------------|
| ModelAdapter interface enhancement | Neural network implementations |
| ModelRegistry implementation | LLM integration |
| ML model adapters (logistic, tree, ensemble) | Live trading |
| Walk-forward benchmark harness | TradingView integration |
| Calibration framework | Portfolio management |
| Abstention framework | Position sizing |
| Audit trail framework | Ensemble composition |
| Comprehensive test suite | Website |

### 14.2 Implementation Order

1. Enhance `ModelResponse` and `ModelAdapter` interfaces
2. Implement `ModelRegistry`
3. Implement `ModelAuditTrail`
4. Create ML model adapters wrapping existing models
5. Build walk-forward benchmark harness with strict temporal separation
6. Integrate calibration framework
7. Add abstention logic
8. Write comprehensive tests
9. Run benchmark across all models and instruments
10. Generate comparison report with full audit trail

### 14.3 Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `models/base.py` | Modify | Enhance ModelResponse, ModelAdapter |
| `models/registry.py` | Create | ModelRegistry implementation |
| `models/config.py` | Create | ModelConfig dataclass |
| `models/audit.py` | Create | ModelAuditTrail implementation |
| `models/adapters/__init__.py` | Create | Adapter package |
| `models/adapters/majority_class.py` | Create | Baseline adapter |
| `models/adapters/random.py` | Create | Random baseline adapter |
| `models/adapters/logistic.py` | Create | Logistic regression adapter |
| `models/adapters/tree.py` | Create | Decision tree adapter |
| `models/adapters/ensemble.py` | Create | Bagged ensemble adapter |
| `models/adapters/stub.py` | Modify | Update to new interface |
| `benchmark/harness.py` | Create | Walk-forward benchmark harness |
| `benchmark/comparison.py` | Create | Multi-model comparison |
| `tests/test_phase8b.py` | Create | Comprehensive test suite |

---

## 15. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Overfitting to 2-year dataset | HIGH | Walk-forward validation, multiple instruments |
| No meaningful signal exists | HIGH | Honest reporting, majority-class comparison, NO_DEPLOYMENT_SIGNAL status |
| CPU models too slow on Android | MEDIUM | Profile inference time, limit model complexity |
| Calibration fails on small datasets | MEDIUM | Use Platt scaling, default to uncalibrated |
| Model registry becomes complex | LOW | Keep simple dict-based implementation |
| Feature duplication across modules | LOW | Don't merge in Phase 8B, document as tech debt |
| False sense of model validity | HIGH | Multi-dimensional evaluation, strict temporal separation |

---

## 16. Definition of Done

Phase 8B is complete when:

1. ✅ `ModelAdapter` interface is enhanced with `model_version`, `confidence`, `uncertainty`
2. ✅ `ModelResponse` is enhanced with calibration, abstention reason, metadata
3. ✅ `ModelRegistry` implements register/get/list/deactivate
4. ✅ `ModelAuditTrail` records complete model selection history
5. ✅ At least 3 ML model adapters wrap existing models
6. ✅ Walk-forward benchmark harness runs end-to-end with strict TRAIN→VALIDATION→TEST separation
7. ✅ Multi-model comparison evaluates across ALL predefined dimensions
8. ✅ All models compared against dynamic majority-class baseline
9. ✅ Transaction costs applied per-position-transition
10. ✅ BH-FDR correction applied across model comparisons
11. ✅ Regime-conditional evaluation with sample-size protection
12. ✅ 50+ tests passing, ruff clean, mypy clean
13. ✅ No model is labeled SUPPORTED without meeting ALL predefined criteria
14. ✅ NO_DEPLOYMENT_SIGNAL status used for models that don't add value
15. ✅ Report documents all results honestly, including failures
16. ✅ No PyTorch, no Transformers, no GPU required
17. ✅ No live trading, no TradingView integration

---

## 17. Explicit Comparison Criteria

### A. Statistical Baseline (majority_class, random, buy_and_hold)
- **Purpose:** Establish minimum performance bar
- **Expected:** DA ≈ majority_class_accuracy
- **Status:** Always BASELINE
- **Value add:** None (reference only)

### B. Classical ML (logistic, tree, ensemble)
- **Purpose:** Test whether simple patterns exist
- **Expected:** Performance near baseline
- **Evaluation:** Multi-dimensional (accuracy, calibration, stability, cost-adjusted)
- **Promotion criteria:** Must demonstrate statistically and practically meaningful OOS improvement across predefined criteria after BH-FDR correction

### C. Small Local Model (future, NOT Phase 8B)
- **Purpose:** Test whether more complex models find patterns
- **Expected:** Uncertain
- **Evaluation:** Same multi-dimensional criteria as classical ML
- **Promotion criteria:** Must provide meaningful incremental value according to predefined criteria — no arbitrary thresholds

### D. Optional Remote Model (future, NOT Phase 8B)
- **Purpose:** Test whether server-side compute helps
- **Expected:** Uncertain
- **Evaluation:** Same multi-dimensional criteria PLUS latency, cost, reliability
- **Promotion criteria:** Must demonstrate reproducible incremental value after accounting for all practical constraints

### Decision Framework

```
Start
  → Run benchmark across all model categories
  → Evaluate each model on ALL predefined dimensions
  → Apply BH-FDR correction across all comparisons
  → For each model:
      If statistically and practically meaningful improvement across criteria:
        → Status: SUPPORTED (rare, requires strong evidence)
      If meaningful but not yet robust:
        → Status: PROMISING (continue research)
      If some evidence but insufficient:
        → Status: WEAK
      If evidence contradicts hypothesis:
        → Status: REJECTED
      If technically valid but no value added:
        → Status: NO_DEPLOYMENT_SIGNAL
      If insufficient evidence:
        → Status: INCONCLUSIVE
  → Continue research regardless of individual model outcomes
  → Do NOT stop research based on any single benchmark result
```

---

**DO NOT IMPLEMENT PHASE 8B. STOP AND WAIT FOR APPROVAL.**
