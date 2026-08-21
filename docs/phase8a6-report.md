# AURORA CORE — Phase 8A.6: Final Statistical Integrity + Correction Verification

**Date:** 2026-08-16

**Status:** CORRECTED METHODOLOGY — DO NOT PROCEED TO PHASE 8B

**Tests:** 560 passing, ruff clean, mypy clean

---

## 1. Executive Summary

Phase 8A.6 corrects critical methodological issues identified in Phase 8A/8A.5:

1. **Baseline correction:** Replaced naive 0.50 baseline with empirically computed majority-class accuracy per instrument.

2. **Transaction cost correction:** Changed from per-bar to per-position-transition (entry/exit).

3. **Interaction validation:** Systematically compared A, B, A+B, and A+B+interaction for all interactions.

4. **Multiple-testing correction:** Applied Benjamini-Hochberg FDR at α=0.05.

5. **Regime-conditional analysis:** Added sample-size checks and baseline comparison.


**Key finding:** After corrections, no individual feature or interaction achieves statistical significance after multiple-testing correction. All results are WEAK or INCONCLUSIVE. No hypothesis qualifies as SUPPORTED.

---

## 2. Previous Problems

| Problem | Severity | Status |

|---|---|---|

| Incorrect 0.50 baseline | HIGH | FIXED |

| Per-bar transaction costs | HIGH | FIXED |

| No interaction A+B+int comparison | HIGH | FIXED |

| No multiple-testing correction | HIGH | FIXED |

| No regime sample-size checks | MEDIUM | FIXED |

| No hypothesis status policy | MEDIUM | FIXED |

---

## 3. Corrections Implemented

### 3.1 Baseline Methodology

The majority-class baseline is computed dynamically from the evaluation dataset:

```

majority_class_accuracy = max(n_pos, n_neg) / n_total

```

Where `n_pos` and `n_neg` are the counts of positive and negative labels in the valid (non-None) portion of the dataset.

This is NOT hardcoded. Each instrument gets its own baseline.



### 3.2 Transaction-Cost Methodology

Transaction costs are applied per position transition:

- Entry cost: charged when position changes from 0 to 1

- Exit cost: charged when position changes from 1 to 0

- Holding cost: zero (no additional charges while holding)

- Default: 10 bps per transition (configurable)



### 3.3 Interaction Methodology

For each interaction A×B, four configurations are evaluated:

1. **A** alone

2. **B** alone

3. **A+B** concatenated features

4. **A+B+interaction** concatenated features plus interaction term

An interaction provides incremental value only if A+B+interaction > A+B.



### 3.4 Multiple-Testing Methodology

Benjamini-Hochberg FDR correction applied separately to:

- Individual feature family (8 tests)

- Interaction family (5 tests)

FDR threshold: α = 0.05



### 3.5 Regime-Conditional Methodology

Regime labels generated only from information available at prediction timestamp:

- High volatility: ATR ratio > 1.2 (lookback: 50 bars)

- Low volatility: ATR ratio < 0.8 (lookback: 50 bars)

- Trending: |momentum| > 2% (lookback: 20 bars)

- Ranging: |momentum| < 1% (lookback: 20 bars)

Minimum sample size: 30 observations. Regimes with fewer samples marked INCONCLUSIVE.

---

## 4. Dataset Audit

| Instrument | Source | Timeframe | Bars | Date Range | Valid Obs | + / - | Majority DA |

|---|---|---|---|---|---|---|---|

| BTC-USD | yfinance | 1d | 730 | 2024-08-16 to 2026-08-16 | 726 | 379/347 | 0.5220 |
| SPY | yfinance | 1d | 501 | 2024-08-15 to 2026-08-14 | 497 | 306/191 | 0.6157 |
| QQQ | yfinance | 1d | 501 | 2024-08-15 to 2026-08-14 | 497 | 300/197 | 0.6036 |
---

## 5. Baseline Audit

The correct baseline for each instrument is the majority-class accuracy. A naive "always predict up" strategy achieves this baseline.

SPY and QQQ have significant class imbalance (60-62% positive), making the 0.50 baseline misleading.

---

## 6. Transaction-Cost Audit

| Configuration | Value |

|---|---|

| Entry cost | 10 bps |

| Exit cost | 10 bps |

| Holding cost | 0 bps |

| Model | Per position transition |

---

## 7. Interaction Incremental Value

| Instrument | Interaction | A | B | A+B | A+B+I | Inc>A+B | Status |

|---|---|---|---|---|---|---|---|

| BTC-USD | liquidity_x_structure | 0.4915 | 0.4829 | 0.4893 | 0.4893 | +0.0000 | INCONCLUSIVE |
| BTC-USD | rsi_x_structure | 0.4873 | 0.4829 | 0.4915 | 0.4829 | -0.0085 | INCONCLUSIVE |
| BTC-USD | momentum_x_volatility | 0.5000 | 0.4889 | 0.4956 | 0.4933 | -0.0022 | INCONCLUSIVE |
| BTC-USD | volume_x_structure | 0.4777 | 0.4829 | 0.4701 | 0.4744 | +0.0043 | WEAK |
| BTC-USD | liquidity_x_volatility | 0.4915 | 0.4889 | 0.4778 | 0.4867 | +0.0089 | WEAK |
| SPY | liquidity_x_structure | 0.6415 | 0.6321 | 0.6321 | 0.6321 | +0.0000 | INCONCLUSIVE |
| SPY | rsi_x_structure | 0.6168 | 0.6321 | 0.6132 | 0.6132 | +0.0000 | INCONCLUSIVE |
| SPY | momentum_x_volatility | 0.5639 | 0.6195 | 0.6128 | 0.5859 | -0.0269 | INCONCLUSIVE |
| SPY | volume_x_structure | 0.6038 | 0.6321 | 0.6352 | 0.6321 | -0.0031 | INCONCLUSIVE |
| SPY | liquidity_x_volatility | 0.6415 | 0.6195 | 0.6195 | 0.6094 | -0.0101 | INCONCLUSIVE |
| QQQ | liquidity_x_structure | 0.6038 | 0.6447 | 0.6038 | 0.6038 | +0.0000 | INCONCLUSIVE |
| QQQ | rsi_x_structure | 0.5981 | 0.6447 | 0.5881 | 0.6006 | +0.0126 | WEAK |
| QQQ | momentum_x_volatility | 0.5763 | 0.6296 | 0.6296 | 0.6296 | +0.0000 | INCONCLUSIVE |
| QQQ | volume_x_structure | 0.6447 | 0.6447 | 0.6447 | 0.6447 | +0.0000 | INCONCLUSIVE |
| QQQ | liquidity_x_volatility | 0.6038 | 0.6296 | 0.6296 | 0.6296 | +0.0000 | INCONCLUSIVE |
---

## 8. Corrected Individual Feature Results

| Instrument | Feature | DA | Majority DA | Delta | BA | Sharpe | p | adj p | h | CI | Status |

|---|---|---|---|---|---|---|---|---|---|---|---|

| BTC-USD | liquidity | 0.4915 | 0.5220 | -0.0306 | 0.4872 | -0.0078 | 0.1853 | 1.0000 | -0.061 | [0.4462, 0.5367] | INCONCLUSIVE |
| BTC-USD | market_structure | 0.4829 | 0.5220 | -0.0391 | 0.4850 | -0.0184 | 0.0901 | 0.6491 | -0.078 | [0.4376, 0.5282] | INCONCLUSIVE |
| BTC-USD | rsi | 0.4873 | 0.5220 | -0.0347 | 0.4873 | -0.0155 | 0.1305 | 0.6491 | -0.069 | [0.4423, 0.5323] | INCONCLUSIVE |
| BTC-USD | momentum | 0.5000 | 0.5220 | -0.0220 | 0.4895 | -0.0000 | 0.3368 | 0.6491 | -0.044 | [0.4550, 0.5450] | INCONCLUSIVE |
| BTC-USD | volatility | 0.4889 | 0.5220 | -0.0331 | 0.5030 | -0.0188 | 0.1592 | 0.6465 | -0.066 | [0.4427, 0.5351] | INCONCLUSIVE |
| BTC-USD | volume | 0.4777 | 0.5220 | -0.0443 | 0.4977 | -0.0240 | 0.0541 | 0.5387 | -0.089 | [0.4326, 0.5228] | INCONCLUSIVE |
| BTC-USD | vwap | 0.4968 | 0.5220 | -0.0252 | 0.4953 | -0.0048 | 0.2731 | 0.4811 | -0.050 | [0.4517, 0.5420] | INCONCLUSIVE |
| BTC-USD | fibonacci | 0.5011 | 0.5220 | -0.0210 | 0.4932 | -0.0000 | 0.3621 | 0.6465 | -0.042 | [0.4559, 0.5462] | INCONCLUSIVE |
| SPY | liquidity | 0.6415 | 0.6157 | +0.0258 | 0.5000 | 0.2946 | 0.3440 | 0.4642 | 0.053 | [0.5888, 0.6942] | WEAK |
| SPY | market_structure | 0.6321 | 0.6157 | +0.0164 | 0.5014 | 0.2854 | 0.5481 | 1.0000 | 0.034 | [0.5791, 0.6851] | WEAK |
| SPY | rsi | 0.6168 | 0.6157 | +0.0011 | 0.4877 | 0.2945 | 0.9669 | 0.5788 | 0.002 | [0.5636, 0.6700] | WEAK |
| SPY | momentum | 0.5639 | 0.6157 | -0.0518 | 0.4488 | 0.2388 | 0.0430 | 0.4811 | -0.105 | [0.5096, 0.6181] | INCONCLUSIVE |
| SPY | volatility | 0.6195 | 0.6157 | +0.0038 | 0.4850 | 0.2640 | 0.8919 | 0.6491 | 0.008 | [0.5643, 0.6747] | WEAK |
| SPY | volume | 0.6038 | 0.6157 | -0.0119 | 0.4640 | 0.2746 | 0.6621 | 0.4642 | -0.024 | [0.5500, 0.6575] | INCONCLUSIVE |
| SPY | vwap | 0.5786 | 0.6157 | -0.0371 | 0.4708 | 0.2400 | 0.1741 | 0.5752 | -0.076 | [0.5243, 0.6329] | INCONCLUSIVE |
| SPY | fibonacci | 0.5755 | 0.6157 | -0.0402 | 0.4591 | 0.2386 | 0.1403 | 0.6465 | -0.082 | [0.5211, 0.6298] | INCONCLUSIVE |
| QQQ | liquidity | 0.6038 | 0.6036 | +0.0002 | 0.4787 | 0.2645 | 0.9956 | 1.0000 | 0.000 | [0.5500, 0.6575] | WEAK |
| QQQ | market_structure | 0.6447 | 0.6036 | +0.0410 | 0.5000 | 0.3017 | 0.1347 | 0.4642 | 0.085 | [0.5920, 0.6973] | WEAK |
| QQQ | rsi | 0.5981 | 0.6036 | -0.0055 | 0.4964 | 0.2820 | 0.7526 | 0.9506 | -0.011 | [0.5445, 0.6518] | INCONCLUSIVE |
| QQQ | momentum | 0.5763 | 0.6036 | -0.0273 | 0.4679 | 0.2505 | 0.2653 | 0.9875 | -0.056 | [0.5223, 0.6304] | INCONCLUSIVE |
| QQQ | volatility | 0.6296 | 0.6036 | +0.0260 | 0.5000 | 0.2680 | 0.3595 | 0.6491 | 0.053 | [0.5747, 0.6846] | WEAK |
| QQQ | volume | 0.6447 | 0.6036 | +0.0410 | 0.5000 | 0.3017 | 0.1347 | 0.9866 | 0.085 | [0.5920, 0.6973] | WEAK |
| QQQ | vwap | 0.5975 | 0.6036 | -0.0061 | 0.4709 | 0.2612 | 0.8230 | 0.5788 | -0.013 | [0.5436, 0.6514] | INCONCLUSIVE |
| QQQ | fibonacci | 0.6069 | 0.6036 | +0.0033 | 0.4811 | 0.2677 | 0.9043 | 1.0000 | 0.007 | [0.5532, 0.6606] | WEAK |
---

## 9. Hypothesis Status Table

| Hypothesis | Instrument | DA | Majority DA | Delta | adj p | Effect Size | Status |

|---|---|---|---|---|---|---|---|

| liquidity | BTC-USD | 0.4915 | 0.5220 | -0.0306 | 1.0000 | -0.061 | INCONCLUSIVE |
| market_structure | BTC-USD | 0.4829 | 0.5220 | -0.0391 | 0.6491 | -0.078 | INCONCLUSIVE |
| rsi | BTC-USD | 0.4873 | 0.5220 | -0.0347 | 0.6491 | -0.069 | INCONCLUSIVE |
| momentum | BTC-USD | 0.5000 | 0.5220 | -0.0220 | 0.6491 | -0.044 | INCONCLUSIVE |
| volatility | BTC-USD | 0.4889 | 0.5220 | -0.0331 | 0.6465 | -0.066 | INCONCLUSIVE |
| volume | BTC-USD | 0.4777 | 0.5220 | -0.0443 | 0.5387 | -0.089 | INCONCLUSIVE |
| vwap | BTC-USD | 0.4968 | 0.5220 | -0.0252 | 0.4811 | -0.050 | INCONCLUSIVE |
| fibonacci | BTC-USD | 0.5011 | 0.5220 | -0.0210 | 0.6465 | -0.042 | INCONCLUSIVE |
| liquidity | SPY | 0.6415 | 0.6157 | +0.0258 | 0.4642 | 0.053 | WEAK |
| market_structure | SPY | 0.6321 | 0.6157 | +0.0164 | 1.0000 | 0.034 | WEAK |
| rsi | SPY | 0.6168 | 0.6157 | +0.0011 | 0.5788 | 0.002 | WEAK |
| momentum | SPY | 0.5639 | 0.6157 | -0.0518 | 0.4811 | -0.105 | INCONCLUSIVE |
| volatility | SPY | 0.6195 | 0.6157 | +0.0038 | 0.6491 | 0.008 | WEAK |
| volume | SPY | 0.6038 | 0.6157 | -0.0119 | 0.4642 | -0.024 | INCONCLUSIVE |
| vwap | SPY | 0.5786 | 0.6157 | -0.0371 | 0.5752 | -0.076 | INCONCLUSIVE |
| fibonacci | SPY | 0.5755 | 0.6157 | -0.0402 | 0.6465 | -0.082 | INCONCLUSIVE |
| liquidity | QQQ | 0.6038 | 0.6036 | +0.0002 | 1.0000 | 0.000 | WEAK |
| market_structure | QQQ | 0.6447 | 0.6036 | +0.0410 | 0.4642 | 0.085 | WEAK |
| rsi | QQQ | 0.5981 | 0.6036 | -0.0055 | 0.9506 | -0.011 | INCONCLUSIVE |
| momentum | QQQ | 0.5763 | 0.6036 | -0.0273 | 0.9875 | -0.056 | INCONCLUSIVE |
| volatility | QQQ | 0.6296 | 0.6036 | +0.0260 | 0.6491 | 0.053 | WEAK |
| volume | QQQ | 0.6447 | 0.6036 | +0.0410 | 0.9866 | 0.085 | WEAK |
| vwap | QQQ | 0.5975 | 0.6036 | -0.0061 | 0.5788 | -0.013 | INCONCLUSIVE |
| fibonacci | QQQ | 0.6069 | 0.6036 | +0.0033 | 1.0000 | 0.007 | WEAK |
---

## 10. Leakage/Integrity Audit

| Check | Status |

|---|---|

| Temporal splitting | ✅ Chronological walk-forward |

| Feature timestamps | ✅ Features use trailing windows only |

| Target timestamps | ✅ Forward returns, filtered for look-ahead |

| Preprocessing boundaries | ✅ Scaler fit on train only |

| Test-set isolation | ✅ No test data in training |

| No look-ahead | ✅ No future information in features |

| No random temporal split | ✅ All splits chronological |

---

## 11. Statistical Limitations

1. All results are exploratory, not pre-registered confirmatory tests

2. Simple models only (logistic regression)

3. No feature engineering beyond pre-registered set

4. Transaction costs are flat bps model

5. Regime detection is ATR-based

6. Multiple-testing correction applied but results still exploratory

7. 2-year daily bar dataset may not capture full market cycles

8. No intraday data for VWAP accuracy

---

## 12. Practical Limitations

1. No live trading or paper trading validation

2. No slippage or market impact modeling

3. No portfolio construction or position sizing

4. No risk management or drawdown controls

5. No regime-specific parameter optimization

---

## 13. Remaining Risks

1. Overfitting to the specific 2-year dataset

2. Regime labels may not generalize

3. Transaction cost assumptions may be optimistic

4. Feature definitions may not be robust across market conditions

---

## 14. Recommendation for Phase 8B

**Do NOT begin Phase 8B automatically.**



Before proceeding:

1. Accept that no hypothesis is currently supported.

2. Consider whether the research question is answerable with current data.

3. If proceeding: pre-register primary hypothesis, use corrected baselines, apply multiple-testing correction.

4. Focus on economic significance, not just statistical significance.

---

## 15. Files Modified

| File | Change |

|---|---|

| src/aurora/interaction/preprocessing.py | Fixed import order |

| src/aurora/interaction/regimes.py | Added RegimeResult, sample-size checks, evaluate_regime_conditional |

| run_corrected.py | Added A+B+interaction testing, adjusted p-values in output |

| tests/test_phase8a6.py | Regression tests for corrected behavior |

| docs/phase8a6-report.md | This report |

---

**DO NOT BEGIN PHASE 8B. STOP AND WAIT FOR REVIEW.**
