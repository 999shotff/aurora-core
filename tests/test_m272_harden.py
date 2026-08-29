"""M27.2 Regression Tests — Chart Architecture + Live Analysis Hardening.

Tests for 4h aggregation, demo provider intraday, and provider fixes.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from aurora.market.provider import (
    DemoMarketDataProvider,
    RealMarketDataProvider,
    CandleData,
)


# ============================================================
# 4h Aggregation
# ============================================================


class Test4hAggregation:
    def _make_candle(self, ts: str, o: float, h: float, l: float, c: float, v: float) -> CandleData:
        return CandleData(
            timestamp=ts,
            open=o, high=h, low=l, close=c, volume=v,
        )

    def test_aggregate_basic(self):
        candles = [
            self._make_candle("2026-01-01T00:00:00Z", 100, 110, 95, 105, 1000),
            self._make_candle("2026-01-01T01:00:00Z", 105, 115, 100, 110, 1200),
            self._make_candle("2026-01-01T02:00:00Z", 110, 120, 105, 115, 800),
            self._make_candle("2026-01-01T03:00:00Z", 115, 125, 110, 120, 900),
        ]
        result = RealMarketDataProvider._aggregate_to_4h(candles)
        assert len(result) == 1
        bar = result[0]
        assert bar.timestamp == "2026-01-01T00:00:00Z"
        assert bar.open == 100
        assert bar.high == 125
        assert bar.low == 95
        assert bar.close == 120
        assert bar.volume == 3900

    def test_aggregate_multiple_4h_windows(self):
        candles = []
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(8):
            ts = (base + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
            candles.append(self._make_candle(ts, 100 + i, 110 + i, 90 + i, 105 + i, 100 * (i + 1)))
        result = RealMarketDataProvider._aggregate_to_4h(candles)
        assert len(result) == 2
        assert result[0].timestamp == "2026-01-01T00:00:00Z"
        assert result[1].timestamp == "2026-01-01T04:00:00Z"

    def test_aggregate_empty(self):
        result = RealMarketDataProvider._aggregate_to_4h([])
        assert result == []

    def test_aggregate_single_candle(self):
        candles = [self._make_candle("2026-01-01T05:00:00Z", 100, 110, 95, 105, 1000)]
        result = RealMarketDataProvider._aggregate_to_4h(candles)
        assert len(result) == 1
        assert result[0].open == 100
        assert result[0].high == 110
        assert result[0].low == 95
        assert result[0].close == 105
        assert result[0].volume == 1000

    def test_aggregate_preserves_ohlc_rules(self):
        candles = [
            self._make_candle("2026-01-01T00:00:00Z", 100, 130, 80, 90, 500),
            self._make_candle("2026-01-01T01:00:00Z", 90, 120, 70, 110, 600),
            self._make_candle("2026-01-01T02:00:00Z", 110, 140, 100, 95, 700),
            self._make_candle("2026-01-01T03:00:00Z", 95, 115, 85, 105, 800),
        ]
        result = RealMarketDataProvider._aggregate_to_4h(candles)
        bar = result[0]
        assert bar.open == 100
        assert bar.high == 140
        assert bar.low == 70
        assert bar.close == 105

    def test_aggregate_volume_sums(self):
        candles = [
            self._make_candle("2026-01-01T00:00:00Z", 100, 110, 95, 105, 100),
            self._make_candle("2026-01-01T01:00:00Z", 100, 110, 95, 105, 200),
            self._make_candle("2026-01-01T02:00:00Z", 100, 110, 95, 105, 300),
            self._make_candle("2026-01-01T03:00:00Z", 100, 110, 95, 105, 400),
        ]
        result = RealMarketDataProvider._aggregate_to_4h(candles)
        assert result[0].volume == 1000


# ============================================================
# Demo Provider Intraday
# ============================================================


class TestDemoIntraday:
    def test_daily_timestamps(self):
        provider = DemoMarketDataProvider()
        resp = provider.get_ohlc("BTC-USD", "1d", 10)
        assert resp.source_status == "ok"
        assert len(resp.candles) == 10
        for i in range(1, len(resp.candles)):
            prev = datetime.fromisoformat(resp.candles[i - 1].timestamp.replace("Z", "+00:00"))
            curr = datetime.fromisoformat(resp.candles[i].timestamp.replace("Z", "+00:00"))
            diff = curr - prev
            assert diff.days >= 1

    def test_1h_timestamps(self):
        provider = DemoMarketDataProvider()
        resp = provider.get_ohlc("BTC-USD", "1h", 10)
        assert resp.source_status == "ok"
        assert len(resp.candles) == 10
        for i in range(1, len(resp.candles)):
            prev = datetime.fromisoformat(resp.candles[i - 1].timestamp.replace("Z", "+00:00"))
            curr = datetime.fromisoformat(resp.candles[i].timestamp.replace("Z", "+00:00"))
            diff = curr - prev
            assert diff == timedelta(hours=1)

    def test_5m_timestamps(self):
        provider = DemoMarketDataProvider()
        resp = provider.get_ohlc("ETH-USD", "5m", 10)
        assert resp.source_status == "ok"
        assert len(resp.candles) == 10
        for i in range(1, len(resp.candles)):
            prev = datetime.fromisoformat(resp.candles[i - 1].timestamp.replace("Z", "+00:00"))
            curr = datetime.fromisoformat(resp.candles[i].timestamp.replace("Z", "+00:00"))
            diff = curr - prev
            assert diff == timedelta(minutes=5)

    def test_1m_timestamps(self):
        provider = DemoMarketDataProvider()
        resp = provider.get_ohlc("SPY", "1m", 10)
        assert resp.source_status == "ok"
        for i in range(1, len(resp.candles)):
            prev = datetime.fromisoformat(resp.candles[i - 1].timestamp.replace("Z", "+00:00"))
            curr = datetime.fromisoformat(resp.candles[i].timestamp.replace("Z", "+00:00"))
            diff = curr - prev
            assert diff == timedelta(minutes=1)

    def test_ohlc_validity(self):
        provider = DemoMarketDataProvider()
        resp = provider.get_ohlc("BTC-USD", "1d", 50)
        assert resp.source_status == "ok"
        for c in resp.candles:
            assert c.high >= max(c.open, c.close)
            assert c.low <= min(c.open, c.close)
            assert c.volume >= 0

    def test_deterministic(self):
        p1 = DemoMarketDataProvider()
        p2 = DemoMarketDataProvider()
        r1 = p1.get_ohlc("BTC-USD", "1d", 20)
        r2 = p2.get_ohlc("BTC-USD", "1d", 20)
        assert len(r1.candles) == len(r2.candles)
        for c1, c2 in zip(r1.candles, r2.candles):
            assert c1.timestamp == c2.timestamp
            assert c1.open == c2.open
            assert c1.close == c2.close

    def test_is_demo(self):
        provider = DemoMarketDataProvider()
        assert provider.is_demo is True
        resp = provider.get_ohlc("BTC-USD", "1d", 10)
        assert resp.is_demo is True


# ============================================================
# Provider Configuration
# ============================================================


class TestProviderConfig:
    def test_create_provider_demo(self):
        from aurora.market.provider import create_provider
        with pytest.MonkeyPatch.context() as m:
            m.setenv("AURORA_DATA_MODE", "demo")
            p = create_provider()
            assert isinstance(p, DemoMarketDataProvider)

    def test_create_provider_real(self):
        from aurora.market.provider import create_provider
        with pytest.MonkeyPatch.context() as m:
            m.setenv("AURORA_DATA_MODE", "real")
            p = create_provider()
            assert isinstance(p, RealMarketDataProvider)
