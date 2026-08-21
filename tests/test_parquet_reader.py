from datetime import datetime, timezone
from pathlib import Path

import pytest

from aurora.data.parquet_reader import read_parquet, write_parquet
from aurora.schemas.market_data import OHLCVBar, OHLCVSequence


def _make_sequence(n: int = 3) -> OHLCVSequence:
    bars = [
        OHLCVBar(
            timestamp=datetime(2025, 1, 1, i, tzinfo=timezone.utc),
            open=100.0 + i,
            high=110.0 + i,
            low=90.0 + i,
            close=105.0 + i,
            volume=1000.0 + i,
            asset="BTCUSD",
            timeframe="1h",
            source="test",
        )
        for i in range(n)
    ]
    return OHLCVSequence(asset="BTCUSD", timeframe="1h", bars=bars)


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("pyarrow"),
    reason="pyarrow not installed",
)
def test_write_and_read_parquet(tmp_path: Path):
    seq = _make_sequence()
    out = tmp_path / "test.parquet"
    write_parquet(seq, out)
    assert out.exists()

    loaded = read_parquet(out, asset="BTCUSD", timeframe="1h")
    assert loaded.bar_count == 3
    assert loaded.asset == "BTCUSD"
    assert loaded.bars[0].open == 100.0
    assert loaded.bars[2].close == 107.0


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("pyarrow"),
    reason="pyarrow not installed",
)
def test_parquet_roundtrip_preserves_sources(tmp_path: Path):
    seq = _make_sequence()
    out = tmp_path / "test.parquet"
    write_parquet(seq, out)
    loaded = read_parquet(out, asset="BTCUSD", timeframe="1h")
    for bar in loaded.bars:
        assert bar.source == "parquet"
        assert bar.data_quality == "historical"


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("pyarrow"),
    reason="pyarrow not installed",
)
def test_parquet_empty_file(tmp_path: Path):
    out = tmp_path / "empty.parquet"
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table(
        {
            "timestamp": pa.array([], type=pa.string()),
            "open": pa.array([], type=pa.float64()),
            "high": pa.array([], type=pa.float64()),
            "low": pa.array([], type=pa.float64()),
            "close": pa.array([], type=pa.float64()),
            "volume": pa.array([], type=pa.float64()),
        }
    )
    pq.write_table(table, str(out))

    with pytest.raises(ValueError, match="no valid bars"):
        read_parquet(out, asset="BTCUSD", timeframe="1h")
