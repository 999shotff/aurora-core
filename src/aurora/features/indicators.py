"""Technical indicators for AURORA CORE.

Deterministic, pure-function indicators. No future-data access.
All indicators satisfy: indicator(T) depends only on data at or before T.

Indicators are descriptive analytical features and do not constitute
trading signals. NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from aurora.features.rolling import ema, rolling_max, rolling_mean, rolling_min, rolling_std

# ============================================================
# Existing indicators (preserved)
# ============================================================


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    window: int = 14,
) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    n = len(highs)
    if not (n == len(lows) == len(closes)):
        raise ValueError("highs, lows, closes must have same length")
    if n < 2:
        return [None] * n

    true_ranges: list[float] = []
    for i in range(n):
        if i == 0:
            true_ranges.append(highs[i] - lows[i])
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

    result: list[float | None] = []
    for i in range(n):
        if i + 1 < window:
            result.append(None)
        else:
            start = i + 1 - window
            result.append(sum(true_ranges[start : i + 1]) / window)
    return result


def rsi(closes: list[float], window: int = 14) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    n = len(closes)
    if n < 2:
        return [None] * n

    changes = [closes[i] - closes[i - 1] for i in range(1, n)]

    result: list[float | None] = [None]

    avg_gain: float | None = None
    avg_loss: float | None = None

    for i, change in enumerate(changes):
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if avg_gain is None:
            if i + 1 < window:
                result.append(None)
                continue
            window_changes = changes[:window]
            avg_gain = sum(max(c, 0.0) for c in window_changes) / window
            avg_loss = sum(max(-c, 0.0) for c in window_changes) / window
        else:
            assert avg_loss is not None
            avg_gain = (avg_gain * (window - 1) + gain) / window
            avg_loss = (avg_loss * (window - 1) + loss) / window

        if avg_loss == 0.0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))

    return result


def ema_indicator(values: list[float], window: int) -> list[float | None]:
    return ema(values, window)


def sma_indicator(values: list[float], window: int) -> list[float | None]:
    return rolling_mean(values, window)


def momentum_indicator(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i < period:
            result.append(None)
        else:
            result.append(values[i] - values[i - period])
    return result


def volatility(
    closes: list[float], window: int = 20
) -> list[float | None]:
    return rolling_std(closes, window)


def bollinger_bands(
    closes: list[float], period: int = 20, num_std: float = 2.0
) -> dict[str, list[float | None]]:
    """Bollinger Bands: upper, middle, lower."""
    middle = rolling_mean(closes, period)
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(closes)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            start = i + 1 - period
            window = closes[start : i + 1]
            mean = middle[i]
            assert mean is not None
            std = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
            upper.append(mean + num_std * std)
            lower.append(mean - num_std * std)
    return {"upper": upper, "middle": middle, "lower": lower}


# ============================================================
# New indicators: Momentum
# ============================================================


def stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    k_period: int = 14,
    d_period: int = 3,
    smooth_k: int = 3,
) -> dict[str, list[float | None]]:
    """Stochastic Oscillator: %K and %D.

    %K (raw) = (Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %K (smoothed) = SMA(%K_raw, smooth_k)
    %D = SMA(%K_smoothed, d_period)

    All values use only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows)):
        raise ValueError("highs, lows, closes must have same length")
    if k_period < 1 or d_period < 1 or smooth_k < 1:
        raise ValueError("periods must be >= 1")

    k_raw: list[float | None] = []
    for i in range(n):
        if i + 1 < k_period:
            k_raw.append(None)
        else:
            start = i + 1 - k_period
            hh = max(highs[start : i + 1])
            ll = min(lows[start : i + 1])
            if hh == ll:
                k_raw.append(50.0)
            else:
                k_raw.append((closes[i] - ll) / (hh - ll) * 100.0)

    k_valid = [v for v in k_raw if v is not None]
    k_smoothed_raw = rolling_mean(k_valid, smooth_k) if k_valid else []

    k_smoothed: list[float | None] = []
    ki = 0
    for v in k_raw:
        if v is None:
            k_smoothed.append(None)
        else:
            if ki < len(k_smoothed_raw):
                k_smoothed.append(k_smoothed_raw[ki])
            else:
                k_smoothed.append(None)
            ki += 1

    k_valid_smoothed = [v for v in k_smoothed if v is not None]
    d_raw = rolling_mean(k_valid_smoothed, d_period) if k_valid_smoothed else []

    d: list[float | None] = []
    di = 0
    for v in k_smoothed:
        if v is None:
            d.append(None)
        else:
            if di < len(d_raw):
                d.append(d_raw[di])
            else:
                d.append(None)
            di += 1

    return {"k": k_smoothed, "d": d}


def adx_dmi(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> dict[str, list[float | None]]:
    """ADX / DMI: +DI, -DI, ADX.

    +DI = 100 * EMA(+DM, period) / ATR(period)
    -DI = 100 * EMA(-DM, period) / ATR(period)
    DX = 100 * abs(+DI - -DI) / (+DI + -DI)
    ADX = EMA(DX, period)

    Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows)):
        raise ValueError("highs, lows, closes must have same length")
    if period < 1:
        raise ValueError("period must be >= 1")
    if n < 2:
        return {
            "plus_di": [None] * n,
            "minus_di": [None] * n,
            "adx": [None] * n,
        }

    tr_list: list[float] = []
    plus_dm_list: list[float] = []
    minus_dm_list: list[float] = []

    for i in range(n):
        if i == 0:
            tr_list.append(highs[i] - lows[i])
            plus_dm_list.append(0.0)
            minus_dm_list.append(0.0)
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_list.append(tr)
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm_list.append(up if up > down and up > 0 else 0.0)
            minus_dm_list.append(down if down > up and down > 0 else 0.0)

    atr_vals = ema(tr_list, period)
    plus_dm_ema = ema(plus_dm_list, period)
    minus_dm_ema = ema(minus_dm_list, period)

    plus_di: list[float | None] = []
    minus_di: list[float | None] = []
    dx_list: list[float | None] = []

    for i in range(n):
        a = atr_vals[i]
        pdm = plus_dm_ema[i]
        mdm = minus_dm_ema[i]
        if a is None or a == 0 or pdm is None or mdm is None:
            plus_di.append(None)
            minus_di.append(None)
            dx_list.append(None)
        else:
            pdi = 100.0 * pdm / a
            mdi = 100.0 * mdm / a
            plus_di.append(pdi)
            minus_di.append(mdi)
            denom = pdi + mdi
            if denom == 0:
                dx_list.append(0.0)
            else:
                dx_list.append(100.0 * abs(pdi - mdi) / denom)

    dx_valid = [v for v in dx_list if v is not None]
    adx_raw = ema(dx_valid, period) if dx_valid else []

    adx: list[float | None] = []
    ai = 0
    for v in dx_list:
        if v is None:
            adx.append(None)
        else:
            if ai < len(adx_raw):
                adx.append(adx_raw[ai])
            else:
                adx.append(None)
            ai += 1

    return {"plus_di": plus_di, "minus_di": minus_di, "adx": adx}


def cci(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 20,
) -> list[float | None]:
    """Commodity Channel Index.

    CCI = (Typical Price - SMA(Typical Price)) / (0.015 * Mean Deviation)
    Typical Price = (High + Low + Close) / 3

    Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows)):
        raise ValueError("highs, lows, closes must have same length")
    if period < 1:
        raise ValueError("period must be >= 1")

    tp = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(n)]
    tp_sma = rolling_mean(tp, period)

    result: list[float | None] = []
    for i in range(n):
        if tp_sma[i] is None:
            result.append(None)
            continue
        start = i + 1 - period
        segment = tp[start : i + 1]
        mean_dev = sum(abs(x - tp_sma[i]) for x in segment) / period
        if mean_dev == 0:
            result.append(0.0)
        else:
            result.append((tp[i] - tp_sma[i]) / (0.015 * mean_dev))
    return result


def roc(values: list[float], period: int = 12) -> list[float | None]:
    """Rate of Change.

    ROC = (Value - Value_n_periods_ago) / Value_n_periods_ago * 100

    Uses only data available at or before each timestamp.
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i < period or values[i - period] == 0:
            result.append(None)
        else:
            result.append((values[i] - values[i - period]) / values[i - period] * 100.0)
    return result


def williams_r(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Williams %R.

    %R = (Highest High - Close) / (Highest High - Lowest Low) * -100

    Values range from -100 to 0. Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows)):
        raise ValueError("highs, lows, closes must have same length")
    if period < 1:
        raise ValueError("period must be >= 1")

    result: list[float | None] = []
    for i in range(n):
        if i + 1 < period:
            result.append(None)
        else:
            start = i + 1 - period
            hh = max(highs[start : i + 1])
            ll = min(lows[start : i + 1])
            if hh == ll:
                result.append(-50.0)
            else:
                result.append((hh - closes[i]) / (hh - ll) * -100.0)
    return result


# ============================================================
# New indicators: Volume
# ============================================================


def obv(closes: list[float], volumes: list[float]) -> list[float]:
    """On-Balance Volume.

    OBV += volume if close > prev_close
    OBV -= volume if close < prev_close
    OBV unchanged if close == prev_close

    Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(volumes)):
        raise ValueError("closes and volumes must have same length")
    if n == 0:
        return []

    result: list[float] = [0.0]
    for i in range(1, n):
        prev = result[-1]
        if closes[i] > closes[i - 1]:
            result.append(prev + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(prev - volumes[i])
        else:
            result.append(prev)
    return result


def vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
) -> list[float | None]:
    """Volume-Weighted Average Price (session-based).

    VWAP = cumulative(Typical Price * Volume) / cumulative(Volume)
    Typical Price = (High + Low + Close) / 3

    Reset behavior: VWAP resets at each new session (each bar represents
    one session boundary). This is the standard daily VWAP calculation.

    Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows) == len(volumes)):
        raise ValueError("highs, lows, closes, volumes must have same length")
    if n == 0:
        return []

    result: list[float | None] = []
    cum_tp_vol = 0.0
    cum_vol = 0.0

    for i in range(n):
        tp = (highs[i] + lows[i] + closes[i]) / 3.0
        cum_tp_vol += tp * volumes[i]
        cum_vol += volumes[i]
        if cum_vol == 0:
            result.append(None)
        else:
            result.append(cum_tp_vol / cum_vol)
    return result


def mfi(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Money Flow Index.

    MFI = 100 - 100 / (1 + Money Flow Ratio)
    Money Flow Ratio = Positive Money Flow / Negative Money Flow
    Money Flow = Typical Price * Volume
    Positive Money Flow = sum of Money Flow where TP > prev TP
    Negative Money Flow = sum of Money Flow where TP < prev TP

    Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows) == len(volumes)):
        raise ValueError("highs, lows, closes, volumes must have same length")
    if period < 1:
        raise ValueError("period must be >= 1")

    tp = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(n)]
    mf = [tp[i] * volumes[i] for i in range(n)]

    result: list[float | None] = []
    for i in range(n):
        if i < period:
            result.append(None)
            continue
        start = i + 1 - period
        pos_mf = 0.0
        neg_mf = 0.0
        for j in range(start + 1, i + 1):
            if tp[j] > tp[j - 1]:
                pos_mf += mf[j]
            elif tp[j] < tp[j - 1]:
                neg_mf += mf[j]
        if neg_mf == 0:
            result.append(100.0)
        else:
            mfr = pos_mf / neg_mf
            result.append(100.0 - 100.0 / (1.0 + mfr))
    return result


# ============================================================
# New indicators: Trend
# ============================================================


def ichimoku(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> dict[str, list[float | None]]:
    """Ichimoku Cloud.

    Tenkan-sen: (Highest High (tenkan_period) + Lowest Low (tenkan_period)) / 2
    Kijun-sen: (Highest High (kijun_period) + Lowest Low (kijun_period)) / 2
    Senkou Span A: (Tenkan-sen + Kijun-sen) / 2
    Senkou Span B: (Highest High (senkou_b_period) + Lowest Low (senkou_b_period)) / 2
    Chikou Span: Close (displaced back by kijun_period)

    CRITICAL: Senkou spans are displaced FORWARD by kijun_period on a chart, but
    the values plotted at time T are computed from data at time T - kijun_period.
    Here we return undisplaced values. The chart layer is responsible for displacement.
    Chikou span is displaced BACKWARD (close at time T plotted at T + kijun_period).

    Uses only data available at or before each timestamp.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows)):
        raise ValueError("highs, lows, closes must have same length")

    tenkan = rolling_max(highs, tenkan_period)
    kijun = rolling_max(highs, kijun_period)
    tenkan_min = rolling_min(lows, tenkan_period)
    kijun_min = rolling_min(lows, kijun_period)

    tenkan_sen: list[float | None] = []
    kijun_sen: list[float | None] = []
    for i in range(n):
        if tenkan[i] is not None and tenkan_min[i] is not None:
            tenkan_sen.append((tenkan[i] + tenkan_min[i]) / 2.0)
        else:
            tenkan_sen.append(None)
        if kijun[i] is not None and kijun_min[i] is not None:
            kijun_sen.append((kijun[i] + kijun_min[i]) / 2.0)
        else:
            kijun_sen.append(None)

    senkou_a: list[float | None] = []
    for i in range(n):
        if tenkan_sen[i] is not None and kijun_sen[i] is not None:
            senkou_a.append((tenkan_sen[i] + kijun_sen[i]) / 2.0)
        else:
            senkou_a.append(None)

    senkou_b_max = rolling_max(highs, senkou_b_period)
    senkou_b_min = rolling_min(lows, senkou_b_period)
    senkou_b: list[float | None] = []
    for i in range(n):
        if senkou_b_max[i] is not None and senkou_b_min[i] is not None:
            senkou_b.append((senkou_b_max[i] + senkou_b_min[i]) / 2.0)
        else:
            senkou_b.append(None)

    chikou: list[float | None] = [None] * n
    for i in range(n):
        target = i - kijun_period
        if target >= 0:
            chikou[target] = closes[i]

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }


# ============================================================
# New indicators: Market Levels
# ============================================================


def pivot_points(
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> dict[str, list[float | None]]:
    """Standard Pivot Points (Floor Trader's Pivots).

    Each bar's pivot levels use the PREVIOUS bar's High, Low, Close.
    This prevents any future-data leakage.

    Pivot  = (Prev High + Prev Low + Prev Close) / 3
    R1     = 2 * Pivot - Prev Low
    R2     = Pivot + (Prev High - Prev Low)
    R3     = Prev High + 2 * (Pivot - Prev Low)
    S1     = 2 * Pivot - Prev High
    S2     = Pivot - (Prev High - Prev Low)
    S3     = Prev Low - 2 * (Prev High - Pivot)

    The first bar has no previous bar, so levels are None.
    """
    n = len(closes)
    if not (n == len(highs) == len(lows)):
        raise ValueError("highs, lows, closes must have same length")

    pivot: list[float | None] = [None]
    r1: list[float | None] = [None]
    r2: list[float | None] = [None]
    r3: list[float | None] = [None]
    s1: list[float | None] = [None]
    s2: list[float | None] = [None]
    s3: list[float | None] = [None]

    for i in range(1, n):
        h = highs[i - 1]
        l = lows[i - 1]
        c = closes[i - 1]
        p = (h + l + c) / 3.0
        pivot.append(p)
        r1.append(2.0 * p - l)
        r2.append(p + (h - l))
        r3.append(h + 2.0 * (p - l))
        s1.append(2.0 * p - h)
        s2.append(p - (h - l))
        s3.append(l - 2.0 * (h - p))

    return {"pivot": pivot, "r1": r1, "r2": r2, "r3": r3, "s1": s1, "s2": s2, "s3": s3}


def fibonacci_retracement(
    high: float,
    low: float,
    levels: list[float] | None = None,
) -> dict[float, float]:
    """Deterministic Fibonacci Retracement levels.

    Calculates price levels for standard Fibonacci retracement.

    Args:
        high: Swing high price
        low: Swing low price
        levels: Retracement levels (default: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])

    Returns:
        Dict mapping level to price.

    This is a deterministic calculation, not a predictive signal.
    """
    if levels is None:
        levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    if high < low:
        high, low = low, high
    diff = high - low
    return {level: high - diff * level for level in levels}
