"""Service layer for AURORA CORE product API.

Composes chart data, indicators, and asset registry into API responses.
"""

from __future__ import annotations

from aurora.product.api import (
    ChartResponse,
    HealthResponse,
    HealthStatus,
    MarketMetadata,
    MarketMetadataResponse,
)
from aurora.product.assets import get_asset, list_assets
from aurora.product.charts import build_chart_response
from aurora.product.config import DEFAULT_CONFIG


def get_market_metadata(symbol: str) -> MarketMetadata | None:
    """Get metadata for a single asset."""
    asset = get_asset(symbol)
    if asset is None:
        return None
    return MarketMetadata(
        symbol=asset.symbol,
        name=asset.name,
        category=asset.category,
        exchange=asset.exchange,
        currency="USD",
        trading_hours="24/7" if asset.category == "crypto" else "Market hours",
        decimals=asset.decimals,
        min_tick=asset.min_tick,
        description=asset.description,
    )


def get_all_market_metadata() -> MarketMetadataResponse:
    """Get metadata for all registered assets."""
    assets = list_assets()
    metadata = [
        MarketMetadata(
            symbol=a.symbol,
            name=a.name,
            category=a.category,
            exchange=a.exchange,
            currency="USD",
            trading_hours="24/7" if a.category == "crypto" else "Market hours",
            decimals=a.decimals,
            min_tick=a.min_tick,
            description=a.description,
        )
        for a in assets
    ]
    return MarketMetadataResponse(assets=metadata, count=len(metadata))


def get_chart(symbol: str, timeframe: str = "1d", n_bars: int = 200) -> ChartResponse:
    """Get chart data with default indicators."""
    return build_chart_response(
        symbol=symbol,
        timeframe=timeframe,
        overlay_names=["sma_20", "ema_12"],
        panel_names=["rsi_14", "macd"],
        n_bars=n_bars,
    )


def get_health() -> HealthResponse:
    """Get system health status."""
    services = [
        HealthStatus(
            service="chart-engine",
            status="operational",
            version=DEFAULT_CONFIG.version,
        ),
        HealthStatus(
            service="asset-registry",
            status="operational",
            version=DEFAULT_CONFIG.version,
        ),
        HealthStatus(
            service="indicator-engine",
            status="operational",
            version=DEFAULT_CONFIG.version,
        ),
    ]
    return HealthResponse(
        status="healthy",
        services=services,
        research_conclusion=DEFAULT_CONFIG.research_conclusion,
    )
