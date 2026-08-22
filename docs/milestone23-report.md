# M23 Milestone Report: Advanced Indicator Engine

**Status:** COMPLETE
**Date:** 2026-08-22
**Commit:** d13f22b

## 1. Objective

Expand Aurora Core's indicator engine with 11 new technical indicators while preserving all existing indicators, maintaining data leakage protection, and providing a user-facing indicator selector in the terminal UI.

Indicators are descriptive analytical features and do not constitute trading signals. NO_DEPLOYMENT_SIGNAL is preserved.

## 2. Existing Architecture

- **Python indicators**: `src/aurora/features/indicators.py` — functional (pure functions), no classes
- **TypeScript indicators**: `frontend/src/services/data.ts` — mirror of Python implementations
- **Rolling helpers**: `src/aurora/features/rolling.py` — EMA, SMA, rolling stats
- **Chart**: `frontend/src/components/PriceChart.tsx` — TradingView Lightweight Charts
- **API**: FastAPI backend serves OHLCV; frontend computes indicators client-side

## 3. Indicators Implemented

### Existing (preserved, unchanged)
| Indicator | Function | Parameters |
|-----------|----------|------------|
| SMA | `sma_indicator()` / `computeSMA()` | window |
| EMA | `ema_indicator()` / `computeEMA()` | window |
| RSI | `rsi()` / `computeRSI()` | window=14 |
| MACD | `computeMACD()` | fast=12, slow=26, signal=9 |
| Bollinger Bands | `bollinger_bands()` / `computeBollinger()` | period=20, num_std=2 |
| ATR | `atr()` / `computeATR()` | window=14 |

### New in M23
| Indicator | Group | Function | Default Params | Output |
|-----------|-------|----------|----------------|--------|
| Stochastic | MOMENTUM | `stochastic()` / `computeStochastic()` | k=14, d=3, smooth=3 | %K, %D |
| ADX/DMI | TREND | `adx_dmi()` / `computeAdxDmi()` | period=14 | +DI, -DI, ADX |
| CCI | MOMENTUM | `cci()` / `computeCCI()` | period=20 | CCI |
| OBV | VOLUME | `obv()` / `computeOBV()` | — | OBV |
| VWAP | VOLUME | `vwap()` / `computeVWAP()` | — | VWAP |
| MFI | VOLUME | `mfi()` / `computeMFI()` | period=14 | MFI |
| ROC | MOMENTUM | `roc()` / `computeROC()` | period=12 | ROC% |
| Williams %R | MOMENTUM | `williams_r()` / `computeWilliamsR()` | period=14 | %R |
| Ichimoku | TREND | `ichimoku()` / `computeIchimoku()` | 9/26/52 | Tenkan, Kijun, Senkou A/B, Chikou |
| Pivot Points | LEVELS | `pivot_points()` / `computePivotPoints()` | — | P, R1-R3, S1-S3 |
| Fibonacci | LEVELS | `fibonacci_retracement()` / `computeFibonacci()` | levels=[0,0.236,...,1] | price levels |

## 4. Mathematical Definitions

All formulas match standard technical analysis definitions. Key formulas:

- **Stochastic %K**: `(Close - LL) / (HH - LL) * 100`, smoothed by SMA
- **ADX**: `EMA(DX, period)` where `DX = 100 * |+DI - -DI| / (+DI + -DI)`
- **CCI**: `(TP - SMA(TP)) / (0.015 * MeanDeviation)`
- **OBV**: Cumulative volume with sign based on close direction
- **VWAP**: `Cumulative(TP * Vol) / Cumulative(Vol)`
- **MFI**: `100 - 100/(1 + PosMF/NegMF)`
- **Ichimoku**: Midpoint of highest high / lowest low over lookback periods
- **Pivot Points**: `(Prev H + Prev L + Prev C) / 3` with standard R/S formulas
- **Fibonacci**: `High - (High - Low) * level`

## 5. Parameters

All indicators support configurable periods. Default parameters match industry standards (e.g., Stochastic 14/3/3, ADX 14, CCI 20, Williams %R 14, Ichimoku 9/26/52).

## 6. Data Requirements

| Indicator | Minimum Bars |
|-----------|-------------|
| Stochastic | k_period |
| ADX/DMI | period + 1 |
| CCI | period |
| OBV | 1 |
| VWAP | 1 |
| MFI | period + 1 |
| ROC | period + 1 |
| Williams %R | period |
| Ichimoku | senkou_b_period (52) |
| Pivot Points | 2 |
| Fibonacci | 2 prices |

## 7. Leakage Prevention

Every indicator satisfies: `indicator(T)` depends only on data at or before timestamp T.

- Stochastic: Rolling window over past k_period highs/lows only
- ADX/DMI: Uses EMA of past DM values; no forward displacement
- CCI: SMA and mean deviation computed from past window only
- OBV: Sequential accumulation using past closes only
- VWAP: Cumulative from bar 0 to current bar only
- MFI: Rolling window of past money flow values
- Ichimoku: All spans computed from past data; displacement handled by chart layer
- Pivot Points: Uses PREVIOUS bar's H/L/C (i-1), never current bar
- Fibonacci: Deterministic calculation from provided high/low values

**10 leakage tests verify**: changing the last 3 bars of a 20-bar series does not alter indicator values for bars 0-16.

## 8. Tests

| Category | Count |
|----------|-------|
| Existing indicator tests | 14 |
| M23 indicator tests | 66 |
| Leakage protection tests | 10 |
| Determinism tests | 12 |
| **Total indicator tests** | **92** |
| Full test suite | **1293** |

All 1293 tests pass. Ruff clean. TypeScript clean.

## 9. API Changes

No backend API changes. Indicators are computed client-side from OHLCV data. The frontend `computeAllIndicators()` function accepts an optional `enabled` set to control which indicators are computed.

## 10. Frontend Changes

- **IndicatorSelector.tsx**: New component with 5 groups (TREND, MOMENTUM, VOLATILITY, VOLUME, LEVELS)
- **App.tsx**: Added `enabledIndicators` state, passes to `computeAllIndicators()`
- **PriceChart.tsx**: Added overlay colors for Ichimoku, VWAP, SMA 50, EMA 26
- **data.ts**: Added 13 new `compute*` functions, `INDICATOR_GROUPS` definition

Default enabled indicators: SMA, EMA, RSI, MACD, Bollinger, ATR (same as M22).

## 11. Performance

All indicators are O(n) or O(n*k) where n = number of bars and k = period. Client-side computation adds negligible latency (<1ms for 200 bars).

## 12. Limitations

- Ichimoku Senkou spans are NOT displaced on chart (chart layer would need custom placement)
- Pivot Points use previous-bar H/L/C (first bar has no levels)
- VWAP resets each session (standard daily behavior)
- No real-time streaming of indicator values (computed on data load)

## 13. Research Integrity

- NO_DEPLOYMENT_SIGNAL preserved
- No BUY/SELL recommendations
- No future-data access in any indicator
- Indicators are descriptive analytical tools only
- No claim that indicators predict future prices
- Existing research conclusions unchanged

## 14. Final Verification

- [x] All 1293 tests pass
- [x] Ruff clean (features module)
- [x] TypeScript clean
- [x] No secrets in git diff
- [x] NO_DEPLOYMENT_SIGNAL preserved
- [x] Existing indicators unchanged
- [x] Leakage tests pass (10/10)
- [x] Determinism tests pass (12/12)
- [x] Git working tree clean
- [x] Pushed to origin/main
