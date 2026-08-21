"""Typed API contracts for AURORA CORE product layer.

All schemas are pure Python dataclasses — no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ============================================================
# OHLCV Data Contracts
# ============================================================

@dataclass(frozen=True)
class OHLCBar:
    """Single OHLCV candle."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class OHLCResponse:
    """Response for OHLC candle data."""
    symbol: str
    timeframe: str
    bars: list[OHLCBar]
    count: int
    data_source: str = "yfinance"
    disclaimer: str = "Research data only. No prediction claims."


# ============================================================
# Indicator Contracts
# ============================================================

@dataclass(frozen=True)
class IndicatorPoint:
    """Single point of an indicator series."""
    timestamp: str
    value: float


@dataclass(frozen=True)
class IndicatorSeries:
    """A time series of indicator values."""
    name: str
    parameters: dict[str, float | int | str]
    points: list[IndicatorPoint]


@dataclass(frozen=True)
class IndicatorResponse:
    """Response for indicator calculations."""
    symbol: str
    timeframe: str
    indicators: list[IndicatorSeries]
    count: int


@dataclass(frozen=True)
class IndicatorRequest:
    """Request for indicator calculation."""
    symbol: str
    timeframe: str = "1d"
    indicators: list[str] = field(default_factory=lambda: ["sma_20", "ema_12", "rsi_14"])
    parameters: dict[str, dict[str, float | int]] = field(default_factory=dict)


# ============================================================
# Market Metadata Contracts
# ============================================================

@dataclass(frozen=True)
class MarketMetadata:
    """Metadata for a market instrument."""
    symbol: str
    name: str
    category: str
    exchange: str
    currency: str
    trading_hours: str
    decimals: int
    min_tick: float
    description: str


@dataclass(frozen=True)
class MarketMetadataResponse:
    """Response for market metadata."""
    assets: list[MarketMetadata]
    count: int


# ============================================================
# Watchlist Contracts
# ============================================================

@dataclass(frozen=True)
class WatchlistItem:
    """Single item in a watchlist."""
    symbol: str
    name: str
    last_price: float | None = None
    change_pct: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class Watchlist:
    """A user watchlist."""
    name: str
    items: list[WatchlistItem]
    updated_at: str = ""


@dataclass(frozen=True)
class WatchlistResponse:
    """Response for watchlist data."""
    watchlists: list[Watchlist]
    count: int


# ============================================================
# Chart Request Contracts
# ============================================================

@dataclass(frozen=True)
class ChartOverlay:
    """An overlay to display on the chart."""
    type: str
    parameters: dict[str, float | int | str] = field(default_factory=dict)
    color: str = "#2196F3"


@dataclass(frozen=True)
class ChartPanel:
    """A separate panel below the main chart."""
    type: str
    parameters: dict[str, float | int | str] = field(default_factory=dict)
    height: int = 150


@dataclass(frozen=True)
class ChartConfiguration:
    """Full chart configuration for TradingView rendering."""
    symbol: str
    timeframe: str
    overlays: list[ChartOverlay] = field(default_factory=list)
    panels: list[ChartPanel] = field(default_factory=list)
    theme: str = "dark"
    responsive: bool = True


@dataclass(frozen=True)
class ChartResponse:
    """Response containing chart data and configuration."""
    configuration: ChartConfiguration
    bars: list[OHLCBar]
    overlays: list[IndicatorSeries]
    panels: list[IndicatorSeries]
    bar_count: int


# ============================================================
# Analysis Request Contracts
# ============================================================

@dataclass(frozen=True)
class AnalysisRequest:
    """Request for market analysis."""
    symbol: str
    timeframe: str = "1d"
    analysis_type: str = "summary"
    lookback_periods: int = 20


@dataclass(frozen=True)
class AnalysisResult:
    """Result of a market analysis."""
    symbol: str
    timeframe: str
    analysis_type: str
    summary: str
    metrics: dict[str, float]
    timestamp: str = ""


@dataclass(frozen=True)
class AnalysisResponse:
    """Response for analysis request."""
    results: list[AnalysisResult]
    disclaimer: str = "Research only. No predictions or recommendations."


# ============================================================
# Health / Status Contracts
# ============================================================

@dataclass(frozen=True)
class HealthStatus:
    """Service health status."""
    service: str
    status: str
    version: str
    uptime_seconds: float = 0.0


@dataclass(frozen=True)
class HealthResponse:
    """Response for health check."""
    status: str
    services: list[HealthStatus]
    research_conclusion: str = "NO_DEPLOYMENT_SIGNAL"
