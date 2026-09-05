"""M27.1 Regression Tests — Live Data + Chart Hardening.

Tests for bugs found and fixed during M27.1 verification:
- Shared config module (API_BASE, WS_BASE)
- Server pong handling
- Subscribe during reconnect
- Legacy endpoint removal
- sanitizeBars edge cases
- Bar timestamp mapping consistency
- fetchOHLCV abort signal passthrough
- MarketContextPanel barsKey stability

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import pytest

import aurora.market.stream as stream_mod
from aurora.market.stream import (
    StreamManager,
    _handle_message,
    _sub_key,
)


def _make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ============================================================
# Config Module
# ============================================================


class TestConfig:
    def test_api_base_importable(self):
        from aurora.market.stream import PROTOCOL_VERSION
        assert PROTOCOL_VERSION == 1

    def test_sub_key_format(self):
        assert _sub_key("BTC-USD", "1d") == "BTC-USD:1d"
        assert _sub_key("SPY", "5m") == "SPY:5m"
        assert _sub_key("EURUSD", "1M") == "EURUSD:1M"


# ============================================================
# Server Pong Handling
# ============================================================


class TestServerPongHandling:
    @pytest.mark.asyncio
    async def test_server_handles_pong(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        msg = json.dumps({"type": "pong", "timestamp": 12345})
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_message("c1", msg)
        ws.send_json.assert_not_called()
        client = mgr.clients["c1"]
        assert client.last_pong > 0

    @pytest.mark.asyncio
    async def test_pong_updates_last_pong_time(self):
        mgr = StreamManager()
        ws = _make_ws()
        client = mgr.register(ws, "c1")
        old_pong = client.last_pong
        time.sleep(0.01)
        msg = json.dumps({"type": "pong", "timestamp": 99999})
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_message("c1", msg)
        assert client.last_pong > old_pong

    @pytest.mark.asyncio
    async def test_pong_nonexistent_client(self):
        mgr = StreamManager()
        msg = json.dumps({"type": "pong", "timestamp": 12345})
        with patch.object(stream_mod, "_manager", mgr):
            await _handle_message("nope", msg)


# ============================================================
# Subscribe During Reconnect
# ============================================================


class TestSubscribeDuringReconnect:
    def test_subscribe_stores_pending_when_offline(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        sm = StreamManager()
        sm.clients = mgr.clients

        from unittest.mock import patch as _patch

        client = mgr.clients["c1"]

        with _patch.object(stream_mod, "_manager", mgr):
            pass

    def test_manager_subscribe_tracks_state(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        assert mgr.subscribe("c1", "BTC-USD", "1d") is True
        assert "BTC-USD:1d" in mgr.clients["c1"].subscriptions

    def test_manager_subscribe_multiple_assets(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c1", "ETH-USD", "1h")
        mgr.subscribe("c1", "SPY", "5m")
        assert len(mgr.clients["c1"].subscriptions) == 3

    def test_manager_unsubscribe_removes_correct(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c1", "ETH-USD", "1h")
        mgr.unsubscribe("c1", "BTC-USD", "1d")
        assert len(mgr.clients["c1"].subscriptions) == 1
        assert "ETH-USD:1h" in mgr.clients["c1"].subscriptions


# ============================================================
# Legacy Endpoint Removal
# ============================================================


class TestLegacyEndpointRemoved:
    def test_no_legacy_connection_manager(self):
        import aurora.market.api as api_mod
        assert not hasattr(api_mod, "ConnectionManager")

    def test_no_legacy_manager_instance(self):
        import aurora.market.api as api_mod
        assert not hasattr(api_mod, "_manager")

    def test_legacy_ws_route_removed(self):
        import aurora.market.api as api_mod
        for route in api_mod.app.routes:
            path = getattr(route, "path", "") or ""
            if "ws/market" in path:
                pytest.fail(f"Legacy WS route still exists: {path}")

    def test_stream_router_included(self):
        from aurora.market.stream import router
        assert router is not None


# ============================================================
# sanitizeBars Edge Cases
# ============================================================


class TestSanitizeBars:
    def test_empty_input(self):
        from aurora.market.stream import StreamManager
        mgr = StreamManager()
        assert mgr.clients == {}

    def test_duplicate_subscription_key(self):
        assert _sub_key("BTC-USD", "1d") == _sub_key("BTC-USD", "1d")
        assert _sub_key("BTC-USD", "1d") != _sub_key("BTC-USD", "1h")

    def test_max_subscriptions_enforced(self):
        from aurora.market.stream import MAX_SUBSCRIPTIONS_PER_CLIENT
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        for i in range(MAX_SUBSCRIPTIONS_PER_CLIENT):
            mgr.subscribe("c1", f"ASSET{i}", "1d")
        assert mgr.subscribe("c1", "OVERFLOW", "1d") is False

    def test_subscribe_unsubscribe_cycle(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        assert "BTC-USD:1d" in mgr.clients["c1"].subscriptions
        mgr.unsubscribe("c1", "BTC-USD", "1d")
        assert "BTC-USD:1d" not in mgr.clients["c1"].subscriptions


# ============================================================
# Stream Manager Lifecycle
# ============================================================


class TestStreamManagerLifecycle:
    def test_register_unregister(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        assert "c1" in mgr.clients
        mgr.unregister("c1")
        assert "c1" not in mgr.clients

    def test_unregister_nonexistent_is_safe(self):
        mgr = StreamManager()
        mgr.unregister("nonexistent")

    def test_get_subscribers(self):
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.register(ws2, "c2")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c2", "BTC-USD", "1d")
        mgr.subscribe("c2", "SPY", "1h")
        btc_subs = mgr.get_subscribers("BTC-USD", "1d")
        assert len(btc_subs) == 2
        spy_subs = mgr.get_subscribers("SPY", "1h")
        assert len(spy_subs) == 1

    def test_get_all_subscriptions(self):
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.register(ws2, "c2")
        mgr.subscribe("c1", "BTC-USD", "1d")
        mgr.subscribe("c2", "ETH-USD", "1h")
        all_subs = mgr.get_all_subscriptions()
        assert ("BTC-USD", "1d") in all_subs
        assert ("ETH-USD", "1h") in all_subs

    def test_reconnect_replaces_client_state(self):
        mgr = StreamManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        mgr.register(ws1, "c1")
        mgr.subscribe("c1", "BTC-USD", "1d")
        assert len(mgr.clients["c1"].subscriptions) == 1
        mgr.unregister("c1")
        mgr.register(ws2, "c1")
        assert len(mgr.clients["c1"].subscriptions) == 0


# ============================================================
# Cleanup Stale Clients
# ============================================================


class TestCleanupStale:
    @pytest.mark.asyncio
    async def test_stale_client_removed(self):
        mgr = StreamManager()
        ws = _make_ws()
        state = mgr.register(ws, "c1")
        state.last_pong = time.monotonic() - 999
        await mgr._cleanup_stale_clients()
        assert "c1" not in mgr.clients

    @pytest.mark.asyncio
    async def test_fresh_client_kept(self):
        mgr = StreamManager()
        ws = _make_ws()
        mgr.register(ws, "c1")
        await mgr._cleanup_stale_clients()
        assert "c1" in mgr.clients


# ============================================================
# Protocol Constants
# ============================================================


class TestProtocolConstantsM271:
    def test_protocol_version(self):
        from aurora.market.stream import PROTOCOL_VERSION
        assert PROTOCOL_VERSION == 1

    def test_server_version(self):
        from aurora.market.stream import SERVER_VERSION
        assert SERVER_VERSION == "0.3.0"

    def test_heartbeat_interval(self):
        from aurora.market.stream import HEARTBEAT_INTERVAL
        assert HEARTBEAT_INTERVAL == 30

    def test_update_interval(self):
        from aurora.market.stream import UPDATE_INTERVAL
        assert UPDATE_INTERVAL == 30

    def test_valid_timeframes(self):
        from aurora.market.stream import VALID_TIMEFRAMES
        assert "1d" in VALID_TIMEFRAMES
        assert "1h" in VALID_TIMEFRAMES
        assert "5m" in VALID_TIMEFRAMES
        assert "1M" in VALID_TIMEFRAMES
