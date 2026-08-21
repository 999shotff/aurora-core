from __future__ import annotations

from aurora.features.rolling import ema, rolling_mean, rolling_std


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
