"""M27 WebSocket Streaming Tests.

Tests for the WebSocket streaming endpoint, message protocol,
subscription management, heartbeat, and connection lifecycle.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import aurora.market.stream as stream_mod
from aurora.market.stream import (
    HEARTBEAT_INTERVAL,
    MAX_SUBSCRIPTIONS_PER_CLIENT,
    PROTOCOL_VERSION,
    SERVER_VERSION,
    VALID_TIMEFRAMES,
    ClientState,
    StreamManager,
    _handle_message,
    _handle_subscribe,
    _handle_unsubscribe,
    _send_error,
    _send_initial_data,
    _send_pong,
    _sub_key,
)


def _make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ============================================================
# Protocol Constants
# ============================================================


class TestProtocolConstants:
    def test_protocol_version(self):
        assert PROTOCOL_VERSION == 1

    def test_server_version(self):
        assert SERVER_VERSION == "0.3.0"

    def test_heartbeat_interval(self):
        assert HEARTBEAT_INTERVAL == 30

    def test_max_subscriptions(self):
        assert MAX_SUBSCRIPTIONS_PER_CLIENT == 10

    def test_valid_timeframes(self):
        expected = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"}
        assert VALID_TIMEFRAMES == expected


# ============================================================
# Sub Key
# ============================================================


class TestSubKey:
    def test_basic(self):
        assert _sub_key("BTC-USD", "1d") == "BTC-USD:1d"

    def test_intraday(self):
        assert _sub_key("SPY", "5m") == "SPY:5m"

    def test_weekly(self):
        assert _sub_key("QQQ", "1w") == "QQQ:1w"


# ============================================================
# StreamManager
# ============================================================


class TestStreamManager:
    def test_init(self):
        mgr = StreamManager()
        assert mgr.clients == {}
        assert mgr._background_task is None

    def test_register(self):
        mgr = StreamManager()
        ws = _make_ws()
        state = mgr.register(ws, "client-1")
        assert isinstance(state, ClientState)
        assert state.ws is ws
        assert state.client_id == "client-1"
        assert "client-1" in mgr.clients

    def test_unregister(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "client-1")
        mgr.unregister("client-1")
        assert "client-1" not in mgr.clients

    def test_unregister_nonexistent(self):
        mgr = StreamManager()
        mgr.unregister("nonexistent")

    def test_subscribe(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        assert mgr.subscribe("c1", "BTC-USD", "1d") is True
        state = mgr.clients["c1"]
        assert "BTC-USD:1d" in state.subscriptions

    def test_subscribe_nonexistent_client(self):
        mgr = StreamManager()
        assert mgr.subscribe("nope", "BTC-USD", "1d") is False

    def test_subscribe_max_reached(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        for i in range(MAX_SUBSCRIPTIONS_PER_CLIENT):
            mgr.subscribe("c1", f"ASSET{i}", "1d")
        assert mgr.subscribe("c1", "OVERFLOW", "1d") is False

    def test_unsubscribe(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        assert mgr.unsubscribe("c1", "BTC-USD", "1d") is True
        state = mgr.clients["c1"]
        assert "BTC-USD:1d" not in state.subscriptions

    def test_unsubscribe_nonexistent(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        assert mgr.unsubscribe("c1", "BTC-USD", "1d") is False

    def test_get_all_subscriptions(self):
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.register(ws2, "c2")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c2", "BTC-USD", "1d")
        mgr.subscribe("c2", "SPY", "1h")
        subs = mgr.get_all_subscriptions()
        assert subs == {("BTC-USD", "1d"), ("SPY", "1h")}

    def test_get_subscribers(self):
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.register(ws2, "c2")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c2", "BTC-USD", "1d")
        mgr.subscribe("c2", "SPY", "1h")
        subs = mgr.get_subscribers("BTC-USD", "1d")
        assert len(subs) == 2
        subs_sp = mgr.get_subscribers("SPY", "1h")
        assert len(subs_sp) == 1

    def test_multiple_subscriptions(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c1", "SPY", "1h")
        mgr.subscribe("c1", "QQQ", "1w")
        state = mgr.clients["c1"]
        assert len(state.subscriptions) == 3

    def test_reconnect_replaces_client(self):
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.unregister("c1")
        mgr.register(ws2, "c1")
        assert "c1" in mgr.clients
        assert len(mgr.clients["c1"].subscriptions) == 0


# ============================================================
# ClientState
# ============================================================


class TestClientState:
    def test_init(self):
        ws = _make_ws()
        state = ClientState(ws=ws, client_id="test-1")
        assert state.ws is ws
        assert state.client_id == "test-1"
        assert state.subscriptions == {}
        assert state.connected_at > 0
        assert state.last_pong > 0


# ============================================================
# Message Handling
# ============================================================


class TestHandleMessage:
    @pytest.mark.asyncio
    async def test_invalid_json(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_message("c1", "not json")
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "error"
        assert call["code"] == "INVALID_JSON"

    @pytest.mark.asyncio
    async def test_unknown_type(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        msg = json.dumps({"type": "unknown_thing"})
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_message("c1", msg)
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "error"
        assert call["code"] == "UNKNOWN_MESSAGE_TYPE"

    @pytest.mark.asyncio
    async def test_ping(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        msg = json.dumps({"type": "ping", "timestamp": 12345})
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_message("c1", msg)
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "pong"
        assert call["timestamp"] == 12345


# ============================================================
# Subscribe Handling
# ============================================================


class TestHandleSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_success(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        msg = {"asset": "BTC-USD", "timeframe": "1d", "request_id": "r1"}
        with patch.object(stream_mod, "_manager", mgr), \
             patch("aurora.market.stream.create_provider") as mock_create:
            provider = MagicMock()
            resp = MagicMock()
            resp.source_status = "error"
            provider.get_ohlc.return_value = resp
            mock_create.return_value = provider
            await _handle_subscribe("c1", msg, "r1")
        assert ws.send_json.call_count >= 1
        first_call = ws.send_json.call_args_list[0][0][0]
        assert first_call["type"] == "subscribed"
        assert first_call["asset"] == "BTC-USD"
        assert first_call["timeframe"] == "1d"

    @pytest.mark.asyncio
    async def test_subscribe_missing_asset(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        msg = {"timeframe": "1d", "request_id": "r1"}
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_subscribe("c1", msg, "r1")
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "error"
        assert call["code"] == "MISSING_ASSET"

    @pytest.mark.asyncio
    async def test_subscribe_invalid_timeframe(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        msg = {"asset": "BTC-USD", "timeframe": "2h", "request_id": "r1"}
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_subscribe("c1", msg, "r1")
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "error"
        assert call["code"] == "INVALID_TIMEFRAME"

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_client(self):
        mgr = StreamManager()
        msg = {"asset": "BTC-USD", "timeframe": "1d", "request_id": "r1"}
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_subscribe("nope", msg, "r1")


# ============================================================
# Unsubscribe Handling
# ============================================================


class TestHandleUnsubscribe:
    @pytest.mark.asyncio
    async def test_unsubscribe_success(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        msg = {"asset": "BTC-USD", "timeframe": "1d", "request_id": "r1"}
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_unsubscribe("c1", msg, "r1")
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "unsubscribed"
        assert call["asset"] == "BTC-USD"

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_client(self):
        mgr = StreamManager()
        msg = {"asset": "BTC-USD", "timeframe": "1d"}
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_unsubscribe("nope", msg, "r1")


# ============================================================
# Error Sending
# ============================================================


class TestSendError:
    @pytest.mark.asyncio
    async def test_send_error(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        with patch.object(stream_mod, "_manager", mgr):
            await _send_error("c1", "TEST_ERROR", "test message", "r1")
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "error"
        assert call["code"] == "TEST_ERROR"
        assert call["message"] == "test message"
        assert call["request_id"] == "r1"

    @pytest.mark.asyncio
    async def test_send_error_nonexistent_client(self):
        mgr = StreamManager()
        with patch.object(stream_mod, "_manager", mgr):
            await _send_error("nope", "TEST_ERROR", "msg", "r1")


# ============================================================
# Pong Sending
# ============================================================


class TestSendPong:
    @pytest.mark.asyncio
    async def test_send_pong(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        with patch.object(stream_mod, "_manager", mgr):
            await _send_pong("c1", 12345)
        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "pong"
        assert call["timestamp"] == 12345
        assert "server_timestamp" in call

    @pytest.mark.asyncio
    async def test_send_pong_nonexistent_client(self):
        mgr = StreamManager()
        with patch.object(stream_mod, "_manager", mgr):
            await _send_pong("nope", 12345)


# ============================================================
# Initial Data Sending
# ============================================================


class TestSendInitialData:
    @pytest.mark.asyncio
    async def test_send_initial_data(self):
        mgr = StreamManager()
        ws = _make_ws()
        client = mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")

        candle = MagicMock()
        candle.timestamp = "2026-01-01T00:00:00"
        candle.open = 100.0
        candle.high = 110.0
        candle.low = 95.0
        candle.close = 105.0
        candle.volume = 1000.0

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        with patch.object(stream_mod, "_manager", mgr), \
             patch("aurora.market.stream.create_provider") as mock_create:
            provider = MagicMock()
            provider.get_ohlc.return_value = resp
            mock_create.return_value = provider
            await _send_initial_data(client, "BTC-USD", "1d")

        ws.send_json.assert_called_once()
        call = ws.send_json.call_args[0][0]
        assert call["type"] == "initial_data"
        assert call["asset"] == "BTC-USD"
        assert call["timeframe"] == "1d"
        assert call["count"] == 1
        assert call["provider"] == "yfinance"
        assert call["is_demo"] is False
        assert len(call["bars"]) == 1

    @pytest.mark.asyncio
    async def test_send_initial_data_provider_error(self):
        mgr = StreamManager()
        ws = _make_ws()
        client = mgr.register(ws, "c1")

        resp = MagicMock()
        resp.source_status = "error"

        with patch.object(stream_mod, "_manager", mgr), \
             patch("aurora.market.stream.create_provider") as mock_create:
            provider = MagicMock()
            provider.get_ohlc.return_value = resp
            mock_create.return_value = provider
            await _send_initial_data(client, "BTC-USD", "1d")

        ws.send_json.assert_not_called()


# ============================================================
# Cleanup
# ============================================================


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_stale_clients(self):
        mgr = StreamManager()
        ws = _make_ws()
        state = mgr.register(ws, "c1")
        state.last_pong = time.monotonic() - 999
        await mgr._cleanup_stale_clients()
        assert "c1" not in mgr.clients
        ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_fresh_clients(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        await mgr._cleanup_stale_clients()
        assert "c1" in mgr.clients
        ws.close.assert_not_called()


# ============================================================
# Module Docstring
# ============================================================


class TestModuleDocstring:
    def test_has_docstring(self):
        import aurora.market.stream as mod
        assert mod.__doc__ is not None
        assert "M27" in mod.__doc__
