"""Tests for Milestone 16: Product Architecture, Assets, API, Charts, Indicators."""

from aurora.product.api import (
    AnalysisRequest,
    ChartConfiguration,
    ChartOverlay,
    ChartPanel,
    HealthStatus,
    IndicatorPoint,
    IndicatorRequest,
    IndicatorSeries,
    MarketMetadata,
    OHLCBar,
    OHLCResponse,
    WatchlistItem,
)
from aurora.product.assets import (
    ASSET_REGISTRY,
    get_asset,
    get_categories,
    get_yahoo_ticker,
    list_assets,
    list_assets_by_category,
)
from aurora.product.charts import (
    INDICATOR_REGISTRY,
    _atr,
    _bollinger_bands,
    _ema,
    _macd,
    _rsi,
    _sma,
    build_chart_response,
    compute_indicators,
    fetch_ohlcv_for_chart,
    generate_mock_ohlcv,
)
from aurora.product.config import (
    DEFAULT_CONFIG,
    DataConfig,
    ServerConfig,
)
from aurora.product.services import (
    get_all_market_metadata,
    get_chart,
    get_health,
    get_market_metadata,
)
from aurora.product.websocket import (
    MockWebSocket,
    WSMessage,
    WSSubscription,
)

# ============================================================
# Asset Registry Tests
# ============================================================

class TestAssetRegistry:
    def test_registry_has_10_assets(self):
        assert len(ASSET_REGISTRY) == 10

    def test_get_asset_btc(self):
        asset = get_asset("BTC-USD")
        assert asset is not None
        assert asset.symbol == "BTC-USD"
        assert asset.category == "crypto"

    def test_get_asset_spy(self):
        asset = get_asset("SPY")
        assert asset is not None
        assert asset.category == "etf"

    def test_get_asset_eurusd(self):
        asset = get_asset("EURUSD")
        assert asset is not None
        assert asset.category == "forex"
        assert asset.decimals == 5

    def test_get_asset_unknown(self):
        assert get_asset("NONEXISTENT") is None

    def test_list_assets(self):
        assets = list_assets()
        assert len(assets) == 10

    def test_list_by_category_crypto(self):
        crypto = list_assets_by_category("crypto")
        assert len(crypto) == 2
        symbols = {a.symbol for a in crypto}
        assert "BTC-USD" in symbols
        assert "ETH-USD" in symbols

    def test_list_by_category_forex(self):
        forex = list_assets_by_category("forex")
        assert len(forex) == 2

    def test_get_categories(self):
        cats = get_categories()
        assert len(cats) >= 4

    def test_yahoo_ticker(self):
        assert get_yahoo_ticker("BTC-USD") == "BTC-USD"
        assert get_yahoo_ticker("SPY") == "SPY"
        assert get_yahoo_ticker("NONEXISTENT") is None

    def test_all_assets_have_required_fields(self):
        for asset in list_assets():
            assert asset.symbol
            assert asset.name
            assert asset.category
            assert asset.exchange
            assert asset.ticker_yahoo
            assert asset.default_timeframe


# ============================================================
# OHLCV Data Tests
# ============================================================

class TestOHLCV:
    def test_mock_ohlcv(self):
        resp = generate_mock_ohlcv("BTC-USD", n_bars=100)
        assert resp.symbol == "BTC-USD"
        assert resp.count == 100
        assert len(resp.bars) == 100

    def test_mock_ohlcv_prices_positive(self):
        resp = generate_mock_ohlcv("TEST", n_bars=50)
        for bar in resp.bars:
            assert bar.open > 0
            assert bar.high > 0
            assert bar.low > 0
            assert bar.close > 0
            assert bar.volume > 0

    def test_mock_ohlcv_high_gte_low(self):
        resp = generate_mock_ohlcv("TEST", n_bars=50)
        for bar in resp.bars:
            assert bar.high >= bar.low

    def test_mock_ohlcv_deterministic(self):
        r1 = generate_mock_ohlcv("TEST", seed=42)
        r2 = generate_mock_ohlcv("TEST", seed=42)
        assert r1.bars[0].close == r2.bars[0].close

    def test_fetch_for_chart(self):
        resp = fetch_ohlcv_for_chart("BTC-USD", "1d", 50)
        assert resp.count == 50


# ============================================================
# Indicator Calculation Tests
# ============================================================

class TestIndicators:
    def test_sma_basic(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _sma(values, 3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] == 2.0
        assert result[3] == 3.0
        assert result[4] == 4.0

    def test_sma_all_none_for_short(self):
        result = _sma([1.0, 2.0], 5)
        assert all(v is None for v in result)

    def test_ema_basic(self):
        values = [float(i) for i in range(20)]
        result = _ema(values, 10)
        assert result[9] is not None
        assert all(v is not None for v in result[9:])

    def test_rsi_all_up(self):
        closes = [100.0 + i for i in range(30)]
        result = _rsi(closes, 14)
        non_none = [v for v in result if v is not None]
        assert all(v == 100.0 for v in non_none)

    def test_rsi_all_down(self):
        closes = [200.0 - i for i in range(30)]
        result = _rsi(closes, 14)
        non_none = [v for v in result if v is not None]
        assert all(v == 0.0 for v in non_none)

    def test_rsi_range(self):
        import random
        rng = random.Random(42)
        closes = [100.0]
        for _ in range(50):
            closes.append(closes[-1] * (1 + rng.gauss(0, 0.02)))
        result = _rsi(closes, 14)
        non_none = [v for v in result if v is not None]
        assert all(0 <= v <= 100 for v in non_none)

    def test_macd_output_length(self):
        closes = [100.0 + i * 0.5 for i in range(50)]
        macd_l, sig_l, hist_l = _macd(closes)
        assert len(macd_l) == 50
        assert len(sig_l) == 50
        assert len(hist_l) == 50

    def test_bollinger_output_length(self):
        closes = [100.0 + i * 0.1 for i in range(30)]
        upper, middle, lower = _bollinger_bands(closes)
        assert len(upper) == 30
        assert len(middle) == 30
        assert len(lower) == 30

    def test_bollinger_upper_gt_lower(self):
        import random
        rng = random.Random(42)
        closes = [100.0]
        for _ in range(40):
            closes.append(closes[-1] * (1 + rng.gauss(0, 0.02)))
        upper, _middle, lower = _bollinger_bands(closes)
        for i in range(19, len(closes)):
            if upper[i] is not None and lower[i] is not None:
                assert upper[i] >= lower[i]

    def test_atr_output_length(self):
        highs = [105.0 + i for i in range(30)]
        lows = [95.0 + i for i in range(30)]
        closes = [100.0 + i for i in range(30)]
        result = _atr(highs, lows, closes, 14)
        assert len(result) == 30

    def test_compute_indicators_sma(self):
        resp = generate_mock_ohlcv("TEST", n_bars=50)
        result = compute_indicators(resp.bars, ["sma_20"])
        assert len(result) == 1
        assert result[0].name == "sma_20"
        assert len(result[0].points) > 0

    def test_compute_indicators_rsi(self):
        resp = generate_mock_ohlcv("TEST", n_bars=50)
        result = compute_indicators(resp.bars, ["rsi_14"])
        assert len(result) == 1
        assert result[0].name == "rsi_14"

    def test_compute_indicators_macd(self):
        resp = generate_mock_ohlcv("TEST", n_bars=50)
        result = compute_indicators(resp.bars, ["macd"])
        names = {s.name for s in result}
        assert "macd_line" in names
        assert "macd_signal" in names
        assert "macd_histogram" in names

    def test_compute_indicators_bollinger(self):
        resp = generate_mock_ohlcv("TEST", n_bars=50)
        result = compute_indicators(resp.bars, ["bollinger"])
        names = {s.name for s in result}
        assert "bb_upper" in names
        assert "bb_middle" in names
        assert "bb_lower" in names

    def test_indicator_registry_populated(self):
        assert len(INDICATOR_REGISTRY) >= 10


# ============================================================
# API Contract Tests
# ============================================================

class TestAPIContracts:
    def test_ohlc_bar(self):
        bar = OHLCBar(timestamp="2024-01-01", open=100, high=105, low=95, close=102, volume=1000)
        assert bar.close == 102

    def test_ohlc_response(self):
        resp = OHLCResponse(symbol="TEST", timeframe="1d", bars=[], count=0)
        assert resp.symbol == "TEST"

    def test_indicator_point(self):
        pt = IndicatorPoint(timestamp="2024-01-01", value=50.0)
        assert pt.value == 50.0

    def test_indicator_series(self):
        series = IndicatorSeries(name="sma_20", parameters={"period": 20}, points=[])
        assert series.name == "sma_20"

    def test_indicator_request(self):
        req = IndicatorRequest(symbol="BTC-USD")
        assert req.symbol == "BTC-USD"
        assert "sma_20" in req.indicators

    def test_market_metadata(self):
        meta = MarketMetadata(
            symbol="BTC-USD", name="Bitcoin", category="crypto",
            exchange="NASDAQ", currency="USD", trading_hours="24/7",
            decimals=2, min_tick=0.01, description="Bitcoin",
        )
        assert meta.symbol == "BTC-USD"

    def test_watchlist_item(self):
        item = WatchlistItem(symbol="BTC-USD", name="Bitcoin", last_price=50000)
        assert item.symbol == "BTC-USD"

    def test_chart_configuration(self):
        config = ChartConfiguration(
            symbol="BTC-USD",
            timeframe="1d",
            overlays=[ChartOverlay(type="sma_20")],
            panels=[ChartPanel(type="rsi_14")],
        )
        assert config.symbol == "BTC-USD"
        assert len(config.overlays) == 1

    def test_analysis_request(self):
        req = AnalysisRequest(symbol="BTC-USD", timeframe="1d")
        assert req.symbol == "BTC-USD"

    def test_health_status(self):
        status = HealthStatus(service="test", status="ok", version="0.1.0")
        assert status.status == "ok"


# ============================================================
# Chart Response Tests
# ============================================================

class TestChartResponse:
    def test_build_chart(self):
        resp = build_chart_response("BTC-USD", "1d", n_bars=50)
        assert resp.bar_count == 50
        assert len(resp.bars) == 50
        assert resp.configuration.symbol == "BTC-USD"

    def test_build_chart_has_overlays(self):
        resp = build_chart_response("BTC-USD", "1d", n_bars=50)
        assert len(resp.overlays) > 0

    def test_build_chart_has_panels(self):
        resp = build_chart_response("BTC-USD", "1d", n_bars=50)
        assert len(resp.panels) > 0


# ============================================================
# WebSocket Tests
# ============================================================

class TestWebSocket:
    def test_mock_connect(self):
        ws = MockWebSocket()
        ws.connect()
        assert ws.connected

    def test_mock_disconnect(self):
        ws = MockWebSocket()
        ws.connect()
        ws.disconnect()
        assert not ws.connected

    def test_mock_subscribe(self):
        ws = MockWebSocket()
        ws.connect()
        sub = WSSubscription(channel="ohlc", symbols=["BTC-USD"])
        ws.subscribe(sub)
        assert len(ws.subscriptions) == 1

    def test_mock_unsubscribe(self):
        ws = MockWebSocket()
        ws.connect()
        sub = WSSubscription(channel="ohlc", symbols=["BTC-USD"])
        ws.subscribe(sub)
        ws.unsubscribe("ohlc", ["BTC-USD"])
        assert len(ws.subscriptions) == 0

    def test_mock_message(self):
        ws = MockWebSocket()
        ws.connect()
        ws.simulate_message("ohlc", {"price": 50000})
        assert len(ws.messages) == 1

    def test_ws_message(self):
        msg = WSMessage(channel="ohlc", data={"price": 50000})
        assert msg.channel == "ohlc"


# ============================================================
# Config Tests
# ============================================================

class TestConfig:
    def test_default_config(self):
        cfg = DEFAULT_CONFIG
        assert cfg.server.host == "127.0.0.1"
        assert cfg.server.port == 8000
        assert cfg.data.provider == "yfinance"
        assert cfg.chart.default_theme == "dark"
        assert cfg.research_conclusion == "NO_DEPLOYMENT_SIGNAL"

    def test_server_config(self):
        cfg = ServerConfig(host="0.0.0.0", port=9000)
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 9000

    def test_data_config(self):
        cfg = DataConfig(cache_enabled=False)
        assert not cfg.cache_enabled


# ============================================================
# Service Tests
# ============================================================

class TestServices:
    def test_market_metadata_btc(self):
        meta = get_market_metadata("BTC-USD")
        assert meta is not None
        assert meta.symbol == "BTC-USD"

    def test_market_metadata_unknown(self):
        assert get_market_metadata("NONEXISTENT") is None

    def test_all_metadata(self):
        resp = get_all_market_metadata()
        assert resp.count == 10

    def test_get_chart(self):
        resp = get_chart("BTC-USD", "1d", 50)
        assert resp.bar_count == 50

    def test_get_health(self):
        resp = get_health()
        assert resp.status == "healthy"
        assert len(resp.services) == 3
        assert resp.research_conclusion == "NO_DEPLOYMENT_SIGNAL"
