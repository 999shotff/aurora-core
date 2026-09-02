from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


class BarFrequency(str, Enum):
    DAILY = "daily"
    FOUR_HOUR = "4h"
    ONE_HOUR = "1h"
    FIFTEEN_MIN = "15m"
    FIVE_MIN = "5m"
    ONE_MIN = "1m"


class QualityGrade(str, Enum):
    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    POOR = "POOR"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Provenance:
    source: str
    symbol: str
    frequency: BarFrequency
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_start: datetime | None = None
    data_end: datetime | None = None
    total_bars: int = 0
    is_demo: bool = False
    source_sha256: str = ""

    def __post_init__(self) -> None:
        if self.total_bars < 0:
            raise ValueError(f"total_bars must be non-negative, got {self.total_bars}")


@dataclass(frozen=True)
class QualityReport:
    total_bars: int
    missing_ohlc: int = 0
    zero_volume_bars: int = 0
    negative_prices: int = 0
    duplicates: int = 0
    gaps_detected: int = 0
    quality_grade: QualityGrade = QualityGrade.GOOD
    notes: list[str] = field(default_factory=list)

    @property
    def quality_score(self) -> float:
        if self.total_bars == 0:
            return 0.0
        bad = self.missing_ohlc + self.negative_prices + self.duplicates
        return max(0.0, 1.0 - (bad / self.total_bars))


@dataclass(frozen=True)
class DatasetMetadata:
    name: str
    description: str = ""
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: tuple[str, ...] = ()
    hypothesis_id: str = ""
    methodology: str = ""


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    indicators: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(
                f"high ({self.high}) must be >= low ({self.low})"
            )
        if any(v < 0 for v in (self.open, self.high, self.low, self.close)):
            raise ValueError("Price values must be non-negative")


@dataclass
class Dataset:
    bars: list[Bar]
    provenance: Provenance
    metadata: DatasetMetadata
    quality: QualityReport = field(default_factory=QualityReport)
    _timestamp_index: dict[datetime, int] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        self._build_index()

    def _build_index(self) -> None:
        self._timestamp_index = {
            bar.timestamp: i for i, bar in enumerate(self.bars)
        }

    @property
    def count(self) -> int:
        return len(self.bars)

    @property
    def start(self) -> datetime | None:
        return self.bars[0].timestamp if self.bars else None

    @property
    def end(self) -> datetime | None:
        return self.bars[-1].timestamp if self.bars else None

    def get_bar(self, timestamp: datetime) -> Bar | None:
        idx = self._timestamp_index.get(timestamp)
        return self.bars[idx] if idx is not None else None

    def slice(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Bar]:
        result = self.bars
        if start is not None:
            result = [b for b in result if b.timestamp >= start]
        if end is not None:
            result = [b for b in result if b.timestamp <= end]
        return result

    def slice_indices(self, start_idx: int, end_idx: int) -> list[Bar]:
        return self.bars[max(0, start_idx) : min(len(self.bars), end_idx)]

    def add_indicator(
        self, name: str, values: dict[datetime, float]
    ) -> None:
        for bar in self.bars:
            if bar.timestamp in values:
                bar.indicators[name] = values[bar.timestamp]

    def validate_chronological(self) -> list[str]:
        errors: list[str] = []
        for i in range(1, len(self.bars)):
            if self.bars[i].timestamp <= self.bars[i - 1].timestamp:
                errors.append(
                    f"Bar {i} timestamp ({self.bars[i].timestamp}) "
                    f"<= bar {i-1} ({self.bars[i-1].timestamp})"
                )
        return errors
