from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aurora.schemas.market_data import OHLCVBar, OHLCVSequence

try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False


def _require_pyarrow() -> None:
    if not HAS_PYARROW:
        raise ImportError(
            "pyarrow is required for Parquet support. "
            "Install with: pip install aurora-core[data]"
        )


def read_parquet(
    path: Path,
    asset: str,
    timeframe: str,
    source: str = "parquet",
) -> OHLCVSequence:
    _require_pyarrow()
    table = pq.read_table(str(path))
    df = table.to_pandas()

    bars: list[OHLCVBar] = []
    for _, row in df.iterrows():
        ts = row["timestamp"]
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts = ts.astimezone(timezone.utc)
        else:
            ts = datetime.fromisoformat(str(ts)).astimezone(timezone.utc)

        bar = OHLCVBar(
            timestamp=ts,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            asset=asset,
            timeframe=timeframe,
            source=source,
        )
        bars.append(bar)

    if not bars:
        raise ValueError("no valid bars found in Parquet file")

    return OHLCVSequence(asset=asset, timeframe=timeframe, bars=bars)


def write_parquet(sequence: OHLCVSequence, path: Path) -> Path:
    _require_pyarrow()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": [bar.timestamp.isoformat() for bar in sequence.bars],
        "open": [bar.open for bar in sequence.bars],
        "high": [bar.high for bar in sequence.bars],
        "low": [bar.low for bar in sequence.bars],
        "close": [bar.close for bar in sequence.bars],
        "volume": [bar.volume for bar in sequence.bars],
        "asset": [bar.asset for bar in sequence.bars],
        "timeframe": [bar.timeframe for bar in sequence.bars],
        "source": [bar.source for bar in sequence.bars],
        "data_quality": [bar.data_quality for bar in sequence.bars],
    }

    table = pa.Table.from_pydict(data)
    pq.write_table(table, str(path))
    return path
