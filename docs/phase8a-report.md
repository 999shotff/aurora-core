# AURORA CORE — Phase 8A Final Report

**Date:** 2026-08-15

**Phase:** 8A — Feature Interaction Research

**Status:** COMPLETE

---

## 1. Pre-registered Feature Set

- **liquidity_sweep** (liquidity): Liquidity sweep detection: price exceeds recent swing then reverses
  - Formula: `sweep = 1 if low < prev_low and close > prev_low; -1 if high > prev_high and close < prev_high`
  - Source: b2280f4443f2611f_p9_c07acebd0
- **market_structure_bos** (market_structure): Break of Structure: price breaks above previous swing high or below swing low
  - Formula: `bos = 1 if close > prev_swing_high; -1 if close < prev_swing_low`
  - Source: 5fcfe5efce295a41_p24_c0f91a7e9
- **rsi_signal** (rsi): RSI oversold/overbought signal
  - Formula: `rsi_signal = 1 if RSI(14) < 30; -1 if RSI(14) > 70`
  - Source: 5fcfe5efce295a41_p3_c58d9f01b
- **momentum_14** (momentum): 14-period price momentum
  - Formula: `mom = (close - close[14]) / close[14]`
  - Source: 5fcfe5efce295a41_p5_ce70606c3
- **atr_ratio** (volatility): ATR expansion ratio (short/long)
  - Formula: `atr_ratio = ATR(14) / ATR(50)`
  - Source: 0973976867d6b506_p97_c32ec2c40
- **volume_divergence** (volume): Volume-price divergence: price trend vs volume trend
  - Formula: `div = -1 if price_slope > 0 and vol_slope < 0; 1 if price_slope < 0 and vol_slope > 0`
  - Source: 6cc3bf8840a7e6d9
- **vwap_deviation** (vwap): Price deviation from VWAP
  - Formula: `vwap_dev = (close - VWAP) / VWAP`
  - Source: 2e15dafca208257c_p7_c33570093
- **fibonacci_distance** (fibonacci): Distance from 0.618 Fibonacci retracement level
  - Formula: `fib_dist = (close - (low + 0.618 * (high - low))) / close`
  - Source: 3d88aa766403f953_p295_cadcf2be2

**Interactions:**
- **liquidity_x_structure**: Liquidity sweep combined with structure break direction
  - Formula: `interaction = liquidity_sweep * market_structure_bos`
- **rsi_x_structure**: RSI signal filtered by structure break
  - Formula: `interaction = rsi_signal if market_structure_bos == 0 else market_structure_bos`
- **momentum_x_volatility**: Momentum scaled by volatility regime
  - Formula: `interaction = momentum_14 * atr_ratio`
- **volume_x_structure**: Volume divergence confirmed by structure break
  - Formula: `interaction = volume_divergence * market_structure_bos`
- **liquidity_x_volatility**: Liquidity sweep in volatility context
  - Formula: `interaction = liquidity_sweep * atr_ratio`

## 2. Individual Feature Results

| Instrument | Model | Feature | DA | BA | F1 | Brier | Sharpe |
|---|---|---|---|---|---|---|---|
| BTC-USD | logistic | liquidity | 0.4936 | 0.5055 | 0.4859 | 0.2560 | 0.0099 |
| BTC-USD | logistic | market_structure | 0.4850 | 0.4991 | 0.4392 | 0.2611 | 0.0088 |
| BTC-USD | logistic | rsi | 0.4873 | 0.5000 | 0.4358 | 0.2549 | -0.0139 |
| BTC-USD | logistic | momentum | 0.5000 | 0.5101 | 0.5469 | 0.2550 | 0.0141 |
| BTC-USD | logistic | volatility | 0.4889 | 0.4877 | 0.6275 | 0.2549 | -0.0236 |
| BTC-USD | logistic | volume | 0.4777 | 0.4797 | 0.6344 | 0.2587 | -0.0260 |
| BTC-USD | logistic | vwap | 0.4968 | 0.5017 | 0.5900 | 0.2572 | -0.0032 |
| BTC-USD | logistic | fibonacci | 0.5011 | 0.5068 | 0.5889 | 0.2594 | 0.0043 |
| BTC-USD | logistic | liquidity_x_structure | 0.4872 | 0.5000 | 0.4352 | 0.2549 | -0.0142 |
| BTC-USD | logistic | rsi_x_structure | 0.4893 | 0.5021 | 0.4433 | 0.2559 | 0.0125 |
| BTC-USD | logistic | momentum_x_volatility | 0.5089 | 0.5156 | 0.6041 | 0.2537 | 0.0100 |
| BTC-USD | logistic | volume_x_structure | 0.4872 | 0.4999 | 0.4344 | 0.2593 | -0.0141 |
| BTC-USD | logistic | liquidity_x_volatility | 0.4933 | 0.5000 | 0.6556 | 0.2537 | -0.0145 |
| BTC-USD | logistic | combined | 0.4644 | 0.4688 | 0.5876 | 0.2740 | -0.0490 |
| BTC-USD | tree | liquidity | 0.5000 | 0.5007 | 0.6594 | 0.2620 | -0.0013 |
| BTC-USD | tree | market_structure | 0.5000 | 0.5000 | 0.6631 | 0.2579 | -0.0017 |
| BTC-USD | tree | rsi | 0.5000 | 0.5000 | 0.6636 | 0.2630 | -0.0016 |
| BTC-USD | tree | momentum | 0.4641 | 0.4802 | 0.5012 | 0.2879 | -0.0355 |
| BTC-USD | tree | volatility | 0.5556 | 0.5618 | 0.6040 | 0.2758 | 0.0703 |
| BTC-USD | tree | volume | 0.4989 | 0.5000 | 0.6623 | 0.2592 | -0.0036 |
| BTC-USD | tree | vwap | 0.5244 | 0.5283 | 0.6255 | 0.2874 | 0.0275 |
| BTC-USD | tree | fibonacci | 0.4862 | 0.4826 | 0.6064 | 0.2930 | -0.0220 |
| BTC-USD | tree | liquidity_x_structure | 0.5000 | 0.5000 | 0.6631 | 0.2556 | -0.0017 |
| BTC-USD | tree | rsi_x_structure | 0.5000 | 0.5000 | 0.6631 | 0.2613 | -0.0017 |
| BTC-USD | tree | momentum_x_volatility | 0.5222 | 0.5177 | 0.6170 | 0.2769 | 0.0128 |
| BTC-USD | tree | volume_x_structure | 0.5000 | 0.5000 | 0.6631 | 0.2569 | -0.0017 |
| BTC-USD | tree | liquidity_x_volatility | 0.5044 | 0.5094 | 0.6633 | 0.2666 | -0.0039 |
| BTC-USD | tree | combined | 0.4733 | 0.4773 | 0.5684 | 0.3204 | -0.0375 |
| BTC-USD | ensemble | liquidity | 0.5000 | 0.5007 | 0.6594 | 0.2642 | -0.0013 |
| BTC-USD | ensemble | market_structure | 0.5000 | 0.5000 | 0.6631 | 0.2571 | -0.0017 |
| BTC-USD | ensemble | rsi | 0.4916 | 0.4924 | 0.6532 | 0.2620 | -0.0098 |
| BTC-USD | ensemble | momentum | 0.4895 | 0.4965 | 0.5894 | 0.2716 | -0.0079 |
| BTC-USD | ensemble | volatility | 0.5311 | 0.5345 | 0.5974 | 0.2715 | 0.0345 |
| BTC-USD | ensemble | volume | 0.4777 | 0.4797 | 0.6344 | 0.2602 | -0.0260 |
| BTC-USD | ensemble | vwap | 0.5032 | 0.5195 | 0.6070 | 0.2725 | 0.0117 |
| BTC-USD | ensemble | fibonacci | 0.4735 | 0.4848 | 0.6046 | 0.2785 | -0.0263 |
| BTC-USD | ensemble | liquidity_x_structure | 0.5000 | 0.5000 | 0.6631 | 0.2554 | -0.0017 |
| BTC-USD | ensemble | rsi_x_structure | 0.5000 | 0.5000 | 0.6631 | 0.2620 | -0.0017 |
| BTC-USD | ensemble | momentum_x_volatility | 0.5067 | 0.5096 | 0.6067 | 0.2643 | -0.0005 |
| BTC-USD | ensemble | volume_x_structure | 0.5000 | 0.5000 | 0.6631 | 0.2562 | -0.0017 |
| BTC-USD | ensemble | liquidity_x_volatility | 0.4889 | 0.4957 | 0.6527 | 0.2604 | -0.0189 |
| BTC-USD | ensemble | combined | 0.5000 | 0.5015 | 0.6200 | 0.2863 | -0.0103 |
| SPY | logistic | liquidity | 0.6415 | 0.5000 | 0.7750 | 0.2446 | 0.3255 |
| SPY | logistic | market_structure | 0.6321 | 0.4920 | 0.7675 | 0.2459 | 0.3162 |
| SPY | logistic | rsi | 0.6231 | 0.5391 | 0.7475 | 0.2619 | 0.3371 |
| SPY | logistic | momentum | 0.5701 | 0.5297 | 0.7035 | 0.2569 | 0.2812 |
| SPY | logistic | volatility | 0.6195 | 0.5237 | 0.7534 | 0.2517 | 0.3047 |
| SPY | logistic | volume | 0.6038 | 0.5650 | 0.7340 | 0.2464 | 0.3480 |
| SPY | logistic | vwap | 0.5786 | 0.4957 | 0.7236 | 0.2554 | 0.2758 |
| SPY | logistic | fibonacci | 0.5755 | 0.5102 | 0.7165 | 0.2559 | 0.2745 |
| SPY | logistic | liquidity_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2443 | 0.3255 |
| SPY | logistic | rsi_x_structure | 0.6195 | 0.5423 | 0.7424 | 0.2492 | 0.3425 |
| SPY | logistic | momentum_x_volatility | 0.6296 | 0.5000 | 0.7637 | 0.2496 | 0.2974 |
| SPY | logistic | volume_x_structure | 0.6352 | 0.4936 | 0.7693 | 0.2469 | 0.3191 |
| SPY | logistic | liquidity_x_volatility | 0.6296 | 0.5000 | 0.7637 | 0.2463 | 0.2974 |
| SPY | logistic | combined | 0.5354 | 0.5202 | 0.6611 | 0.2813 | 0.2519 |
| SPY | tree | liquidity | 0.6415 | 0.5025 | 0.7703 | 0.2406 | 0.3266 |
| SPY | tree | market_structure | 0.6321 | 0.4920 | 0.7675 | 0.2457 | 0.3162 |
| SPY | tree | rsi | 0.6417 | 0.5000 | 0.7766 | 0.2395 | 0.3209 |
| SPY | tree | momentum | 0.6137 | 0.5415 | 0.7388 | 0.2706 | 0.3199 |
| SPY | tree | volatility | 0.5993 | 0.5383 | 0.7220 | 0.2519 | 0.2886 |
| SPY | tree | volume | 0.6415 | 0.5000 | 0.7750 | 0.2479 | 0.3255 |
| SPY | tree | vwap | 0.6101 | 0.4841 | 0.7500 | 0.2520 | 0.2936 |
| SPY | tree | fibonacci | 0.5566 | 0.5027 | 0.6892 | 0.2579 | 0.2553 |
| SPY | tree | liquidity_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2417 | 0.3255 |
| SPY | tree | rsi_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2414 | 0.3255 |
| SPY | tree | momentum_x_volatility | 0.6195 | 0.5050 | 0.7490 | 0.2546 | 0.2924 |
| SPY | tree | volume_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2417 | 0.3255 |
| SPY | tree | liquidity_x_volatility | 0.6263 | 0.5033 | 0.7574 | 0.2510 | 0.2952 |
| SPY | tree | combined | 0.5084 | 0.4449 | 0.6261 | 0.3137 | 0.1711 |
| SPY | ensemble | liquidity | 0.6415 | 0.5025 | 0.7703 | 0.2437 | 0.3266 |
| SPY | ensemble | market_structure | 0.6321 | 0.4920 | 0.7675 | 0.2498 | 0.3162 |
| SPY | ensemble | rsi | 0.6417 | 0.5000 | 0.7766 | 0.2402 | 0.3209 |
| SPY | ensemble | momentum | 0.5826 | 0.5067 | 0.7211 | 0.2495 | 0.2866 |
| SPY | ensemble | volatility | 0.5724 | 0.5066 | 0.7060 | 0.2494 | 0.2519 |
| SPY | ensemble | volume | 0.6415 | 0.5000 | 0.7750 | 0.2457 | 0.3255 |
| SPY | ensemble | vwap | 0.5975 | 0.5133 | 0.7322 | 0.2506 | 0.2915 |
| SPY | ensemble | fibonacci | 0.5566 | 0.4631 | 0.7032 | 0.2543 | 0.2376 |
| SPY | ensemble | liquidity_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2448 | 0.3255 |
| SPY | ensemble | rsi_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2447 | 0.3255 |
| SPY | ensemble | momentum_x_volatility | 0.5522 | 0.5467 | 0.6692 | 0.2580 | 0.2656 |
| SPY | ensemble | volume_x_structure | 0.6415 | 0.5000 | 0.7750 | 0.2448 | 0.3255 |
| SPY | ensemble | liquidity_x_volatility | 0.6263 | 0.4998 | 0.7564 | 0.2480 | 0.2933 |
| SPY | ensemble | combined | 0.5084 | 0.4905 | 0.6371 | 0.2549 | 0.1981 |
| QQQ | logistic | liquidity | 0.6038 | 0.4896 | 0.7493 | 0.2458 | 0.2874 |
| QQQ | logistic | market_structure | 0.6447 | 0.5000 | 0.7793 | 0.2427 | 0.3289 |
| QQQ | logistic | rsi | 0.6012 | 0.5265 | 0.7183 | 0.2595 | 0.3224 |
| QQQ | logistic | momentum | 0.5857 | 0.4964 | 0.7311 | 0.2527 | 0.2730 |
| QQQ | logistic | volatility | 0.6296 | 0.5000 | 0.7673 | 0.2413 | 0.2889 |
| QQQ | logistic | volume | 0.6447 | 0.5000 | 0.7793 | 0.2422 | 0.3289 |
| QQQ | logistic | vwap | 0.5975 | 0.4996 | 0.7418 | 0.2524 | 0.2914 |
| QQQ | logistic | fibonacci | 0.6069 | 0.4916 | 0.7516 | 0.2505 | 0.2912 |
| QQQ | logistic | liquidity_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2420 | 0.3289 |
| QQQ | logistic | rsi_x_structure | 0.5912 | 0.5234 | 0.7146 | 0.2567 | 0.3168 |
| QQQ | logistic | momentum_x_volatility | 0.6296 | 0.5000 | 0.7673 | 0.2447 | 0.2889 |
| QQQ | logistic | volume_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2412 | 0.3289 |
| QQQ | logistic | liquidity_x_volatility | 0.6296 | 0.5000 | 0.7673 | 0.2423 | 0.2889 |
| QQQ | logistic | combined | 0.4983 | 0.4857 | 0.6164 | 0.2954 | 0.1808 |
| QQQ | tree | liquidity | 0.6384 | 0.4946 | 0.7726 | 0.2407 | 0.3230 |
| QQQ | tree | market_structure | 0.6447 | 0.5000 | 0.7793 | 0.2398 | 0.3289 |
| QQQ | tree | rsi | 0.6449 | 0.5000 | 0.7803 | 0.2400 | 0.3252 |
| QQQ | tree | momentum | 0.5109 | 0.4994 | 0.6215 | 0.2712 | 0.2026 |
| QQQ | tree | volatility | 0.5791 | 0.4824 | 0.7113 | 0.2730 | 0.2460 |
| QQQ | tree | volume | 0.6447 | 0.5000 | 0.7793 | 0.2406 | 0.3289 |
| QQQ | tree | vwap | 0.5063 | 0.4606 | 0.6464 | 0.2816 | 0.2019 |
| QQQ | tree | fibonacci | 0.5975 | 0.4835 | 0.7394 | 0.2667 | 0.2843 |
| QQQ | tree | liquidity_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2403 | 0.3289 |
| QQQ | tree | rsi_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2417 | 0.3289 |
| QQQ | tree | momentum_x_volatility | 0.5960 | 0.4764 | 0.7339 | 0.2586 | 0.2580 |
| QQQ | tree | volume_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2403 | 0.3289 |
| QQQ | tree | liquidity_x_volatility | 0.6195 | 0.5062 | 0.7563 | 0.2497 | 0.2824 |
| QQQ | tree | combined | 0.5758 | 0.4745 | 0.7213 | 0.2679 | 0.2369 |
| QQQ | ensemble | liquidity | 0.6447 | 0.5000 | 0.7793 | 0.2437 | 0.3289 |
| QQQ | ensemble | market_structure | 0.6447 | 0.5000 | 0.7793 | 0.2433 | 0.3289 |
| QQQ | ensemble | rsi | 0.6449 | 0.5000 | 0.7803 | 0.2420 | 0.3252 |
| QQQ | ensemble | momentum | 0.5327 | 0.4748 | 0.6759 | 0.2529 | 0.2179 |
| QQQ | ensemble | volatility | 0.5724 | 0.4747 | 0.7104 | 0.2673 | 0.2309 |
| QQQ | ensemble | volume | 0.6447 | 0.5000 | 0.7793 | 0.2398 | 0.3289 |
| QQQ | ensemble | vwap | 0.5283 | 0.4844 | 0.6657 | 0.2567 | 0.2276 |
| QQQ | ensemble | fibonacci | 0.5881 | 0.4953 | 0.7330 | 0.2510 | 0.2794 |
| QQQ | ensemble | liquidity_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2434 | 0.3289 |
| QQQ | ensemble | rsi_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2450 | 0.3289 |
| QQQ | ensemble | momentum_x_volatility | 0.5690 | 0.4707 | 0.7159 | 0.2570 | 0.2328 |
| QQQ | ensemble | volume_x_structure | 0.6447 | 0.5000 | 0.7793 | 0.2434 | 0.3289 |
| QQQ | ensemble | liquidity_x_volatility | 0.6094 | 0.4976 | 0.7497 | 0.2442 | 0.2725 |
| QQQ | ensemble | combined | 0.5657 | 0.4788 | 0.7116 | 0.2570 | 0.2298 |

## 3. Interaction Definitions

- **liquidity_x_structure**: interaction = liquidity_sweep * market_structure_bos
- **rsi_x_structure**: interaction = rsi_signal if market_structure_bos == 0 else market_structure_bos
- **momentum_x_volatility**: interaction = momentum_14 * atr_ratio
- **volume_x_structure**: interaction = volume_divergence * market_structure_bos
- **liquidity_x_volatility**: interaction = liquidity_sweep * atr_ratio

## 4. Ablation Results

### ablation_liquidity_logistic
- Model: logistic
- Features: ['liquidity']
- Train: 235, Test: 470
- DA: 0.4936, BA: 0.5055
- F1: 0.4859, Brier: 0.2560
- Sharpe: 0.0099
- Negative Control DA: 0.4965
- Feature importances:
  - liquidity_sweep: 0.0069

### ablation_market_structure_logistic
- Model: logistic
- Features: ['market_structure']
- Train: 235, Test: 470
- DA: 0.4850, BA: 0.4991
- F1: 0.4392, Brier: 0.2611
- Sharpe: 0.0088
- Negative Control DA: 0.4965
- Feature importances:
  - market_structure_bos: 0.5849

### ablation_rsi_logistic
- Model: logistic
- Features: ['rsi']
- Train: 237, Test: 475
- DA: 0.4873, BA: 0.5000
- F1: 0.4358, Brier: 0.2549
- Sharpe: -0.0139
- Negative Control DA: 0.4958
- Feature importances:
  - rsi_signal: 0.0051

### ablation_momentum_logistic
- Model: logistic
- Features: ['momentum']
- Train: 237, Test: 475
- DA: 0.5000, BA: 0.5101
- F1: 0.5469, Brier: 0.2550
- Sharpe: 0.0141
- Negative Control DA: 0.4958
- Feature importances:
  - momentum_14: 0.1131

### ablation_volatility_logistic
- Model: logistic
- Features: ['volatility']
- Train: 225, Test: 452
- DA: 0.4889, BA: 0.4877
- F1: 0.6275, Brier: 0.2549
- Sharpe: -0.0236
- Negative Control DA: 0.4978
- Feature importances:
  - atr_ratio: 0.0698

### ablation_volume_logistic
- Model: logistic
- Features: ['volume']
- Train: 235, Test: 471
- DA: 0.4777, BA: 0.4797
- F1: 0.6344, Brier: 0.2587
- Sharpe: -0.0260
- Negative Control DA: 0.4972
- Feature importances:
  - volume_divergence: 0.1504

### ablation_vwap_logistic
- Model: logistic
- Features: ['vwap']
- Train: 235, Test: 471
- DA: 0.4968, BA: 0.5017
- F1: 0.5900, Brier: 0.2572
- Sharpe: -0.0032
- Negative Control DA: 0.4972
- Feature importances:
  - vwap_deviation: 0.2048

### ablation_fibonacci_logistic
- Model: logistic
- Features: ['fibonacci']
- Train: 235, Test: 471
- DA: 0.5011, BA: 0.5068
- F1: 0.5889, Brier: 0.2594
- Sharpe: 0.0043
- Negative Control DA: 0.4972
- Feature importances:
  - fibonacci_distance: 0.2379

### ablation_liquidity_x_structure_logistic
- Model: logistic
- Features: ['liquidity_x_structure']
- Train: 235, Test: 470
- DA: 0.4872, BA: 0.5000
- F1: 0.4352, Brier: 0.2549
- Sharpe: -0.0142
- Negative Control DA: 0.4965
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_logistic
- Model: logistic
- Features: ['rsi_x_structure']
- Train: 235, Test: 470
- DA: 0.4893, BA: 0.5021
- F1: 0.4433, Brier: 0.2559
- Sharpe: 0.0125
- Negative Control DA: 0.4965
- Feature importances:
  - rsi_x_structure: 0.0936

### ablation_momentum_x_volatility_logistic
- Model: logistic
- Features: ['momentum_x_volatility']
- Train: 225, Test: 452
- DA: 0.5089, BA: 0.5156
- F1: 0.6041, Brier: 0.2537
- Sharpe: 0.0100
- Negative Control DA: 0.4978
- Feature importances:
  - momentum_x_volatility: 0.0279

### ablation_volume_x_structure_logistic
- Model: logistic
- Features: ['volume_x_structure']
- Train: 235, Test: 470
- DA: 0.4872, BA: 0.4999
- F1: 0.4344, Brier: 0.2593
- Sharpe: -0.0141
- Negative Control DA: 0.4965
- Feature importances:
  - volume_x_structure: 0.3263

### ablation_liquidity_x_volatility_logistic
- Model: logistic
- Features: ['liquidity_x_volatility']
- Train: 225, Test: 452
- DA: 0.4933, BA: 0.5000
- F1: 0.6556, Brier: 0.2537
- Sharpe: -0.0145
- Negative Control DA: 0.4978
- Feature importances:
  - liquidity_x_volatility: 0.0139

### ablation_combined_logistic
- Model: logistic
- Features: ['combined']
- Train: 225, Test: 452
- DA: 0.4644, BA: 0.4688
- F1: 0.5876, Brier: 0.2740
- Sharpe: -0.0490
- Negative Control DA: 0.4978
- Feature importances:
  - vwap_deviation: 0.4766
  - market_structure_bos: 0.4593
  - momentum_14: 0.2718
  - momentum_x_volatility: 0.2303
  - liquidity_sweep: 0.1981
  - rsi_x_structure: 0.1906
  - fibonacci_distance: 0.1413
  - liquidity_x_volatility: 0.1058
  - volume_x_structure: 0.1043
  - rsi_signal: 0.0734
  - volume_divergence: 0.0615
  - atr_ratio: 0.0052
  - liquidity_x_structure: 0.0000

### ablation_liquidity_tree
- Model: tree
- Features: ['liquidity']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5007
- F1: 0.6594, Brier: 0.2620
- Sharpe: -0.0013
- Negative Control DA: 0.4965
- Feature importances:
  - liquidity_sweep: 1.0000

### ablation_market_structure_tree
- Model: tree
- Features: ['market_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2579
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - market_structure_bos: 1.0000

### ablation_rsi_tree
- Model: tree
- Features: ['rsi']
- Train: 237, Test: 475
- DA: 0.5000, BA: 0.5000
- F1: 0.6636, Brier: 0.2630
- Sharpe: -0.0016
- Negative Control DA: 0.4958
- Feature importances:
  - rsi_signal: 1.0000

### ablation_momentum_tree
- Model: tree
- Features: ['momentum']
- Train: 237, Test: 475
- DA: 0.4641, BA: 0.4802
- F1: 0.5012, Brier: 0.2879
- Sharpe: -0.0355
- Negative Control DA: 0.4958
- Feature importances:
  - momentum_14: 1.0000

### ablation_volatility_tree
- Model: tree
- Features: ['volatility']
- Train: 225, Test: 452
- DA: 0.5556, BA: 0.5618
- F1: 0.6040, Brier: 0.2758
- Sharpe: 0.0703
- Negative Control DA: 0.4978
- Feature importances:
  - atr_ratio: 1.0000

### ablation_volume_tree
- Model: tree
- Features: ['volume']
- Train: 235, Test: 471
- DA: 0.4989, BA: 0.5000
- F1: 0.6623, Brier: 0.2592
- Sharpe: -0.0036
- Negative Control DA: 0.4972
- Feature importances:
  - volume_divergence: 1.0000

### ablation_vwap_tree
- Model: tree
- Features: ['vwap']
- Train: 235, Test: 471
- DA: 0.5244, BA: 0.5283
- F1: 0.6255, Brier: 0.2874
- Sharpe: 0.0275
- Negative Control DA: 0.4972
- Feature importances:
  - vwap_deviation: 1.0000

### ablation_fibonacci_tree
- Model: tree
- Features: ['fibonacci']
- Train: 235, Test: 471
- DA: 0.4862, BA: 0.4826
- F1: 0.6064, Brier: 0.2930
- Sharpe: -0.0220
- Negative Control DA: 0.4972
- Feature importances:
  - fibonacci_distance: 1.0000

### ablation_liquidity_x_structure_tree
- Model: tree
- Features: ['liquidity_x_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2556
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_tree
- Model: tree
- Features: ['rsi_x_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2613
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - rsi_x_structure: 1.0000

### ablation_momentum_x_volatility_tree
- Model: tree
- Features: ['momentum_x_volatility']
- Train: 225, Test: 452
- DA: 0.5222, BA: 0.5177
- F1: 0.6170, Brier: 0.2769
- Sharpe: 0.0128
- Negative Control DA: 0.4978
- Feature importances:
  - momentum_x_volatility: 1.0000

### ablation_volume_x_structure_tree
- Model: tree
- Features: ['volume_x_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2569
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - volume_x_structure: 0.0000

### ablation_liquidity_x_volatility_tree
- Model: tree
- Features: ['liquidity_x_volatility']
- Train: 225, Test: 452
- DA: 0.5044, BA: 0.5094
- F1: 0.6633, Brier: 0.2666
- Sharpe: -0.0039
- Negative Control DA: 0.4978
- Feature importances:
  - liquidity_x_volatility: 1.0000

### ablation_combined_tree
- Model: tree
- Features: ['combined']
- Train: 225, Test: 452
- DA: 0.4733, BA: 0.4773
- F1: 0.5684, Brier: 0.3204
- Sharpe: -0.0375
- Negative Control DA: 0.4978
- Feature importances:
  - atr_ratio: 0.4607
  - momentum_x_volatility: 0.1733
  - vwap_deviation: 0.1631
  - fibonacci_distance: 0.1460
  - momentum_14: 0.0570
  - market_structure_bos: 0.0000
  - rsi_x_structure: 0.0000
  - volume_x_structure: 0.0000
  - liquidity_sweep: 0.0000
  - liquidity_x_structure: 0.0000
  - volume_divergence: 0.0000
  - rsi_signal: 0.0000
  - liquidity_x_volatility: 0.0000

### ablation_liquidity_ensemble
- Model: ensemble
- Features: ['liquidity']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5007
- F1: 0.6594, Brier: 0.2642
- Sharpe: -0.0013
- Negative Control DA: 0.4965
- Feature importances:
  - liquidity_sweep: 1.0000

### ablation_market_structure_ensemble
- Model: ensemble
- Features: ['market_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2571
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - market_structure_bos: 1.0000

### ablation_rsi_ensemble
- Model: ensemble
- Features: ['rsi']
- Train: 237, Test: 475
- DA: 0.4916, BA: 0.4924
- F1: 0.6532, Brier: 0.2620
- Sharpe: -0.0098
- Negative Control DA: 0.4958
- Feature importances:
  - rsi_signal: 1.0000

### ablation_momentum_ensemble
- Model: ensemble
- Features: ['momentum']
- Train: 237, Test: 475
- DA: 0.4895, BA: 0.4965
- F1: 0.5894, Brier: 0.2716
- Sharpe: -0.0079
- Negative Control DA: 0.4958
- Feature importances:
  - momentum_14: 1.0000

### ablation_volatility_ensemble
- Model: ensemble
- Features: ['volatility']
- Train: 225, Test: 452
- DA: 0.5311, BA: 0.5345
- F1: 0.5974, Brier: 0.2715
- Sharpe: 0.0345
- Negative Control DA: 0.4978
- Feature importances:
  - atr_ratio: 1.0000

### ablation_volume_ensemble
- Model: ensemble
- Features: ['volume']
- Train: 235, Test: 471
- DA: 0.4777, BA: 0.4797
- F1: 0.6344, Brier: 0.2602
- Sharpe: -0.0260
- Negative Control DA: 0.4972
- Feature importances:
  - volume_divergence: 1.0000

### ablation_vwap_ensemble
- Model: ensemble
- Features: ['vwap']
- Train: 235, Test: 471
- DA: 0.5032, BA: 0.5195
- F1: 0.6070, Brier: 0.2725
- Sharpe: 0.0117
- Negative Control DA: 0.4972
- Feature importances:
  - vwap_deviation: 1.0000

### ablation_fibonacci_ensemble
- Model: ensemble
- Features: ['fibonacci']
- Train: 235, Test: 471
- DA: 0.4735, BA: 0.4848
- F1: 0.6046, Brier: 0.2785
- Sharpe: -0.0263
- Negative Control DA: 0.4972
- Feature importances:
  - fibonacci_distance: 1.0000

### ablation_liquidity_x_structure_ensemble
- Model: ensemble
- Features: ['liquidity_x_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2554
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_ensemble
- Model: ensemble
- Features: ['rsi_x_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2620
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - rsi_x_structure: 1.0000

### ablation_momentum_x_volatility_ensemble
- Model: ensemble
- Features: ['momentum_x_volatility']
- Train: 225, Test: 452
- DA: 0.5067, BA: 0.5096
- F1: 0.6067, Brier: 0.2643
- Sharpe: -0.0005
- Negative Control DA: 0.4978
- Feature importances:
  - momentum_x_volatility: 1.0000

### ablation_volume_x_structure_ensemble
- Model: ensemble
- Features: ['volume_x_structure']
- Train: 235, Test: 470
- DA: 0.5000, BA: 0.5000
- F1: 0.6631, Brier: 0.2562
- Sharpe: -0.0017
- Negative Control DA: 0.4965
- Feature importances:
  - volume_x_structure: 0.0000

### ablation_liquidity_x_volatility_ensemble
- Model: ensemble
- Features: ['liquidity_x_volatility']
- Train: 225, Test: 452
- DA: 0.4889, BA: 0.4957
- F1: 0.6527, Brier: 0.2604
- Sharpe: -0.0189
- Negative Control DA: 0.4978
- Feature importances:
  - liquidity_x_volatility: 1.0000

### ablation_combined_ensemble
- Model: ensemble
- Features: ['combined']
- Train: 225, Test: 452
- DA: 0.5000, BA: 0.5015
- F1: 0.6200, Brier: 0.2863
- Sharpe: -0.0103
- Negative Control DA: 0.4978
- Feature importances:
  - atr_ratio: 0.3027
  - fibonacci_distance: 0.1937
  - vwap_deviation: 0.1639
  - liquidity_x_volatility: 0.1331
  - momentum_x_volatility: 0.1021
  - liquidity_sweep: 0.0620
  - momentum_14: 0.0393
  - volume_divergence: 0.0033
  - market_structure_bos: 0.0000
  - rsi_x_structure: 0.0000
  - volume_x_structure: 0.0000
  - liquidity_x_structure: 0.0000
  - rsi_signal: 0.0000

### ablation_liquidity_logistic
- Model: logistic
- Features: ['liquidity']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2446
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_sweep: 0.0442

### ablation_market_structure_logistic
- Model: logistic
- Features: ['market_structure']
- Train: 158, Test: 318
- DA: 0.6321, BA: 0.4920
- F1: 0.7675, Brier: 0.2459
- Sharpe: 0.3162
- Negative Control DA: 0.4937
- Feature importances:
  - market_structure_bos: 0.1729

### ablation_rsi_logistic
- Model: logistic
- Features: ['rsi']
- Train: 161, Test: 322
- DA: 0.6231, BA: 0.5391
- F1: 0.7475, Brier: 0.2619
- Sharpe: 0.3371
- Negative Control DA: 0.4928
- Feature importances:
  - rsi_signal: 0.9852

### ablation_momentum_logistic
- Model: logistic
- Features: ['momentum']
- Train: 161, Test: 322
- DA: 0.5701, BA: 0.5297
- F1: 0.7035, Brier: 0.2569
- Sharpe: 0.2812
- Negative Control DA: 0.4928
- Feature importances:
  - momentum_14: 0.3465

### ablation_volatility_logistic
- Model: logistic
- Features: ['volatility']
- Train: 149, Test: 299
- DA: 0.6195, BA: 0.5237
- F1: 0.7534, Brier: 0.2517
- Sharpe: 0.3047
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 0.2249

### ablation_volume_logistic
- Model: logistic
- Features: ['volume']
- Train: 159, Test: 318
- DA: 0.6038, BA: 0.5650
- F1: 0.7340, Brier: 0.2464
- Sharpe: 0.3480
- Negative Control DA: 0.4927
- Feature importances:
  - volume_divergence: 0.2297

### ablation_vwap_logistic
- Model: logistic
- Features: ['vwap']
- Train: 159, Test: 318
- DA: 0.5786, BA: 0.4957
- F1: 0.7236, Brier: 0.2554
- Sharpe: 0.2758
- Negative Control DA: 0.4927
- Feature importances:
  - vwap_deviation: 0.2773

### ablation_fibonacci_logistic
- Model: logistic
- Features: ['fibonacci']
- Train: 159, Test: 318
- DA: 0.5755, BA: 0.5102
- F1: 0.7165, Brier: 0.2559
- Sharpe: 0.2745
- Negative Control DA: 0.4927
- Feature importances:
  - fibonacci_distance: 0.2935

### ablation_liquidity_x_structure_logistic
- Model: logistic
- Features: ['liquidity_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2443
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_logistic
- Model: logistic
- Features: ['rsi_x_structure']
- Train: 158, Test: 318
- DA: 0.6195, BA: 0.5423
- F1: 0.7424, Brier: 0.2492
- Sharpe: 0.3425
- Negative Control DA: 0.4937
- Feature importances:
  - rsi_x_structure: 0.2020

### ablation_momentum_x_volatility_logistic
- Model: logistic
- Features: ['momentum_x_volatility']
- Train: 149, Test: 299
- DA: 0.6296, BA: 0.5000
- F1: 0.7637, Brier: 0.2496
- Sharpe: 0.2974
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 0.1145

### ablation_volume_x_structure_logistic
- Model: logistic
- Features: ['volume_x_structure']
- Train: 158, Test: 318
- DA: 0.6352, BA: 0.4936
- F1: 0.7693, Brier: 0.2469
- Sharpe: 0.3191
- Negative Control DA: 0.4937
- Feature importances:
  - volume_x_structure: 0.2353

### ablation_liquidity_x_volatility_logistic
- Model: logistic
- Features: ['liquidity_x_volatility']
- Train: 149, Test: 299
- DA: 0.6296, BA: 0.5000
- F1: 0.7637, Brier: 0.2463
- Sharpe: 0.2974
- Negative Control DA: 0.4911
- Feature importances:
  - liquidity_x_volatility: 0.0655

### ablation_combined_logistic
- Model: logistic
- Features: ['combined']
- Train: 149, Test: 299
- DA: 0.5354, BA: 0.5202
- F1: 0.6611, Brier: 0.2813
- Sharpe: 0.2519
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_14: 1.6711
  - rsi_signal: 0.7871
  - momentum_x_volatility: 0.6601
  - liquidity_sweep: 0.6229
  - market_structure_bos: 0.5440
  - atr_ratio: 0.4820
  - liquidity_x_volatility: 0.4703
  - volume_x_structure: 0.4585
  - vwap_deviation: 0.4285
  - rsi_x_structure: 0.2616
  - fibonacci_distance: 0.2145
  - volume_divergence: 0.0033
  - liquidity_x_structure: 0.0000

### ablation_liquidity_tree
- Model: tree
- Features: ['liquidity']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5025
- F1: 0.7703, Brier: 0.2406
- Sharpe: 0.3266
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_sweep: 1.0000

### ablation_market_structure_tree
- Model: tree
- Features: ['market_structure']
- Train: 158, Test: 318
- DA: 0.6321, BA: 0.4920
- F1: 0.7675, Brier: 0.2457
- Sharpe: 0.3162
- Negative Control DA: 0.4937
- Feature importances:
  - market_structure_bos: 1.0000

### ablation_rsi_tree
- Model: tree
- Features: ['rsi']
- Train: 161, Test: 322
- DA: 0.6417, BA: 0.5000
- F1: 0.7766, Brier: 0.2395
- Sharpe: 0.3209
- Negative Control DA: 0.4928
- Feature importances:
  - rsi_signal: 1.0000

### ablation_momentum_tree
- Model: tree
- Features: ['momentum']
- Train: 161, Test: 322
- DA: 0.6137, BA: 0.5415
- F1: 0.7388, Brier: 0.2706
- Sharpe: 0.3199
- Negative Control DA: 0.4928
- Feature importances:
  - momentum_14: 1.0000

### ablation_volatility_tree
- Model: tree
- Features: ['volatility']
- Train: 149, Test: 299
- DA: 0.5993, BA: 0.5383
- F1: 0.7220, Brier: 0.2519
- Sharpe: 0.2886
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 1.0000

### ablation_volume_tree
- Model: tree
- Features: ['volume']
- Train: 159, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2479
- Sharpe: 0.3255
- Negative Control DA: 0.4927
- Feature importances:
  - volume_divergence: 1.0000

### ablation_vwap_tree
- Model: tree
- Features: ['vwap']
- Train: 159, Test: 318
- DA: 0.6101, BA: 0.4841
- F1: 0.7500, Brier: 0.2520
- Sharpe: 0.2936
- Negative Control DA: 0.4927
- Feature importances:
  - vwap_deviation: 1.0000

### ablation_fibonacci_tree
- Model: tree
- Features: ['fibonacci']
- Train: 159, Test: 318
- DA: 0.5566, BA: 0.5027
- F1: 0.6892, Brier: 0.2579
- Sharpe: 0.2553
- Negative Control DA: 0.4927
- Feature importances:
  - fibonacci_distance: 1.0000

### ablation_liquidity_x_structure_tree
- Model: tree
- Features: ['liquidity_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2417
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_tree
- Model: tree
- Features: ['rsi_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2414
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - rsi_x_structure: 1.0000

### ablation_momentum_x_volatility_tree
- Model: tree
- Features: ['momentum_x_volatility']
- Train: 149, Test: 299
- DA: 0.6195, BA: 0.5050
- F1: 0.7490, Brier: 0.2546
- Sharpe: 0.2924
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 1.0000

### ablation_volume_x_structure_tree
- Model: tree
- Features: ['volume_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2417
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - volume_x_structure: 0.0000

### ablation_liquidity_x_volatility_tree
- Model: tree
- Features: ['liquidity_x_volatility']
- Train: 149, Test: 299
- DA: 0.6263, BA: 0.5033
- F1: 0.7574, Brier: 0.2510
- Sharpe: 0.2952
- Negative Control DA: 0.4911
- Feature importances:
  - liquidity_x_volatility: 1.0000

### ablation_combined_tree
- Model: tree
- Features: ['combined']
- Train: 149, Test: 299
- DA: 0.5084, BA: 0.4449
- F1: 0.6261, Brier: 0.3137
- Sharpe: 0.1711
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 0.5886
  - momentum_14: 0.2039
  - fibonacci_distance: 0.1055
  - momentum_x_volatility: 0.1020
  - market_structure_bos: 0.0000
  - rsi_x_structure: 0.0000
  - volume_x_structure: 0.0000
  - liquidity_sweep: 0.0000
  - vwap_deviation: 0.0000
  - liquidity_x_structure: 0.0000
  - volume_divergence: 0.0000
  - rsi_signal: 0.0000
  - liquidity_x_volatility: 0.0000

### ablation_liquidity_ensemble
- Model: ensemble
- Features: ['liquidity']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5025
- F1: 0.7703, Brier: 0.2437
- Sharpe: 0.3266
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_sweep: 1.0000

### ablation_market_structure_ensemble
- Model: ensemble
- Features: ['market_structure']
- Train: 158, Test: 318
- DA: 0.6321, BA: 0.4920
- F1: 0.7675, Brier: 0.2498
- Sharpe: 0.3162
- Negative Control DA: 0.4937
- Feature importances:
  - market_structure_bos: 1.0000

### ablation_rsi_ensemble
- Model: ensemble
- Features: ['rsi']
- Train: 161, Test: 322
- DA: 0.6417, BA: 0.5000
- F1: 0.7766, Brier: 0.2402
- Sharpe: 0.3209
- Negative Control DA: 0.4928
- Feature importances:
  - rsi_signal: 1.0000

### ablation_momentum_ensemble
- Model: ensemble
- Features: ['momentum']
- Train: 161, Test: 322
- DA: 0.5826, BA: 0.5067
- F1: 0.7211, Brier: 0.2495
- Sharpe: 0.2866
- Negative Control DA: 0.4928
- Feature importances:
  - momentum_14: 1.0000

### ablation_volatility_ensemble
- Model: ensemble
- Features: ['volatility']
- Train: 149, Test: 299
- DA: 0.5724, BA: 0.5066
- F1: 0.7060, Brier: 0.2494
- Sharpe: 0.2519
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 1.0000

### ablation_volume_ensemble
- Model: ensemble
- Features: ['volume']
- Train: 159, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2457
- Sharpe: 0.3255
- Negative Control DA: 0.4927
- Feature importances:
  - volume_divergence: 1.0000

### ablation_vwap_ensemble
- Model: ensemble
- Features: ['vwap']
- Train: 159, Test: 318
- DA: 0.5975, BA: 0.5133
- F1: 0.7322, Brier: 0.2506
- Sharpe: 0.2915
- Negative Control DA: 0.4927
- Feature importances:
  - vwap_deviation: 1.0000

### ablation_fibonacci_ensemble
- Model: ensemble
- Features: ['fibonacci']
- Train: 159, Test: 318
- DA: 0.5566, BA: 0.4631
- F1: 0.7032, Brier: 0.2543
- Sharpe: 0.2376
- Negative Control DA: 0.4927
- Feature importances:
  - fibonacci_distance: 1.0000

### ablation_liquidity_x_structure_ensemble
- Model: ensemble
- Features: ['liquidity_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2448
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_ensemble
- Model: ensemble
- Features: ['rsi_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2447
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - rsi_x_structure: 1.0000

### ablation_momentum_x_volatility_ensemble
- Model: ensemble
- Features: ['momentum_x_volatility']
- Train: 149, Test: 299
- DA: 0.5522, BA: 0.5467
- F1: 0.6692, Brier: 0.2580
- Sharpe: 0.2656
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 1.0000

### ablation_volume_x_structure_ensemble
- Model: ensemble
- Features: ['volume_x_structure']
- Train: 158, Test: 318
- DA: 0.6415, BA: 0.5000
- F1: 0.7750, Brier: 0.2448
- Sharpe: 0.3255
- Negative Control DA: 0.4937
- Feature importances:
  - volume_x_structure: 0.0000

### ablation_liquidity_x_volatility_ensemble
- Model: ensemble
- Features: ['liquidity_x_volatility']
- Train: 149, Test: 299
- DA: 0.6263, BA: 0.4998
- F1: 0.7564, Brier: 0.2480
- Sharpe: 0.2933
- Negative Control DA: 0.4911
- Feature importances:
  - liquidity_x_volatility: 1.0000

### ablation_combined_ensemble
- Model: ensemble
- Features: ['combined']
- Train: 149, Test: 299
- DA: 0.5084, BA: 0.4905
- F1: 0.6371, Brier: 0.2549
- Sharpe: 0.1981
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 0.2550
  - fibonacci_distance: 0.2372
  - atr_ratio: 0.2146
  - vwap_deviation: 0.1914
  - momentum_14: 0.0734
  - liquidity_x_volatility: 0.0283
  - market_structure_bos: 0.0000
  - rsi_x_structure: 0.0000
  - volume_x_structure: 0.0000
  - liquidity_sweep: 0.0000
  - liquidity_x_structure: 0.0000
  - volume_divergence: 0.0000
  - rsi_signal: 0.0000

### ablation_liquidity_logistic
- Model: logistic
- Features: ['liquidity']
- Train: 158, Test: 318
- DA: 0.6038, BA: 0.4896
- F1: 0.7493, Brier: 0.2458
- Sharpe: 0.2874
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_sweep: 0.1060

### ablation_market_structure_logistic
- Model: logistic
- Features: ['market_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2427
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - market_structure_bos: 0.0231

### ablation_rsi_logistic
- Model: logistic
- Features: ['rsi']
- Train: 161, Test: 322
- DA: 0.6012, BA: 0.5265
- F1: 0.7183, Brier: 0.2595
- Sharpe: 0.3224
- Negative Control DA: 0.4928
- Feature importances:
  - rsi_signal: 0.4357

### ablation_momentum_logistic
- Model: logistic
- Features: ['momentum']
- Train: 161, Test: 322
- DA: 0.5857, BA: 0.4964
- F1: 0.7311, Brier: 0.2527
- Sharpe: 0.2730
- Negative Control DA: 0.4928
- Feature importances:
  - momentum_14: 0.2194

### ablation_volatility_logistic
- Model: logistic
- Features: ['volatility']
- Train: 149, Test: 299
- DA: 0.6296, BA: 0.5000
- F1: 0.7673, Brier: 0.2413
- Sharpe: 0.2889
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 0.0314

### ablation_volume_logistic
- Model: logistic
- Features: ['volume']
- Train: 159, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2422
- Sharpe: 0.3289
- Negative Control DA: 0.4927
- Feature importances:
  - volume_divergence: 0.0467

### ablation_vwap_logistic
- Model: logistic
- Features: ['vwap']
- Train: 159, Test: 318
- DA: 0.5975, BA: 0.4996
- F1: 0.7418, Brier: 0.2524
- Sharpe: 0.2914
- Negative Control DA: 0.4927
- Feature importances:
  - vwap_deviation: 0.2298

### ablation_fibonacci_logistic
- Model: logistic
- Features: ['fibonacci']
- Train: 159, Test: 318
- DA: 0.6069, BA: 0.4916
- F1: 0.7516, Brier: 0.2505
- Sharpe: 0.2912
- Negative Control DA: 0.4927
- Feature importances:
  - fibonacci_distance: 0.1817

### ablation_liquidity_x_structure_logistic
- Model: logistic
- Features: ['liquidity_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2420
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_logistic
- Model: logistic
- Features: ['rsi_x_structure']
- Train: 158, Test: 318
- DA: 0.5912, BA: 0.5234
- F1: 0.7146, Brier: 0.2567
- Sharpe: 0.3168
- Negative Control DA: 0.4937
- Feature importances:
  - rsi_x_structure: 0.3617

### ablation_momentum_x_volatility_logistic
- Model: logistic
- Features: ['momentum_x_volatility']
- Train: 149, Test: 299
- DA: 0.6296, BA: 0.5000
- F1: 0.7673, Brier: 0.2447
- Sharpe: 0.2889
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 0.1151

### ablation_volume_x_structure_logistic
- Model: logistic
- Features: ['volume_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2412
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - volume_x_structure: 0.5666

### ablation_liquidity_x_volatility_logistic
- Model: logistic
- Features: ['liquidity_x_volatility']
- Train: 149, Test: 299
- DA: 0.6296, BA: 0.5000
- F1: 0.7673, Brier: 0.2423
- Sharpe: 0.2889
- Negative Control DA: 0.4911
- Feature importances:
  - liquidity_x_volatility: 0.0142

### ablation_combined_logistic
- Model: logistic
- Features: ['combined']
- Train: 149, Test: 299
- DA: 0.4983, BA: 0.4857
- F1: 0.6164, Brier: 0.2954
- Sharpe: 0.1808
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_14: 3.0910
  - momentum_x_volatility: 1.5546
  - vwap_deviation: 1.2730
  - volume_divergence: 0.8727
  - liquidity_x_volatility: 0.8497
  - liquidity_sweep: 0.8332
  - atr_ratio: 0.7273
  - volume_x_structure: 0.6417
  - rsi_signal: 0.2539
  - rsi_x_structure: 0.1848
  - market_structure_bos: 0.1412
  - fibonacci_distance: 0.0783
  - liquidity_x_structure: 0.0000

### ablation_liquidity_tree
- Model: tree
- Features: ['liquidity']
- Train: 158, Test: 318
- DA: 0.6384, BA: 0.4946
- F1: 0.7726, Brier: 0.2407
- Sharpe: 0.3230
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_sweep: 1.0000

### ablation_market_structure_tree
- Model: tree
- Features: ['market_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2398
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - market_structure_bos: 1.0000

### ablation_rsi_tree
- Model: tree
- Features: ['rsi']
- Train: 161, Test: 322
- DA: 0.6449, BA: 0.5000
- F1: 0.7803, Brier: 0.2400
- Sharpe: 0.3252
- Negative Control DA: 0.4928
- Feature importances:
  - rsi_signal: 1.0000

### ablation_momentum_tree
- Model: tree
- Features: ['momentum']
- Train: 161, Test: 322
- DA: 0.5109, BA: 0.4994
- F1: 0.6215, Brier: 0.2712
- Sharpe: 0.2026
- Negative Control DA: 0.4928
- Feature importances:
  - momentum_14: 1.0000

### ablation_volatility_tree
- Model: tree
- Features: ['volatility']
- Train: 149, Test: 299
- DA: 0.5791, BA: 0.4824
- F1: 0.7113, Brier: 0.2730
- Sharpe: 0.2460
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 1.0000

### ablation_volume_tree
- Model: tree
- Features: ['volume']
- Train: 159, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2406
- Sharpe: 0.3289
- Negative Control DA: 0.4927
- Feature importances:
  - volume_divergence: 1.0000

### ablation_vwap_tree
- Model: tree
- Features: ['vwap']
- Train: 159, Test: 318
- DA: 0.5063, BA: 0.4606
- F1: 0.6464, Brier: 0.2816
- Sharpe: 0.2019
- Negative Control DA: 0.4927
- Feature importances:
  - vwap_deviation: 1.0000

### ablation_fibonacci_tree
- Model: tree
- Features: ['fibonacci']
- Train: 159, Test: 318
- DA: 0.5975, BA: 0.4835
- F1: 0.7394, Brier: 0.2667
- Sharpe: 0.2843
- Negative Control DA: 0.4927
- Feature importances:
  - fibonacci_distance: 1.0000

### ablation_liquidity_x_structure_tree
- Model: tree
- Features: ['liquidity_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2403
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_tree
- Model: tree
- Features: ['rsi_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2417
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - rsi_x_structure: 1.0000

### ablation_momentum_x_volatility_tree
- Model: tree
- Features: ['momentum_x_volatility']
- Train: 149, Test: 299
- DA: 0.5960, BA: 0.4764
- F1: 0.7339, Brier: 0.2586
- Sharpe: 0.2580
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 1.0000

### ablation_volume_x_structure_tree
- Model: tree
- Features: ['volume_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2403
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - volume_x_structure: 0.0000

### ablation_liquidity_x_volatility_tree
- Model: tree
- Features: ['liquidity_x_volatility']
- Train: 149, Test: 299
- DA: 0.6195, BA: 0.5062
- F1: 0.7563, Brier: 0.2497
- Sharpe: 0.2824
- Negative Control DA: 0.4911
- Feature importances:
  - liquidity_x_volatility: 1.0000

### ablation_combined_tree
- Model: tree
- Features: ['combined']
- Train: 149, Test: 299
- DA: 0.5758, BA: 0.4745
- F1: 0.7213, Brier: 0.2679
- Sharpe: 0.2369
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 0.4921
  - rsi_x_structure: 0.2600
  - volume_divergence: 0.1955
  - fibonacci_distance: 0.0524
  - market_structure_bos: 0.0000
  - momentum_x_volatility: 0.0000
  - volume_x_structure: 0.0000
  - liquidity_sweep: 0.0000
  - momentum_14: 0.0000
  - vwap_deviation: 0.0000
  - liquidity_x_structure: 0.0000
  - rsi_signal: 0.0000
  - liquidity_x_volatility: 0.0000

### ablation_liquidity_ensemble
- Model: ensemble
- Features: ['liquidity']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2437
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_sweep: 1.0000

### ablation_market_structure_ensemble
- Model: ensemble
- Features: ['market_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2433
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - market_structure_bos: 1.0000

### ablation_rsi_ensemble
- Model: ensemble
- Features: ['rsi']
- Train: 161, Test: 322
- DA: 0.6449, BA: 0.5000
- F1: 0.7803, Brier: 0.2420
- Sharpe: 0.3252
- Negative Control DA: 0.4928
- Feature importances:
  - rsi_signal: 1.0000

### ablation_momentum_ensemble
- Model: ensemble
- Features: ['momentum']
- Train: 161, Test: 322
- DA: 0.5327, BA: 0.4748
- F1: 0.6759, Brier: 0.2529
- Sharpe: 0.2179
- Negative Control DA: 0.4928
- Feature importances:
  - momentum_14: 1.0000

### ablation_volatility_ensemble
- Model: ensemble
- Features: ['volatility']
- Train: 149, Test: 299
- DA: 0.5724, BA: 0.4747
- F1: 0.7104, Brier: 0.2673
- Sharpe: 0.2309
- Negative Control DA: 0.4911
- Feature importances:
  - atr_ratio: 1.0000

### ablation_volume_ensemble
- Model: ensemble
- Features: ['volume']
- Train: 159, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2398
- Sharpe: 0.3289
- Negative Control DA: 0.4927
- Feature importances:
  - volume_divergence: 1.0000

### ablation_vwap_ensemble
- Model: ensemble
- Features: ['vwap']
- Train: 159, Test: 318
- DA: 0.5283, BA: 0.4844
- F1: 0.6657, Brier: 0.2567
- Sharpe: 0.2276
- Negative Control DA: 0.4927
- Feature importances:
  - vwap_deviation: 1.0000

### ablation_fibonacci_ensemble
- Model: ensemble
- Features: ['fibonacci']
- Train: 159, Test: 318
- DA: 0.5881, BA: 0.4953
- F1: 0.7330, Brier: 0.2510
- Sharpe: 0.2794
- Negative Control DA: 0.4927
- Feature importances:
  - fibonacci_distance: 1.0000

### ablation_liquidity_x_structure_ensemble
- Model: ensemble
- Features: ['liquidity_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2434
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - liquidity_x_structure: 0.0000

### ablation_rsi_x_structure_ensemble
- Model: ensemble
- Features: ['rsi_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2450
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - rsi_x_structure: 1.0000

### ablation_momentum_x_volatility_ensemble
- Model: ensemble
- Features: ['momentum_x_volatility']
- Train: 149, Test: 299
- DA: 0.5690, BA: 0.4707
- F1: 0.7159, Brier: 0.2570
- Sharpe: 0.2328
- Negative Control DA: 0.4911
- Feature importances:
  - momentum_x_volatility: 1.0000

### ablation_volume_x_structure_ensemble
- Model: ensemble
- Features: ['volume_x_structure']
- Train: 158, Test: 318
- DA: 0.6447, BA: 0.5000
- F1: 0.7793, Brier: 0.2434
- Sharpe: 0.3289
- Negative Control DA: 0.4937
- Feature importances:
  - volume_x_structure: 0.0000

### ablation_liquidity_x_volatility_ensemble
- Model: ensemble
- Features: ['liquidity_x_volatility']
- Train: 149, Test: 299
- DA: 0.6094, BA: 0.4976
- F1: 0.7497, Brier: 0.2442
- Sharpe: 0.2725
- Negative Control DA: 0.4911
- Feature importances:
  - liquidity_x_volatility: 1.0000

### ablation_combined_ensemble
- Model: ensemble
- Features: ['combined']
- Train: 149, Test: 299
- DA: 0.5657, BA: 0.4788
- F1: 0.7116, Brier: 0.2570
- Sharpe: 0.2298
- Negative Control DA: 0.4911
- Feature importances:
  - fibonacci_distance: 0.1902
  - vwap_deviation: 0.1889
  - atr_ratio: 0.1352
  - momentum_x_volatility: 0.1246
  - rsi_x_structure: 0.1029
  - liquidity_x_volatility: 0.0687
  - liquidity_sweep: 0.0662
  - volume_divergence: 0.0642
  - momentum_14: 0.0591
  - market_structure_bos: 0.0000
  - volume_x_structure: 0.0000
  - liquidity_x_structure: 0.0000
  - rsi_signal: 0.0000


## 5. Baseline Comparisons

Baseline = buy-and-hold (always long). DA baseline ~0.5 for balanced markets.


## 6. Out-of-Sample Results

All results are walk-forward out-of-sample. 3-fold temporal validation.


## 7. Transaction-Cost Sensitivity

All results include 10 bps transaction cost.


## 8. Regime Analysis

Regime definitions: high_volatility (ATR ratio > 1.2), low_volatility (< 0.8), trending (|momentum| > 2%), ranging (< 1%).


## 9. Negative Controls

- ablation_liquidity_logistic: NC DA = 0.4965
- ablation_market_structure_logistic: NC DA = 0.4965
- ablation_rsi_logistic: NC DA = 0.4958
- ablation_momentum_logistic: NC DA = 0.4958
- ablation_volatility_logistic: NC DA = 0.4978
- ablation_volume_logistic: NC DA = 0.4972
- ablation_vwap_logistic: NC DA = 0.4972
- ablation_fibonacci_logistic: NC DA = 0.4972
- ablation_liquidity_x_structure_logistic: NC DA = 0.4965
- ablation_rsi_x_structure_logistic: NC DA = 0.4965
- ablation_momentum_x_volatility_logistic: NC DA = 0.4978
- ablation_volume_x_structure_logistic: NC DA = 0.4965
- ablation_liquidity_x_volatility_logistic: NC DA = 0.4978
- ablation_combined_logistic: NC DA = 0.4978
- ablation_liquidity_tree: NC DA = 0.4965
- ablation_market_structure_tree: NC DA = 0.4965
- ablation_rsi_tree: NC DA = 0.4958
- ablation_momentum_tree: NC DA = 0.4958
- ablation_volatility_tree: NC DA = 0.4978
- ablation_volume_tree: NC DA = 0.4972
- ablation_vwap_tree: NC DA = 0.4972
- ablation_fibonacci_tree: NC DA = 0.4972
- ablation_liquidity_x_structure_tree: NC DA = 0.4965
- ablation_rsi_x_structure_tree: NC DA = 0.4965
- ablation_momentum_x_volatility_tree: NC DA = 0.4978
- ablation_volume_x_structure_tree: NC DA = 0.4965
- ablation_liquidity_x_volatility_tree: NC DA = 0.4978
- ablation_combined_tree: NC DA = 0.4978
- ablation_liquidity_ensemble: NC DA = 0.4965
- ablation_market_structure_ensemble: NC DA = 0.4965
- ablation_rsi_ensemble: NC DA = 0.4958
- ablation_momentum_ensemble: NC DA = 0.4958
- ablation_volatility_ensemble: NC DA = 0.4978
- ablation_volume_ensemble: NC DA = 0.4972
- ablation_vwap_ensemble: NC DA = 0.4972
- ablation_fibonacci_ensemble: NC DA = 0.4972
- ablation_liquidity_x_structure_ensemble: NC DA = 0.4965
- ablation_rsi_x_structure_ensemble: NC DA = 0.4965
- ablation_momentum_x_volatility_ensemble: NC DA = 0.4978
- ablation_volume_x_structure_ensemble: NC DA = 0.4965
- ablation_liquidity_x_volatility_ensemble: NC DA = 0.4978
- ablation_combined_ensemble: NC DA = 0.4978
- ablation_liquidity_logistic: NC DA = 0.4937
- ablation_market_structure_logistic: NC DA = 0.4937
- ablation_rsi_logistic: NC DA = 0.4928
- ablation_momentum_logistic: NC DA = 0.4928
- ablation_volatility_logistic: NC DA = 0.4911
- ablation_volume_logistic: NC DA = 0.4927
- ablation_vwap_logistic: NC DA = 0.4927
- ablation_fibonacci_logistic: NC DA = 0.4927
- ablation_liquidity_x_structure_logistic: NC DA = 0.4937
- ablation_rsi_x_structure_logistic: NC DA = 0.4937
- ablation_momentum_x_volatility_logistic: NC DA = 0.4911
- ablation_volume_x_structure_logistic: NC DA = 0.4937
- ablation_liquidity_x_volatility_logistic: NC DA = 0.4911
- ablation_combined_logistic: NC DA = 0.4911
- ablation_liquidity_tree: NC DA = 0.4937
- ablation_market_structure_tree: NC DA = 0.4937
- ablation_rsi_tree: NC DA = 0.4928
- ablation_momentum_tree: NC DA = 0.4928
- ablation_volatility_tree: NC DA = 0.4911
- ablation_volume_tree: NC DA = 0.4927
- ablation_vwap_tree: NC DA = 0.4927
- ablation_fibonacci_tree: NC DA = 0.4927
- ablation_liquidity_x_structure_tree: NC DA = 0.4937
- ablation_rsi_x_structure_tree: NC DA = 0.4937
- ablation_momentum_x_volatility_tree: NC DA = 0.4911
- ablation_volume_x_structure_tree: NC DA = 0.4937
- ablation_liquidity_x_volatility_tree: NC DA = 0.4911
- ablation_combined_tree: NC DA = 0.4911
- ablation_liquidity_ensemble: NC DA = 0.4937
- ablation_market_structure_ensemble: NC DA = 0.4937
- ablation_rsi_ensemble: NC DA = 0.4928
- ablation_momentum_ensemble: NC DA = 0.4928
- ablation_volatility_ensemble: NC DA = 0.4911
- ablation_volume_ensemble: NC DA = 0.4927
- ablation_vwap_ensemble: NC DA = 0.4927
- ablation_fibonacci_ensemble: NC DA = 0.4927
- ablation_liquidity_x_structure_ensemble: NC DA = 0.4937
- ablation_rsi_x_structure_ensemble: NC DA = 0.4937
- ablation_momentum_x_volatility_ensemble: NC DA = 0.4911
- ablation_volume_x_structure_ensemble: NC DA = 0.4937
- ablation_liquidity_x_volatility_ensemble: NC DA = 0.4911
- ablation_combined_ensemble: NC DA = 0.4911
- ablation_liquidity_logistic: NC DA = 0.4937
- ablation_market_structure_logistic: NC DA = 0.4937
- ablation_rsi_logistic: NC DA = 0.4928
- ablation_momentum_logistic: NC DA = 0.4928
- ablation_volatility_logistic: NC DA = 0.4911
- ablation_volume_logistic: NC DA = 0.4927
- ablation_vwap_logistic: NC DA = 0.4927
- ablation_fibonacci_logistic: NC DA = 0.4927
- ablation_liquidity_x_structure_logistic: NC DA = 0.4937
- ablation_rsi_x_structure_logistic: NC DA = 0.4937
- ablation_momentum_x_volatility_logistic: NC DA = 0.4911
- ablation_volume_x_structure_logistic: NC DA = 0.4937
- ablation_liquidity_x_volatility_logistic: NC DA = 0.4911
- ablation_combined_logistic: NC DA = 0.4911
- ablation_liquidity_tree: NC DA = 0.4937
- ablation_market_structure_tree: NC DA = 0.4937
- ablation_rsi_tree: NC DA = 0.4928
- ablation_momentum_tree: NC DA = 0.4928
- ablation_volatility_tree: NC DA = 0.4911
- ablation_volume_tree: NC DA = 0.4927
- ablation_vwap_tree: NC DA = 0.4927
- ablation_fibonacci_tree: NC DA = 0.4927
- ablation_liquidity_x_structure_tree: NC DA = 0.4937
- ablation_rsi_x_structure_tree: NC DA = 0.4937
- ablation_momentum_x_volatility_tree: NC DA = 0.4911
- ablation_volume_x_structure_tree: NC DA = 0.4937
- ablation_liquidity_x_volatility_tree: NC DA = 0.4911
- ablation_combined_tree: NC DA = 0.4911
- ablation_liquidity_ensemble: NC DA = 0.4937
- ablation_market_structure_ensemble: NC DA = 0.4937
- ablation_rsi_ensemble: NC DA = 0.4928
- ablation_momentum_ensemble: NC DA = 0.4928
- ablation_volatility_ensemble: NC DA = 0.4911
- ablation_volume_ensemble: NC DA = 0.4927
- ablation_vwap_ensemble: NC DA = 0.4927
- ablation_fibonacci_ensemble: NC DA = 0.4927
- ablation_liquidity_x_structure_ensemble: NC DA = 0.4937
- ablation_rsi_x_structure_ensemble: NC DA = 0.4937
- ablation_momentum_x_volatility_ensemble: NC DA = 0.4911
- ablation_volume_x_structure_ensemble: NC DA = 0.4937
- ablation_liquidity_x_volatility_ensemble: NC DA = 0.4911
- ablation_combined_ensemble: NC DA = 0.4911

## 10. Leakage Audit

Chronological walk-forward validation used throughout. No random splits. No future information leakage.


## 11. Calibration Results

- ablation_liquidity_logistic: calibration error = 0.0702
- ablation_market_structure_logistic: calibration error = 0.0796
- ablation_rsi_logistic: calibration error = 0.0700
- ablation_momentum_logistic: calibration error = 0.0732
- ablation_volatility_logistic: calibration error = 0.0751
- ablation_volume_logistic: calibration error = 0.0945
- ablation_vwap_logistic: calibration error = 0.0847
- ablation_fibonacci_logistic: calibration error = 0.0854
- ablation_liquidity_x_structure_logistic: calibration error = 0.0695
- ablation_rsi_x_structure_logistic: calibration error = 0.0764
- ablation_momentum_x_volatility_logistic: calibration error = 0.0684
- ablation_volume_x_structure_logistic: calibration error = 0.0798
- ablation_liquidity_x_volatility_logistic: calibration error = 0.0546
- ablation_combined_logistic: calibration error = 0.1521
- ablation_liquidity_tree: calibration error = 0.0787
- ablation_market_structure_tree: calibration error = 0.0718
- ablation_rsi_tree: calibration error = 0.0732
- ablation_momentum_tree: calibration error = 0.1481
- ablation_volatility_tree: calibration error = 0.1616
- ablation_volume_tree: calibration error = 0.0806
- ablation_vwap_tree: calibration error = 0.1405
- ablation_fibonacci_tree: calibration error = 0.1415
- ablation_liquidity_x_structure_tree: calibration error = 0.0657
- ablation_rsi_x_structure_tree: calibration error = 0.0788
- ablation_momentum_x_volatility_tree: calibration error = 0.1085
- ablation_volume_x_structure_tree: calibration error = 0.0662
- ablation_liquidity_x_volatility_tree: calibration error = 0.0709
- ablation_combined_tree: calibration error = 0.2055
- ablation_liquidity_ensemble: calibration error = 0.0831
- ablation_market_structure_ensemble: calibration error = 0.0718
- ablation_rsi_ensemble: calibration error = 0.0777
- ablation_momentum_ensemble: calibration error = 0.1344
- ablation_volatility_ensemble: calibration error = 0.1571
- ablation_volume_ensemble: calibration error = 0.1040
- ablation_vwap_ensemble: calibration error = 0.1212
- ablation_fibonacci_ensemble: calibration error = 0.1401
- ablation_liquidity_x_structure_ensemble: calibration error = 0.0681
- ablation_rsi_x_structure_ensemble: calibration error = 0.0822
- ablation_momentum_x_volatility_ensemble: calibration error = 0.0899
- ablation_volume_x_structure_ensemble: calibration error = 0.0679
- ablation_liquidity_x_volatility_ensemble: calibration error = 0.0774
- ablation_combined_ensemble: calibration error = 0.1644
- ablation_liquidity_logistic: calibration error = 0.1508
- ablation_market_structure_logistic: calibration error = 0.1602
- ablation_rsi_logistic: calibration error = 0.1804
- ablation_momentum_logistic: calibration error = 0.1894
- ablation_volatility_logistic: calibration error = 0.1858
- ablation_volume_logistic: calibration error = 0.1597
- ablation_vwap_logistic: calibration error = 0.1958
- ablation_fibonacci_logistic: calibration error = 0.1884
- ablation_liquidity_x_structure_logistic: calibration error = 0.1530
- ablation_rsi_x_structure_logistic: calibration error = 0.1776
- ablation_momentum_x_volatility_logistic: calibration error = 0.1806
- ablation_volume_x_structure_logistic: calibration error = 0.1592
- ablation_liquidity_x_volatility_logistic: calibration error = 0.1678
- ablation_combined_logistic: calibration error = 0.2728
- ablation_liquidity_tree: calibration error = 0.1386
- ablation_market_structure_tree: calibration error = 0.1483
- ablation_rsi_tree: calibration error = 0.1235
- ablation_momentum_tree: calibration error = 0.2091
- ablation_volatility_tree: calibration error = 0.1829
- ablation_volume_tree: calibration error = 0.1743
- ablation_vwap_tree: calibration error = 0.1752
- ablation_fibonacci_tree: calibration error = 0.2048
- ablation_liquidity_x_structure_tree: calibration error = 0.1438
- ablation_rsi_x_structure_tree: calibration error = 0.1468
- ablation_momentum_x_volatility_tree: calibration error = 0.1955
- ablation_volume_x_structure_tree: calibration error = 0.1438
- ablation_liquidity_x_volatility_tree: calibration error = 0.1689
- ablation_combined_tree: calibration error = 0.2801
- ablation_liquidity_ensemble: calibration error = 0.1468
- ablation_market_structure_ensemble: calibration error = 0.1562
- ablation_rsi_ensemble: calibration error = 0.1265
- ablation_momentum_ensemble: calibration error = 0.1821
- ablation_volatility_ensemble: calibration error = 0.1827
- ablation_volume_ensemble: calibration error = 0.1489
- ablation_vwap_ensemble: calibration error = 0.2054
- ablation_fibonacci_ensemble: calibration error = 0.1709
- ablation_liquidity_x_structure_ensemble: calibration error = 0.1501
- ablation_rsi_x_structure_ensemble: calibration error = 0.1535
- ablation_momentum_x_volatility_ensemble: calibration error = 0.1882
- ablation_volume_x_structure_ensemble: calibration error = 0.1501
- ablation_liquidity_x_volatility_ensemble: calibration error = 0.1734
- ablation_combined_ensemble: calibration error = 0.1914
- ablation_liquidity_logistic: calibration error = 0.1390
- ablation_market_structure_logistic: calibration error = 0.1286
- ablation_rsi_logistic: calibration error = 0.1964
- ablation_momentum_logistic: calibration error = 0.1778
- ablation_volatility_logistic: calibration error = 0.1220
- ablation_volume_logistic: calibration error = 0.1583
- ablation_vwap_logistic: calibration error = 0.1859
- ablation_fibonacci_logistic: calibration error = 0.1748
- ablation_liquidity_x_structure_logistic: calibration error = 0.1193
- ablation_rsi_x_structure_logistic: calibration error = 0.1947
- ablation_momentum_x_volatility_logistic: calibration error = 0.1412
- ablation_volume_x_structure_logistic: calibration error = 0.1246
- ablation_liquidity_x_volatility_logistic: calibration error = 0.1283
- ablation_combined_logistic: calibration error = 0.2445
- ablation_liquidity_tree: calibration error = 0.1191
- ablation_market_structure_tree: calibration error = 0.1151
- ablation_rsi_tree: calibration error = 0.1104
- ablation_momentum_tree: calibration error = 0.2266
- ablation_volatility_tree: calibration error = 0.1855
- ablation_volume_tree: calibration error = 0.1113
- ablation_vwap_tree: calibration error = 0.2218
- ablation_fibonacci_tree: calibration error = 0.1975
- ablation_liquidity_x_structure_tree: calibration error = 0.1130
- ablation_rsi_x_structure_tree: calibration error = 0.1180
- ablation_momentum_x_volatility_tree: calibration error = 0.1989
- ablation_volume_x_structure_tree: calibration error = 0.1130
- ablation_liquidity_x_volatility_tree: calibration error = 0.1335
- ablation_combined_tree: calibration error = 0.1823
- ablation_liquidity_ensemble: calibration error = 0.1242
- ablation_market_structure_ensemble: calibration error = 0.1210
- ablation_rsi_ensemble: calibration error = 0.1147
- ablation_momentum_ensemble: calibration error = 0.1563
- ablation_volatility_ensemble: calibration error = 0.1773
- ablation_volume_ensemble: calibration error = 0.1192
- ablation_vwap_ensemble: calibration error = 0.1616
- ablation_fibonacci_ensemble: calibration error = 0.1634
- ablation_liquidity_x_structure_ensemble: calibration error = 0.1189
- ablation_rsi_x_structure_ensemble: calibration error = 0.1235
- ablation_momentum_x_volatility_ensemble: calibration error = 0.1747
- ablation_volume_x_structure_ensemble: calibration error = 0.1189
- ablation_liquidity_x_volatility_ensemble: calibration error = 0.1252
- ablation_combined_ensemble: calibration error = 0.1901

## 12. Strongest Interaction Candidates

- QQQ/liquidity_x_structure: DA=0.6447, Sharpe=0.3289
- QQQ/volume_x_structure: DA=0.6447, Sharpe=0.3289
- SPY/liquidity_x_structure: DA=0.6415, Sharpe=0.3255
- SPY/volume_x_structure: DA=0.6352, Sharpe=0.3191
- SPY/momentum_x_volatility: DA=0.6296, Sharpe=0.2974

## 13. Failed Interactions

- BTC-USD/liquidity_x_volatility: DA=0.4933, Sharpe=-0.0145
- BTC-USD/liquidity_x_structure: DA=0.4872, Sharpe=-0.0142
- BTC-USD/volume_x_structure: DA=0.4872, Sharpe=-0.0141

## 14. Limitations

1. Real market data but limited to 2 years daily bars
2. Simple models only (logistic regression, decision tree, bagging)
3. No feature engineering beyond pre-registered set
4. No hyperparameter tuning
5. Transaction costs flat bps model
6. Regime detection is ATR-based, not regime-optimal
7. No intraday data for VWAP accuracy
8. Results apply to tested definition, dataset, horizon and regime

## 15. Recommendation for Phase 8B

**Do NOT begin Phase 8B automatically.**

Review findings before proceeding to any next phase.