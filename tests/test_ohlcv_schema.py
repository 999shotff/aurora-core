from datetime import datetime, timedelta, timezone

import pytest

from aurora.schemas.market_data import OHLCVBar, OHLCVSequence


def _bar(**overrides) -> OHLCVBar:
    defaults = {
        "timestamp": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "open": 100.0,
        "high": 110.0,
        "low": 90.0,
        "close": 105.0,
        "volume": 1000.0,
        "asset": "BTCUSD",
        "timeframe": "1h",
    }
    defaults.update(overrides)
    return OHLCVBar(**defaults)


def test_ohlcv_bar_valid():
    bar = _bar()
    assert bar.open == 100.0
    assert bar.timestamp.tzinfo is not None


def test_ohlcv_bar_utc_normalization():
    eastern = timezone(timedelta(hours=-5))
    bar = _bar(timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=eastern))
    assert bar.timestamp.utcoffset() == timedelta(0)


def test_ohlcv_bar_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        _bar(timestamp=datetime(2025, 1, 1, 12, 0))  # noqa: DTZ001


def test_ohlcv_bar_finite_validation():
    with pytest.raises(Exception, match="|finite|greater than"):
        _bar(open=float("nan"))
    with pytest.raises(Exception, match="|finite|less than"):
        _bar(high=float("inf"))


def test_ohlcv_bar_negative_volume():
    with pytest.raises(ValueError):
        _bar(volume=-1.0)


def test_ohlcv_bar_high_lt_low():
    with pytest.raises(ValueError, match="high.*must be >= low"):
        _bar(high=80.0, low=90.0)


def test_ohlcv_bar_high_lt_open():
    with pytest.raises(ValueError, match="high.*must be >= open"):
        _bar(high=90.0, open=100.0)


def test_ohlcv_bar_high_lt_close():
    with pytest.raises(ValueError, match="high.*must be >= close"):
        _bar(high=90.0, close=100.0, open=80.0)


def test_ohlcv_bar_low_gt_open():
    with pytest.raises(ValueError, match="low.*must be <= open"):
        _bar(low=110.0, open=100.0)


def test_ohlcv_bar_low_gt_close():
    with pytest.raises(ValueError, match="low.*must be <= close"):
        _bar(low=110.0, close=100.0, open=120.0, high=130.0)


def test_ohlcv_sequence_valid():
    bars = [
        _bar(timestamp=datetime(2025, 1, 1, i, tzinfo=timezone.utc))
        for i in range(3)
    ]
    seq = OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)
    assert seq.bar_count == 3


def test_ohlcv_sequence_unordered():
    bars = [
        _bar(timestamp=datetime(2025, 1, 1, 2, tzinfo=timezone.utc)),
        _bar(timestamp=datetime(2025, 1, 1, 1, tzinfo=timezone.utc)),
    ]
    with pytest.raises(ValueError, match="ordered by timestamp"):
        OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)


def test_ohlcv_sequence_duplicate_timestamps():
    ts = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    bars = [_bar(timestamp=ts), _bar(timestamp=ts)]
    with pytest.raises(ValueError, match="duplicate timestamps"):
        OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)


def test_ohlcv_sequence_empty():
    with pytest.raises(ValueError):
        OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=[])


def test_ohlcv_sequence_mismatched_asset():
    bars = [
        _bar(timestamp=datetime(2025, 1, 1, 1, tzinfo=timezone.utc), asset="BTCUSD"),
        _bar(timestamp=datetime(2025, 1, 1, 2, tzinfo=timezone.utc), asset="ETHUSD"),
    ]
    with pytest.raises(ValueError, match="bar asset"):
        OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)


def test_ohlcv_typical_prices():
    bars = [_bar(high=110.0, low=90.0, close=105.0)]
    seq = OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)
    tp = seq.typical_prices()
    assert abs(tp[0] - 101.66666666666667) < 1e-10


def test_ohlcv_timestamps():
    bars = [
        _bar(timestamp=datetime(2025, 1, 1, i, tzinfo=timezone.utc))
        for i in range(3)
    ]
    seq = OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)
    ts = seq.timestamps()
    assert len(ts) == 3
    assert ts[0].hour == 0
