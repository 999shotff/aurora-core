"""Tests for Milestone 18: Market Data Backend + WebSocket Pipeline.

Comprehensive tests covering:
- Provider interface, demo provider, real provider adapter
- OHLC normalization, validation, timestamp ordering, duplicates
- REST endpoints, WebSocket subscriptions, reconnect
- Provider errors, rate limiting, cache behavior
- LIVE/DEMO status, research firewall
"""

import time

from aurora.market.cache import BoundedCache
from aurora.market.errors import (
    ERROR_INVALID_ASSET,
    ERROR_RATE_LIMIT,
    error_with_context,
)
from aurora.market.normalization import normalize_and_validate
from aurora.market.provenance import create_provenance
from aurora.market.provider import (
    CandleData,
    DemoMarketDataProvider,
    ProviderError,
    RealMarketDataProvider,
    create_provider,
)
from aurora.market.rate_limiter import RateLimiter, RequestThrottler, RetryPolicy
from aurora.market.ws import MarketWebSocketService

# ============================================================
# CandleData Tests
# ============================================================

class TestCandleData:
    def test_candle_creation(self):
        c = CandleData(timestamp="2024-01-01T00:00:00Z", open=100, high=105, low=95, close=102, volume=1000)
        assert c.open == 100
        assert c.close == 102

    def test_candle_frozen(self):
        c = CandleData(timestamp="2024-01-01T00:00:00Z", open=100, high=105, low=95, close=102, volume=1000)
        try:
            c.open = 200  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass


# ============================================================
# Demo Provider Tests
# ============================================================

class TestDemoProvider:
    def test_provider_name(self):
        p = DemoMarketDataProvider()
        assert p.name == "demo"

    def test_is_demo(self):
        p = DemoMarketDataProvider()
        assert p.is_demo is True

    def test_get_ohlc(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("BTC-USD", "1d", 100)
        assert resp.source_status == "ok"
        assert resp.is_demo is True
        assert resp.provider_name == "demo"
        assert len(resp.candles) == 100

    def test_get_ohlc_unknown_asset(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("NONEXISTENT", "1d", 10)
        assert resp.source_status == "error"
        assert resp.error is not None
        assert resp.error.code == "INVALID_ASSET"

    def test_get_latest_quote(self):
        p = DemoMarketDataProvider()
        resp = p.get_latest_quote("BTC-USD")
        assert resp.source_status == "ok"
        assert len(resp.candles) == 1

    def test_get_asset_metadata(self):
        p = DemoMarketDataProvider()
        meta = p.get_asset_metadata("BTC-USD")
        assert meta is not None
        assert meta["symbol"] == "BTC-USD"

    def test_get_asset_metadata_unknown(self):
        p = DemoMarketDataProvider()
        meta = p.get_asset_metadata("NONEXISTENT")
        assert meta is None

    def test_get_available_timeframes(self):
        p = DemoMarketDataProvider()
        tfs = p.get_available_timeframes("BTC-USD")
        assert "1d" in tfs
        assert "1h" in tfs
        assert "1w" in tfs

    def test_get_available_timeframes_unknown(self):
        p = DemoMarketDataProvider()
        tfs = p.get_available_timeframes("NONEXISTENT")
        assert tfs == []

    def test_candles_have_positive_prices(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("SPY", "1d", 50)
        for c in resp.candles:
            assert c.open > 0
            assert c.high > 0
            assert c.low > 0
            assert c.close > 0

    def test_candles_high_gte_low(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("QQQ", "1d", 50)
        for c in resp.candles:
            assert c.high >= c.low

    def test_candles_high_gte_open_close(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("GOLD", "1d", 50)
        for c in resp.candles:
            assert c.high >= c.open
            assert c.high >= c.close

    def test_candles_low_lte_open_close(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("SILVER", "1d", 50)
        for c in resp.candles:
            assert c.low <= c.open
            assert c.low <= c.close


# ============================================================
# Real Provider Tests
# ============================================================

class TestRealProvider:
    def test_provider_name(self):
        p = RealMarketDataProvider()
        assert p.name == "yfinance"

    def test_is_not_demo(self):
        p = RealMarketDataProvider()
        assert p.is_demo is False

    def test_get_ohlc_unknown_asset(self):
        p = RealMarketDataProvider()
        resp = p.get_ohlc("NONEXISTENT", "1d", 10)
        assert resp.source_status == "error"
        assert resp.error is not None
        assert resp.error.code == "INVALID_ASSET"

    def test_get_ohlc_invalid_timeframe(self):
        p = RealMarketDataProvider()
        resp = p.get_ohlc("BTC-USD", "2h", 10)
        assert resp.source_status == "error"
        assert resp.error is not None
        assert resp.error.code == "INVALID_TIMEFRAME"

    def test_get_available_timeframes(self):
        p = RealMarketDataProvider()
        tfs = p.get_available_timeframes("BTC-USD")
        assert "1d" in tfs
        assert "1h" in tfs

    def test_get_available_timeframes_unknown(self):
        p = RealMarketDataProvider()
        tfs = p.get_available_timeframes("NONEXISTENT")
        assert tfs == []


# ============================================================
# Provider Factory Tests
# ============================================================

class TestProviderFactory:
    def test_create_demo(self):
        p = create_provider("demo")
        assert isinstance(p, DemoMarketDataProvider)

    def test_create_real(self):
        p = create_provider("real")
        assert isinstance(p, RealMarketDataProvider)

    def test_create_yfinance(self):
        p = create_provider("yfinance")
        assert isinstance(p, RealMarketDataProvider)

    def test_create_default(self):
        p = create_provider(None)
        assert isinstance(p, (DemoMarketDataProvider, RealMarketDataProvider))


# ============================================================
# Normalization Tests
# ============================================================

class TestNormalization:
    def test_valid_candles(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 105, 95, 102, 1000),
            CandleData("2024-01-02T00:00:00Z", 102, 108, 99, 106, 1200),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is True
        assert len(result.candles) == 2
        assert result.rejected_count == 0

    def test_empty_candles(self):
        result = normalize_and_validate([])
        assert result.valid is True
        assert len(result.candles) == 0

    def test_negative_price_rejected(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", -100, 105, 95, 102, 1000),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False
        assert result.rejected_count == 1
        assert any("positive" in e for e in result.errors)

    def test_zero_price_rejected(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 0, 105, 95, 102, 1000),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False

    def test_high_lt_low_rejected(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 90, 95, 102, 1000),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False
        assert any("high" in e.lower() and "low" in e.lower() for e in result.errors)

    def test_high_lt_open_rejected(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 95, 90, 102, 1000),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False

    def test_low_gt_close_rejected(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 110, 105, 102, 1000),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False

    def test_negative_volume_rejected(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 105, 95, 102, -100),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False
        assert any("volume" in e for e in result.errors)

    def test_duplicate_timestamp_removed(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 105, 95, 102, 1000),
            CandleData("2024-01-01T00:00:00Z", 103, 108, 100, 106, 1200),
        ]
        result = normalize_and_validate(candles)
        assert len(result.candles) == 1
        assert any("Duplicate" in e for e in result.errors)

    def test_timestamp_ordering(self):
        candles = [
            CandleData("2024-01-02T00:00:00Z", 100, 105, 95, 102, 1000),
            CandleData("2024-01-01T00:00:00Z", 103, 108, 100, 106, 1200),
        ]
        result = normalize_and_validate(candles)
        assert len(result.errors) > 0 or result.rejected_count > 0

    def test_naive_timestamp_rejected(self):
        candles = [
            CandleData("2024-01-01", 100, 105, 95, 102, 1000),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is False

    def test_valid_candles_passed_through(self):
        candles = [
            CandleData("2024-01-01T00:00:00Z", 100, 105, 95, 102, 1000),
            CandleData("2024-01-02T00:00:00Z", 102, 108, 99, 106, 1200),
            CandleData("2024-01-03T00:00:00Z", 106, 112, 103, 110, 1500),
        ]
        result = normalize_and_validate(candles)
        assert result.valid is True
        assert len(result.candles) == 3
        assert result.candles[0].close == 102
        assert result.candles[1].close == 106
        assert result.candles[2].close == 110


# ============================================================
# Provenance Tests
# ============================================================

class TestProvenance:
    def test_create_provenance(self):
        p = create_provenance(
            provider="demo", asset="BTC-USD", timeframe="1d",
            is_demo=True, source_status="ok", candle_count=100,
        )
        assert p.provider == "demo"
        assert p.asset == "BTC-USD"
        assert p.is_demo is True
        assert p.candle_count == 100

    def test_provenance_with_errors(self):
        p = create_provenance(
            provider="yfinance", asset="BTC-USD", timeframe="1d",
            is_demo=False, source_status="error",
            error_code="NO_DATA", error_message="No data",
        )
        assert p.source_status == "error"
        assert p.error_code == "NO_DATA"

    def test_provenance_is_frozen(self):
        p = create_provenance(
            provider="demo", asset="BTC-USD", timeframe="1d",
            is_demo=True, source_status="ok",
        )
        try:
            p.provider = "changed"  # type: ignore[misc]
            assert False, "Should be frozen"
        except AttributeError:
            pass


# ============================================================
# Cache Tests
# ============================================================

class TestCache:
    def test_put_and_get(self):
        cache = BoundedCache(max_size=10, default_ttl=60)
        cache.put("key1", {"data": "value1"})
        result = cache.get("key1")
        assert result == {"data": "value1"}

    def test_get_miss(self):
        cache = BoundedCache(max_size=10, default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_eviction_on_size(self):
        cache = BoundedCache(max_size=3, default_ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_ttl_expiration(self):
        cache = BoundedCache(max_size=10, default_ttl=0.01)
        cache.put("key1", "value1")
        time.sleep(0.02)
        assert cache.get("key1") is None

    def test_invalidate(self):
        cache = BoundedCache(max_size=10, default_ttl=60)
        cache.put("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None
        assert cache.invalidate("key1") is False

    def test_invalidate_prefix(self):
        cache = BoundedCache(max_size=10, default_ttl=60)
        cache.put("ohlc:BTC:1d", "data1")
        cache.put("ohlc:ETH:1d", "data2")
        cache.put("quote:BTC", "data3")
        count = cache.invalidate_prefix("ohlc:")
        assert count == 2
        assert cache.get("ohlc:BTC:1d") is None
        assert cache.get("quote:BTC") == "data3"

    def test_clear(self):
        cache = BoundedCache(max_size=10, default_ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_lru_order(self):
        cache = BoundedCache(max_size=3, default_ttl=60)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")
        cache.put("d", 4)
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_size_and_capacity(self):
        cache = BoundedCache(max_size=5, default_ttl=60)
        assert cache.size == 0
        assert cache.capacity == 5


# ============================================================
# Rate Limiter Tests
# ============================================================

class TestRateLimiter:
    def test_acquire_within_burst(self):
        rl = RateLimiter(requests_per_minute=60, burst=5)
        for _ in range(5):
            assert rl.acquire() is True

    def test_acquire_exceeds_burst(self):
        rl = RateLimiter(requests_per_minute=60, burst=2)
        assert rl.acquire() is True
        assert rl.acquire() is True
        assert rl.acquire() is False

    def test_wait_time(self):
        rl = RateLimiter(requests_per_minute=60, burst=1)
        assert rl.acquire() is True
        wt = rl.wait_time()
        assert wt > 0

    def test_refill(self):
        rl = RateLimiter(requests_per_minute=600, burst=1)
        assert rl.acquire() is True
        assert rl.acquire() is False
        time.sleep(0.12)
        assert rl.acquire() is True


class TestRetryPolicy:
    def test_retry_delays(self):
        rp = RetryPolicy(max_retries=3, base_delay=1.0)
        d1 = rp.delay()
        d2 = rp.delay()
        d3 = rp.delay()
        assert d1 < d2 < d3

    def test_should_retry(self):
        rp = RetryPolicy(max_retries=2)
        assert rp.should_retry is True
        rp.delay()
        assert rp.should_retry is True
        rp.delay()
        assert rp.should_retry is False

    def test_reset(self):
        rp = RetryPolicy(max_retries=3)
        rp.delay()
        rp.delay()
        rp.reset()
        assert rp.should_retry is True


class TestRequestThrottler:
    def test_can_request(self):
        t = RequestThrottler()
        assert t.can_request("demo") is True

    def test_per_provider(self):
        t = RequestThrottler()
        t.get_limiter("a").burst = 1
        t.get_limiter("b").burst = 10
        assert t.can_request("a") is True
        assert t.can_request("a") is False
        assert t.can_request("b") is True


# ============================================================
# Error Tests
# ============================================================

class TestErrors:
    def test_error_attributes(self):
        e = ERROR_INVALID_ASSET
        assert e.code == "INVALID_ASSET"
        assert e.retryable is False

    def test_error_with_context(self):
        e = error_with_context(
            ERROR_INVALID_ASSET,
            provider="yfinance",
            asset="BTC-USD",
            message="Custom message",
        )
        assert e.provider == "yfinance"
        assert e.asset == "BTC-USD"
        assert e.message == "Custom message"

    def test_rate_limit_error(self):
        e = ERROR_RATE_LIMIT
        assert e.retryable is True
        assert e.status_code == 429


# ============================================================
# WebSocket Service Tests
# ============================================================

class TestWebSocketService:
    def test_subscribe(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        result = svc.subscribe("BTC-USD", "1d")
        assert result["action"] == "subscribed"
        assert result["status"] == "ok"

    def test_unsubscribe(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        svc.subscribe("BTC-USD", "1d")
        result = svc.unsubscribe("BTC-USD", "1d")
        assert result["action"] == "unsubscribed"

    def test_get_latest_candle(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        result = svc.get_latest_candle("BTC-USD", "1d")
        assert result["channel"] == "ohlc"
        assert result["is_demo"] is True

    def test_get_latest_candle_unknown(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        result = svc.get_latest_candle("NONEXISTENT", "1d")
        assert result["channel"] == "error"

    def test_connection_status(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        status = svc.get_connection_status()
        assert status["connected"] is False
        assert status["is_demo"] is True

    def test_connect_disconnect(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        svc.connect()
        assert svc.state.connected is True
        svc.disconnect()
        assert svc.state.connected is False

    def test_reconnect(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        result = svc.handle_reconnect()
        assert result["action"] == "reconnected"
        assert result["attempt"] == 1
        assert svc.state.connected is True

    def test_multiple_subscriptions(self):
        p = DemoMarketDataProvider()
        svc = MarketWebSocketService(p)
        svc.subscribe("BTC-USD", "1d")
        svc.subscribe("ETH-USD", "1h")
        svc.subscribe("SPY", "1d")
        assert len(svc.state.subscriptions) == 3


# ============================================================
# Research Firewall Tests
# ============================================================

class TestResearchFirewall:
    def test_no_prediction_in_response(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("BTC-USD", "1d", 10)
        resp_dict = {
            "provider": resp.provider_name,
            "is_demo": resp.is_demo,
            "source_status": resp.source_status,
        }
        for value in resp_dict.values():
            assert "prediction" not in str(value).lower()
            assert "buy" not in str(value).lower()
            assert "sell" not in str(value).lower()
            assert "recommend" not in str(value).lower()

    def test_provider_is_demo_or_real(self):
        demo = DemoMarketDataProvider()
        real = RealMarketDataProvider()
        assert demo.is_demo is True
        assert real.is_demo is False

    def test_provenance_has_is_demo(self):
        p = create_provenance(
            provider="demo", asset="BTC-USD", timeframe="1d",
            is_demo=True, source_status="ok",
        )
        assert p.is_demo is True
        assert "prediction" not in str(p).lower()


# ============================================================
# Provider Protocol Compliance Tests
# ============================================================

class TestProviderProtocol:
    def test_demo_implements_protocol(self):
        p = DemoMarketDataProvider()
        assert hasattr(p, "name")
        assert hasattr(p, "is_demo")
        assert hasattr(p, "get_ohlc")
        assert hasattr(p, "get_latest_quote")
        assert hasattr(p, "get_asset_metadata")
        assert hasattr(p, "get_available_timeframes")

    def test_real_implements_protocol(self):
        p = RealMarketDataProvider()
        assert hasattr(p, "name")
        assert hasattr(p, "is_demo")
        assert hasattr(p, "get_ohlc")
        assert hasattr(p, "get_latest_quote")
        assert hasattr(p, "get_asset_metadata")
        assert hasattr(p, "get_available_timeframes")

    def test_demo_response_structure(self):
        p = DemoMarketDataProvider()
        resp = p.get_ohlc("BTC-USD", "1d", 10)
        assert hasattr(resp, "candles")
        assert hasattr(resp, "symbol")
        assert hasattr(resp, "timeframe")
        assert hasattr(resp, "provider_name")
        assert hasattr(resp, "is_demo")
        assert hasattr(resp, "retrieved_at")
        assert hasattr(resp, "data_timestamp")
        assert hasattr(resp, "source_status")

    def test_provider_error_structure(self):
        err = ProviderError(code="TEST", message="test error", provider="test")
        assert err.code == "TEST"
        assert err.message == "test error"
        assert err.retryable is False
