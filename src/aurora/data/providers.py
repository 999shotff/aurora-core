from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from aurora.schemas.instrument import InstrumentIdentity
from aurora.schemas.market_data import OHLCVSequence


class MarketDataProvider(ABC):
    @abstractmethod
    def load(self, path: Path, asset: str, timeframe: str) -> OHLCVSequence:
        raise NotImplementedError

    @abstractmethod
    def save(self, sequence: OHLCVSequence, path: Path) -> Path:
        raise NotImplementedError

    @abstractmethod
    def supported_suffixes(self) -> list[str]:
        raise NotImplementedError


Resolution = Literal["1", "5", "15", "30", "60", "120", "240", "D", "W", "M"]


@dataclass(frozen=True)
class BarRequest:
    symbol: str
    resolution: Resolution
    from_timestamp: datetime
    to_timestamp: datetime
    countback: int | None = None


@dataclass
class DatafeedBar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class DatafeedConfig:
    supported_resolutions: list[Resolution] = field(
        default_factory=lambda: ["1", "5", "15", "30", "60", "240", "D", "W", "M"]
    )
    has_intraday: bool = True
    has_daily: bool = True
    has_weekly: bool = True
    has_monthly: bool = True
    exchanges: list[dict[str, str]] = field(default_factory=list)
    symbols_types: list[dict[str, str]] = field(default_factory=list)
    supports_search: bool = True
    supports_group_request: bool = False
    supports_marks: bool = False
    supports_timescale_marks: bool = False


class DatafeedProvider(ABC):
    @abstractmethod
    def get_instruments(self) -> list[InstrumentIdentity]:
        raise NotImplementedError

    @abstractmethod
    def resolve_symbol(self, symbol: str) -> InstrumentIdentity:
        raise NotImplementedError

    @abstractmethod
    def get_bars(self, request: BarRequest) -> list[DatafeedBar]:
        raise NotImplementedError

    @abstractmethod
    def subscribe(
        self,
        symbol: str,
        resolution: Resolution,
        callback: Any,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_config(self) -> DatafeedConfig:
        raise NotImplementedError

    def to_ohlcv(self, bars: list[DatafeedBar], asset: str, timeframe: str) -> OHLCVSequence:
        from aurora.schemas.market_data import OHLCVBar

        ohlc_bars = []
        for b in bars:
            ohlc_bars.append(
                OHLCVBar(
                    timestamp=b.time,
                    open=b.open,
                    high=b.high,
                    low=b.low,
                    close=b.close,
                    volume=b.volume,
                    asset=asset,
                    timeframe=timeframe,
                    source="datafeed",
                )
            )
        return OHLCVSequence(asset=asset, timeframe=timeframe, bars=ohlc_bars)


class InMemoryDatafeed(DatafeedProvider):
    def __init__(self) -> None:
        self._instruments: dict[str, InstrumentIdentity] = {}
        self._bars: dict[str, list[DatafeedBar]] = {}
        self._subscriptions: dict[str, Any] = {}
        self._config = DatafeedConfig()
        self._sub_counter = 0

    def register_instrument(self, instrument: InstrumentIdentity) -> None:
        self._instruments[instrument.symbol.upper()] = instrument

    def register_bars(self, symbol: str, bars: list[DatafeedBar]) -> None:
        key = symbol.upper()
        existing = self._bars.get(key, [])
        existing.extend(bars)
        self._bars[key] = sorted(existing, key=lambda b: b.time)

    def get_instruments(self) -> list[InstrumentIdentity]:
        return list(self._instruments.values())

    def resolve_symbol(self, symbol: str) -> InstrumentIdentity:
        key = symbol.upper()
        if key not in self._instruments:
            raise KeyError(f"symbol not found: {symbol}")
        return self._instruments[key]

    def get_bars(self, request: BarRequest) -> list[DatafeedBar]:
        key = request.symbol.upper()
        if key not in self._bars:
            return []
        bars = self._bars[key]
        return [
            b
            for b in bars
            if request.from_timestamp <= b.time <= request.to_timestamp
        ]

    def subscribe(
        self,
        symbol: str,
        resolution: Resolution,
        callback: Any,
    ) -> str:
        self._sub_counter += 1
        sub_id = f"sub_{self._sub_counter}"
        self._subscriptions[sub_id] = {
            "symbol": symbol.upper(),
            "resolution": resolution,
            "callback": callback,
        }
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]

    def get_config(self) -> DatafeedConfig:
        return self._config
