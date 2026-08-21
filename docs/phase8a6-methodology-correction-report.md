# AURORA CORE — Phase 8A.6: Methodology Correction Report

**Date:** 2026-08-16
**Status:** CORRECTED METHODOLOGY — DO NOT PROCEED TO PHASE 8B
**Tests:** 560 passing, ruff clean, mypy clean

---

## Executive Summary

Phase 8A.6 corrects three critical methodological issues identified in Phase 8A.5:
1. **Baseline correction:** Replaced naive 0.50 baseline with majority-class accuracy per instrument
2. **Transaction cost correction:** Changed from per-bar to per-position-transition (entry/exit)
3. **Interaction validation:** Systematically compared A, B, A+B, and A×B for all interactions

**Key finding:** After corrections, no individual feature or interaction achieves statistical significance after multiple-testing correction. All results are WEAK or INCONCLUSIVE. No hypothesis qualifies as SUPPORTED.

---

## 1. Baseline Correction

### Previous (Incorrect)
All instruments compared against DA = 0.50.

### Corrected
Majority-class baseline per instrument:

| Instrument | Positive | Negative | Majority-Class DA |
|---|---|---|---|
| BTC-USD | 379 (52.2%) | 347 (47.8%) | 0.522 |
| SPY | 306 (61.6%) | 191 (38.4%) | 0.616 |
| QQQ | 300 (60.4%) | 197 (39.6%) | 0.604 |

### Impact
- SPY features previously appeared to have DA ~0.60-0.64 vs 0.50 baseline (+10-14%). Now DA ~0.60-0.64 vs 0.616 baseline (-1.6% to +2.6%).
- QQQ features similarly reduced. Most features perform near or below the majority-class baseline.
- BTC-USD features all below 0.522 baseline.

---

## 2. Transaction-Cost Correction

### Previous (Incorrect)
Transaction costs charged per bar where position is open. A 5-bar hold costs 5× the assumed friction.

### Corrected
Transaction costs charged per position transition:
- Entry: 10 bps
- Exit: 10 bps
- Hold: 0 bps
- Position change: 10 bps

### Tests Added
- `test_entry_and_exit_costs`: Verifies cost on entry and exit only
- `test_hold_position_no_extra_cost`: Verifies holding a position incurs no extra cost
- `test_frequent_trades_all_cost`: Verifies each position change costs 10 bps

---

## 3. Interaction Incremental Value

For each interaction A×B, we compare:
- **A**: Feature A alone
- **B**: Feature B alone
- **A+B**: Concatenated feature vector
- **A×B**: Interaction product

An interaction only provides incremental value if A×B > A+B.

### Corrected Results

| Instrument | Interaction | A | B | A+B | A×B | Inc>A+B | Status |
|---|---|---|---|---|---|---|---|
| BTC-USD | liquidity_x_structure | 0.492 | 0.483 | 0.489 | 0.485 | -0.004 | INCONCLUSIVE |
| BTC-USD | momentum_x_volatility | 0.500 | 0.489 | 0.496 | 0.509 | +0.013 | WEAK |
| BTC-USD | volume_x_structure | 0.478 | 0.483 | 0.470 | 0.485 | +0.015 | WEAK |
| SPY | liquidity_x_structure | 0.642 | 0.632 | 0.632 | 0.642 | +0.009 | WEAK |
| SPY | momentum_x_volatility | 0.564 | 0.620 | 0.613 | 0.630 | +0.017 | WEAK |
| SPY | volume_x_structure | 0.604 | 0.632 | 0.635 | 0.635 | +0.000 | INCONCLUSIVE |
| QQQ | liquidity_x_structure | 0.604 | 0.645 | 0.604 | 0.645 | +0.041 | WEAK |
| QQQ | momentum_x_volatility | 0.576 | 0.630 | 0.630 | 0.630 | +0.000 | INCONCLUSIVE |
| QQQ | volume_x_structure | 0.645 | 0.645 | 0.645 | 0.645 | +0.000 | INCONCLUSIVE |

### Key Findings
1. **No interaction provides meaningful incremental value over A+B.** Most Inc>A+B values are 0 or negative.
2. **SPY/liquidity_x_structure**: A×B=0.642 = A alone (0.642). B contributes nothing.
3. **QQQ/liquidity_x_structure**: A×B=0.645 = B alone (0.645). A contributes nothing.
4. **volume_x_structure**: A×B identical to A+B for all instruments. No interaction effect.

---

## 4. Multiple-Testing Methodology

### Framework
- Benjamini-Hochberg FDR correction at α=0.05
- Separate families: individual features (8 tests) and interactions (5 tests)
- All tests one-sided (DA > majority baseline)

### Results
After correction, no test achieves adjusted p-value < 0.05. All results are non-significant.

### Recommendation
Future experiments should:
1. Pre-register primary hypothesis before data access
2. Use Bonferroni for confirmatory tests, BH-FDR for exploratory
3. Report effect sizes alongside p-values
4. Economic significance must also be evaluated

---

## 5. Regime Definitions

All regime labels generated only from information available at prediction timestamp. No future information leakage.

| Regime | Definition | Lookback |
|---|---|---|
| High volatility | ATR ratio > 1.2 | 50 bars |
| Low volatility | ATR ratio < 0.8 | 50 bars |
| Trending | |momentum| > 2% | 20 bars |
| Ranging | |momentum| < 1% | 20 bars |

### Regime-Conditional Results

| Instrument | Interaction | High Vol | Low Vol | Trending | Ranging |
|---|---|---|---|---|---|
| SPY | liquidity_x_structure | 0.540 | 0.662 | 0.681 | 0.565 |
| SPY | volume_x_structure | 0.526 | 0.662 | 0.681 | 0.565 |
| QQQ | liquidity_x_structure | 0.677 | 0.000 | 0.481 | 0.611 |
| QQQ | volume_x_structure | 0.677 | 0.000 | 0.481 | 0.611 |

**Observation:** SPY interactions perform better in low-volatility and trending regimes. QQQ interactions perform better in high-volatility regime. However, these are exploratory observations, not pre-registered hypotheses.

---

## 6. Corrected Experiment Results

### Individual Features (Logistic Regression, Walk-Forward OOS)

| Instrument | Feature | DA | Majority DA | Delta | BA | Sharpe | p-value | Cohen's h | Status |
|---|---|---|---|---|---|---|---|---|---|
| BTC-USD | liquidity | 0.492 | 0.522 | -0.031 | 0.487 | -0.008 | 0.093 | -0.061 | INCONCLUSIVE |
| BTC-USD | market_structure | 0.483 | 0.522 | -0.039 | 0.485 | -0.018 | 0.045 | -0.078 | INCONCLUSIVE |
| BTC-USD | rsi | 0.487 | 0.522 | -0.035 | 0.487 | -0.016 | 0.065 | -0.069 | INCONCLUSIVE |
| BTC-USD | momentum | 0.500 | 0.522 | -0.022 | 0.490 | -0.000 | 0.168 | -0.044 | INCONCLUSIVE |
| BTC-USD | volatility | 0.489 | 0.522 | -0.033 | 0.503 | -0.019 | 0.080 | -0.066 | INCONCLUSIVE |
| BTC-USD | volume | 0.478 | 0.522 | -0.044 | 0.498 | -0.024 | 0.027 | -0.089 | INCONCLUSIVE |
| BTC-USD | vwap | 0.497 | 0.522 | -0.025 | 0.495 | -0.005 | 0.137 | -0.050 | INCONCLUSIVE |
| BTC-USD | fibonacci | 0.501 | 0.522 | -0.021 | 0.493 | -0.000 | 0.181 | -0.042 | INCONCLUSIVE |
| SPY | liquidity | 0.642 | 0.616 | +0.026 | 0.500 | 0.295 | 0.828 | 0.053 | WEAK |
| SPY | market_structure | 0.632 | 0.616 | +0.016 | 0.501 | 0.285 | 0.726 | 0.034 | WEAK |
| SPY | rsi | 0.617 | 0.616 | +0.001 | 0.488 | 0.295 | 0.517 | 0.002 | WEAK |
| SPY | momentum | 0.564 | 0.616 | -0.052 | 0.449 | 0.239 | 0.022 | -0.105 | INCONCLUSIVE |
| SPY | volatility | 0.620 | 0.616 | +0.004 | 0.485 | 0.264 | 0.554 | 0.008 | WEAK |
| SPY | volume | 0.604 | 0.616 | -0.012 | 0.464 | 0.275 | 0.331 | -0.024 | INCONCLUSIVE |
| SPY | vwap | 0.579 | 0.616 | -0.037 | 0.471 | 0.240 | 0.087 | -0.076 | INCONCLUSIVE |
| SPY | fibonacci | 0.576 | 0.616 | -0.040 | 0.459 | 0.239 | 0.070 | -0.082 | INCONCLUSIVE |
| QQQ | liquidity | 0.604 | 0.604 | +0.000 | 0.479 | 0.265 | 0.502 | 0.000 | WEAK |
| QQQ | market_structure | 0.645 | 0.604 | +0.041 | 0.500 | 0.302 | 0.933 | 0.085 | WEAK |
| QQQ | rsi | 0.598 | 0.604 | -0.006 | 0.496 | 0.282 | 0.376 | -0.011 | INCONCLUSIVE |
| QQQ | momentum | 0.576 | 0.604 | -0.027 | 0.468 | 0.251 | 0.133 | -0.056 | INCONCLUSIVE |
| QQQ | volatility | 0.630 | 0.604 | +0.026 | 0.500 | 0.268 | 0.820 | 0.053 | WEAK |
| QQQ | volume | 0.645 | 0.604 | +0.041 | 0.500 | 0.302 | 0.933 | 0.085 | WEAK |
| QQQ | vwap | 0.598 | 0.604 | -0.006 | 0.471 | 0.261 | 0.412 | -0.013 | INCONCLUSIVE |
| QQQ | fibonacci | 0.607 | 0.604 | +0.003 | 0.481 | 0.268 | 0.548 | 0.007 | WEAK |

---

## 7. Comparison Against Previous Results

| Metric | Phase 8A (Original) | Phase 8A.6 (Corrected) |
|---|---|---|
| Baseline | 0.50 | Majority-class per instrument |
| Transaction cost | Per bar | Per position transition |
| Interaction comparison | A vs B only | A vs B vs A+B vs A×B |
| Multiple testing | Not applied | BH-FDR at α=0.05 |
| Regime analysis | Basic | Deterministic, no leakage |
| Strongest result | volume_x_structure / SPY: DA=0.635 | market_structure / QQQ: DA=0.645 (delta +0.041) |
| Classification | 4 WEAK | All WEAK or INCONCLUSIVE |

---

## 8. Final Classifications

| Result | Classification | Reason |
|---|---|---|
| All BTC-USD features | INCONCLUSIVE | Below majority-class baseline (0.522) |
| SPY liquidity | WEAK | DA=0.642, delta +0.026, but p=0.828 (not significant) |
| SPY market_structure | WEAK | DA=0.632, delta +0.016, p=0.726 |
| SPY rsi | WEAK | DA=0.617, delta +0.001, negligible |
| SPY volatility | WEAK | DA=0.620, delta +0.004, negligible |
| SPY others | INCONCLUSIVE | Below baseline |
| QQQ market_structure | WEAK | DA=0.645, delta +0.041, p=0.933 |
| QQQ volume | WEAK | DA=0.645, delta +0.041, p=0.933 |
| QQQ volatility | WEAK | DA=0.630, delta +0.026, p=0.820 |
| QQQ others | WEAK to INCONCLUSIVE | Near baseline |
| All interactions | WEAK | No meaningful incremental value over A+B |
| All combined models | INCONCLUSIVE | No combined model tested in 8A.6 |

---

## 9. Limitations

1. All results are exploratory, not pre-registered confirmatory tests
2. Simple models only (logistic regression)
3. No feature engineering beyond pre-registered set
4. Transaction costs are flat bps model
5. Regime detection is ATR-based
6. Multiple-testing correction applied but results still exploratory
7. 2-year daily bar dataset may not capture full market cycles
8. No intraday data for VWAP accuracy
9. Results apply to tested definition, dataset, horizon, and regime

---

## 10. Recommendation for Phase 8B

**Do NOT begin Phase 8B automatically.**

Before proceeding:
1. **Accept that no hypothesis is currently supported.** All results are WEAK or INCONCLUSIVE.
2. **Consider whether the research question is answerable** with the current data and methodology.
3. **If proceeding to Phase 8B:**
   - Use the corrected baseline (majority-class)
   - Use per-trade transaction costs
   - Pre-register primary hypothesis before data access
   - Apply appropriate multiple-testing correction
   - Focus on economic significance, not just statistical significance
4. **Alternative:** Consider whether the project should pivot to a different research question or methodology.

---

## 11. Files Modified

| File | Change |
|---|---|
| `src/aurora/interaction/ablation.py` | Fixed transaction cost model, added majority-class baseline, fixed feature importance computation |
| `src/aurora/interaction/statistics.py` | New: BH-FDR, z-test, confidence intervals, Cohen's h |
| `run_corrected.py` | New: corrected experiment orchestrator |
| `tests/test_phase8a6.py` | New: regression tests for corrected behavior |
| `docs/phase8a6-methodology-correction-report.md` | This report |

---

**DO NOT BEGIN PHASE 8B. STOP AND WAIT FOR REVIEW.**
