# Phase 8A.5: Result Integrity Audit Report

**Date:** 2026-08-16
**Status:** AUDIT COMPLETE — DO NOT PROCEED TO PHASE 8B
**Author:** Autonomous agent, no human review

---

## Executive Summary

Phase 8A reported no SUPPORTED hypotheses and 4 WEAK results. This audit reveals **critical methodological issues** that invalidate the apparent strength of the two strongest interactions (volume × structure on SPY, liquidity × structure on QQQ). After correcting for class-imbalance baselines and verifying interaction incremental value, **all Phase 8A results are INCONCLUSIVE or WEAK at best, with no actionable signal.**

---

## 1. Dataset Audit

| Property | BTC-USD | SPY | QQQ |
|----------|---------|-----|-----|
| Source | yfinance | yfinance | yfinance |
| Timeframe | 1d | 1d | 1d |
| Total bars | 730 | 501 | 501 |
| Date range | 2024-08-16 to 2026-08-16 | 2024-08-15 to 2026-08-14 | 2024-08-15 to 2026-08-14 |
| Valid observations | 726 | 497 | 497 |
| Train size (min_train) | 242 | 165 | 165 |
| Fold size | 161 | 110 | 110 |
| Test size (total OOS) | 483 | 332 | 332 |
| Target horizon | 4 daily bars | 4 daily bars | 4 daily bars |
| Transaction cost | 10 bps per bar | 10 bps per bar | 10 bps per bar |

**Issue:** BTC-USD has 730 bars vs 501 for SPY/QQQ. Different instruments have different date ranges (BTC starts 1 day later). This is acceptable — yfinance returns different date ranges for different symbols.

**Issue:** Transaction cost is charged per bar where position is open, not per trade. This systematically overstates friction for multi-bar holds. A 5-bar hold costs 5× the assumed transaction cost.

---

## 2. Baseline Audit

| Property | BTC-USD | SPY | QQQ |
|----------|---------|-----|-----|
| Positive (up) | 379 (52.2%) | 306 (61.6%) | 300 (60.4%) |
| Negative (down) | 347 (47.8%) | 191 (38.4%) | 197 (39.6%) |
| **Majority-class baseline DA** | **0.522** | **0.616** | **0.604** |

**CRITICAL FINDING:** The Phase 8A report assumed baseline DA = 0.50 for all instruments. This is incorrect.

- SPY majority class is 61.6% positive — a naive "always predict up" strategy achieves DA = 0.616
- QQQ majority class is 60.4% positive — naive baseline DA = 0.604
- BTC-USD majority class is 52.2% — naive baseline DA = 0.522

**Implication:** The reported SPY DA of 0.635 is only **1.9% above the majority-class baseline** (0.635 - 0.616). The reported QQQ DA of 0.645 is **4.1% above baseline** (0.645 - 0.604). These are small deltas that may not survive transaction costs.

---

## 3. Horizon Audit

All experiments use a consistent horizon of 4 daily bars. The target is:
```
target[i] = 1 if (close[i+4] - close[i]) / close[i] > 0
```

Features at index `i` use data up to bar `i`'s close. The target uses bar `i+4`'s close. This is consistent across all instruments and experiments.

**Issue:** There is no explicit 1-bar lag to ensure features are available before the decision point. At bar `i`'s close, the model uses bar `i`'s OHLCV to predict the return from bar `i` to bar `i+4`. This is a common convention but means the model assumes instantaneous execution at bar `i`'s close.

---

## 4. Feature Selection Audit

All 8 features were pre-registered in `registry.py` before Phase 8A execution. The feature set was designed based on Phase 7.5 exploratory results. All features were included (not just top performers), so this is not cherry-picking.

However, the feature set was chosen based on Phase 7.5 findings. The 5 interactions were also pre-registered.

**Classification:** EXPLORATORY. The feature set was designed around Phase 7.5 results. Phase 8A results are not independent confirmation.

---

## 5. Test-Set Integrity

| Check | Status |
|-------|--------|
| Test data not used for feature selection | ✅ PASS — features pre-registered |
| Test data not used for parameter tuning | ✅ PASS — walk-forward validates on held-out folds |
| Preprocessing fit on train only | ✅ PASS — StandardScaler fit on train_X only |
| Model selection not based on test performance | ⚠️ PARTIAL — model comparison used OOS metrics |

**Issue:** The walk-forward framework correctly prevents test-data leakage. The scaler is fit on training data only. However, the final feature importance model is trained only on the first `min_train` observations (not the full training set from the last fold), producing misleading importances.

---

## 6. Multiple Testing Exposure

| Dimension | Count |
|-----------|-------|
| Feature families | 8 |
| Interactions | 5 |
| Models | 3 (logistic, tree, ensemble) |
| Instruments | 3 |
| Feature×Model×Instrument | 72 |
| Interaction×Model×Instrument | 45 |
| **Grand total tests** | **117** |

With 117 tests, there is substantial opportunity for false discoveries. The two "strong" results (volume × structure / SPY, liquidity × structure / QQQ) may be false positives.

**Recommended correction:** Benjamini-Hochberg FDR control at q=0.05 for future experiments.

---

## 7. Transaction Cost Audit

| Result | Gross DA | Cost/Bar | Gross Sharpe |
|--------|----------|----------|--------------|
| volume_x_structure / SPY | 0.6352 | 10 bps | 0.3191 |
| liquidity_x_structure / QQQ | 0.6447 | 10 bps | 0.3289 |

**Issue:** Transaction costs are charged per bar where position is open, not per trade. This overstates friction. A more accurate model would charge only on position entry/exit.

**Cost-adjusted assessment:**
- SPY: DA=0.6352 vs baseline=0.616 → edge = +0.019. At 10 bps per bar, even a 2-bar hold costs 20 bps. The edge is likely wiped out.
- QQQ: DA=0.6447 vs baseline=0.604 → edge = +0.041. At 10 bps per bar, a 2-bar hold costs 20 bps. The edge is marginal.

---

## 8. Robustness Audit

### volume × structure / SPY

| Window | DA | Sharpe | n |
|--------|-----|--------|---|
| 10 | 0.6358 | 0.3174 | 324 |
| 15 | 0.6386 | 0.3187 | 321 |
| 20 | 0.6352 | 0.3191 | 318 |
| 25 | 0.6314 | 0.2966 | 312 |
| 30 | 0.6311 | 0.2863 | 309 |

**Stable across windows.** DA ranges 0.631–0.639, Sharpe ranges 0.286–0.319. Slight degradation at larger windows but no collapse.

### liquidity × structure / QQQ

| Window | DA | Sharpe | n |
|--------|-----|--------|---|
| 10 | 0.6481 | 0.3330 | 324 |
| 15 | 0.6449 | 0.3255 | 321 |
| 20 | 0.6447 | 0.3289 | 318 |
| 25 | 0.6378 | 0.3043 | 312 |
| 30 | 0.6343 | 0.2900 | 309 |

**Stable across windows.** DA ranges 0.634–0.648, Sharpe ranges 0.290–0.333. Slight degradation at larger windows but no collapse.

---

## 9. Interaction Interpretation

### The critical question: does the interaction provide incremental information over A, B, and A+B?

#### SPY: volume × structure

| Configuration | DA | Sharpe |
|--------------|-----|--------|
| A: volume_divergence | 0.6038 | 0.3480 |
| B: market_structure_bos | 0.6321 | 0.3162 |
| A+B (concatenated features) | 0.6352 | 0.3193 |
| A*B (interaction product) | 0.6352 | 0.3191 |

**FINDING:** The interaction A*B is **identical** to A+B (DA=0.6352 vs 0.6352). The interaction provides **zero incremental value** over simply concatenating the two features. Furthermore, the interaction barely exceeds B alone (0.6352 vs 0.6321, delta=+0.003). The interaction is not meaningful.

#### QQQ: liquidity × structure

| Configuration | DA | Sharpe |
|--------------|-----|--------|
| A: liquidity_sweep | 0.6038 | 0.2874 |
| B: market_structure_bos | 0.6447 | 0.3289 |
| A+B (concatenated features) | 0.6038 | 0.2874 |
| A*B (interaction product) | 0.6447 | 0.3289 |

**FINDING:** The interaction A*B is **identical** to B alone (DA=0.6447 vs 0.6447). The interaction provides **zero incremental value** over market_structure_bos alone. The interaction is not meaningful.

### Conclusion on Interaction Interpretation

**Neither interaction provides incremental information beyond its individual components.** The interaction term acts as a proxy for one of the two individual features, not as a genuine combination.

---

## 10. Final Status

| Result | Classification | Reason |
|--------|---------------|--------|
| volume × structure / SPY | **WEAK** | DA=0.635 is only 1.9% above majority-class baseline (0.616); interaction provides no incremental value over B alone; stable across windows but edge too small for transaction costs |
| liquidity × structure / QQQ | **WEAK** | DA=0.645 is 4.1% above baseline (0.604); interaction is identical to B alone (market_structure_bos); stable across windows; edge marginal after costs |
| All BTC-USD features | **INCONCLUSIVE** | DA ~0.48-0.50, below majority-class baseline (0.522) |
| All other SPY/QQQ features | **WEAK to INCONCLUSIVE** | Most features hover near or below majority-class baseline |
| All combined-feature models | **REJECTED** | Combined features perform worse than individual features |

**No hypothesis qualifies as SUPPORTED.** The predefined support criteria (DA > baseline + 2%, Sharpe > 0.3, mean_return > 0) are not met after correcting for class imbalance.

---

## 11. Recommendations for Phase 8B

### Critical Issues to Address Before Phase 8B

1. **Fix baseline calculation.** Use majority-class baseline, not 0.50. For SPY/QQQ, the baseline is ~60-62%.

2. **Fix transaction cost model.** Charge per trade (position entry/exit), not per bar held. This is a systematic error that overstates friction.

3. **Fix feature importance computation.** Use the full training set from the last fold, not just the first `min_train` observations.

4. **Fix Sharpe ratio aggregation.** Compute from pooled returns across all folds, not by averaging per-fold Sharpe ratios.

5. **Verify interaction incremental value.** For any interaction, compare against A, B, and A+B. If the interaction is not meaningfully better, it is not a genuine interaction.

### Phase 8B Design Considerations

1. **Lower the bar for "interesting" results.** With a ~60% majority-class baseline, the bar for meaningful edge is higher. Focus on results where DA > 0.65 or Sharpe > 0.4.

2. **Use regime-conditional analysis.** The regime analysis from Phase 8A suggests interactions may be regime-dependent. Test interactions only in specific regimes.

3. **Apply multiple-testing correction.** With 117+ tests, use Benjamini-Hochberg FDR control.

4. **Consider different prediction horizons.** The 4-day horizon may not be optimal. Test 1-day, 2-day, and 8-day horizons.

5. **Do not treat Phase 8A results as prior evidence.** All Phase 8A results are exploratory. Phase 8B should be a fresh experiment.

---

## Appendix: Code Integrity Issues Found

| Issue | Severity | Location | Description |
|-------|----------|----------|-------------|
| Transaction cost per bar | HIGH | `ablation.py:162-166` | Cost charged per bar held, not per trade |
| Feature importance stale | MEDIUM | `ablation.py:185-195` | Importance model trained on first fold only |
| Sharpe averaging | MEDIUM | `ablation.py:172-183` | Per-fold Sharpe averaged instead of pooled |
| import math order | LOW | `preprocessing.py:50,82` | Import at bottom of file |
| One-bar look-ahead | LOW | `run_phase8a.py:51` | Features at bar i use bar i data |

---

**DO NOT BEGIN PHASE 8B. STOP AND WAIT FOR REVIEW.**
