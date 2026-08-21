"""Chart data service with technical indicators.

Provides OHLCV data and indicator calculations for TradingView rendering.

NO prediction claims. Analysis and visualization only.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from aurora.product.api import (
    ChartConfiguration,
    ChartOverlay,
    ChartPanel,
    ChartResponse,
    IndicatorPoint,
    IndicatorSeries,
    OHLCBar,
    OHLCResponse,
)

# ============================================================
# OHLCV Data Provider
# ============================================================

def generate_mock_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    n_bars: int = 200,
    start_price: float = 100.0,
    volatility: float = 0.02,
    seed: int = 42,
) -> OHLCResponse:
    """Generate mock OHLCV data for chart development and testing.

    This produces realistic-looking price data using geometric Brownian motion.
    For live data, use yfinance integration (existing in research layer).
    """
    rng = random.Random(seed)
    bars: list[OHLCBar] = []
    price = start_price
    start_date = datetime(2024, 1, 1)  # noqa: DTZ001

    for i in range(n_bars):
        ts = start_date + timedelta(days=i)
        ret = rng.gauss(0.0002, volatility)
        price *= (1 + ret)
        high = price * (1 + abs(rng.gauss(0, volatility * 0.5)))
        low = price * (1 - abs(rng.gauss(0, volatility * 0.5)))
        opn = price * (1 + rng.gauss(0, volatility * 0.2))
        vol = rng.uniform(1_000_000, 50_000_000)

        bar = OHLCBar(
            timestamp=ts.strftime("%Y-%m-%d"),
            open=round(opn, 2),
            high=round(max(high, opn, price), 2),
            low=round(min(low, opn, price), 2),
            close=round(price, 2),
            volume=round(vol, 0),
        )
        bars.append(bar)

    return OHLCResponse(
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
        count=len(bars),
        data_source="mock",
        disclaimer="Mock data for development. Not real market data.",
    )


def fetch_ohlcv_for_chart(
    symbol: str,
    timeframe: str = "1d",
    n_bars: int = 200,
) -> OHLCResponse:
    """Fetch OHLCV data for charting.

    Currently returns mock data. Can be extended to use yfinance.
    """
    return generate_mock_ohlcv(symbol, timeframe, n_bars)


# ============================================================
# Technical Indicator Calculations
# ============================================================

def _sma(values: list[float], period: int) -> list[float | None]:
    """Simple Moving Average."""
    result: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            window = values[i - period + 1: i + 1]
            result.append(round(sum(window) / period, 6))
    return result


def _ema(values: list[float], period: int) -> list[float | None]:
    """Exponential Moving Average."""
    if not values:
        return []
    result: list[float | None] = [None] * (period - 1)
    multiplier = 2.0 / (period + 1)
    ema_val = sum(values[:period]) / period
    result.append(round(ema_val, 6))
    for i in range(period, len(values)):
        ema_val = values[i] * multiplier + ema_val * (1 - multiplier)
        result.append(round(ema_val, 6))
    return result


def _rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return [None] * len(closes)

    result: list[float | None] = [None] * period
    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100 - (100 / (1 + rs)), 2))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - (100 / (1 + rs)), 2))

    return result


def _macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """MACD: line, signal, histogram."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    macd_line: list[float | None] = []
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(round(ema_fast[i] - ema_slow[i], 6))
        else:
            macd_line.append(None)

    valid_macd = [v for v in macd_line if v is not None]
    signal_line_raw = _ema(valid_macd, signal) if len(valid_macd) >= signal else [None] * len(valid_macd)

    signal_line: list[float | None] = []
    j = 0
    for v in macd_line:
        if v is None:
            signal_line.append(None)
        else:
            if j < len(signal_line_raw):
                signal_line.append(signal_line_raw[j])
            else:
                signal_line.append(None)
            j += 1

    histogram: list[float | None] = []
    for i in range(len(macd_line)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram.append(round(macd_line[i] - signal_line[i], 6))
        else:
            histogram.append(None)

    return macd_line, signal_line, histogram


def _bollinger_bands(
    closes: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Bollinger Bands: upper, middle, lower."""
    middle = _sma(closes, period)
    upper: list[float | None] = []
    lower: list[float | None] = []

    for i in range(len(closes)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            window = closes[i - period + 1: i + 1]
            std = (sum((x - middle[i]) ** 2 for x in window) / period) ** 0.5
            upper.append(round(middle[i] + num_std * std, 6))
            lower.append(round(middle[i] - num_std * std, 6))

    return upper, middle, lower


def _atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    """Average True Range."""
    if len(closes) < 2:
        return [None] * len(closes)

    tr_values: list[float] = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_values.append(tr)

    return _sma(tr_values, period)


# ============================================================
# Indicator Provider
# ============================================================

INDICATOR_REGISTRY: dict[str, str] = {
    "sma_5": "SMA(5)",
    "sma_10": "SMA(10)",
    "sma_20": "SMA(20)",
    "sma_50": "SMA(50)",
    "sma_200": "SMA(200)",
    "ema_12": "EMA(12)",
    "ema_26": "EMA(26)",
    "ema_50": "EMA(50)",
    "rsi_14": "RSI(14)",
    "rsi_7": "RSI(7)",
    "macd": "MACD(12,26,9)",
    "bollinger": "Bollinger(20,2)",
    "atr_14": "ATR(14)",
}


def compute_indicators(
    bars: list[OHLCBar],
    indicator_names: list[str],
    parameters: dict[str, dict[str, float | int]] | None = None,
) -> list[IndicatorSeries]:
    """Compute technical indicators from OHLCV bars."""
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    timestamps = [b.timestamp for b in bars]

    results: list[IndicatorSeries] = []

    for name in indicator_names:
        params = parameters.get(name, {}) if parameters else {}

        if name.startswith("sma_"):
            period = int(name.split("_")[1])
            values = _sma(closes, period)
        elif name.startswith("ema_"):
            period = int(name.split("_")[1])
            values = _ema(closes, period)
        elif name.startswith("rsi_"):
            period = int(name.split("_")[1])
            values = _rsi(closes, period)
        elif name == "macd":
            macd_l, sig_l, hist_l = _macd(closes)
            results.append(IndicatorSeries(
                name="macd_line",
                parameters={"fast": 12, "slow": 26, "signal": 9},
                points=[IndicatorPoint(timestamp=timestamps[i], value=macd_l[i]) for i in range(len(timestamps)) if macd_l[i] is not None],
            ))
            results.append(IndicatorSeries(
                name="macd_signal",
                parameters={"fast": 12, "slow": 26, "signal": 9},
                points=[IndicatorPoint(timestamp=timestamps[i], value=sig_l[i]) for i in range(len(timestamps)) if sig_l[i] is not None],
            ))
            results.append(IndicatorSeries(
                name="macd_histogram",
                parameters={"fast": 12, "slow": 26, "signal": 9},
                points=[IndicatorPoint(timestamp=timestamps[i], value=hist_l[i]) for i in range(len(timestamps)) if hist_l[i] is not None],
            ))
            continue
        elif name == "bollinger":
            upper, middle, lower = _bollinger_bands(closes)
            results.append(IndicatorSeries(
                name="bb_upper",
                parameters={"period": 20, "num_std": 2.0},
                points=[IndicatorPoint(timestamp=timestamps[i], value=upper[i]) for i in range(len(timestamps)) if upper[i] is not None],
            ))
            results.append(IndicatorSeries(
                name="bb_middle",
                parameters={"period": 20, "num_std": 2.0},
                points=[IndicatorPoint(timestamp=timestamps[i], value=middle[i]) for i in range(len(timestamps)) if middle[i] is not None],
            ))
            results.append(IndicatorSeries(
                name="bb_lower",
                parameters={"period": 20, "num_std": 2.0},
                points=[IndicatorPoint(timestamp=timestamps[i], value=lower[i]) for i in range(len(timestamps)) if lower[i] is not None],
            ))
            continue
        elif name.startswith("atr_"):
            period = int(name.split("_")[1])
            values = _atr(highs, lows, closes, period)
        else:
            continue

        points = [
            IndicatorPoint(timestamp=timestamps[i], value=values[i])
            for i in range(len(timestamps))
            if values[i] is not None
        ]
        results.append(IndicatorSeries(name=name, parameters=params, points=points))

    return results


# ============================================================
# Chart Builder
# ============================================================

def build_chart_response(
    symbol: str,
    timeframe: str = "1d",
    overlay_names: list[str] | None = None,
    panel_names: list[str] | None = None,
    n_bars: int = 200,
) -> ChartResponse:
    """Build a complete chart response with data and indicators."""
    ohlcv = fetch_ohlcv_for_chart(symbol, timeframe, n_bars)

    overlay_indicators = compute_indicators(ohlcv.bars, overlay_names or ["sma_20", "ema_12"])
    panel_indicators = compute_indicators(ohlcv.bars, panel_names or ["rsi_14", "macd"])

    config = ChartConfiguration(
        symbol=symbol,
        timeframe=timeframe,
        overlays=[ChartOverlay(type=name) for name in (overlay_names or ["sma_20", "ema_12"])],
        panels=[ChartPanel(type=name) for name in (panel_names or ["rsi_14", "macd"])],
        theme="dark",
        responsive=True,
    )

    return ChartResponse(
        configuration=config,
        bars=ohlcv.bars,
        overlays=overlay_indicators,
        panels=panel_indicators,
        bar_count=len(ohlcv.bars),
    )
