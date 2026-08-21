"""Real OHLCV data acquisition via yfinance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]


@dataclass(frozen=True)
class OHLCVBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class OHLCVDataset:
    instrument: str
    timeframe: str
    bars: tuple[OHLCVBar, ...]
    source: str = "yfinance"
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def count(self) -> int:
        return len(self.bars)

    @property
    def start_date(self) -> datetime:
        return self.bars[0].timestamp if self.bars else datetime.min.replace(tzinfo=timezone.utc)

    @property
    def end_date(self) -> datetime:
        return self.bars[-1].timestamp if self.bars else datetime.max.replace(tzinfo=timezone.utc)

    def closes(self) -> list[float]:
        return [b.close for b in self.bars]

    def highs(self) -> list[float]:
        return [b.high for b in self.bars]

    def lows(self) -> list[float]:
        return [b.low for b in self.bars]

    def volumes(self) -> list[float]:
        return [b.volume for b in self.bars]

    def returns(self) -> list[float]:
        c = self.closes()
        return [(c[i] - c[i - 1]) / c[i - 1] for i in range(1, len(c))]


DEFAULT_INSTRUMENTS = ("BTC-USD", "SPY", "QQQ")


def fetch_yfinance(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
) -> OHLCVDataset:
    if yf is None:
        raise ImportError("yfinance is required for real data acquisition")
    t = yf.Ticker(ticker)
    hist = t.history(period=period, interval=interval)
    if hist.empty:
        raise ValueError(f"No data returned for {ticker}")
    bars: list[OHLCVBar] = []
    for idx, row in hist.iterrows():
        ts = idx.to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        bars.append(OHLCVBar(
            timestamp=ts,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
        ))
    return OHLCVDataset(instrument=ticker, timeframe=interval, bars=tuple(bars))


def fetch_all_instruments(
    tickers: tuple[str, ...] = DEFAULT_INSTRUMENTS,
    period: str = "2y",
    interval: str = "1d",
) -> dict[str, OHLCVDataset]:
    datasets: dict[str, OHLCVDataset] = {}
    for ticker in tickers:
        try:
            datasets[ticker] = fetch_yfinance(ticker, period=period, interval=interval)
        except Exception:  # noqa: BLE001, S112
            continue
    return datasets
