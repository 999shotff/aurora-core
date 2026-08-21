"""Shared types for AURORA CORE product layer."""

from __future__ import annotations

from typing import Literal

Timeframe = Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]

ChartTheme = Literal["dark", "light"]

IndicatorType = Literal[
    "sma", "ema", "rsi", "macd", "bollinger", "atr",
    "stochastic", "adx", "cci", "williams_r", "vwap",
]

OverlayType = Literal["sma", "ema", "bollinger", "vwap", "fibonacci"]

PanelType = Literal["rsi", "macd", "stochastic", "volume", "atr", "adx"]

AssetCategory = Literal["crypto", "commodity", "equity_index", "forex", "etf"]
