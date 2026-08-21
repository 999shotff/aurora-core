# Phase 14: Advanced Model + Ensemble + Feature Selection + Risk Research

**EXPERIMENTAL — No deployment signal.**

## Summary

Phase 14 evaluated gradient boosting, ensemble voting, feature selection, calibration, and diversity analysis across BTC-USD, SPY, and QQQ with 5 years of daily data. **No experiment produces a statistically significant improvement over the baseline after multiple-testing correction.**

## Architecture

- **GradientBoostingClassifier**: Pure Python gradient boosting with decision stumps, logistic loss, configurable learning rate/estimators/depth
- **Model Factory**: LR, Decision Tree, Random Forest, Gradient Boosting
- **Grid Search**: Hyperparameter optimization on validation set (selection only, not deployment)
- **Feature Selection**: Permutation importance and model-based importance
- **Ensemble**: Hard vote, soft vote, weighted vote
- **Diversity**: Prediction agreement, probability correlation, error overlap
- **Calibration**: Brier score, mean calibration error

## Results

### BTC-USD (Baseline: 0.505)

| Model | Accuracy | Delta | p-value | Sharpe | Brier |
|-------|----------|-------|---------|--------|-------|
| Logistic Regression | 0.492 | -0.013 | 0.462 | -0.388 | 0.403 |
| Decision Tree | 0.493 | -0.013 | 0.484 | -0.360 | 0.352 |
| Random Forest | 0.491 | -0.015 | 0.419 | -0.391 | 0.268 |
| Gradient Boosting | 0.511 | +0.005 | 0.760 | -0.367 | 0.251 |
| Ensemble (LR+DT) | 0.497 | -0.008 | 0.654 | — | — |

Corrected p-values: [1.0, 1.0, 1.0, 1.0, 1.0] — **0/5 significant**

### SPY (Baseline: 0.541)

| Model | Accuracy | Delta | p-value | Sharpe | Brier |
|-------|----------|-------|---------|--------|-------|
| Logistic Regression | 0.527 | -0.014 | 0.540 | -0.227 | 0.375 |
| Decision Tree | 0.491 | -0.050 | 0.026 | -0.292 | 0.344 |
| Random Forest | 0.526 | -0.015 | 0.511 | -0.203 | 0.262 |
| Gradient Boosting | 0.553 | +0.012 | 0.580 | -0.116 | 0.247 |
| Ensemble (LR+DT) | 0.512 | -0.029 | 0.199 | — | — |

Corrected p-values: [1.0, 0.131, 1.0, 1.0, 0.996] — **0/5 significant**

### QQQ (Baseline: 0.543)

| Model | Accuracy | Delta | p-value | Sharpe | Brier |
|-------|----------|-------|---------|--------|-------|
| Logistic Regression | 0.494 | -0.049 | 0.028 | -0.332 | 0.401 |
| Decision Tree | 0.508 | -0.035 | 0.116 | -0.242 | 0.358 |
| Random Forest | 0.521 | -0.022 | 0.323 | -0.211 | 0.266 |
| Gradient Boosting | 0.562 | +0.019 | 0.394 | -0.133 | 0.247 |
| Ensemble (LR+DT) | 0.500 | -0.043 | 0.054 | — | — |

Corrected p-values: [0.141, 0.582, 1.0, 1.0, 0.270] — **0/5 significant**

## Cross-Instrument Summary

- **Total experiments**: 15 (5 per instrument × 3 instruments)
- **Significant before correction**: 1 (QQQ DT p=0.028, but directionally negative — model WORSE than baseline)
- **Significant after correction**: 0
- **Best positive delta**: QQQ Gradient Boosting +1.9% (p=0.394, not significant)
- **All Sharpe ratios negative**: Every model produces negative risk-adjusted returns
- **No ensemble outperforms individual models**

## Key Findings

1. **Gradient Boosting** consistently achieves the highest accuracy (closest to baseline) but never exceeds it significantly
2. **No model architecture** produces statistically significant improvement over baseline
3. **All Sharpe ratios negative** — no model generates positive risk-adjusted returns
4. **Ensemble voting** does not improve over individual models (LR+DT ensemble worse than either alone on QQQ/SPY)
5. **Feature selection** identifies 10 features via permutation importance — same pattern across instruments
6. **Diversity analysis** shows moderate prediction agreement (0.56-0.72) but insufficient for ensemble benefit
7. **Calibration** is well-calibrated (Brier ~0.25-0.40) but calibration does not imply predictive power

## Test Results

- Phase 14 tests: 22 pass
- Total test suite: 1046 pass, 0 fail

## Classification

**NO_DEPLOYMENT_SIGNAL** — Advanced models, ensemble methods, and feature selection do not produce statistically significant improvement over baseline after multiple-testing correction.
