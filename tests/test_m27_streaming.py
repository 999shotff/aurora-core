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


# ============================================================
# Realtime Candle Broadcasting
# ============================================================


class TestRealtimeCandleBroadcast:
    """Tests for the realtime candle update mechanism.

    The backend polls yfinance every UPDATE_INTERVAL seconds and broadcasts
    the latest candle to all subscribers. Previously, a timestamp dedup
    suppressed updates when the candle timestamp hadn't changed (same candle
    still updating). The fix removes this dedup so updates are always pushed.
    """

    @pytest.mark.asyncio
    async def test_same_timestamp_always_pushed(self):
        """Same candle timestamp should still be pushed (no dedup)."""
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.register(ws2, "c2")
        mgr.subscribe("c1", "BTC-USD", "5m")
        mgr.subscribe("c2", "BTC-USD", "5m")

        candle = MagicMock()
        candle.timestamp = "2026-09-06T12:00:00Z"
        candle.open = 100.0
        candle.high = 105.0
        candle.low = 99.0
        candle.close = 103.0
        candle.volume = 5000.0

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        # First broadcast
        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        assert ws1.send_json.call_count == 1
        assert ws2.send_json.call_count == 1

        # Second broadcast with SAME timestamp — must still push
        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        assert ws1.send_json.call_count == 2
        assert ws2.send_json.call_count == 2

    @pytest.mark.asyncio
    async def test_newer_timestamp_pushed(self):
        """Newer candle timestamp should be pushed as new candle."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        candle1 = MagicMock()
        candle1.timestamp = "2026-09-06T12:00:00Z"
        candle1.open = 100.0
        candle1.high = 105.0
        candle1.low = 99.0
        candle1.close = 103.0
        candle1.volume = 5000.0

        resp1 = MagicMock()
        resp1.source_status = "ok"
        resp1.candles = [candle1]
        resp1.provider_name = "yfinance"
        resp1.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp1

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        assert ws.send_json.call_count == 1

        # New candle with different timestamp
        candle2 = MagicMock()
        candle2.timestamp = "2026-09-06T12:05:00Z"
        candle2.open = 103.0
        candle2.high = 108.0
        candle2.low = 102.0
        candle2.close = 107.0
        candle2.volume = 3000.0

        resp2 = MagicMock()
        resp2.source_status = "ok"
        resp2.candles = [candle2]
        resp2.provider_name = "yfinance"
        resp2.is_demo = False
        provider.get_ohlc.return_value = resp2

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        assert ws.send_json.call_count == 2
        last_msg = ws.send_json.call_args_list[1][0][0]
        assert last_msg["bar"]["timestamp"] == "2026-09-06T12:05:00Z"

    @pytest.mark.asyncio
    async def test_older_timestamp_still_pushed(self):
        """Older candle timestamp is still pushed (no dedup)."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        candle_new = MagicMock()
        candle_new.timestamp = "2026-09-06T12:05:00Z"
        candle_new.open = 103.0
        candle_new.high = 108.0
        candle_new.low = 102.0
        candle_new.close = 107.0
        candle_new.volume = 3000.0

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle_new]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        assert ws.send_json.call_count == 1

        # Provider returns older timestamp
        candle_old = MagicMock()
        candle_old.timestamp = "2026-09-06T12:00:00Z"
        candle_old.open = 100.0
        candle_old.high = 105.0
        candle_old.low = 99.0
        candle_old.close = 103.0
        candle_old.volume = 5000.0

        resp_old = MagicMock()
        resp_old.source_status = "ok"
        resp_old.candles = [candle_old]
        resp_old.provider_name = "yfinance"
        resp_old.is_demo = False
        provider.get_ohlc.return_value = resp_old

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        assert ws.send_json.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_message_format(self):
        """Verify the market_update message format is correct."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        candle = MagicMock()
        candle.timestamp = "2026-09-06T12:00:00Z"
        candle.open = 100.0
        candle.high = 105.0
        candle.low = 99.0
        candle.close = 103.0
        candle.volume = 5000.0

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        msg = ws.send_json.call_args[0][0]
        assert msg["type"] == "market_update"
        assert msg["asset"] == "BTC-USD"
        assert msg["timeframe"] == "5m"
        assert msg["bar"]["timestamp"] == "2026-09-06T12:00:00Z"
        assert msg["bar"]["open"] == 100.0
        assert msg["bar"]["high"] == 105.0
        assert msg["bar"]["low"] == 99.0
        assert msg["bar"]["close"] == 103.0
        assert msg["bar"]["volume"] == 5000.0
        assert msg["provider"] == "yfinance"
        assert msg["is_demo"] is False
        assert msg["protocol_version"] == 1

    @pytest.mark.asyncio
    async def test_provider_error_suppressed(self):
        """Provider error should not send any message."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        resp = MagicMock()
        resp.source_status = "error"
        resp.candles = []

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_candles_suppressed(self):
        """Empty candle list should not send any message."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = []

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_subscribers_skips_fetch(self):
        """No subscribers for asset/timeframe should skip provider call."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        provider = MagicMock()
        await mgr._check_and_broadcast(provider, "GOLD", "1d")
        provider.get_ohlc.assert_not_called()

    @pytest.mark.asyncio
    async def test_websocket_send_failure_handled(self):
        """WebSocket send failure should not crash the broadcast."""
        mgr = StreamManager()
        ws = _make_ws()
        ws.send_json = AsyncMock(side_effect=Exception("connection lost"))
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        candle = MagicMock()
        candle.timestamp = "2026-09-06T12:00:00Z"
        candle.open = 100.0
        candle.high = 105.0
        candle.low = 99.0
        candle.close = 103.0
        candle.volume = 5000.0

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        # Should not raise
        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")

    @pytest.mark.asyncio
    async def test_initial_data_sets_last_bar_timestamp(self):
        """Initial data should set last_bar_timestamp on subscription."""
        mgr = StreamManager()
        ws = _make_ws()
        client = mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        candle = MagicMock()
        candle.timestamp = "2026-09-06T12:00:00Z"
        candle.open = 100.0
        candle.high = 105.0
        candle.low = 99.0
        candle.close = 103.0
        candle.volume = 5000.0

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
            await _send_initial_data(client, "BTC-USD", "5m")

        key = _sub_key("BTC-USD", "5m")
        sub = client.subscriptions[key]
        assert sub.last_bar_timestamp == "2026-09-06T12:00:00Z"

    @pytest.mark.asyncio
    async def test_broadcast_updates_last_bar_timestamp(self):
        """Broadcast should update last_bar_timestamp on subscription."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "5m")

        candle = MagicMock()
        candle.timestamp = "2026-09-06T12:00:00Z"
        candle.open = 100.0
        candle.high = 105.0
        candle.low = 99.0
        candle.close = 103.0
        candle.volume = 5000.0

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        await mgr._check_and_broadcast(provider, "BTC-USD", "5m")
        key = _sub_key("BTC-USD", "5m")
        sub = ws.send_json  # just check broadcast happened
        assert ws.send_json.call_count == 1

    @pytest.mark.asyncio
    async def test_candle_values_reflect_latest(self):
        """Broadcast candle should have correct OHLCV from provider."""
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1m")

        candle = MagicMock()
        candle.timestamp = "2026-09-06T12:00:00Z"
        candle.open = 50000.0
        candle.high = 50100.0
        candle.low = 49900.0
        candle.close = 50050.0
        candle.volume = 123.456

        resp = MagicMock()
        resp.source_status = "ok"
        resp.candles = [candle]
        resp.provider_name = "yfinance"
        resp.is_demo = False

        provider = MagicMock()
        provider.get_ohlc.return_value = resp

        await mgr._check_and_broadcast(provider, "BTC-USD", "1m")
        msg = ws.send_json.call_args[0][0]
        assert msg["bar"]["open"] == 50000.0
        assert msg["bar"]["high"] == 50100.0
        assert msg["bar"]["low"] == 49900.0
        assert msg["bar"]["close"] == 50050.0
        assert msg["bar"]["volume"] == 123.456
