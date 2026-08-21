from datetime import datetime, timedelta, timezone

import pytest

from aurora.data.splits import TimeBasedSplitter
from aurora.schemas.market_data import OHLCVBar, OHLCVSequence


def _make_sequence(n: int = 100) -> OHLCVSequence:
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = [
        OHLCVBar(
            timestamp=base + timedelta(hours=i),
            open=100.0 + i,
            high=110.0 + i,
            low=90.0 + i,
            close=105.0 + i,
            volume=1000.0,
            asset="BTCUSD",
            timeframe="1h",
        )
        for i in range(n)
    ]
    return OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)


def test_split_counts():
    seq = _make_sequence(100)
    splitter = TimeBasedSplitter()
    splits = splitter.split(seq)
    assert splits["train"].bar_count + splits["validation"].bar_count + splits["test"].bar_count == 100


def test_split_ratios():
    seq = _make_sequence(100)
    splitter = TimeBasedSplitter(train_ratio=0.6, validation_ratio=0.2, test_ratio=0.2)
    splits = splitter.split(seq)
    assert splits["train"].bar_count == 60
    assert splits["validation"].bar_count == 20
    assert splits["test"].bar_count == 20


def test_split_no_leakage():
    seq = _make_sequence(100)
    splitter = TimeBasedSplitter()
    splits = splitter.split(seq)
    assert splitter.validate_no_leakage(splits)


def test_split_all_same_asset():
    seq = _make_sequence(50)
    splitter = TimeBasedSplitter()
    splits = splitter.split(seq)
    for s in splits.values():
        assert s.asset == "BTCUSD"
        assert s.timeframe == "1h"


def test_split_assignments():
    seq = _make_sequence(100)
    splitter = TimeBasedSplitter()
    assigns = splitter.assignments(seq)
    assert len(assigns) == 3
    assert assigns[0].split == "train"
    assert assigns[1].split == "validation"
    assert assigns[2].split == "test"


def test_split_ratios_invalid():
    with pytest.raises(ValueError, match="sum to 1.0"):
        TimeBasedSplitter(train_ratio=0.5, validation_ratio=0.5, test_ratio=0.5)
