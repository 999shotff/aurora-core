from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DataQuality = Literal["live", "historical", "simulated", "inferred"]


class OHLCVBar(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    timestamp: datetime
    open: float = Field(ge=0.0)
    high: float = Field(ge=0.0)
    low: float = Field(ge=0.0)
    close: float = Field(ge=0.0)
    volume: float = Field(ge=0.0)
    asset: str
    timeframe: str
    source: str = "unknown"
    data_quality: DataQuality = "historical"

    @model_validator(mode="after")
    def _validate_ohlc(self) -> OHLCVBar:
        if not math.isfinite(self.open):
            raise ValueError(f"open must be finite, got {self.open}")
        if not math.isfinite(self.high):
            raise ValueError(f"high must be finite, got {self.high}")
        if not math.isfinite(self.low):
            raise ValueError(f"low must be finite, got {self.low}")
        if not math.isfinite(self.close):
            raise ValueError(f"close must be finite, got {self.close}")
        if not math.isfinite(self.volume):
            raise ValueError(f"volume must be finite, got {self.volume}")

        if self.high < self.low:
            raise ValueError(f"high ({self.high}) must be >= low ({self.low})")
        if self.high < self.open:
            raise ValueError(f"high ({self.high}) must be >= open ({self.open})")
        if self.high < self.close:
            raise ValueError(f"high ({self.high}) must be >= close ({self.close})")
        if self.low > self.open:
            raise ValueError(f"low ({self.low}) must be <= open ({self.open})")
        if self.low > self.close:
            raise ValueError(f"low ({self.low}) must be <= close ({self.close})")

        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.timestamp.utcoffset() != timedelta(0):
            self.timestamp = self.timestamp.astimezone(timezone.utc)

        return self


class OHLCVSequence(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    asset: str
    timeframe: str
    bars: list[OHLCVBar] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_sequence(self) -> OHLCVSequence:
        if len(self.bars) < 1:
            raise ValueError("sequence must contain at least one bar")
        for bar in self.bars:
            if bar.asset != self.asset:
                raise ValueError(
                    f"bar asset '{bar.asset}' != sequence asset '{self.asset}'"
                )
            if bar.timeframe != self.timeframe:
                raise ValueError(
                    f"bar timeframe '{bar.timeframe}' != sequence timeframe '{self.timeframe}'"
                )
        timestamps = [bar.timestamp for bar in self.bars]
        if timestamps != sorted(timestamps):
            raise ValueError("bars must be ordered by timestamp")
        if len(timestamps) != len(set(timestamps)):
            dupes = [t for t in timestamps if timestamps.count(t) > 1]
            raise ValueError(f"duplicate timestamps: {sorted(set(dupes))}")
        return self

    @property
    def bar_count(self) -> int:
        return len(self.bars)

    def opens(self) -> list[float]:
        return [bar.open for bar in self.bars]

    def highs(self) -> list[float]:
        return [bar.high for bar in self.bars]

    def lows(self) -> list[float]:
        return [bar.low for bar in self.bars]

    def closes(self) -> list[float]:
        return [bar.close for bar in self.bars]

    def volumes(self) -> list[float]:
        return [bar.volume for bar in self.bars]

    def typical_prices(self) -> list[float]:
        return [(bar.high + bar.low + bar.close) / 3.0 for bar in self.bars]

    def timestamps(self) -> list[datetime]:
        return [bar.timestamp for bar in self.bars]
