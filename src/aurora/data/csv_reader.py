from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from aurora.schemas.market_data import OHLCVBar, OHLCVSequence

COLUMN_ALIASES: dict[str, list[str]] = {
    "timestamp": ["timestamp", "time", "date", "datetime", "ts", "open_time"],
    "open": ["open", "open_price", "o"],
    "high": ["high", "high_price", "h"],
    "low": ["low", "low_price", "l"],
    "close": ["close", "close_price", "c"],
    "volume": ["volume", "vol", "v"],
}


def _normalize_column_name(name: str) -> str:
    stripped = name.strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in COLUMN_ALIASES.items():
        if stripped in aliases:
            return canonical
    return stripped


def _parse_timestamp(value: str) -> datetime:
    value = value.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unable to parse timestamp: {value!r}")


def read_csv(
    path: Path,
    asset: str,
    timeframe: str,
    source: str = "csv",
    delimiter: str = ",",
) -> OHLCVSequence:
    bars: list[OHLCVBar] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or has no header")

        normalized = {_normalize_column_name(fn): fn for fn in reader.fieldnames}
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(normalized.keys())
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")

        for row_num, row in enumerate(reader, start=2):
            try:
                ts = _parse_timestamp(row[normalized["timestamp"]])
                bar = OHLCVBar(
                    timestamp=ts,
                    open=float(row[normalized["open"]]),
                    high=float(row[normalized["high"]]),
                    low=float(row[normalized["low"]]),
                    close=float(row[normalized["close"]]),
                    volume=float(row[normalized["volume"]]),
                    asset=asset,
                    timeframe=timeframe,
                    source=source,
                )
                bars.append(bar)
            except (ValueError, KeyError) as e:
                raise ValueError(f"row {row_num}: {e}") from e

    if not bars:
        raise ValueError("no valid bars found in CSV")

    return OHLCVSequence(asset=asset, timeframe=timeframe, bars=bars)
