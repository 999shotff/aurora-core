from datetime import datetime, timezone

from aurora.data.providers import (
    BarRequest,
    DatafeedBar,
    DatafeedConfig,
    InMemoryDatafeed,
)
from aurora.schemas.instrument import build_instrument


def _bar(ts_hour: int, base: float = 100.0) -> DatafeedBar:
    return DatafeedBar(
        time=datetime(2025, 1, 1, ts_hour, tzinfo=timezone.utc),
        open=base,
        high=base + 5,
        low=base - 5,
        close=base + 2,
        volume=1000.0,
    )


def test_inmemory_instruments():
    feed = InMemoryDatafeed()
    btc = build_instrument("BTCUSD", asset_class="crypto", exchange="binance")
    eth = build_instrument("ETHUSD", asset_class="crypto", exchange="binance")
    feed.register_instrument(btc)
    feed.register_instrument(eth)
    instruments = feed.get_instruments()
    assert len(instruments) == 2
    symbols = {i.symbol for i in instruments}
    assert symbols == {"BTCUSD", "ETHUSD"}


def test_inmemory_resolve():
    feed = InMemoryDatafeed()
    btc = build_instrument("BTCUSD", asset_class="crypto")
    feed.register_instrument(btc)
    resolved = feed.resolve_symbol("BTCUSD")
    assert resolved.symbol == "BTCUSD"
    assert resolved.asset_class == "crypto"


def test_inmemory_resolve_missing():
    feed = InMemoryDatafeed()
    try:
        feed.resolve_symbol("MISSING")
        assert False, "should raise"
    except KeyError:
        pass


def test_inmemory_bars():
    feed = InMemoryDatafeed()
    bars = [_bar(i) for i in range(5)]
    feed.register_bars("BTCUSD", bars)
    request = BarRequest(
        symbol="BTCUSD",
        resolution="60",
        from_timestamp=datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
        to_timestamp=datetime(2025, 1, 1, 4, tzinfo=timezone.utc),
    )
    result = feed.get_bars(request)
    assert len(result) == 5


def test_inmemory_subscribe_unsubscribe():
    feed = InMemoryDatafeed()
    sub_id = feed.subscribe("BTCUSD", "60", lambda x: None)
    assert sub_id.startswith("sub_")
    feed.unsubscribe(sub_id)
    assert sub_id not in feed._subscriptions


def test_inmemory_config():
    feed = InMemoryDatafeed()
    config = feed.get_config()
    assert isinstance(config, DatafeedConfig)
    assert "60" in config.supported_resolutions
    assert config.supports_search is True
