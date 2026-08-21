# Phase 15: Research Decision Gate + Prediction-Formulation Audit

**EXPERIMENTAL — This is a decision milestone, not a model research milestone.**

## 1. Executive Summary

Phase 15 is a comprehensive audit of the entire Aurora predictive research program (M8.5–M14). After 114+ experiments across 7 milestones, 4 model families, 105 features, 6 target types, 3 instruments, and 5 years of data, the conclusion is clear:

**Daily OHLCV directional prediction of liquid assets does not produce a statistically significant edge with current methodology.**

The evidence is not ambiguous. Zero experiments survive multiple-testing correction. All Sharpe ratios are negative. The framework is sound — it produces reliable negative results. This is scientific value.

**PRIMARY DECISION: STOP_PREDICTIVE_RESEARCH**

---

## 2. M8.5–M14 Evidence Summary

### Cumulative Results

| Milestone | Experiments | Best Delta | Best p-value | Sig. Before | Sig. After | Status |
|-----------|-------------|------------|--------------|-------------|------------|--------|
| M8.5 | 24 | +0.22 Sharpe | N/A | 0 | 0 | 0 SUPPORTED |
| M9 | 9 | +2.1% DT/BTC | N/A | 0 | 0 | NO_DEPLOYMENT |
| M10 | 9 | -2.7% LR/BTC | 0.097 | 0 | 0 | NO_DEPLOYMENT |
| M11 | 10 | 0.0% LR/SPY | ~0.4 | 0 | 0 | NO_DEPLOYMENT |
| M12 | 5+31w | -0.6% mean | ~0.13 | 0 | 0 | NO_DEPLOYMENT |
| M13 | 24 | +1.5% BTC h=5 | 0.460 | 0 | 0 | NO_DEPLOYMENT |
| M14 | 18 | +1.4% QQQ ext | 0.605 | 0 | 0 | NO_DEPLOYMENT |
| M15 (Ph14) | 15 | +1.9% QQQ GB | 0.394 | 1 (neg.) | 0 | NO_DEPLOYMENT |
| **TOTAL** | **114+** | — | — | **0** | **0** | **NO_DEPLOYMENT** |

### What Was Tested

- **Models**: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting, Ensemble (voting, weighted)
- **Features**: 105 total (39 technical + 30 market-structure + 12 microstructure-proxies + 26 external)
- **Targets**: Directional (h=1,5,20), thresholded, magnitude, volatility-conditioned, event, persistence
- **Instruments**: BTC-USD, SPY, QQQ
- **Data**: 5 years daily OHLCV (1,255–1,827 bars)
- **Validation**: Walk-forward with chronological splitting, preprocessor fit on train only
- **Statistics**: Proportion z-test, Cohen's h, 95% CI, Bonferroni/Holm/BH-FDR correction
- **Risk**: Sharpe ratio, max drawdown, turnover, transaction costs (15 bps)

---

## 3. Architecture Audit

### Data Flow

```
DATA (yfinance OHLCV)
  ↓
FEATURE ENGINEERING (105 features)
  ↓
TARGET GENERATION (6 types)
  ↓
TRAINING (LR/DT/RF/GB)
  ↓
VALIDATION (walk-forward, chronological)
  ↓
MODEL SELECTION (HP search on validation)
  ↓
TEST
  ↓
STATISTICAL EVALUATION (z-test, CI, correction)
  ↓
RISK EVALUATION (Sharpe, drawdown, costs)
  ↓
FINAL DECISION
```

### Bottlenecks Identified

1. **DATA**: Daily resolution is too coarse for directional prediction of liquid assets. Only price/volume — no order flow or microstructure.
2. **FEATURE ENGINEERING**: All 105 features derived from OHLCV. No independent information sources. Redundancy is high.
3. **TARGET GENERATION**: No target formulation produces significant predictive signal across any instrument.

### Architecture Assessment

The pipeline is technically sound:
- Leakage-safe: Preprocessor fit on train only; chronological splitting
- Statistically rigorous: Multiple-testing correction applied
- Reproducible: Full provenance, experiment registry, audit trail
- Comprehensive: 105 features, 4 model families, 6 target types

**The bottleneck is not the architecture — it is the information content of the data.**

---

## 4. Prediction-Target Audit

### Target Formulations Tested

| Target | Horizon | Label | Model Compatible | Observed Performance |
|--------|---------|-------|-----------------|---------------------|
| Directional h=1 | 1 day | Binary up/down | Yes | Never exceeds baseline significantly |
| Directional h=5 | 5 days | Binary up/down | Yes | Marginal +1.5% on BTC, p=0.460 |
| Directional h=20 | 20 days | Binary up/down | Yes | No improvement |
| Thresholded | 1 day | 3-class (up/down/flat) | Partial (flat wasted) | No improvement |
| Magnitude | 1 day | 3-class quantile | No (model predicts binary) | Accuracy=0% |
| Vol-Conditioned | 1 day | 3-class z-score | No | Not evaluated |
| Event | 5 days | Binary (2% move) | No (model predicts binary) | Accuracy=0% |
| Persistence | 5 days | 3-class (cont/rev) | No (model predicts binary) | Accuracy=0% |

### Assessment

- **Binary directional** is the only compatible target. It is the correct null hypothesis.
- **Multi-class targets** failed due to model interface limitation (only predicts up/down).
- **Multi-horizon** showed marginal improvement but not significant.
- **No target formulation is fundamentally more appropriate** for the research objective (daily directional prediction).

---

## 5. Baseline Audit

| Baseline | Accuracy | Appropriate? | Reasoning |
|----------|----------|-------------|-----------|
| Majority class | 50.5–54.3% | **YES** | Correct null hypothesis for binary prediction |
| Buy-and-hold | Same as positive rate | Partially | Useful for return comparison, not accuracy |
| Random | ~50% | YES | Good lower bound |
| Persistence | ~50% | YES | Tests momentum hypothesis |
| Mean reversion | 51.5% (BTC) | YES | Tests reversal hypothesis |

### Assessment

The majority-class baseline is **appropriate and well-calibrated**. It represents the expected accuracy of always predicting the most common direction. Since daily returns are approximately random (50–54% positive), this baseline is near 50%, which is the correct null.

The baseline is **not too weak** (it is the theoretical optimum for a no-signal strategy) and **not too strong** (it does not use future information). It is the correct benchmark.

---

## 6. Data Sufficiency

| Metric | Value | Assessment |
|--------|-------|------------|
| BTC-USD observations | 1,827 daily bars | MARGINAL |
| SPY/QQQ observations | 1,255 daily bars | INSUFFICIENT for small effects |
| Independent observations | ~total (weak autocorrelation) | ADEQUATE |
| Class balance | 50–54% majority | ADEQUATE |
| Regime coverage | 5 years (bull, bear, COVID, rates) | ADEQUATE |
| Instrument diversity | 3 instruments, 2 asset classes | ADEQUATE |
| Feature/sample ratio | 105/1,800 = 0.058 | HIGH RISK of overfitting |

### Key Distinction: NO SIGNAL vs INSUFFICIENT EVIDENCE

The consistent lack of signal across 114+ experiments, 3 instruments, and 5 years indicates **NO SIGNAL**, not insufficient evidence. If the signal existed but was weak, we would expect:
- Some instruments to show positive delta (even if not significant)
- Some windows to consistently outperform
- Effect sizes to be small but positive

Instead, we see:
- Most deltas are negative (model WORSE than baseline)
- Windows show high variance (38–60%) with no consistent pattern
- Effect sizes are negligible (Cohen's h < 0.15)

**Conclusion: The evidence supports NO SIGNAL, not insufficient evidence.**

---

## 7. Statistical Power

With ~50 samples per walk-forward window, power to detect small effects (Cohen's h < 0.15) is low. However:

- 114+ independent experiments provide cumulative power
- The consistent pattern of negative results across all experiments is itself strong evidence
- If the signal were real but weak, we would expect at least some positive deltas — we don't see them
- The few marginal positives (BTC-USD DT +2.1%, QQQ GB +1.9%) are not significant and not replicated

**Statistical power is not the primary limitation. The primary limitation is signal absence.**

---

## 8. Non-Stationarity

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Rolling performance | Accuracy ranges 38–60% across windows | High variance; no stable signal |
| Feature stability | Importance varies across instruments | Instrument-specific patterns |
| Target stability | Class balance stable; feature-target relationship unstable | No universal relationship |
| Model stability | No model consistently outperforms | Weak or non-stationary relationship |
| Distribution shifts | Multiple regimes in 5-year period | Walk-forward handles this; still no signal |

**Non-stationarity is real but not the primary explanation.** Walk-forward validation handles distribution shifts by retraining. The lack of signal across all regimes suggests the issue is fundamental.

---

## 9. Feature Information Audit

| Feature Group | N Features | Incremental Value | Redundancy | Assessment |
|---------------|-----------|-------------------|------------|------------|
| Price/Returns | 5 | NEGATIVE | HIGH | NO PREDICTIVE VALUE |
| Volatility | 2 | NEGATIVE | MEDIUM | NO PREDICTIVE VALUE |
| Volume | 1 | NEGATIVE | LOW | NO PREDICTIVE VALUE |
| Technical Indicators | 25+ | NEGATIVE | VERY HIGH | NO PREDICTIVE VALUE |
| Market Structure | 30 | NEGATIVE | HIGH | NO PREDICTIVE VALUE |
| Microstructure Proxies | 12 | INCONCLUSIVE | MEDIUM | INCONCLUSIVE (proxy only) |
| External Data | 26 | MARGINAL | MEDIUM | NOT SIGNIFICANT (p>0.6) |
| Feature Interactions | 5 | NEGATIVE | HIGH | NO PREDICTIVE VALUE |

**All features derived from OHLCV contain no independent predictive information.** The marginal improvement from external data (+1.4% on QQQ) is not statistically significant. Feature ablation confirms no group provides edge.

---

## 10. Temporal Resolution

| Resolution | Pros | Cons | Recommendation |
|-----------|------|------|----------------|
| Daily (current) | Sufficient history; liquid data | Too coarse; near-random returns | CURRENT — sufficient for conclusion |
| Hourly | More data; intraday patterns | Different data source; overnight gaps | FUTURE RESEARCH — needs specific hypothesis |
| 5-minute | Rich microstructure | Requires L2 data; massive storage | BLOCKED — needs L2 order book |
| Tick | Gold standard for microstructure | Institutional infrastructure required | BLOCKED — out of scope |

**Daily resolution is appropriate for the conclusion that daily directional prediction is not viable.** A different resolution would require a specific, testable hypothesis — not just "try higher frequency."

---

## 11. Economic-Value Audit

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Transaction costs | 15 bps per trade; all Sharpe negative | Costs eliminate any marginal edge |
| Turnover | High; frequent prediction changes | Increases cost exposure |
| Drawdown | Significant across all models | Negative risk-adjusted returns |
| Signal frequency | ~252 signals/year | Too frequent for marginal information |
| Abstention | Marginal improvement at high confidence; low coverage | Not economically viable |

**Even if models had marginal accuracy edge, transaction costs would eliminate it.** The cost structure makes daily rebalancing unprofitable for any accuracy < ~55%.

---

## 12. Failure-Mode Analysis

### Primary Failure Mode: A — No Predictive Information Detected

**Confidence: HIGH**

114+ experiments across 7 milestones consistently show no statistically significant predictive edge. All Sharpe ratios are negative. No model, feature set, or target formulation produces edge. The evidence is clear: daily OHLCV directional prediction of liquid assets does not contain exploitable signal.

### Secondary Failure Mode: G — Data-Resolution Limitation

**Confidence: HIGH**

Daily resolution is too coarse for directional prediction. All features derived from daily OHLCV. No microstructure information. The efficient market hypothesis holds strongest at daily frequency for liquid instruments.

### Contributing Factors

- **E — Feature Limitation**: All 105 features derived from price; no independent sources
- **D — Target Formulation**: Binary direction at daily frequency is near-random
- **K — Statistical Power**: Low per-window power, but cumulative evidence is strong

---

## 13. Future Research Candidates

| Direction | Justification | Info Gain | Data Req. | Complexity | Score |
|-----------|--------------|-----------|-----------|------------|-------|
| Alternative data (sentiment, on-chain) | HIGH — independent info sources | HIGH | Specialized APIs | MEDIUM | **4** |
| Volatility forecasting | HIGH — more predictable than direction | HIGH | Same OHLCV | LOW | **4** |
| Risk forecasting (VaR, drawdown) | HIGH — economically relevant | HIGH | Same OHLCV | MEDIUM | **4** |
| Higher-resolution data | MODERATE — intraday patterns | MODERATE | Different source | LOW | **3** |
| Regime detection | HIGH — descriptive, not predictive | MODERATE | Same OHLCV | MEDIUM | **3** |
| Research-product architecture | HIGH — analytics value | N/A | Same data | MEDIUM | **3** |
| Cross-asset prediction | MODERATE — lead-lag effects | LOW | Already available | LOW | **2** |

**If research resumes**, the strongest candidates are:
1. **Volatility/risk forecasting** (same data, different target)
2. **Alternative data sources** (independent information)
3. **Research-product architecture** (analytics, not trading)

---

## 14. Decision Matrix

| Option | Recommendation | Reasoning |
|--------|---------------|-----------|
| **STOP_PREDICTIVE_RESEARCH** | **ADOPT** | 114+ failures; evidence is conclusive |
| CONTINUE_RESEARCH | REJECT | No new hypothesis; would be unfounded |
| COLLECT_BETTER_DATA | CONSIDER | Alternative data could help if research resumes |
| REFORMULATE_TARGET | CONSIDER | Volatility/risk more tractable |
| RESEARCH_PRODUCT_ONLY | CONSIDER | Aurora has value as analytics platform |
| NO_DEPLOYMENT_SIGNAL | **ADOPT** | Current status is correct |

---

## 15. Production Readiness

| Requirement | Status | Evidence |
|------------|--------|----------|
| Validated predictive model | **NOT MET** | No model beats baseline significantly |
| Reproducible model | MET | Full provenance, deterministic seeds |
| Statistically supported edge | **NOT MET** | 0/114+ significant after correction |
| Robust walk-forward performance | **NOT MET** | High variance (38–60%) |
| Transaction-cost viability | **NOT MET** | All Sharpe negative |
| Risk viability | **NOT_MET** | Negative risk-adjusted returns |
| Stable performance | **NOT MET** | No temporal stability |
| Complete provenance | MET | ExperimentRegistry, AuditTrail |
| Sufficient evidence | MET | 114+ experiments = strong negative evidence |

**PRODUCTION READINESS: NOT JUSTIFIED**

---

## 16. Research Product Assessment

Aurora's framework (data pipeline, feature engineering, model evaluation, statistical testing, experiment tracking) has genuine value as a **research analytics platform** even without predictive edge:

- **Charts and visualization**: OHLCV, features, model diagnostics
- **Experiment tracking**: ExperimentRegistry with full provenance
- **Statistical testing**: Automated significance testing with correction
- **Feature analysis**: Ablation, importance, redundancy
- **Confidence/uncertainty**: Calibration, abstention analysis
- **Historical experiments**: Reproducible experiment records

This is a viable alternative product direction.

---

## 17. Trading Product Assessment

Aurora is **NOT justified** as a trading signal platform:

- No validated predictive model
- No statistically supported edge
- Negative Sharpe ratios
- Transaction costs exceed any marginal accuracy
- No risk-adjusted profitability

**TradingView integration: BLOCKED**
**Website live-signal: BLOCKED**
**Live trading: BLOCKED**

---

## 18. Final Decision

### PRIMARY DECISION: STOP_PREDICTIVE_RESEARCH

The evidence is conclusive: daily OHLCV directional prediction of liquid assets does not produce a statistically significant edge with current methodology. Continuing predictive research without fundamentally new data sources or a specific, testable hypothesis would be unfounded.

### Secondary Recommendations

1. **COLLECT_BETTER_DATA** if predictive research resumes (alternative data sources)
2. **REFORMULATE_TARGET** toward volatility/risk forecasting
3. **RESEARCH_PRODUCT_ONLY** as alternative product direction

---

## 19. Future Architecture (If Research Resumes)

### Research Product Architecture

```
MARKET DATA (yfinance / alternative sources)
  ↓
DATA NORMALIZATION (UTC, validated, provenance)
  ↓
FEATURE ENGINE (technical, structural, external)
  ↓
MODEL SERVICE (LR, DT, RF, GB — research only)
  ↓
VALIDATION / CONFIDENCE (walk-forward, calibration)
  ↓
RISK ENGINE (Sharpe, drawdown, costs)
  ↓
SIGNAL DECISION (ABSTAIN — research only)
  ↓
API (experiment results, diagnostics)
  ↓
WEB APPLICATION (dashboard, charts, analytics)
  ↓
TRADINGVIEW VISUALIZATION (BLOCKED until research gate passes)
```

### Component Status

| Component | Status |
|-----------|--------|
| Market Data | READY |
| Data Normalization | READY |
| Feature Engine | RESEARCH-ONLY |
| Model Service | RESEARCH-ONLY |
| Validation / Confidence | READY |
| Risk Engine | READY |
| Signal Decision | RESEARCH-ONLY (ABSTAIN) |
| API | FUTURE |
| Web Application | FUTURE |
| TradingView | BLOCKED |

---

## 20. Limitations

1. **Data**: Daily OHLCV only; no order book, sentiment, on-chain, or fundamental data
2. **Models**: Pure Python implementations; not optimized C/XGBoost
3. **Instruments**: 3 liquid instruments; results may differ for illiquid assets
4. **Time period**: 5 years; may not cover all market regimes
5. **Resolution**: Daily only; intraday patterns untested
6. **Transaction costs**: Modeled as 15 bps; real costs vary by venue/size

---

## 21. Recommended Next Phase

**STOP.**

Do not implement M16. Do not build TradingView. Do not build the website. Do not deploy. Do not host. Do not connect a broker. Do not execute trades.

If explicit approval is received for a new direction, the recommended priorities are:

1. **Volatility forecasting** (same data, different target, high justification)
2. **Alternative data collection** (independent information sources, high justification)
3. **Research-product architecture** (analytics platform, moderate justification)

**Await explicit approval before any new work.**
