"""REST API endpoints for market data.

FastAPI endpoints: /health, /assets, /market/{asset}/quote,
/market/{asset}/ohlc, /market/{asset}/metadata.

Compatible with M16 contracts. Research firewall enforced.
Includes stale-data detection, provider health, and connection status.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from aurora.market.cache import BoundedCache
from aurora.market.normalization import normalize_and_validate
from aurora.market.provenance import create_provenance
from aurora.market.provider import (
    MarketDataProvider,
    create_provider,
)
from aurora.market.rate_limiter import RequestThrottler
from aurora.product.assets import get_asset, list_assets

# ============================================================
# App State
# ============================================================

_start_time = time.monotonic()
_cache = BoundedCache(max_size=256, default_ttl=60.0)
_throttler = RequestThrottler()
_provider: MarketDataProvider | None = None


class _ProviderHealth:
    """Tracks provider health and staleness."""

    def __init__(self) -> None:
        self.last_success: float = 0.0
        self.last_failure: float = 0.0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.last_error: str = ""
        self.consecutive_failures: int = 0

    def record_success(self) -> None:
        self.last_success = time.monotonic()
        self.success_count += 1
        self.consecutive_failures = 0

    def record_failure(self, error: str) -> None:
        self.last_failure = time.monotonic()
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_error = error

    @property
    def is_healthy(self) -> bool:
        return self.consecutive_failures < 3

    @property
    def seconds_since_last_success(self) -> float:
        if self.last_success == 0:
            return float("inf")
        return time.monotonic() - self.last_success

    @property
    def is_stale(self) -> bool:
        return self.seconds_since_last_success > 300

    def to_dict(self) -> dict:
        return {
            "healthy": self.is_healthy,
            "stale": self.is_stale,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "seconds_since_last_success": round(self.seconds_since_last_success, 1),
        }


_health = _ProviderHealth()


def _get_provider() -> MarketDataProvider:
    global _provider
    if _provider is None:
        _provider = create_provider()
    return _provider


def _get_cors_origins() -> list[str]:
    """Load CORS origins from environment."""
    import os
    raw = os.environ.get("AURORA_CORS_ORIGINS", "https://aurora-core.vercel.app")
    return [o.strip() for o in raw.split(",") if o.strip()]


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="AURORA CORE Market Data API",
    description="Market data infrastructure. No predictions. NO_DEPLOYMENT_SIGNAL.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health() -> dict:
    provider = _get_provider()
    return {
        "status": "healthy" if _health.is_healthy else "degraded",
        "services": [
            {"service": "market-data-api", "status": "operational", "version": "0.1.0"},
            {"service": "market-data-provider", "status": "operational" if _health.is_healthy else "degraded", "version": provider.name},
            {"service": "chart-engine", "status": "operational", "version": "0.1.0"},
        ],
        "research_conclusion": "NO_DEPLOYMENT_SIGNAL",
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
        "provider_health": _health.to_dict(),
        "is_demo": provider.is_demo,
    }


# ============================================================
# Assets
# ============================================================

@app.get("/assets")
def list_all_assets() -> dict:
    assets = list_assets()
    return {
        "assets": [
            {
                "symbol": a.symbol,
                "name": a.name,
                "category": a.category,
                "exchange": a.exchange,
                "ticker_yahoo": a.ticker_yahoo,
                "default_timeframe": a.default_timeframe,
            }
            for a in assets
        ],
        "count": len(assets),
    }


# ============================================================
# Market Data
# ============================================================

@app.get("/market/{asset}/quote")
def get_quote(asset: str) -> dict:
    provider = _get_provider()
    if not _throttler.can_request(provider.name):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    cache_key = f"quote:{asset}"
    cached = _cache.get(cache_key)
    if cached is not None:
        result: dict[str, Any] = cached  # type: ignore[assignment]
        result["stale"] = _health.is_stale
        return result
    resp = provider.get_latest_quote(asset)
    if resp.source_status == "error":
        _health.record_failure(resp.error.message if resp.error else "No data")
        raise HTTPException(status_code=404, detail=resp.error.message if resp.error else "No data")
    _health.record_success()
    result = {
        "symbol": resp.symbol,
        "last_price": resp.candles[-1].close if resp.candles else 0,
        "timestamp": resp.candles[-1].timestamp if resp.candles else "",
        "provider": resp.provider_name,
        "is_demo": resp.is_demo,
        "source_status": resp.source_status,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "stale": False,
    }
    _cache.put(cache_key, result, ttl=30)
    return result


@app.get("/market/{asset}/ohlc")
def get_ohlc(
    asset: str,
    timeframe: str = Query(default="1d", pattern="^(1m|5m|15m|30m|1h|4h|1d|1w|1M)$"),
    limit: int = Query(default=200, ge=1, le=5000),
) -> dict:
    provider = _get_provider()
    if not _throttler.can_request(provider.name):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    cache_key = f"ohlc:{asset}:{timeframe}:{limit}"
    cached = _cache.get(cache_key)
    if cached is not None:
        result: dict[str, Any] = cached  # type: ignore[assignment]
        prov: dict[str, Any] = result.get("provenance", {})  # type: ignore[assignment]
        prov["stale"] = _health.is_stale
        result["provenance"] = prov
        return result
    resp = provider.get_ohlc(asset, timeframe, limit)
    if resp.source_status == "error":
        _health.record_failure(resp.error.message if resp.error else "No data")
        raise HTTPException(status_code=404, detail=resp.error.message if resp.error else "No data")
    _health.record_success()
    validation = normalize_and_validate(resp.candles, asset)
    provenance = create_provenance(
        provider=resp.provider_name,
        asset=asset,
        timeframe=timeframe,
        is_demo=resp.is_demo,
        source_status=resp.source_status,
        candle_count=len(validation.candles),
        data_timestamp=resp.data_timestamp,
        validation_errors=validation.errors,
    )
    result = {
        "symbol": resp.symbol,
        "timeframe": resp.timeframe,
        "bars": [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in validation.candles
        ],
        "count": len(validation.candles),
        "rejected_count": validation.rejected_count,
        "validation_errors": validation.errors,
        "provenance": {
            "provider": provenance.provider,
            "asset": provenance.asset,
            "timeframe": provenance.timeframe,
            "retrieved_at": provenance.retrieved_at,
            "data_timestamp": provenance.data_timestamp,
            "source_status": provenance.source_status,
            "is_demo": provenance.is_demo,
            "stale": _health.is_stale,
        },
    }
    _cache.put(cache_key, result, ttl=60)
    return result


@app.get("/market/{asset}/metadata")
def get_asset_metadata(asset: str) -> dict:
    asset_obj = get_asset(asset)
    if asset_obj is None:
        raise HTTPException(status_code=404, detail=f"Unknown asset: {asset}")
    return {
        "symbol": asset_obj.symbol,
        "name": asset_obj.name,
        "category": asset_obj.category,
        "exchange": asset_obj.exchange,
        "currency": "USD",
        "ticker_yahoo": asset_obj.ticker_yahoo,
        "decimals": asset_obj.decimals,
        "min_tick": asset_obj.min_tick,
        "description": asset_obj.description,
    }


@app.get("/market/{asset}/timeframes")
def get_available_timeframes(asset: str) -> dict:
    provider = _get_provider()
    timeframes = provider.get_available_timeframes(asset)
    return {
        "symbol": asset,
        "provider": provider.name,
        "is_demo": provider.is_demo,
        "timeframes": timeframes,
    }


# ============================================================
# Market Analysis (M25)
# ============================================================


@app.get("/market/{asset}/analysis")
def get_market_analysis(
    asset: str,
    timeframe: str = Query(default="1d", pattern="^(1m|5m|15m|30m|1h|4h|1d|1w|1M)$"),
    limit: int = Query(default=200, ge=30, le=5000),
) -> dict:
    """Deterministic market analysis engine.

    Produces structured analytical context from real OHLCV data.
    NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
    Includes M26 evidence aggregation, confluence scoring, and scenario analysis.
    """
    from aurora.features.evidence import analyze_market_full
    from aurora.features.market_context import analyze_market

    provider = _get_provider()

    # Fetch primary timeframe data
    resp = provider.get_ohlc(asset, timeframe, limit)
    if resp.source_status == "error":
        _health.record_failure(resp.error.message if resp.error else "No data")
        raise HTTPException(status_code=404, detail=resp.error.message if resp.error else "No data")
    _health.record_success()

    validation = normalize_and_validate(resp.candles, asset)
    bars = [
        {
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in validation.candles
    ]

    # Fetch multi-timeframe data (best effort, non-blocking)
    mtf_timeframes = {"1h", "4h", "1d"}
    bars_by_tf: dict[str, list[dict]] = {}
    for mtf_tf in mtf_timeframes:
        if mtf_tf == timeframe:
            bars_by_tf[mtf_tf] = bars
            continue
        try:
            mtf_resp = provider.get_ohlc(asset, mtf_tf, min(limit, 200))
            if mtf_resp.source_status != "error" and mtf_resp.candles:
                mtf_validation = normalize_and_validate(mtf_resp.candles, asset)
                bars_by_tf[mtf_tf] = [
                    {
                        "timestamp": c.timestamp,
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume,
                    }
                    for c in mtf_validation.candles
                ]
        except Exception:  # noqa: BLE001, S110
            pass  # Best effort — missing MTF data is acceptable

    # Run analysis
    context = analyze_market(
        bars=bars,
        asset=asset,
        timeframe=timeframe,
        provider=resp.provider_name,
        stale=_health.is_stale,
        bars_by_tf=bars_by_tf if bars_by_tf else None,
    )

    # Run M26 evidence confluence and scenario analysis
    analysis = analyze_market_full(context)

    # Convert dataclass to dict for JSON serialization
    from dataclasses import asdict

    def _convert(obj: object) -> object:
        if hasattr(obj, "value"):  # Enum
            return obj.value
        if hasattr(obj, "__dataclass_fields__"):  # dataclass
            return {k: _convert(v) for k, v in asdict(obj).items()}
        if isinstance(obj, list):
            return [_convert(item) for item in obj]
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        return obj

    result = _convert(analysis)

    # Add metadata
    result["provider"] = resp.provider_name
    result["is_demo"] = resp.is_demo
    result["research_conclusion"] = "NO_DEPLOYMENT_SIGNAL"

    return result


# ============================================================
# WebSocket
# ============================================================

class ConnectionManager:
    """WebSocket connection manager."""

    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, channel: str) -> None:
        await ws.accept()
        if channel not in self.active:
            self.active[channel] = []
        self.active[channel].append(ws)

    def disconnect(self, ws: WebSocket, channel: str) -> None:
        if channel in self.active:
            self.active[channel] = [w for w in self.active[channel] if w != ws]

    async def broadcast(self, channel: str, data: dict) -> None:
        if channel in self.active:
            for ws in self.active[channel]:
                try:
                    await ws.send_json(data)
                except Exception:  # noqa: BLE001, S110
                    pass


_manager = ConnectionManager()


@app.websocket("/ws/market/{asset}")
async def websocket_market(ws: WebSocket, asset: str) -> None:
    await _manager.connect(ws, f"market:{asset}")
    provider = _get_provider()
    try:
        while True:
            resp = provider.get_ohlc(asset, "1d", 1)
            if resp.candles:
                await ws.send_json({
                    "channel": "ohlc",
                    "symbol": asset,
                    "data": {
                        "timestamp": resp.candles[0].timestamp,
                        "open": resp.candles[0].open,
                        "high": resp.candles[0].high,
                        "low": resp.candles[0].low,
                        "close": resp.candles[0].close,
                        "volume": resp.candles[0].volume,
                    },
                    "provider": resp.provider_name,
                    "is_demo": resp.is_demo,
                })
            await ws.receive_text()
    except WebSocketDisconnect:
        _manager.disconnect(ws, f"market:{asset}")
