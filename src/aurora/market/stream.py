"""M27 WebSocket Streaming Endpoint.

Provides live market data streaming via WebSocket.
Message protocol v1. Supports subscribe/unsubscribe, heartbeat,
and incremental market updates from real data providers.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from aurora.market.provider import create_provider

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# Constants
# ============================================================

PROTOCOL_VERSION = 1
SERVER_VERSION = "0.3.0"
HEARTBEAT_INTERVAL = 30
UPDATE_INTERVAL = 30
MAX_SUBSCRIPTIONS_PER_CLIENT = 10

VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"}


# ============================================================
# Subscription State
# ============================================================


@dataclass
class Subscription:
    asset: str
    timeframe: str
    last_bar_timestamp: str = ""
    last_check: float = 0.0


@dataclass
class ClientState:
    ws: WebSocket
    client_id: str
    subscriptions: dict[str, Subscription] = field(default_factory=dict)
    connected_at: float = field(default_factory=time.monotonic)
    last_pong: float = field(default_factory=time.monotonic)

    @property
    def subscription_key(self) -> str:
        return ""


def _sub_key(asset: str, timeframe: str) -> str:
    return f"{asset}:{timeframe}"


# ============================================================
# Connection Manager
# ============================================================


class StreamManager:
    """Manages WebSocket connections and subscriptions."""

    def __init__(self) -> None:
        self.clients: dict[str, ClientState] = {}
        self._background_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(self._update_loop())

    async def stop(self) -> None:
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

    def register(self, ws: WebSocket, client_id: str) -> ClientState:
        state = ClientState(ws=ws, client_id=client_id)
        self.clients[client_id] = state
        return state

    def unregister(self, client_id: str) -> None:
        self.clients.pop(client_id, None)

    def subscribe(self, client_id: str, asset: str, timeframe: str) -> bool:
        client = self.clients.get(client_id)
        if not client:
            return False
        if len(client.subscriptions) >= MAX_SUBSCRIPTIONS_PER_CLIENT:
            return False
        key = _sub_key(asset, timeframe)
        client.subscriptions[key] = Subscription(asset=asset, timeframe=timeframe)
        return True

    def unsubscribe(self, client_id: str, asset: str, timeframe: str) -> bool:
        client = self.clients.get(client_id)
        if not client:
            return False
        key = _sub_key(asset, timeframe)
        removed = client.subscriptions.pop(key, None)
        return removed is not None

    def get_all_subscriptions(self) -> set[tuple[str, str]]:
        result: set[tuple[str, str]] = set()
        for client in self.clients.values():
            for sub in client.subscriptions.values():
                result.add((sub.asset, sub.timeframe))
        return result

    def get_subscribers(self, asset: str, timeframe: str) -> list[ClientState]:
        key = _sub_key(asset, timeframe)
        return [
            c for c in self.clients.values()
            if key in c.subscriptions
        ]

    async def _update_loop(self) -> None:
        provider = create_provider()
        while True:
            try:
                await asyncio.sleep(UPDATE_INTERVAL)
                subs = self.get_all_subscriptions()
                for asset, timeframe in subs:
                    await self._check_and_broadcast(provider, asset, timeframe)
                await self._cleanup_stale_clients()
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001
                logger.exception("Error in update loop")
                await asyncio.sleep(5)

    async def _check_and_broadcast(
        self, provider: Any, asset: str, timeframe: str,
    ) -> None:
        subscribers = self.get_subscribers(asset, timeframe)
        if not subscribers:
            return
        try:
            resp = provider.get_ohlc(asset, timeframe, 1)
            if resp.source_status == "error" or not resp.candles:
                return
            candle = resp.candles[0]
            bar_ts = candle.timestamp
            for client in subscribers:
                key = _sub_key(asset, timeframe)
                sub = client.subscriptions.get(key)
                if not sub:
                    continue
                if sub.last_bar_timestamp == bar_ts:
                    continue
                sub.last_bar_timestamp = bar_ts
                sub.last_check = time.monotonic()
                msg = {
                    "type": "market_update",
                    "asset": asset,
                    "timeframe": timeframe,
                    "bar": {
                        "timestamp": candle.timestamp,
                        "open": candle.open,
                        "high": candle.high,
                        "low": candle.low,
                        "close": candle.close,
                        "volume": candle.volume,
                    },
                    "provider": resp.provider_name,
                    "is_demo": resp.is_demo,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "protocol_version": PROTOCOL_VERSION,
                }
                try:
                    await client.ws.send_json(msg)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            logger.debug("Failed to fetch data for %s %s", asset, timeframe)

    async def _cleanup_stale_clients(self) -> None:
        now = time.monotonic()
        stale = [
            cid for cid, c in self.clients.items()
            if now - c.last_pong > HEARTBEAT_INTERVAL * 3
        ]
        for cid in stale:
            client = self.clients.pop(cid, None)
            if client:
                try:
                    await client.ws.close()
                except Exception:  # noqa: BLE001
                    pass


_manager = StreamManager()


# ============================================================
# Message Handling
# ============================================================


async def _handle_message(client_id: str, raw: str) -> None:
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await _send_error(client_id, "INVALID_JSON", "Malformed JSON message")
        return

    msg_type = msg.get("type", "")
    request_id = msg.get("request_id", str(uuid.uuid4()))

    if msg_type == "ping":
        await _send_pong(client_id, msg.get("timestamp", 0))
    elif msg_type == "subscribe":
        await _handle_subscribe(client_id, msg, request_id)
    elif msg_type == "unsubscribe":
        await _handle_unsubscribe(client_id, msg, request_id)
    else:
        await _send_error(client_id, "UNKNOWN_MESSAGE_TYPE", f"Unknown type: {msg_type}", request_id)


async def _handle_subscribe(client_id: str, msg: dict, request_id: str) -> None:
    asset = msg.get("asset", "")
    timeframe = msg.get("timeframe", "1d")

    if not asset:
        await _send_error(client_id, "MISSING_ASSET", "Asset is required", request_id)
        return
    if timeframe not in VALID_TIMEFRAMES:
        await _send_error(client_id, "INVALID_TIMEFRAME", f"Invalid timeframe: {timeframe}", request_id)
        return

    client = _manager.clients.get(client_id)
    if not client:
        return

    if _manager.subscribe(client_id, asset, timeframe):
        await client.ws.send_json({
            "type": "subscribed",
            "asset": asset,
            "timeframe": timeframe,
            "request_id": request_id,
            "protocol_version": PROTOCOL_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await _send_initial_data(client, asset, timeframe)
    else:
        await _send_error(client_id, "SUBSCRIBE_FAILED", "Max subscriptions reached or client not found", request_id)


async def _send_initial_data(client: ClientState, asset: str, timeframe: str) -> None:
    try:
        provider = create_provider()
        resp = provider.get_ohlc(asset, timeframe, 200)
        if resp.source_status != "error" and resp.candles:
            bars = [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in resp.candles
            ]
            key = _sub_key(asset, timeframe)
            sub = client.subscriptions.get(key)
            if sub and resp.candles:
                sub.last_bar_timestamp = resp.candles[-1].timestamp

            await client.ws.send_json({
                "type": "initial_data",
                "asset": asset,
                "timeframe": timeframe,
                "bars": bars,
                "count": len(bars),
                "provider": resp.provider_name,
                "is_demo": resp.is_demo,
                "protocol_version": PROTOCOL_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:  # noqa: BLE001
        logger.debug("Failed to send initial data for %s %s", asset, timeframe)


async def _handle_unsubscribe(client_id: str, msg: dict, request_id: str) -> None:
    asset = msg.get("asset", "")
    timeframe = msg.get("timeframe", "1d")
    client = _manager.clients.get(client_id)
    if not client:
        return
    _manager.unsubscribe(client_id, asset, timeframe)
    await client.ws.send_json({
        "type": "unsubscribed",
        "asset": asset,
        "timeframe": timeframe,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def _send_pong(client_id: str, client_timestamp: int) -> None:
    client = _manager.clients.get(client_id)
    if client:
        client.last_pong = time.monotonic()
        await client.ws.send_json({
            "type": "pong",
            "timestamp": client_timestamp,
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        })


async def _send_error(client_id: str, code: str, message: str, request_id: str = "") -> None:
    client = _manager.clients.get(client_id)
    if client:
        try:
            await client.ws.send_json({
                "type": "error",
                "code": code,
                "message": message,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:  # noqa: BLE001
            pass


# ============================================================
# WebSocket Endpoint
# ============================================================


@router.websocket("/ws/stream")
async def stream_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    client_id = str(uuid.uuid4())
    client = _manager.register(ws, client_id)

    await _manager.start()

    try:
        await ws.send_json({
            "type": "connected",
            "server_id": "aurora-core",
            "version": SERVER_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "client_id": client_id,
            "heartbeat_interval": HEARTBEAT_INTERVAL,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            try:
                raw = await asyncio.wait_for(
                    ws.receive_text(),
                    timeout=HEARTBEAT_INTERVAL * 2,
                )
                await _handle_message(client_id, raw)
            except asyncio.TimeoutError:
                try:
                    await ws.send_json({
                        "type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "server_initiated": True,
                    })
                except Exception:  # noqa: BLE001
                    break
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.debug("WebSocket error for client %s", client_id)
    finally:
        _manager.unregister(client_id)
