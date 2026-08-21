"""WebSocket service for real-time market data streaming.

Handles subscribe/unsubscribe, latest candle, quote updates,
connection status, provider errors, reconnect handling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aurora.market.provider import MarketDataProvider


@dataclass
class WSSubscriptionState:
    """State of a WebSocket subscription."""
    asset: str
    timeframe: str
    active: bool = True
    last_update: str = ""
    error_count: int = 0


@dataclass
class WSConnectionState:
    """WebSocket connection state."""
    connected: bool = False
    subscriptions: dict[str, WSSubscriptionState] = field(default_factory=dict)
    last_ping: float = 0.0
    reconnect_count: int = 0


class MarketWebSocketService:
    """WebSocket service for market data streaming.

    Manages subscriptions, connection lifecycle, and data push.
    """

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider
        self._state = WSConnectionState()
        self._callbacks: dict[str, list[Any]] = {}

    @property
    def state(self) -> WSConnectionState:
        return self._state

    def subscribe(self, asset: str, timeframe: str = "1d") -> dict:
        """Subscribe to an asset/timeframe stream."""
        key = f"{asset}:{timeframe}"
        self._state.subscriptions[key] = WSSubscriptionState(
            asset=asset, timeframe=timeframe
        )
        return {
            "action": "subscribed",
            "asset": asset,
            "timeframe": timeframe,
            "status": "ok",
        }

    def unsubscribe(self, asset: str, timeframe: str = "1d") -> dict:
        """Unsubscribe from an asset/timeframe stream."""
        key = f"{asset}:{timeframe}"
        if key in self._state.subscriptions:
            del self._state.subscriptions[key]
        return {
            "action": "unsubscribed",
            "asset": asset,
            "timeframe": timeframe,
        }

    def get_latest_candle(self, asset: str, timeframe: str = "1d") -> dict:
        """Get latest candle for a subscribed asset."""
        resp = self._provider.get_ohlc(asset, timeframe, 1)
        if resp.source_status == "error":
            return {
                "channel": "error",
                "asset": asset,
                "timeframe": timeframe,
                "error": resp.error.message if resp.error else "Unknown error",
                "provider": resp.provider_name,
                "is_demo": resp.is_demo,
            }
        if resp.candles:
            return {
                "channel": "ohlc",
                "asset": asset,
                "timeframe": timeframe,
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
                "source_status": resp.source_status,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "channel": "no_data",
            "asset": asset,
            "timeframe": timeframe,
            "provider": resp.provider_name,
            "is_demo": resp.is_demo,
        }

    def get_connection_status(self) -> dict:
        """Get current connection status."""
        return {
            "connected": self._state.connected,
            "subscriptions": len(self._state.subscriptions),
            "reconnect_count": self._state.reconnect_count,
            "provider": self._provider.name,
            "is_demo": self._provider.is_demo,
        }

    def connect(self) -> None:
        """Mark connection as established."""
        self._state.connected = True
        self._state.last_ping = time.monotonic()

    def disconnect(self) -> None:
        """Mark connection as closed."""
        self._state.connected = False

    def handle_reconnect(self) -> dict:
        """Handle reconnection."""
        self._state.reconnect_count += 1
        self._state.connected = True
        self._state.last_ping = time.monotonic()
        return {
            "action": "reconnected",
            "attempt": self._state.reconnect_count,
            "subscriptions_restored": len(self._state.subscriptions),
        }
