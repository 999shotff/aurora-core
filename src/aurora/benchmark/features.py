"""Feature implementations for each methodology family.

Each function takes raw OHLCV data and returns a list of feature values
aligned with the input (None for warmup period). All features are
deterministic given the input data.
"""

from __future__ import annotations


def fibonacci_retracement_level(
    closes: list[float],
    swing_window: int = 20,
    ratio: float = 0.618,
) -> list[float | None]:
    n = len(closes)
    result: list[float | None] = []
    for i in range(n):
        if i < swing_window:
            result.append(None)
            continue
        window = closes[i - swing_window + 1 : i + 1]
        high = max(window)
        low = min(window)
        rng = high - low
        if rng == 0:
            result.append(None)
        else:
            level = low + ratio * rng
            result.append((closes[i] - level) / closes[i] if closes[i] != 0 else 0.0)
    return result


def fibonacci_extension_level(
    closes: list[float],
    swing_window: int = 20,
    ratio: float = 1.618,
) -> list[float | None]:
    n = len(closes)
    result: list[float | None] = []
    for i in range(n):
        if i < swing_window:
            result.append(None)
            continue
        window = closes[i - swing_window + 1 : i + 1]
        high = max(window)
        low = min(window)
        rng = high - low
        if rng == 0:
            result.append(None)
        else:
            level = high + ratio * rng
            result.append((closes[i] - level) / closes[i] if closes[i] != 0 else 0.0)
    return result


def atr_ratio(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    short_window: int = 14,
    long_window: int = 50,
) -> list[float | None]:
    n = len(closes)
    tr = [0.0] * n
    for i in range(n):
        if i == 0:
            tr[i] = highs[i] - lows[i]
        else:
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
    short_atr: list[float | None] = [None] * n
    long_atr: list[float | None] = [None] * n
    for i in range(n):
        if i + 1 >= short_window:
            start = i + 1 - short_window
            short_atr[i] = sum(tr[start : i + 1]) / short_window
        if i + 1 >= long_window:
            start = i + 1 - long_window
            long_atr[i] = sum(tr[start : i + 1]) / long_window
    result: list[float | None] = []
    for i in range(n):
        s = short_atr[i]
        l = long_atr[i]
        if s is None or l is None or l == 0:
            result.append(None)
        else:
            result.append(s / l)
    return result


def liquidity_sweep(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    lookback: int = 20,
) -> list[int | None]:
    n = len(closes)
    result: list[int | None] = []
    for i in range(n):
        if i < lookback + 1:
            result.append(None)
            continue
        prev_high = max(highs[i - lookback : i])
        prev_low = min(lows[i - lookback : i])
        swept_high = highs[i] > prev_high and closes[i] < prev_high
        swept_low = lows[i] < prev_low and closes[i] > prev_low
        if swept_high:
            result.append(-1)
        elif swept_low:
            result.append(1)
        else:
            result.append(0)
    return result


def volume_price_divergence(
    closes: list[float],
    volumes: list[float],
    window: int = 20,
) -> list[float | None]:
    n = len(closes)
    result: list[float | None] = []
    for i in range(n):
        if i < window:
            result.append(None)
            continue
        price_slice = closes[i - window + 1 : i + 1]
        vol_slice = volumes[i - window + 1 : i + 1]
        price_slope = _linear_slope(price_slice)
        vol_slope = _linear_slope(vol_slice)
        if price_slope > 0 and vol_slope < 0:
            result.append(-1.0)
        elif price_slope < 0 and vol_slope > 0:
            result.append(1.0)
        else:
            result.append(0.0)
    return result


def vwap_deviation(
    closes: list[float],
    volumes: list[float],
    window: int = 20,
) -> list[float | None]:
    n = len(closes)
    result: list[float | None] = []
    for i in range(n):
        if i < window:
            result.append(None)
            continue
        start = i - window + 1
        pv_sum = sum(closes[j] * volumes[j] for j in range(start, i + 1))
        v_sum = sum(volumes[j] for j in range(start, i + 1))
        if v_sum == 0:
            result.append(None)
        else:
            vwap = pv_sum / v_sum
            result.append((closes[i] - vwap) / vwap if vwap != 0 else 0.0)
    return result


def market_structure_break(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    lookback: int = 20,
) -> list[int | None]:
    n = len(closes)
    result: list[int | None] = []
    prev_direction = 0
    for i in range(n):
        if i < lookback + 1:
            result.append(None)
            continue
        swing_high = max(highs[i - lookback : i])
        swing_low = min(lows[i - lookback : i])
        if closes[i] > swing_high:
            direction = 1
        elif closes[i] < swing_low:
            direction = -1
        else:
            direction = 0
        if direction != 0 and direction != prev_direction and prev_direction != 0:
            result.append(direction)
        else:
            result.append(0)
        if direction != 0:
            prev_direction = direction
    return result


def momentum_signal(
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    n = len(closes)
    result: list[float | None] = []
    for i in range(n):
        if i < period:
            result.append(None)
        else:
            result.append((closes[i] - closes[i - period]) / closes[i - period] if closes[i - period] != 0 else 0.0)
    return result


def sma_crossover(
    closes: list[float],
    fast_period: int = 10,
    slow_period: int = 50,
) -> list[int | None]:
    n = len(closes)
    result: list[int | None] = []
    prev_fast: float | None = None
    prev_slow: float | None = None
    for i in range(n):
        if i + 1 < slow_period:
            result.append(None)
            prev_fast = None
            prev_slow = None
            continue
        fast_start = i + 1 - fast_period
        fast_val = sum(closes[fast_start : i + 1]) / fast_period
        slow_start = i + 1 - slow_period
        slow_val = sum(closes[slow_start : i + 1]) / slow_period
        if prev_fast is not None and prev_slow is not None:
            if prev_fast <= prev_slow and fast_val > slow_val:
                result.append(1)
            elif prev_fast >= prev_slow and fast_val < slow_val:
                result.append(-1)
            else:
                result.append(0)
        else:
            result.append(0)
        prev_fast = fast_val
        prev_slow = slow_val
    return result


def rsi_signal(
    closes: list[float],
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[int | None]:
    n = len(closes)
    if n < 2:
        return [None] * n
    changes = [closes[i] - closes[i - 1] for i in range(1, n)]
    rsi_vals: list[float | None] = [None]
    avg_gain: float | None = None
    avg_loss: float | None = None
    for i, change in enumerate(changes):
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        if avg_gain is None:
            if i + 1 < period:
                rsi_vals.append(None)
                continue
            window_changes = changes[:period]
            avg_gain = sum(max(c, 0.0) for c in window_changes) / period
            avg_loss = sum(max(-c, 0.0) for c in window_changes) / period
        else:
            assert avg_loss is not None
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0.0:
            rsi_vals.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))
    result: list[int | None] = []
    for rsi_val in rsi_vals:
        if rsi_val is None:
            result.append(None)
        elif rsi_val < oversold:
            result.append(1)
        elif rsi_val > overbought:
            result.append(-1)
        else:
            result.append(0)
    return result


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0
