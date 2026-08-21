import csv
from datetime import timedelta
from pathlib import Path

import pytest

from aurora.data.csv_reader import read_csv


def _write_csv(rows: list[dict], path: Path) -> Path:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_read_csv_standard_columns(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    rows = [
        {"timestamp": "2025-01-01T00:00:00Z", "open": "100", "high": "110", "low": "90", "close": "105", "volume": "1000"},
        {"timestamp": "2025-01-01T01:00:00Z", "open": "105", "high": "115", "low": "95", "close": "110", "volume": "1200"},
    ]
    _write_csv(rows, csv_file)
    seq = read_csv(csv_file, asset="BTCUSD", timeframe="1h")
    assert seq.asset == "BTCUSD"
    assert seq.bar_count == 2
    assert seq.bars[0].open == 100.0


def test_read_csv_aliased_columns(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    rows = [
        {"time": "2025-01-01T00:00:00Z", "o": "100", "h": "110", "l": "90", "c": "105", "vol": "1000"},
    ]
    _write_csv(rows, csv_file)
    seq = read_csv(csv_file, asset="ETHUSD", timeframe="4h")
    assert seq.bar_count == 1
    assert seq.bars[0].asset == "ETHUSD"
    assert seq.bars[0].timeframe == "4h"


def test_read_csv_auto_utc(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    rows = [
        {"timestamp": "2025-01-01 12:00:00", "open": "100", "high": "110", "low": "90", "close": "105", "volume": "1000"},
    ]
    _write_csv(rows, csv_file)
    seq = read_csv(csv_file, asset="BTCUSD", timeframe="1h")
    assert seq.bars[0].timestamp.tzinfo is not None
    assert seq.bars[0].timestamp.utcoffset() == timedelta(0)


def test_read_csv_missing_columns(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    rows = [{"timestamp": "2025-01-01T00:00:00Z", "open": "100"}]
    _write_csv(rows, csv_file)
    with pytest.raises(ValueError, match="missing required columns"):
        read_csv(csv_file, asset="BTCUSD", timeframe="1h")


def test_read_csv_empty_file(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("timestamp,open,high,low,close,volume\n")
    with pytest.raises(ValueError, match="no valid bars"):
        read_csv(csv_file, asset="BTCUSD", timeframe="1h")


def test_read_csv_semicolon_delimiter(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    with open(csv_file, "w", newline="") as f:
        f.write("timestamp;open;high;low;close;volume\n")
        f.write("2025-01-01T00:00:00Z;100;110;90;105;1000\n")
    seq = read_csv(csv_file, asset="BTCUSD", timeframe="1h", delimiter=";")
    assert seq.bar_count == 1


def test_read_csv_date_only_timestamp(tmp_path: Path):
    csv_file = tmp_path / "data.csv"
    rows = [{"timestamp": "2025-01-01", "open": "100", "high": "110", "low": "90", "close": "105", "volume": "1000"}]
    _write_csv(rows, csv_file)
    seq = read_csv(csv_file, asset="BTCUSD", timeframe="1d")
    assert seq.bars[0].timestamp.hour == 0
