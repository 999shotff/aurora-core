"""Asset registry for configurable market instruments.

Supports: BTC-USD, ETH-USD, Gold, Silver, SPY, QQQ, NIFTY, NASDAQ, EURUSD, USDJPY.

NO prediction claims. Registry and UI selection only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssetCategory = Literal[
    "crypto",
    "commodity",
    "equity_index",
    "forex",
    "etf",
]

Timeframe = Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]


@dataclass(frozen=True)
class Asset:
    """A tradeable instrument configuration."""
    symbol: str
    name: str
    category: AssetCategory
    exchange: str
    ticker_yahoo: str
    default_timeframe: Timeframe
    description: str
    decimals: int = 2
    min_tick: float = 0.01


@dataclass(frozen=True)
class AssetMetadata:
    """Runtime metadata for an asset."""
    symbol: str
    last_price: float | None = None
    last_update: str = ""
    data_available: bool = False
    history_years: int = 0


ASSET_REGISTRY: dict[str, Asset] = {}


def _register_assets() -> None:
    """Register all supported assets."""
    assets = [
        Asset(
            symbol="BTC-USD",
            name="Bitcoin",
            category="crypto",
            exchange="NASDAQ",
            ticker_yahoo="BTC-USD",
            default_timeframe="1d",
            description="Bitcoin vs US Dollar",
            decimals=2,
            min_tick=0.01,
        ),
        Asset(
            symbol="ETH-USD",
            name="Ethereum",
            category="crypto",
            exchange="NASDAQ",
            ticker_yahoo="ETH-USD",
            default_timeframe="1d",
            description="Ethereum vs US Dollar",
            decimals=2,
            min_tick=0.01,
        ),
        Asset(
            symbol="GOLD",
            name="Gold",
            category="commodity",
            exchange="COMEX",
            ticker_yahoo="GC=F",
            default_timeframe="1d",
            description="Gold Futures",
            decimals=2,
            min_tick=0.01,
        ),
        Asset(
            symbol="SILVER",
            name="Silver",
            category="commodity",
            exchange="COMEX",
            ticker_yahoo="SI=F",
            default_timeframe="1d",
            description="Silver Futures",
            decimals=3,
            min_tick=0.001,
        ),
        Asset(
            symbol="SPY",
            name="S&P 500 ETF",
            category="etf",
            exchange="NYSE",
            ticker_yahoo="SPY",
            default_timeframe="1d",
            description="SPDR S&P 500 ETF Trust",
            decimals=2,
            min_tick=0.01,
        ),
        Asset(
            symbol="QQQ",
            name="Nasdaq 100 ETF",
            category="etf",
            exchange="NASDAQ",
            ticker_yahoo="QQQ",
            default_timeframe="1d",
            description="Invesco QQQ Trust",
            decimals=2,
            min_tick=0.01,
        ),
        Asset(
            symbol="NIFTY",
            name="Nifty 50",
            category="equity_index",
            exchange="NSE",
            ticker_yahoo="^NSEI",
            default_timeframe="1d",
            description="NSE Nifty 50 Index",
            decimals=2,
            min_tick=0.05,
        ),
        Asset(
            symbol="NASDAQ",
            name="NASDAQ Composite",
            category="equity_index",
            exchange="NASDAQ",
            ticker_yahoo="^IXIC",
            default_timeframe="1d",
            description="NASDAQ Composite Index",
            decimals=2,
            min_tick=0.01,
        ),
        Asset(
            symbol="EURUSD",
            name="Euro/US Dollar",
            category="forex",
            exchange="FOREX",
            ticker_yahoo="EURUSD=X",
            default_timeframe="1d",
            description="EUR/USD Exchange Rate",
            decimals=5,
            min_tick=0.00001,
        ),
        Asset(
            symbol="USDJPY",
            name="US Dollar/Japanese Yen",
            category="forex",
            exchange="FOREX",
            ticker_yahoo="JPY=X",
            default_timeframe="1d",
            description="USD/JPY Exchange Rate",
            decimals=3,
            min_tick=0.001,
        ),
    ]
    for asset in assets:
        ASSET_REGISTRY[asset.symbol] = asset


_register_assets()


def get_asset(symbol: str) -> Asset | None:
    """Get asset by symbol."""
    return ASSET_REGISTRY.get(symbol)


def list_assets() -> list[Asset]:
    """List all registered assets."""
    return list(ASSET_REGISTRY.values())


def list_assets_by_category(category: AssetCategory) -> list[Asset]:
    """List assets filtered by category."""
    return [a for a in ASSET_REGISTRY.values() if a.category == category]


def get_categories() -> list[AssetCategory]:
    """List all asset categories."""
    categories: set[AssetCategory] = set()
    for asset in ASSET_REGISTRY.values():
        categories.add(asset.category)
    return sorted(categories)


def get_yahoo_ticker(symbol: str) -> str | None:
    """Get Yahoo Finance ticker for a symbol."""
    asset = get_asset(symbol)
    return asset.ticker_yahoo if asset else None
