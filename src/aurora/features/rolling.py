from __future__ import annotations


def rolling_mean(values: list[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            result.append(None)
        else:
            start = i + 1 - window
            result.append(sum(values[start : i + 1]) / window)
    return result


def rolling_std(values: list[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            result.append(None)
        else:
            start = i + 1 - window
            segment = values[start : i + 1]
            mean = sum(segment) / window
            variance = sum((x - mean) ** 2 for x in segment) / window
            result.append(variance ** 0.5)
    return result


def rolling_max(values: list[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            result.append(None)
        else:
            start = i + 1 - window
            result.append(max(values[start : i + 1]))
    return result


def rolling_min(values: list[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            result.append(None)
        else:
            start = i + 1 - window
            result.append(min(values[start : i + 1]))
    return result


def ema(values: list[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    if not values:
        return []
    result: list[float | None] = []
    multiplier = 2.0 / (window + 1)
    prev_ema: float | None = None
    for i, val in enumerate(values):
        if prev_ema is None:
            if i + 1 < window:
                result.append(None)
            else:
                segment = values[: i + 1]
                prev_ema = sum(segment) / len(segment)
                result.append(prev_ema)
        else:
            prev_ema = val * multiplier + prev_ema * (1 - multiplier)
            result.append(prev_ema)
    return result


def sma(values: list[float], window: int) -> list[float | None]:
    return rolling_mean(values, window)


def momentum(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be >= 1")
    result: list[float | None] = []
    for i in range(len(values)):
        if i < period:
            result.append(None)
        else:
            result.append(values[i] - values[i - period])
    return result


def returns(prices: list[float]) -> list[float]:
    if len(prices) < 2:
        return []
    return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]


def volume_ratio(volumes: list[float], window: int) -> list[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    result: list[float | None] = []
    for i in range(len(volumes)):
        if i + 1 < window:
            result.append(None)
        else:
            start = i + 1 - window
            avg_vol = sum(volumes[start : i + 1]) / window
            if avg_vol == 0.0:
                result.append(0.0)
            else:
                result.append(volumes[i] / avg_vol)
    return result
