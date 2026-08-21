"""Market data provider abstraction.

Application depends on MarketDataProvider protocol, not on concrete providers.
Demo and real implementations available.
NO prediction claims. Data infrastructure only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import ClassVar, Protocol

from aurora.product.assets import get_asset, get_yahoo_ticker

# ============================================================
# Provider Errors
# ============================================================


@dataclass(frozen=True)
class ProviderError:
    """Structured provider error."""
    code: str
    message: str
    provider: str
    asset: str = ""
    retryable: bool = False


# ============================================================
# Provider Response Contracts
# ============================================================


@dataclass(frozen=True)
class CandleData:
    """Single normalized candle."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class QuoteData:
    """Latest quote for an asset."""
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume_24h: float
    change_pct: float
    timestamp: str


@dataclass(frozen=True)
class ProviderResponse:
    """Response from a market data provider."""
    candles: list[CandleData]
    symbol: str
    timeframe: str
    provider_name: str
    is_demo: bool
    retrieved_at: str
    data_timestamp: str
    source_status: str  # "ok", "unavailable", "error"
    error: ProviderError | None = None
    metadata: dict[str, str | int | float] = field(default_factory=dict)


# ============================================================
# MarketDataProvider Protocol
# ============================================================


class MarketDataProvider(Protocol):
    """Protocol for market data providers.

    Application code depends on this interface, not concrete implementations.
    """

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    def is_demo(self) -> bool:
        """Whether this is a demo/simulated provider."""
        ...

    def get_ohlc(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 200,
    ) -> ProviderResponse:
        """Fetch OHLC candle data.

        Returns structured response with candles or error.
        Never raises on provider failures.
        """
        ...

    def get_latest_quote(self, symbol: str) -> ProviderResponse:
        """Fetch latest quote for an asset.

        Returns structured response with single candle or error.
        """
        ...

    def get_asset_metadata(self, symbol: str) -> dict[str, str | int | float] | None:
        """Get metadata for an asset from the provider."""
        ...

    def get_available_timeframes(self, symbol: str) -> list[str]:
        """List timeframes available for this asset from this provider."""
        ...


# ============================================================
# Demo Market Data Provider
# ============================================================


class DemoMarketDataProvider:
    """Development-only mock market data provider.

    Generates deterministic simulated data. No real market data.
    Clearly labeled as DEMO in all responses.
    """

    _ASSET_DEFAULTS: ClassVar[dict[str, tuple[float, float]]] = {
        "BTC-USD": (50000.0, 0.02),
        "ETH-USD": (3000.0, 0.03),
        "GOLD": (2000.0, 0.008),
        "SILVER": (25.0, 0.015),
        "SPY": (450.0, 0.01),
        "QQQ": (380.0, 0.012),
        "NIFTY": (18000.0, 0.008),
        "NASDAQ": (14000.0, 0.011),
        "EURUSD": (1.08, 0.005),
        "USDJPY": (148.0, 0.006),
    }

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    @property
    def name(self) -> str:
        return "demo"

    @property
    def is_demo(self) -> bool:
        return True

    def _generate_candles(
        self, symbol: str, timeframe: str, limit: int
    ) -> list[CandleData]:
        import random
        rng = random.Random(self._seed + hash(symbol) + hash(timeframe))
        start_price, volatility = self._ASSET_DEFAULTS.get(symbol, (100.0, 0.02))
        now = datetime.now(timezone.utc)
        bars: list[CandleData] = []
        price = start_price
        for i in range(limit):
            ts = now - timedelta(days=limit - i)
            ret = rng.gauss(0.0002, volatility)
            price *= (1 + ret)
            high = price * (1 + abs(rng.gauss(0, volatility * 0.5)))
            low = price * (1 - abs(rng.gauss(0, volatility * 0.5)))
            opn = price * (1 + rng.gauss(0, volatility * 0.2))
            vol = rng.uniform(1_000_000, 50_000_000)
            bars.append(CandleData(
                timestamp=ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                open=round(opn, 4),
                high=round(max(high, opn, price), 4),
                low=round(min(low, opn, price), 4),
                close=round(price, 4),
                volume=round(vol, 0),
            ))
        return bars

    def get_ohlc(
        self, symbol: str, timeframe: str = "1d", limit: int = 200
    ) -> ProviderResponse:
        now = datetime.now(timezone.utc)
        asset = get_asset(symbol)
        if asset is None:
            return ProviderResponse(
                candles=[], symbol=symbol, timeframe=timeframe,
                provider_name=self.name, is_demo=True,
                retrieved_at=now.isoformat(), data_timestamp="",
                source_status="error",
                error=ProviderError(code="INVALID_ASSET", message=f"Unknown symbol: {symbol}", provider=self.name),
            )
        candles = self._generate_candles(symbol, timeframe, limit)
        return ProviderResponse(
            candles=candles, symbol=symbol, timeframe=timeframe,
            provider_name=self.name, is_demo=True,
            retrieved_at=now.isoformat(),
            data_timestamp=candles[-1].timestamp if candles else "",
            source_status="ok",
        )

    def get_latest_quote(self, symbol: str) -> ProviderResponse:
        return self.get_ohlc(symbol, "1d", 1)

    def get_asset_metadata(self, symbol: str) -> dict[str, str | int | float] | None:
        asset = get_asset(symbol)
        if asset is None:
            return None
        return {
            "symbol": asset.symbol,
            "name": asset.name,
            "category": asset.category,
            "exchange": asset.exchange,
        }

    def get_available_timeframes(self, symbol: str) -> list[str]:
        if get_asset(symbol) is None:
            return []
        return ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]


# ============================================================
# Real Market Data Provider (yfinance)
# ============================================================

# yfinance timeframe mapping
_TIMEFRAME_MAP: dict[str, tuple[str, str]] = {
    "1m": ("1m", "5d"),
    "5m": ("5m", "60d"),
    "15m": ("15m", "60d"),
    "30m": ("30m", "60d"),
    "1h": ("1h", "730d"),
    "4h": ("1h", "730d"),
    "1d": ("1d", "5y"),
    "1w": ("1wk", "10y"),
    "1M": ("1mo", "10y"),
}


class RealMarketDataProvider:
    """Production market data provider using yfinance.

    Fetches real market data from Yahoo Finance.
    Requires network access and yfinance installed.
    API key via environment variable AURORA_YAHOO_API_KEY (optional for yfinance).
    """

    def __init__(self) -> None:
        self._api_key: str = os.environ.get("AURORA_YAHOO_API_KEY", "")

    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def is_demo(self) -> bool:
        return False

    def get_ohlc(
        self, symbol: str, timeframe: str = "1d", limit: int = 200
    ) -> ProviderResponse:
        now = datetime.now(timezone.utc)
        yahoo_ticker = get_yahoo_ticker(symbol)
        if yahoo_ticker is None:
            return ProviderResponse(
                candles=[], symbol=symbol, timeframe=timeframe,
                provider_name=self.name, is_demo=False,
                retrieved_at=now.isoformat(), data_timestamp="",
                source_status="error",
                error=ProviderError(
                    code="INVALID_ASSET",
                    message=f"Unknown symbol: {symbol}",
                    provider=self.name,
                ),
            )
        if timeframe not in _TIMEFRAME_MAP:
            return ProviderResponse(
                candles=[], symbol=symbol, timeframe=timeframe,
                provider_name=self.name, is_demo=False,
                retrieved_at=now.isoformat(), data_timestamp="",
                source_status="error",
                error=ProviderError(
                    code="INVALID_TIMEFRAME",
                    message=f"Unsupported timeframe: {timeframe}",
                    provider=self.name,
                    retryable=False,
                ),
            )
        interval, period = _TIMEFRAME_MAP[timeframe]
        try:
            import yfinance as yf
            ticker = yf.Ticker(yahoo_ticker)
            df = ticker.history(period=period, interval=interval)
            if df is None or df.empty:
                return ProviderResponse(
                    candles=[], symbol=symbol, timeframe=timeframe,
                    provider_name=self.name, is_demo=False,
                    retrieved_at=now.isoformat(), data_timestamp="",
                    source_status="unavailable",
                    error=ProviderError(
                        code="NO_DATA",
                        message=f"No data available for {symbol} ({timeframe})",
                        provider=self.name,
                    ),
                )
            candles: list[CandleData] = []
            for idx, row in df.iterrows():
                ts = idx.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(idx, "strftime") else str(idx)
                candles.append(CandleData(
                    timestamp=ts,
                    open=round(float(row["Open"]), 4),
                    high=round(float(row["High"]), 4),
                    low=round(float(row["Low"]), 4),
                    close=round(float(row["Close"]), 4),
                    volume=round(float(row["Volume"]), 0),
                ))
            candles = candles[-limit:]
            return ProviderResponse(
                candles=candles, symbol=symbol, timeframe=timeframe,
                provider_name=self.name, is_demo=False,
                retrieved_at=now.isoformat(),
                data_timestamp=candles[-1].timestamp if candles else "",
                source_status="ok",
            )
        except Exception as e:  # noqa: BLE001
            return ProviderResponse(
                candles=[], symbol=symbol, timeframe=timeframe,
                provider_name=self.name, is_demo=False,
                retrieved_at=now.isoformat(), data_timestamp="",
                source_status="error",
                error=ProviderError(
                    code="PROVIDER_ERROR",
                    message=str(e),
                    provider=self.name,
                    retryable=True,
                ),
            )

    def get_latest_quote(self, symbol: str) -> ProviderResponse:
        return self.get_ohlc(symbol, "1d", 1)

    def get_asset_metadata(self, symbol: str) -> dict[str, str | int | float] | None:
        asset = get_asset(symbol)
        if asset is None:
            return None
        return {
            "symbol": asset.symbol,
            "name": asset.name,
            "category": asset.category,
            "exchange": asset.exchange,
        }

    def get_available_timeframes(self, symbol: str) -> list[str]:
        if get_asset(symbol) is None:
            return []
        return list(_TIMEFRAME_MAP.keys())


# ============================================================
# Provider Factory
# ============================================================


def create_provider(provider_name: str | None = None) -> MarketDataProvider:
    """Create a market data provider by name.

    Defaults to demo if not specified or if AURORA_DATA_MODE=demo.
    """
    if provider_name is None:
        provider_name = os.environ.get("AURORA_DATA_MODE", "demo")
    if provider_name == "real" or provider_name == "yfinance":
        return RealMarketDataProvider()
    return DemoMarketDataProvider()
