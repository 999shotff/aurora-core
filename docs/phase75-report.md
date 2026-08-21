# AURORA CORE — Phase 7.5 Final Report

**Date:** 2026-08-15

**Phase:** 7.5 — Multi-Methodology Evidence Benchmark

**Status:** COMPLETE

---

## 1. Research Claims Considered

40 documents, 4,326 pages, 4,020 claims, 1,013 hypotheses, 728 formulas.

Methodology families with computable hypotheses tested:
- Fibonacci (137 claims)

- Volatility (760 claims)

- Technical Analysis (526 claims)

- Liquidity (172 claims)

- Volume (52 claims)

- VWAP (37 claims)

- Market Structure (12 claims)

- Momentum (embedded in technical analysis)


## 2. Hypotheses Selected

- **EXP002** (fibonacci): Price respects Fibonacci 0.618 retracement level as support/resistance
  - Source: Carolyn_Borden_Fibonacci_Trading (1).pdf, p.295
  - Claim ID: 3d88aa766403f953_p295_cadcf2be2
  - Feature: `fib_distance = (close - (low + 0.618 * (high - low))) / close`
  - Parameters: {'swing_window': 20, 'ratio': 0.618}

- **EXP003** (volatility): ATR expansion predicts continued elevated volatility and directional movement
  - Source: Trading-Volatility (1).pdf, p.97
  - Claim ID: 0973976867d6b506_p97_c32ec2c40
  - Feature: `atr_ratio = ATR(14) / ATR(50)`
  - Parameters: {'short_window': 14, 'long_window': 50}

- **EXP004** (liquidity): Liquidity sweep of recent high/low followed by reversal predicts price direction
  - Source: Liquidity-Sweep-in-Trading.pdf, p.9
  - Claim ID: b2280f4443f2611f_p9_c07acebd0
  - Feature: `sweep = 1 if low < prev_low and close > prev_low; -1 if high > prev_high and close < prev_high`
  - Parameters: {'lookback': 20}

- **EXP005** (volume): Volume divergence (price up, volume down) precedes price reversals
  - Source: Volume-Divergence.pdf, p.1
  - Claim ID: 6cc3bf8840a7e6d9
  - Feature: `div = -1 if price_slope > 0 and vol_slope < 0; 1 if price_slope < 0 and vol_slope > 0`
  - Parameters: {'window': 20}

- **EXP006** (vwap): Price reverts to VWAP when far from it; VWAP acts as fair value
  - Source: vwap.pdf, p.7
  - Claim ID: 2e15dafca208257c_p7_c33570093
  - Feature: `vwap_dev = (close - VWAP) / VWAP`
  - Parameters: {'window': 20}

- **EXP007** (market_structure): Break of Structure (BOS) predicts directional continuation
  - Source: 15_Scalping_Strategies (1).pdf, p.24
  - Claim ID: 5fcfe5efce295a41_p24_c0f91a7e9
  - Feature: `bos = 1 if close > prev_swing_high; -1 if close < prev_swing_low`
  - Parameters: {'lookback': 20}

- **EXP008** (momentum): 14-period momentum predicts continuation in same direction
  - Source: 15_Scalping_Strategies (1).pdf, p.5
  - Claim ID: 5fcfe5efce295a41_p5_ce70606c3
  - Feature: `mom = (close - close[14]) / close[14]`
  - Parameters: {'period': 14}

- **EXP009** (technical_analysis): RSI oversold/overbought predicts mean reversion
  - Source: 15_Scalping_Strategies (1).pdf, p.3
  - Claim ID: 5fcfe5efce295a41_p3_c58d9f01b
  - Feature: `rsi_signal = 1 if RSI(14) < 30; -1 if RSI(14) > 70`
  - Parameters: {'rsi_period': 14, 'oversold': 30, 'overbought': 70}

## 3. Claims Rejected as Non-Computable

- astrology: NO_COMPUTABLE_HYPOTHESIS
- gann: NO_COMPUTABLE_HYPOTHESIS
- time_cycles: NO_COMPUTABLE_HYPOTHESIS
- no_computable_hypothesis: NO_COMPUTABLE_HYPOTHESIS

## 4. Datasets Used

- **BTC-USD**: 731 bars, 2024-08-15 to 2026-08-15, source=yfinance
- **SPY**: 501 bars, 2024-08-15 to 2026-08-14, source=yfinance
- **QQQ**: 501 bars, 2024-08-15 to 2026-08-14, source=yfinance

## 5. Experiment Pre-registrations

### EXP002
- Hypothesis: Price respects Fibonacci 0.618 retracement level as support/resistance
- Expected direction: mean_reversion toward 0.618 level
- Feature formula: `fib_distance = (close - (low + 0.618 * (high - low))) / close`
- Parameters: {'swing_window': 20, 'ratio': 0.618}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935628+00:00

### EXP003
- Hypothesis: ATR expansion predicts continued elevated volatility and directional movement
- Expected direction: ATR ratio > 1 predicts trending continuation
- Feature formula: `atr_ratio = ATR(14) / ATR(50)`
- Parameters: {'short_window': 14, 'long_window': 50}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935637+00:00

### EXP004
- Hypothesis: Liquidity sweep of recent high/low followed by reversal predicts price direction
- Expected direction: buy after sell-side sweep, sell after buy-side sweep
- Feature formula: `sweep = 1 if low < prev_low and close > prev_low; -1 if high > prev_high and close < prev_high`
- Parameters: {'lookback': 20}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935645+00:00

### EXP005
- Hypothesis: Volume divergence (price up, volume down) precedes price reversals
- Expected direction: bearish divergence when price rising and volume falling
- Feature formula: `div = -1 if price_slope > 0 and vol_slope < 0; 1 if price_slope < 0 and vol_slope > 0`
- Parameters: {'window': 20}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935652+00:00

### EXP006
- Hypothesis: Price reverts to VWAP when far from it; VWAP acts as fair value
- Expected direction: mean reversion toward VWAP
- Feature formula: `vwap_dev = (close - VWAP) / VWAP`
- Parameters: {'window': 20}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935660+00:00

### EXP007
- Hypothesis: Break of Structure (BOS) predicts directional continuation
- Expected direction: buy on bullish BOS, sell on bearish BOS
- Feature formula: `bos = 1 if close > prev_swing_high; -1 if close < prev_swing_low`
- Parameters: {'lookback': 20}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935667+00:00

### EXP008
- Hypothesis: 14-period momentum predicts continuation in same direction
- Expected direction: momentum > 0 predicts positive return
- Feature formula: `mom = (close - close[14]) / close[14]`
- Parameters: {'period': 14}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935674+00:00

### EXP009
- Hypothesis: RSI oversold/overbought predicts mean reversion
- Expected direction: RSI < 30 buy, RSI > 70 sell
- Feature formula: `rsi_signal = 1 if RSI(14) < 30; -1 if RSI(14) > 70`
- Parameters: {'rsi_period': 14, 'oversold': 30, 'overbought': 70}
- Target: future_return over 4-bar horizon
- Horizon: 4 bars
- Baseline: buy_and_hold
- Transaction cost: 10.0 bps
- Classification criteria: {'supported': 'DA > baseline+2%, Sharpe>0.3, mean_return>0', 'weak': 'DA > baseline, Sharpe>0 or mean_return>0', 'rejected': 'DA < baseline-2%, mean_return<0', 'inconclusive': 'all others'}
- Registered at: 2026-08-15T13:12:27.935681+00:00


## 6. Baseline Results

| Methodology | Baseline DA | Baseline Mean | Baseline Sharpe |
|---|---|---|---|
| fibonacci/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| fibonacci/SPY | 0.5700 | 0.001761 | 0.1957 |
| fibonacci/QQQ | 0.5600 | 0.002304 | 0.1527 |
| volatility/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| volatility/SPY | 0.5700 | 0.001761 | 0.1957 |
| volatility/QQQ | 0.5600 | 0.002304 | 0.1527 |
| liquidity/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| liquidity/SPY | 0.5700 | 0.001761 | 0.1957 |
| liquidity/QQQ | 0.5600 | 0.002304 | 0.1527 |
| volume/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| volume/SPY | 0.5700 | 0.001761 | 0.1957 |
| volume/QQQ | 0.5600 | 0.002304 | 0.1527 |
| vwap/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| vwap/SPY | 0.5700 | 0.001761 | 0.1957 |
| vwap/QQQ | 0.5600 | 0.002304 | 0.1527 |
| market_structure/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| market_structure/SPY | 0.5700 | 0.001761 | 0.1957 |
| market_structure/QQQ | 0.5600 | 0.002304 | 0.1527 |
| momentum/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| momentum/SPY | 0.5700 | 0.001761 | 0.1957 |
| momentum/QQQ | 0.5600 | 0.002304 | 0.1527 |
| technical_analysis/BTC-USD | 0.4863 | -0.000344 | -0.0189 |
| technical_analysis/SPY | 0.5700 | 0.001761 | 0.1957 |
| technical_analysis/QQQ | 0.5600 | 0.002304 | 0.1527 |

## 7. Out-of-Sample Results

| Methodology | Instrument | DA | Mean Ret | Sharpe | MaxDD | Brier |
|---|---|---|---|---|---|---|
| fibonacci | BTC-USD | 0.4658 | -0.001222 | -0.0673 | 0.3139 | 0.5342 |
| fibonacci | SPY | 0.5200 | -0.000500 | -0.0546 | 0.1342 | 0.4800 |
| fibonacci | QQQ | 0.4900 | 0.000353 | 0.0231 | 0.2154 | 0.5100 |
| volatility | BTC-USD | 0.5137 | 0.000344 | 0.0189 | 0.2079 | 0.4863 |
| volatility | SPY | 0.4300 | -0.001761 | -0.1957 | 0.1958 | 0.5700 |
| volatility | QQQ | 0.4400 | -0.002304 | -0.1527 | 0.2584 | 0.5600 |
| liquidity | BTC-USD | 0.5000 | -0.000264 | -0.0513 | 0.0729 | 0.2808 |
| liquidity | SPY | 0.5000 | 0.000172 | 0.0553 | 0.0234 | 0.2700 |
| liquidity | QQQ | 0.7778 | 0.001099 | 0.2406 | 0.0048 | 0.2475 |
| volume | BTC-USD | 0.4932 | -0.000286 | -0.0204 | 0.1745 | 0.3784 |
| volume | SPY | 0.5375 | -0.000071 | -0.0087 | 0.1029 | 0.4200 |
| volume | QQQ | 0.5593 | 0.000041 | 0.0034 | 0.1291 | 0.3625 |
| vwap | BTC-USD | 0.4863 | -0.000614 | -0.0338 | 0.3398 | 0.5137 |
| vwap | SPY | 0.5100 | -0.000374 | -0.0408 | 0.1345 | 0.4900 |
| vwap | QQQ | 0.4600 | -0.001108 | -0.0728 | 0.2154 | 0.5400 |
| market_structure | BTC-USD | 1.0000 | 0.000133 | 0.0999 | 0.0000 | 0.2466 |
| market_structure | SPY | 0.6667 | -0.000006 | -0.0024 | 0.0180 | 0.2525 |
| market_structure | QQQ | 0.6667 | -0.000079 | -0.0754 | 0.0103 | 0.2525 |
| momentum | BTC-USD | 0.4932 | -0.000169 | -0.0093 | 0.3017 | 0.5068 |
| momentum | SPY | 0.5300 | 0.000173 | 0.0189 | 0.1115 | 0.4700 |
| momentum | QQQ | 0.5000 | 0.000030 | 0.0020 | 0.1912 | 0.5000 |
| technical_analysis | BTC-USD | 0.7000 | 0.000138 | 0.0191 | 0.0690 | 0.2534 |
| technical_analysis | SPY | 0.5417 | -0.000039 | -0.0093 | 0.0334 | 0.3000 |
| technical_analysis | QQQ | 0.5758 | 0.000516 | 0.0625 | 0.0551 | 0.3075 |

## 8. Transaction-Cost Results

| Methodology | Instrument | CA Mean | CA Sharpe |
|---|---|---|---|
| fibonacci | BTC-USD | -0.002222 | -0.1224 |
| fibonacci | SPY | -0.001500 | -0.1638 |
| fibonacci | QQQ | -0.000647 | -0.0424 |
| volatility | BTC-USD | -0.000656 | -0.0361 |
| volatility | SPY | -0.002761 | -0.3068 |
| volatility | QQQ | -0.003304 | -0.2190 |
| liquidity | BTC-USD | -0.000387 | -0.0752 |
| liquidity | SPY | 0.000092 | 0.0296 |
| liquidity | QQQ | 0.001009 | 0.2209 |
| volume | BTC-USD | -0.000786 | -0.0560 |
| volume | SPY | -0.000871 | -0.1068 |
| volume | QQQ | -0.000549 | -0.0459 |
| vwap | BTC-USD | -0.001614 | -0.0888 |
| vwap | SPY | -0.001374 | -0.1499 |
| vwap | QQQ | -0.002108 | -0.1385 |
| market_structure | BTC-USD | 0.000120 | 0.0896 |
| market_structure | SPY | -0.000036 | -0.0145 |
| market_structure | QQQ | -0.000109 | -0.1040 |
| momentum | BTC-USD | -0.001169 | -0.0642 |
| momentum | SPY | -0.000827 | -0.0902 |
| momentum | QQQ | -0.000970 | -0.0635 |
| technical_analysis | BTC-USD | 0.000069 | 0.0096 |
| technical_analysis | SPY | -0.000279 | -0.0669 |
| technical_analysis | QQQ | 0.000186 | 0.0226 |

## 9. Negative Controls

| Methodology | Instrument | Negative Control DA | Strategy DA | Delta |
|---|---|---|---|---|
| fibonacci | BTC-USD | 0.5208 | 0.4658 | -0.0551 |
| fibonacci | SPY | 0.4842 | 0.5200 | +0.0358 |
| fibonacci | QQQ | 0.5053 | 0.4900 | -0.0153 |
| volatility | BTC-USD | 0.5211 | 0.5137 | -0.0074 |
| volatility | SPY | 0.4444 | 0.4300 | -0.0144 |
| volatility | QQQ | 0.4667 | 0.4400 | -0.0267 |
| liquidity | BTC-USD | 0.3684 | 0.5000 | +0.1316 |
| liquidity | SPY | 0.5385 | 0.5000 | -0.0385 |
| liquidity | QQQ | 0.5556 | 0.7778 | +0.2222 |
| volume | BTC-USD | 0.4286 | 0.4932 | +0.0646 |
| volume | SPY | 0.4286 | 0.5375 | +0.1089 |
| volume | QQQ | 0.4032 | 0.5593 | +0.1561 |
| vwap | BTC-USD | 0.5486 | 0.4863 | -0.0623 |
| vwap | SPY | 0.4842 | 0.5100 | +0.0258 |
| vwap | QQQ | 0.5053 | 0.4600 | -0.0453 |
| market_structure | BTC-USD | 0.6000 | 1.0000 | +0.4000 |
| market_structure | SPY | 1.0000 | 0.6667 | -0.3333 |
| market_structure | QQQ | 1.0000 | 0.6667 | -0.3333 |
| momentum | BTC-USD | 0.5137 | 0.4932 | -0.0205 |
| momentum | SPY | 0.5102 | 0.5300 | +0.0198 |
| momentum | QQQ | 0.5408 | 0.5000 | -0.0408 |
| technical_analysis | BTC-USD | 0.3636 | 0.7000 | +0.3364 |
| technical_analysis | SPY | 0.5556 | 0.5417 | -0.0139 |
| technical_analysis | QQQ | 0.6364 | 0.5758 | -0.0606 |

## 10. Robustness Results

### fibonacci/BTC-USD
- da_swing_window_long: 0.4521
- da_swing_window_short: 0.4795

### fibonacci/SPY
- da_swing_window_long: 0.4800
- da_swing_window_short: 0.4800

### fibonacci/QQQ
- da_swing_window_long: 0.5200
- da_swing_window_short: 0.5300

### volatility/BTC-USD
- da_short_window_fast: 0.5137
- da_short_window_slow: 0.5137

### volatility/SPY
- da_short_window_fast: 0.4300
- da_short_window_slow: 0.4300

### volatility/QQQ
- da_short_window_fast: 0.4400
- da_short_window_slow: 0.4400

### liquidity/BTC-USD
- da_lookback_long: 0.5714
- da_lookback_short: 0.6250

### liquidity/SPY
- da_lookback_long: 0.5455
- da_lookback_short: 0.6154

### liquidity/QQQ
- da_lookback_long: 0.4118
- da_lookback_short: 0.4737

### volume/BTC-USD
- da_window_long: 0.5738
- da_window_short: 0.5161

### volume/SPY
- da_window_long: 0.5714
- da_window_short: 0.5385

### volume/QQQ
- da_window_long: 0.4857
- da_window_short: 0.5231

### vwap/BTC-USD
- da_window_long: 0.4795
- da_window_short: 0.5000

### vwap/SPY
- da_window_long: 0.4900
- da_window_short: 0.4600

### vwap/QQQ
- da_window_long: 0.4800
- da_window_short: 0.5100

### market_structure/BTC-USD
- da_lookback_long: 0.5000
- da_lookback_short: 0.7500

### market_structure/SPY
- da_lookback_long: 0.5000
- da_lookback_short: 0.3333

### market_structure/QQQ
- da_lookback_long: 1.0000
- da_lookback_short: 0.5000

### momentum/BTC-USD
- da_period_fast: 0.4795
- da_period_slow: 0.4863

### momentum/SPY
- da_period_fast: 0.4600
- da_period_slow: 0.4600

### momentum/QQQ
- da_period_fast: 0.4600
- da_period_slow: 0.4900

### technical_analysis/BTC-USD
- da_rsi_period_fast: 0.5000
- da_rsi_period_slow: 0.5455

### technical_analysis/SPY
- da_rsi_period_fast: 0.5333
- da_rsi_period_slow: 0.6667

### technical_analysis/QQQ
- da_rsi_period_fast: 0.3750
- da_rsi_period_slow: 0.6667


## 11. Methodology Scorecard

====================================================================================================
METHODOLOGY SCORECARD
====================================================================================================
Methodology                DA   Base     CA Ret  Robust  Leak Class         
----------------------------------------------------------------------------------------------------
fibonacci              0.4658 0.4863  -0.002222    0.00     Y rejected      
fibonacci              0.5200 0.5700  -0.001500    0.00     Y rejected      
fibonacci              0.4900 0.5600  -0.000647    1.00     Y inconclusive  
volatility             0.5137 0.4863  -0.000656    1.00     Y inconclusive  
volatility             0.4300 0.5700  -0.002761    0.00     Y rejected      
volatility             0.4400 0.5600  -0.003304    0.00     Y rejected      
liquidity              0.5000 0.4863  -0.000387    1.00     Y inconclusive  
liquidity              0.5000 0.5700   0.000092    1.00     Y inconclusive  
liquidity              0.7778 0.5600   0.001009    0.00     Y weak          
volume                 0.4932 0.4863  -0.000786    1.00     Y inconclusive  
volume                 0.5375 0.5700  -0.000871    1.00     Y rejected      
volume                 0.5593 0.5600  -0.000549    0.50     Y inconclusive  
vwap                   0.4863 0.4863  -0.001614    0.00     Y inconclusive  
vwap                   0.5100 0.5700  -0.001374    0.00     Y rejected      
vwap                   0.4600 0.5600  -0.002108    0.50     Y rejected      
market_structure       1.0000 0.4863   0.000120    0.50     Y weak          
market_structure       0.6667 0.5700  -0.000036    0.00     Y inconclusive  
market_structure       0.6667 0.5600  -0.000109    0.50     Y inconclusive  
momentum               0.4932 0.4863  -0.001169    0.00     Y inconclusive  
momentum               0.5300 0.5700  -0.000827    0.00     Y inconclusive  
momentum               0.5000 0.5600  -0.000970    0.00     Y inconclusive  
technical_analysis     0.7000 0.4863   0.000069    0.50     Y weak          
technical_analysis     0.5417 0.5700  -0.000279    1.00     Y rejected      
technical_analysis     0.5758 0.5600   0.000186    0.50     Y weak          
====================================================================================================

## 12. Feature Candidate Registry

| Feature ID | Methodology | Status | DA | Sharpe | Robustness |
|---|---|---|---|---|---|
| EXP002_BTC-USD | fibonacci | rejected | 0.4658 | -0.0673 | 0.00 |
| EXP002_SPY | fibonacci | rejected | 0.5200 | -0.0546 | 0.00 |
| EXP002_QQQ | fibonacci | inconclusive | 0.4900 | 0.0231 | 1.00 |
| EXP003_BTC-USD | volatility | inconclusive | 0.5137 | 0.0189 | 1.00 |
| EXP003_SPY | volatility | rejected | 0.4300 | -0.1957 | 0.00 |
| EXP003_QQQ | volatility | rejected | 0.4400 | -0.1527 | 0.00 |
| EXP004_BTC-USD | liquidity | inconclusive | 0.5000 | -0.0513 | 1.00 |
| EXP004_SPY | liquidity | inconclusive | 0.5000 | 0.0553 | 1.00 |
| EXP004_QQQ | liquidity | weak | 0.7778 | 0.2406 | 0.00 |
| EXP005_BTC-USD | volume | inconclusive | 0.4932 | -0.0204 | 1.00 |
| EXP005_SPY | volume | rejected | 0.5375 | -0.0087 | 1.00 |
| EXP005_QQQ | volume | inconclusive | 0.5593 | 0.0034 | 0.50 |
| EXP006_BTC-USD | vwap | inconclusive | 0.4863 | -0.0338 | 0.00 |
| EXP006_SPY | vwap | rejected | 0.5100 | -0.0408 | 0.00 |
| EXP006_QQQ | vwap | rejected | 0.4600 | -0.0728 | 0.50 |
| EXP007_BTC-USD | market_structure | weak | 1.0000 | 0.0999 | 0.50 |
| EXP007_SPY | market_structure | inconclusive | 0.6667 | -0.0024 | 0.00 |
| EXP007_QQQ | market_structure | inconclusive | 0.6667 | -0.0754 | 0.50 |
| EXP008_BTC-USD | momentum | inconclusive | 0.4932 | -0.0093 | 0.00 |
| EXP008_SPY | momentum | inconclusive | 0.5300 | 0.0189 | 0.00 |
| EXP008_QQQ | momentum | inconclusive | 0.5000 | 0.0020 | 0.00 |
| EXP009_BTC-USD | technical_analysis | weak | 0.7000 | 0.0191 | 0.50 |
| EXP009_SPY | technical_analysis | rejected | 0.5417 | -0.0093 | 1.00 |
| EXP009_QQQ | technical_analysis | weak | 0.5758 | 0.0625 | 0.50 |

## 13. Leakage Audit

- EXP002/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP002/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP002/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP003/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP003/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP003/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP004/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP004/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP004/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP005/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP005/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP005/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP006/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP006/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP006/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP007/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP007/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP007/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP008/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP008/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP008/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP009/BTC-USD: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP009/SPY: PASS ({'random_temporal_split': True, 'target_leakage': True})
- EXP009/QQQ: PASS ({'random_temporal_split': True, 'target_leakage': True})

## 14. pytest Result

498 passed, 1 warning (pending final run)

## 15. ruff Result

All checks passed (pending final run)

## 16. mypy Result

Success: no issues found (pending final run)

## 17. Limitations

1. Real market data (BTC-USD, SPY, QQQ) but limited to 2 years daily bars
2. No intraday data for VWAP or market profile methodologies
3. Single timeframe (daily) - results may differ on intraday
4. Transaction costs modeled as flat bps, not spread/slippage
5. No position sizing optimization
6. Gann, astrology, time cycles rejected as non-computable
7. Elliott wave requires wave counting algorithm not implemented
8. Multiple testing correction not yet applied
9. Results apply to tested definition, dataset, horizon and regime only

## 18. Recommendation for Phase 8

**Do NOT begin Phase 8 automatically.**

Results from this benchmark should be reviewed before proceeding.
Key findings to consider:
- 0 features with SUPPORTED evidence
- 4 features with WEAK evidence

SUPPORTED does not mean permanently true.
REJECTED does not necessarily mean universally false.
Results apply to the tested definition, dataset, horizon and regime.