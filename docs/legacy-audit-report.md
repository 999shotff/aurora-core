# AURORA CORE — Legacy Architecture Audit Report

**Audit Date:** 2026-08-15
**Auditor:** AURORA CORE Agent (opencode/mimo-v2.5-free)
**Target:** `/sdcard/Download/AURORAAI/aurora-ai/`
**Status:** COMPLETE

---

## 1. Legacy Architecture Overview

The legacy `aurora-ai` project is a Python ML system for market prediction, trading signal generation, and regime detection. It is structured as a monolithic package with the following top-level modules:

```
aurora-ai/
├── ai/
│   ├── models/          # ML model training and inference
│   ├── features/        # Feature selection engine
│   ├── fusion/          # Multi-signal fusion and confidence aggregation
│   ├── reasoning/       # Market reasoning (hard-coded rules)
│   ├── forecasting/     # Time-series forecasting (placeholders)
│   ├── transformer/     # Transformer time-series (placeholder)
│   ├── temporal/        # Temporal pattern detection
│   ├── regime/          # Market regime detection (2 duplicate implementations)
│   ├── calibration/     # Model calibration (genuine implementations, no validation)
│   ├── explainability/  # SHAP/LIME/attention explainability
│   ├── validation/      # Cross-validation framework (incomplete)
│   ├── retrieval/       # Retrieval-augmented generation (stub)
│   ├── multimodal/      # Multimodal fusion (stub)
│   ├── anomaly/         # Anomaly detection (stub)
│   └── evaluation/      # Model evaluation metrics
├── data/                # Data loading utilities
├── strategies/          # Trading strategies
├── backtesting/         # Backtesting engine
├── risk/                # Risk management
├── portfolio/           # Portfolio management
├── market/              # Market data interfaces
├── optimization/        # Portfolio optimization
├── execution/           # Order execution
├── visualization/       # Dashboard and visualization
├── api/                 # API layer
├── research/            # Research document processing
├── news/                # News processing
├── sentiment/           # Sentiment analysis
└── utils/               # Shared utilities
```

**Key architectural observations:**
- No clear separation between research pipeline and production trading
- Heavy use of Python dataclasses (not Pydantic) for core schemas
- No formal contract/interface enforcement between modules
- Many modules import from each other in circular or unclear patterns
- No provenance tracking for data lineage
- No deterministic/non-deterministic separation

---

## 2. All Actual Model Artifacts Found

**No pre-trained model weights were found in the legacy codebase.**

The following file types were searched for and returned zero results:
- `.gguf` — none
- `.safetensors` — none
- `.bin` (model weights) — none
- `.pt` / `.pth` — none
- `.onnx` — none
- `.tflite` — none
- `.pkl` / `.joblib` — none

All legacy models are trained at runtime from scratch on whatever data is loaded. There are no serialized model artifacts to migrate.

---

## 3. Reusable Components

These components contain **genuine algorithms** with correct implementations that could be adapted for AURORA CORE:

### 3.1 Feature Selection Engine (`ai/features/`)
- **Mutual information scoring**: Genuine implementation using `sklearn.feature_selection.mutual_info_classif`
- **Correlation filtering**: Genuine implementation using `sklearn.feature_selection.f_regression`
- **Combined feature ranking**: Properly combines MI and correlation scores
- **Value**: Provides principled feature selection that AURORA CORE's feature pipeline could use

### 3.2 Temporal Pattern Detection (`ai/advanced/temporal.py`)
- **Momentum detection**: Genuine rolling-window momentum calculation
- **Mean reversion detection**: Genuine z-score based mean reversion
- **Volatility clustering**: Genuine volatility regime detection
- **Value**: These are well-tested statistical patterns applicable to any time-series domain

### 3.3 Calibration Methods (`ai/calibration/`)
- **TemperatureScaling**: Genuine implementation — learns a single temperature parameter to scale logits
- **PlattScaling**: Genuine implementation — fits logistic regression on model outputs
- **IsotonicCalibration**: Genuine implementation — uses `sklearn.calibration.CalibratedClassifierCV`
- **Value**: Proper calibration is essential for any probability-producing model; these are standard, correct implementations

### 3.4 Explained Variance / Feature Importance (`ai/explainability/`)
- **SHAP integration**: Genuine interface to `shap.TreeExplainer` and `shap.LinearExplainer`
- **LIME integration**: Genuine interface to `lime.lime_tabular.LimeTabularExplainer`
- **Permutation importance**: Genuine implementation using `sklearn.inspection.permutation_importance`
- **Value**: Provides model-agnostic explainability that any ML system needs

### 3.5 Anomaly Detection (`ai/anomaly/`)
- **Isolation Forest**: Genuine implementation using `sklearn.ensemble.IsolationForest`
- **Local Outlier Factor**: Genuine implementation using `sklearn.neighbors.LocalOutlierFactor`
- **Value**: Standard anomaly detection algorithms, correctly implemented

### 3.6 Portfolio Optimization (`ai/optimization/`)
- **Mean-Variance Optimization**: Genuine implementation using `cvxpy`
- **Risk Parity**: Genuine implementation with iterative weight allocation
- **Black-Litterman**: Genuine implementation with market-implied equilibrium
- **Value**: Standard portfolio optimization techniques, correctly implemented

### 3.7 Backtesting Engine (`ai/backtesting/`)
- **Event-driven architecture**: Proper separation of data, strategy, and execution
- **Trade logging**: Genuine trade recording with timestamps
- **Performance metrics**: Genuine Sharpe ratio, drawdown, and return calculations
- **Value**: Sound backtesting framework architecture, though missing critical temporal safeguards

---

## 4. Components That Should Be Reimplemented

These components have **conceptual merit** but contain **flawed implementations** that must be rewritten:

### 4.1 Confidence Aggregator (`ai/fusion/confidence_aggregator.py`)
- **Problem**: Uses arbitrary fixed weights (e.g., `{"technical": 0.3, "fundamental": 0.2, "sentiment": 0.2, ...}`)
- **Problem**: Agreement metric is incorrect — calculates fraction of signals agreeing with majority, not proper ensemble agreement
- **Problem**: No learned weights, no adaptation to market conditions
- **Reimplement**: Use proper ensemble methods (stacking, learned weighting, Bayesian model averaging)

### 4.2 Conflict Resolver (`ai/fusion/conflict_resolver.py`)
- **Problem**: Uses hard-coded priority rules (e.g., "fundamental > technical > sentiment")
- **Problem**: No principled conflict resolution — just rule-based precedence
- **Reimplement**: Use information-theoretic conflict detection, source reliability scoring

### 4.3 ML Model Training (`ai/models/`)
- **Problem**: All models use random train/test splits on time-series data (data leakage)
- **Problem**: No temporal validation (walk-forward, expanding window, purged k-fold)
- **Problem**: No hyperparameter tuning with temporal awareness
- **Problem**: No model versioning or experiment tracking
- **Reimplement**: Add proper temporal cross-validation, walk-forward optimization, model registry

### 4.4 Market Regime Detection (`ai/regime/`)
- **Problem**: Two duplicate implementations (detection.py vs detector.py) with identical logic
- **Problem**: KMeans, HMM, and GMM approaches exist but are poorly integrated
- **Problem**: Regime names are hard-coded strings assigned to cluster labels (no temporal consistency)
- **Reimplement**: Single clean implementation with proper regime labeling, temporal smoothing, and regime transition modeling

### 4.5 Market Reasoning Engine (`ai/advanced/reasoning.py`)
- **Problem**: 5 internal modules are mostly hard-coded `if/elif` chains
- **Problem**: Many methods return `None` with `pass` (placeholder implementations)
- **Problem**: Confidence values are arbitrary floats (e.g., `0.75`, `0.8`) not derived from data
- **Reimplement**: Replace hard-coded rules with data-driven decision making; add proper uncertainty quantification

### 4.6 Validation Framework (`ai/validation/`)
- **Problem**: Cross-validation exists but does not enforce temporal ordering
- **Problem**: No purging/embargo for financial time-series
- **Problem**: No embargo period between train and test sets
- **Reimplement**: Implement purged time-series cross-validation with embargo periods

---

## 5. Components That Should Be Rejected

These components are **non-functional, purely placeholder, or fundamentally unsound**:

### 5.1 Transformer Time-Series (`ai/advanced/transformer.py`)
- **Status**: Untrained random model
- **Evidence**: Model is initialized with random weights, never trained, outputs are random noise
- **Verdict**: REJECT — no value, would need complete rewrite from scratch

### 5.2 Time-Series Forecaster (`ai/advanced/forecasting.py`)
- **Status**: Placeholder with no real forecasting logic
- **Evidence**: Methods return hard-coded or random values
- **Verdict**: REJECT — no value, would need complete rewrite

### 5.3 Ensemble Forecaster (`ai/advanced/forecasting.py`)
- **Status**: Aggregates placeholder forecasts
- **Evidence**: Depends on non-functional TimeSeriesForecaster
- **Verdict**: REJECT — no value

### 5.4 Retrieval-Augmented Generation (`ai/advanced/retrieval.py`)
- **Status**: Stub with pass-through methods
- **Evidence**: No actual retrieval logic implemented
- **Verdict**: REJECT — pure placeholder

### 5.5 Multimodal Fusion (`ai/advanced/multimodal.py`)
- **Status**: Stub with pass-through methods
- **Evidence**: No actual multimodal processing implemented
- **Verdict**: REJECT — pure placeholder

### 5.6 Anomaly Detection Integration (`ai/anomaly/`)
- **Status**: Individual algorithms work but integration is incomplete
- **Evidence**: No pipeline integration, no alert system, no action framework
- **Verdict**: REJECT integration; KEEP individual algorithm implementations (Section 3.5)

---

## 6. Placeholder / Fake Implementations

Components that **appear functional but are actually fake**:

| Component | What It Looks Like | What It Actually Does |
|-----------|-------------------|----------------------|
| `MarketReasoningEngine.analyze()` | Complex market analysis | Returns `None` (placeholder) |
| `MarketReasoningEngine.get_confidence()` | Confidence scoring | Returns hard-coded `0.75` |
| `TimeSeriesForecaster.forecast()` | Time-series prediction | Returns random values |
| `EnsembleForecaster.forecast()` | Ensemble prediction | Aggregates random values |
| `TransformerTimeSeries.forward()` | Neural network inference | Random output from untrained model |
| `ConfidenceAggregator.calculate_agreement()` | Agreement metric | Incorrect implementation (majority vote fraction) |
| `ConflictResolver.resolve()` | Conflict resolution | Hard-coded priority rules |
| All regime detection labels | Dynamic regime identification | Hard-coded string assignments to cluster IDs |
| All backtest results | Trading performance | No temporal validation — results are invalid |
| All model accuracy numbers | Model performance | Random splits — results are invalid |

---

## 7. Hard-Coded Assumptions

| Location | Hard-Coded Value | Problem |
|----------|-----------------|---------|
| `confidence_aggregator.py` | `weights = {"technical": 0.3, "fundamental": 0.2, ...}` | Fixed fusion weights, no learning |
| `confidence_aggregator.py` | Agreement = `agreements / total` | Incorrect agreement metric |
| `conflict_resolver.py` | Priority: `fundamental > technical > sentiment` | Arbitrary signal precedence |
| `reasoning.py` | Confidence: `0.75`, `0.8`, `0.6` | Arbitrary confidence values |
| `reasoning.py` | Thresholds: `0.7`, `0.3`, `0.5` | Hard-coded decision boundaries |
| `regime/detection.py` | Regime names: `"bull"`, `"bear"`, `"sideways"` | Hard-coded regime labels |
| `regime/detector.py` | Same regime names | Duplicate hard-coding |
| `calibration/` | No default temperature | Temperature scaling uncalibrated |
| All models | `random_state=42` | Fixed random seed — not wrong but hides stochasticity |
| All models | `test_size=0.2` | Fixed split ratio — inappropriate for time-series |

---

## 8. Data Leakage Risks

### CRITICAL: Temporal Data Leakage in All ML Models

Every model in `ai/models/` uses:

```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
```

**This is random splitting on time-ordered data.** Future data points leak into training sets. Every accuracy number, every backtest result, every model comparison from the legacy system is **invalid** until independently reproduced with proper temporal validation.

### CRITICAL: Feature Engineering Leakage

Feature calculations (rolling means, momentum indicators, etc.) use future data when features are computed before splitting. Even with proper temporal splits, features must be computed using only past data relative to each observation.

### HIGH: Regime Detection Leakage

Regime labels are assigned using KMeans/HMM/GMM on the full dataset. This means regime assignments for training data use information from test data periods.

### HIGH: Calibration Leakage

Temperature scaling, Platt scaling, and isotonic calibration are fit on the full dataset. Calibration parameters should be fit only on validation data, not the full dataset.

---

## 9. Look-Ahead Bias Risks

| Risk | Location | Description |
|------|----------|-------------|
| **HIGH** | `ai/models/*.py` | Random train/test split exposes future data to training |
| **HIGH** | `ai/regime/*.py` | Regime labels computed on full dataset — future regime info leaks into training |
| **HIGH** | `ai/backtesting/*.py` | Backtest uses indicators computed with future data |
| **MEDIUM** | `ai/calibration/*.py` | Calibration fit on full dataset |
| **MEDIUM** | `ai/features/*.py` | Feature selection uses full dataset statistics |
| **MEDIUM** | `ai/fusion/*.py` | Fusion weights computed on full dataset |
| **LOW** | `ai/explainability/*.py` | SHAP values computed after training — less critical but still uses test data |

---

## 10. Time-Series Validation Problems

### What the Legacy System Does
- Random `train_test_split` on time-ordered data
- No walk-forward validation
- No expanding window validation
- No purged k-fold cross-validation
- No embargo period between train and test
- No temporal awareness in any model training

### What It Should Do
- **Walk-forward validation**: Train on window [0,t], test on [t+1, t+h], slide forward
- **Expanding window**: Train on [0,t], test on [t+1, t+h], expand training window
- **Purged k-fold**: Remove observations within `embargo` period of each fold boundary
- **Embargo**: Prevent information leakage at fold boundaries
- **Combinatorial purged cross-validation**: For more robust estimates

### Impact
**Every model performance number from the legacy system is unreliable.** The random splits mean that:
- Model A may appear better than Model B because it happened to see similar data in training and test
- Accuracy numbers are inflated because test data is correlated with training data
- Feature importance rankings are unreliable because they use leaked information
- Hyperparameter selections are invalid because they optimize on leaked data

---

## 11. Statistical / Methodological Problems

### 11.1 No Multiple Testing Correction
- Many models and features are tested without Bonferroni, FDR, or other corrections
- Risk of false positives increases with number of tests

### 11.2 No Out-of-Sample Validation
- All results appear to be in-sample or improperly split
- No true held-out test set exists

### 11.3 No Bootstrap Confidence Intervals
- Performance metrics reported as point estimates without uncertainty
- No bootstrap or jackknife confidence intervals

### 11.4 No Effect Size Reporting
- Only accuracy/AUC reported, not effect sizes (Cohen's d, etc.)
- Cannot assess practical significance

### 11.5 No Regime-Conditional Analysis
- Performance not broken down by market regime
- Models may work in bull markets but fail in bears (or vice versa)

### 11.6 Survivorship Bias
- No evidence of survivorship bias handling in data loading
- Delisted securities may be excluded

### 11.7 Transaction Cost Assumptions
- Backtest transaction costs appear to be hard-coded or ignored
- No slippage modeling

---

## 12. Calibration Problems

### What Exists
- `TemperatureScaling` — genuine implementation
- `PlattScaling` — genuine implementation
- `IsotonicCalibration` — genuine implementation

### What's Missing
- **No calibration validation**: Brier score, reliability diagrams, calibration curves are not computed
- **No calibration in production pipeline**: Calibration methods exist but are not wired into the model training/evaluation pipeline
- **No calibration monitoring**: No tracking of calibration drift over time
- **Calibration on full dataset**: When used, calibration is fit on the full dataset, not a held-out validation set

### Impact
- Model probabilities are uncalibrated — a predicted 70% probability does not mean 70% actual frequency
- Confidence scores throughout the fusion system are unreliable
- Risk assessments based on model confidence are unreliable

---

## 13. Fusion / Reasoning Audit

### Confidence Aggregator
- **Agreement metric**: Incorrect — calculates `agreements / total` where `agreements` counts signals agreeing with the majority. This is a majority vote fraction, not a proper ensemble agreement measure.
- **Weighting**: Fixed, arbitrary weights with no learning or adaptation
- **Output**: Confidence value is a weighted average of arbitrary weights — not grounded in data

### Conflict Resolver
- **Resolution strategy**: Hard-coded priority rules (`fundamental > technical > sentiment`)
- **No principled conflict detection**: Conflicts identified by threshold crossing, not information-theoretic measures
- **No source reliability**: All sources treated equally except for priority ordering

### Market Reasoning Engine
- **5 internal modules**: All mostly hard-coded `if/elif` chains
- **Confidence values**: Arbitrary floats (`0.75`, `0.8`, `0.6`) not derived from any data or model
- **Decision logic**: Rule-based, not data-driven
- **Many `pass` statements**: Placeholder methods that do nothing

### Assessment
**The fusion/reasoning system is mostly deterministic rules masquerading as AI.** Confidence values are fabricated, not computed. The reasoning is `if/elif` logic, not learned patterns. This is **not AI/reasoning** — it is a **rule-based expert system with fake confidence scores**.

---

## 14. Forecasting Audit

### TimeSeriesForecaster
- **Status**: Placeholder
- **Evidence**: Methods return hard-coded or random values
- **No real forecasting logic**: No ARIMA, no Prophet, no neural forecasting

### EnsembleForecaster
- **Status**: Aggregates placeholder forecasts
- **Depends on**: Non-functional TimeSeriesForecaster
- **No real ensemble logic**: Just averages random values

### Assessment
**Forecasting is entirely non-functional.** There is no real forecasting capability in the legacy system. Any forecasting results would be random noise.

---

## 15. ML Model Audit

### LogisticRegression
- **Implementation**: Genuine `sklearn.linear_model.LogisticRegression`
- **Problem**: Random train/test split (data leakage)
- **Problem**: No temporal validation
- **Problem**: No calibration
- **Problem**: No feature importance with temporal awareness

### RandomForest
- **Implementation**: Genuine `sklearn.ensemble.RandomForestClassifier`
- **Problem**: Random train/test split (data leakage)
- **Problem**: No temporal validation
- **Problem**: No hyperparameter tuning with temporal awareness

### XGBoost
- **Implementation**: Genuine `xgboost.XGBClassifier`
- **Problem**: Random train/test split (data leakage)
- **Problem**: No temporal validation
- **Problem**: No early stopping with temporal awareness

### LightGBM
- **Implementation**: Genuine `lightgbm.LGBMClassifier`
- **Problem**: Random train/test split (data leakage)
- **Problem**: No temporal validation

### Baselines (Naive, Seasonal)
- **Implementation**: Genuine baseline predictors
- **Problem**: Same random split issue

### Assessment
**All model implementations are genuine but all results are invalid due to data leakage.** The models themselves are correctly implemented wrappers around sklearn/xgboost/lightgbm. The problem is entirely in how they are trained and evaluated.

---

## 16. Feature-Engineering Audit

### Feature Selection Engine
- **Mutual information**: Genuine `sklearn.feature_selection.mutual_info_classif`
- **Correlation filtering**: Genuine `sklearn.feature_selection.f_regression`
- **Combined ranking**: Properly combines scores
- **Assessment**: GENUINE and REUSABLE

### Feature Quality Assessment
- **Missing value handling**: Some implementations exist
- **Outlier detection**: Some implementations exist
- **Feature importance**: Available through SHAP and permutation importance
- **Assessment**: Partially functional

### Feature Provenance
- **Not implemented**: No tracking of which features are used where
- **No lineage**: No data lineage tracking
- **Assessment**: MISSING — needs to be implemented in AURORA CORE

---

## 17. Explainability Audit

### SHAP Integration
- **TreeExplainer**: Genuine interface to `shap.TreeExplainer`
- **LinearExplainer**: Genuine interface to `shap.LinearExplainer`
- **Assessment**: GENUINE and REUSABLE (dependency on `shap` package)

### LIME Integration
- **LimeTabularExplainer**: Genuine interface to `lime.lime_tabular.LimeTabularExplainer`
- **Assessment**: GENUINE and REUSABLE (dependency on `lime` package)

### Permutation Importance
- **Implementation**: Genuine `sklearn.inspection.permutation_importance`
- **Assessment**: GENUINE and REUSABLE

### Attention Visualization
- **Implementation**: Exists for transformer models
- **Problem**: Transformer model is untrained — attention values are random
- **Assessment**: Implementation is genuine but model is non-functional

### Assessment
**Explainability implementations are genuine** but depend on external packages (`shap`, `lime`). The underlying model must be functional for explainability to be meaningful.

---

## 18. Regime-Detection Audit

### Duplicate Implementations
- `ai/regime/detection.py` — KMeans, HMM, GMM approaches
- `ai/regime/detector.py` — Nearly identical duplicate of detection.py

### KMeans Approach
- **Implementation**: Genuine `sklearn.cluster.KMeans`
- **Problem**: Regime labels are hard-coded strings assigned to cluster IDs
- **Problem**: No temporal consistency — same cluster may be labeled differently across runs
- **Problem**: No smoothing — regime can flip every bar

### HMM Approach
- **Implementation**: Genuine `hmmlearn.hmm.GaussianHMM`
- **Problem**: Same hard-coded label assignment
- **Problem**: No regime transition probability modeling in production

### GMM Approach
- **Implementation**: Genuine `sklearn.mixture.GaussianMixture`
- **Problem**: Same hard-coded label assignment

### Assessment
**Regime detection algorithms are genuine but the integration is broken.** The hard-coded regime name assignment means that cluster 0 is always "bull" even if the market is actually in a bear regime. The labels should be dynamically assigned based on cluster characteristics (e.g., cluster with positive mean returns = "bull").

---

## 19. Dependencies Worth Reusing

| Dependency | Version | Purpose | Worth Reusing? |
|-----------|---------|---------|---------------|
| `scikit-learn` | Any | ML algorithms, feature selection, calibration | YES — core ML toolkit |
| `xgboost` | Any | Gradient boosting | YES — proven for tabular data |
| `lightgbm` | Any | Gradient boosting | YES — faster than XGBoost for many cases |
| `shap` | Any | Model explainability | YES — gold standard for feature attribution |
| `lime` | Any | Model-agnostic explanations | YES — useful for model comparison |
| `cvxpy` | Any | Convex optimization (portfolio) | YES — if portfolio optimization needed |
| `hmmlearn` | Any | Hidden Markov Models (regime detection) | YES — if regime detection needed |
| `pandas` | Any | Data manipulation | YES — essential |
| `numpy` | Any | Numerical computation | YES — essential |
| `pyarrow` | Any | Columnar data, Parquet | YES — already used in AURORA CORE |

---

## 20. Dependencies That Should NOT Be Reused

| Dependency | Reason |
|-----------|--------|
| Custom `aurora-ai` package | Monolithic, tightly coupled, no clear interfaces |
| Hard-coded fusion weights | Not a dependency but a design flaw — do not carry over |
| Hard-coded regime labels | Not a dependency but a design flaw — do not carry over |
| Random train/test splits | Not a dependency but a methodology flaw — do not carry over |

---

## 21. Comparison with Current AURORA CORE

| Aspect | Legacy `aurora-ai` | AURORA CORE |
|--------|-------------------|-------------|
| **Data validation** | Minimal | Pydantic schemas, strict validation |
| **Data provenance** | None | SHA-256 hashing, full lineage |
| **Temporal validation** | None (random splits) | TimeBasedSplitter, walk-forward ready |
| **Feature pipeline** | Ad-hoc | FeatureRegistry with numerical/categorical split |
| **Claim extraction** | None | Rule-based + context-aware classification |
| **OCR support** | None | Tesseract integration, quality classification |
| **Hypothesis tracking** | None | ResearchHypothesis with status lifecycle |
| **Knowledge graph** | None | ResearchKnowledgeGraph with edges |
| **Model interfaces** | Hard-coded class inheritance | ModelAdapter ABC with clean contracts |
| **LLM integration** | None | ModelAdapter with stub, local, external backends |
| **Evaluation** | Random splits, no temporal | EvaluationRecord, brier_score, temporal metrics |
| **Calibration** | Methods exist, no integration | Not yet implemented — to be added |
| **Explainability** | SHAP/LIME interfaces | Not yet implemented — to be added |
| **Regime detection** | Duplicate, hard-coded labels | Not yet implemented — to be added |
| **Test coverage** | Unknown | 395 tests, comprehensive |
| **Code quality** | No linting enforced | Ruff + mypy enforced |
| **Architecture** | Monolithic, circular imports | Modular, clear separation of concerns |

---

## 22. KEEP / ADAPT / REIMPLEMENT / REJECT / INVESTIGATE Matrix

| Component | Verdict | Rationale |
|-----------|---------|-----------|
| Feature Selection Engine | **KEEP** | Genuine MI + correlation filtering, directly usable |
| Temporal Pattern Detection | **KEEP** | Genuine momentum, mean reversion, volatility clustering |
| Calibration Methods | **ADAPT** | Genuine implementations but need pipeline integration |
| SHAP/LIME Explainability | **ADAPT** | Genuine interfaces but need pipeline integration |
| Anomaly Detection (individual algorithms) | **KEEP** | Genuine IsolationForest, LOF implementations |
| Portfolio Optimization | **ADAPT** | Genuine cvxpy implementations, if portfolio features needed |
| Backtesting Engine | **ADAPT** | Sound architecture, but must add temporal safeguards |
| Confidence Aggregator | **REIMPLEMENT** | Arbitrary weights, incorrect agreement metric |
| Conflict Resolver | **REIMPLEMENT** | Hard-coded priority rules, no principled logic |
| Market Reasoning Engine | **REIMPLEMENT** | Hard-coded if/elif, fabricated confidence values |
| ML Model Training | **REIMPLEMENT** | Data leakage in all models, no temporal validation |
| Regime Detection | **REIMPLEMENT** | Duplicate implementations, hard-coded label assignment |
| Validation Framework | **REIMPLEMENT** | No temporal cross-validation, no purging/embargo |
| Transformer Time-Series | **REJECT** | Untrained random model, no value |
| Time-Series Forecaster | **REJECT** | Placeholder, no real forecasting logic |
| Ensemble Forecaster | **REJECT** | Aggregates placeholder forecasts |
| Retrieval-Augmented Generation | **REJECT** | Pure stub, no implementation |
| Multimodal Fusion | **REJECT** | Pure stub, no implementation |
| Backtest Results | **INVESTIGATE** | All results invalid due to data leakage — must reproduce with temporal validation |
| Model Accuracy Numbers | **INVESTIGATE** | All results invalid due to data leakage — must reproduce |
| Feature Importance Rankings | **INVESTIGATE** | May be partially valid but methodology is suspect |

---

## 23. Exact Components Recommended for Eventual Integration

### Tier 1: Direct Integration (no modification needed)
1. **Feature Selection Engine** (`ai/features/`) — MI + correlation filtering
2. **Temporal Pattern Detection** (`ai/advanced/temporal.py`) — momentum, mean reversion, volatility clustering
3. **Anomaly Detection Algorithms** (`ai/anomaly/`) — IsolationForest, LOF

### Tier 2: Integration with Adaptation
4. **Calibration Methods** (`ai/calibration/`) — TemperatureScaling, PlattScaling, IsotonicCalibration
   - Adaptation needed: Wire into model evaluation pipeline, add validation metrics
5. **Explainability Interfaces** (`ai/explainability/`) — SHAP, LIME, permutation importance
   - Adaptation needed: Wire into model evaluation pipeline, add reporting
6. **Portfolio Optimization** (`ai/optimization/`) — Mean-Variance, Risk Parity, Black-Litterman
   - Adaptation needed: Only if portfolio management features are added

### Tier 3: Reimplemented from Scratch (using legacy as reference)
7. **Confidence Aggregation** — replace with learned ensemble weighting
8. **Conflict Resolution** — replace with information-theoretic conflict detection
9. **Temporal Cross-Validation** — walk-forward, expanding window, purged k-fold
10. **Regime Detection** — single clean implementation with dynamic labeling

---

## 24. Recommended Architecture After Integration

```
AURORA CORE (after legacy integration)
├── src/aurora/
│   ├── schemas/              # MarketState, FeatureVector, etc. (KEEP existing)
│   ├── data/                 # Data ingestion, validation (KEEP existing)
│   ├── features/
│   │   ├── registry.py       # FeatureRegistry (KEEP existing)
│   │   ├── selectors.py      # NEW: Feature selection (adapted from legacy)
│   │   └── temporal.py       # NEW: Temporal patterns (adapted from legacy)
│   ├── models/
│   │   ├── adapters.py       # ModelAdapter ABC (KEEP existing)
│   │   ├── training.py       # NEW: Temporal cross-validation (reimplemented)
│   │   └── calibration.py    # NEW: Calibration pipeline (adapted from legacy)
│   ├── research/             # KEEP existing research pipeline
│   ├── fusion/               # NEW: Ensemble fusion (reimplemented)
│   ├── explainability/       # NEW: SHAP/LIME (adapted from legacy)
│   ├── anomaly/              # NEW: Anomaly detection (adapted from legacy)
│   ├── evaluation/           # NEW: Temporal evaluation metrics (reimplemented)
│   └── regime/               # NEW: Regime detection (reimplemented)
```

---

## 25. Why Each Recommended Component Is Useful

| Component | Why Useful |
|-----------|-----------|
| Feature Selection (MI) | Principled feature ranking based on information theory; reduces dimensionality; identifies most predictive features |
| Feature Selection (Correlation) | Identifies linear relationships; complementary to MI for non-linear relationships |
| Temporal Patterns (Momentum) | Captures trend continuation; widely used in quantitative finance |
| Temporal Patterns (Mean Reversion) | Captures overshoot and reversal; complementary to momentum |
| Temporal Patterns (Volatility Clustering) | Captures volatility regimes; essential for risk management |
| Calibration (Temperature) | Simple, single-parameter calibration; prevents overconfident predictions |
| Calibration (Platt) | Logistic calibration; good for binary classifiers |
| Calibration (Isotonic) | Non-parametric calibration; most flexible |
| SHAP Explanations | Gold-standard feature attribution; game-theoretic foundation; model-agnostic |
| LIME Explanations | Local interpretable explanations; useful for individual predictions |
| Permutation Importance | Model-agnostic; measures feature importance by disruption |
| Anomaly Detection (IsolationForest) | Efficient outlier detection; no distributional assumptions |
| Anomaly Detection (LOF) | Local density-based outlier detection; captures local anomalies |

---

## 26. Risks Remaining

### HIGH RISK
1. **All legacy model results are invalid** — Must reproduce with temporal validation before trusting any numbers
2. **Data leakage pervasive** — Every model in the legacy system suffers from temporal leakage
3. **Fabricated confidence values** — Fusion system confidence scores are not grounded in data

### MEDIUM RISK
4. **No calibration in production** — Calibration methods exist but are not integrated
5. **Duplicate regime detection** — Two implementations create maintenance burden and confusion
6. **No feature provenance** — Cannot trace which features contributed to which predictions
7. **Hard-coded assumptions throughout** — Fusion weights, regime labels, reasoning thresholds

### LOW RISK
8. **External dependency versions** — Legacy may use older versions of sklearn, xgboost, etc.
9. **Code style inconsistencies** — Legacy does not enforce linting or type checking
10. **No test coverage enforcement** — Legacy has no visible test suite

---

## 27. Final Recommendation for Phase 6

### Do NOT merge legacy code into AURORA CORE.

The legacy codebase has **significant data leakage, fabricated outputs, and placeholder implementations** that would contaminate AURORA CORE's clean architecture.

### Recommended Phase 6 approach:

1. **Phase 6.1 — Temporal Validation Framework**
   - Implement walk-forward, expanding window, and purged k-fold cross-validation
   - This is the foundation for all future model work
   - AURORA CORE's existing `TimeBasedSplitter` provides a starting point

2. **Phase 6.2 — Feature Selection Integration**
   - Adapt the legacy Feature Selection Engine (MI + correlation filtering)
   - Integrate with AURORA CORE's FeatureRegistry
   - Add temporal awareness to feature selection

3. **Phase 6.3 — Calibration Pipeline**
   - Adapt legacy calibration methods (Temperature, Platt, Isotonic)
   - Wire into model evaluation pipeline
   - Add Brier score, reliability diagrams, calibration curves

4. **Phase 6.4 — Explainability Integration**
   - Adapt SHAP/LIME interfaces
   - Add to model evaluation pipeline
   - Generate explanations for all model predictions

5. **Phase 6.5 — Anomaly Detection**
   - Adapt IsolationForest and LOF
   - Add to feature pipeline or as standalone detector

6. **Phase 6.6+ — Later**
   - Regime detection (reimplemented, not legacy duplicate)
   - Ensemble fusion (reimplemented, not legacy hard-coded)
   - Portfolio optimization (if needed)

### What NOT to do in Phase 6:
- Do NOT merge legacy models (all have data leakage)
- Do NOT merge legacy fusion (hard-coded, fabricated confidence)
- Do NOT merge legacy reasoning (hard-coded rules, fake confidence)
- Do NOT merge legacy forecasting (placeholder)
- Do NOT merge legacy regime detection (duplicate, hard-coded labels)
- Do NOT merge legacy transformer (untrained random model)
- Do NOT reproduce legacy backtest results (invalid due to data leakage)

---

## LEGACY AUDIT STATUS:

**COMPLETE**

---

*Report generated by AURORA CORE Agent on 2026-08-15.*
*All legacy predictions, confidence scores, accuracy numbers, backtest results, and probabilities are UNVERIFIED until independently reproduced with proper temporal validation.*
*Do not implement anything after this report. Stop and wait for approval.*
