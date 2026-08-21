from datetime import datetime

from aurora.data.validation import validate_ohlcv
from aurora.schemas.market_data import OHLCVBar


def _bar(i: int, **overrides) -> OHLCVBar:
    defaults = {
        "timestamp": datetime(2025, 1, 1, i, tzinfo=__import__("datetime").timezone.utc),
        "open": 100.0 + i,
        "high": 110.0 + i,
        "low": 90.0 + i,
        "close": 105.0 + i,
        "volume": 1000.0,
        "asset": "BTCUSD",
        "timeframe": "1h",
    }
    defaults.update(overrides)
    return OHLCVBar(**defaults)


def test_validate_clean_data():
    bars = [_bar(0), _bar(1), _bar(2)]
    _accepted, report = validate_ohlcv(bars, "BTCUSD", "1h")
    assert report.rows_received == 3
    assert report.rows_accepted == 3
    assert report.rows_rejected == 0


def test_validate_duplicate_timestamps():
    bars = [_bar(0), _bar(0)]
    _accepted, report = validate_ohlcv(bars, "BTCUSD", "1h")
    assert report.duplicate_count == 1
    assert report.rows_rejected == 1


def test_validate_mixed_valid_invalid():
    bars = [_bar(0), _bar(1)]
    bad_bar = OHLCVBar(
        timestamp=datetime(2025, 1, 1, 2, tzinfo=__import__("datetime").timezone.utc),
        open=100.0,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=0.0,
        asset="BTCUSD",
        timeframe="1h",
    )
    _accepted, report = validate_ohlcv(bars + [bad_bar], "BTCUSD", "1h")
    assert report.rows_received == 3
    assert report.rows_accepted == 3
    assert len(_accepted) == 3


def test_validate_report_dict():
    bars = [_bar(0), _bar(1)]
    _, report = validate_ohlcv(bars, "BTCUSD", "1h")
    d = report.to_dict()
    assert d["asset"] == "BTCUSD"
    assert d["rows_accepted"] == 2
    assert "time_range_start" in d


def test_validate_expected_frequency():
    bars = [_bar(0), _bar(1), _bar(3)]
    _, report = validate_ohlcv(
        bars, "BTCUSD", "1h", expected_frequency_minutes=60
    )
    assert report.missing_timestamp_count == 1


def test_validate_empty_list():
    _, report = validate_ohlcv([], "BTCUSD", "1h")
    assert report.rows_received == 0
    assert report.rows_accepted == 0
