from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from aurora.schemas.market_data import OHLCVSequence

SplitType = Literal["train", "validation", "test"]


class SplitWindow(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    split_type: SplitType
    start: datetime
    end: datetime
    bar_count: int
    fold_index: int = 0


@dataclass(frozen=True)
class ChronologicalSplitter:
    train_ratio: float = 0.7
    validation_ratio: float = 0.15
    test_ratio: float = 0.15

    def __post_init__(self) -> None:
        total = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"ratios must sum to 1.0, got {total}")

    def split(self, sequence: OHLCVSequence) -> list[SplitWindow]:
        bars = sequence.bars
        n = len(bars)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.validation_ratio)
        return [
            SplitWindow(
                split_type="train",
                start=bars[0].timestamp,
                end=bars[train_end - 1].timestamp if train_end > 0 else bars[0].timestamp,
                bar_count=train_end,
            ),
            SplitWindow(
                split_type="validation",
                start=bars[train_end].timestamp if train_end < n else bars[-1].timestamp,
                end=bars[val_end - 1].timestamp if val_end > train_end else bars[train_end].timestamp,
                bar_count=val_end - train_end,
            ),
            SplitWindow(
                split_type="test",
                start=bars[val_end].timestamp if val_end < n else bars[-1].timestamp,
                end=bars[-1].timestamp,
                bar_count=n - val_end,
            ),
        ]


@dataclass(frozen=True)
class WalkForwardSplitter:
    train_bars: int = 500
    test_bars: int = 100
    step_bars: int = 100
    gap_bars: int = 0

    def __post_init__(self) -> None:
        if self.train_bars <= 0:
            raise ValueError("train_bars must be positive")
        if self.test_bars <= 0:
            raise ValueError("test_bars must be positive")
        if self.step_bars <= 0:
            raise ValueError("step_bars must be positive")
        if self.gap_bars < 0:
            raise ValueError("gap_bars must be non-negative")

    def split(self, sequence: OHLCVSequence) -> list[SplitWindow]:
        bars = sequence.bars
        n = len(bars)
        windows: list[SplitWindow] = []
        fold = 0
        start = 0
        while start + self.train_bars + self.gap_bars + self.test_bars <= n:
            train_start = start
            train_end = start + self.train_bars
            test_start = train_end + self.gap_bars
            test_end = test_start + self.test_bars
            windows.append(
                SplitWindow(
                    split_type="train",
                    start=bars[train_start].timestamp,
                    end=bars[train_end - 1].timestamp,
                    bar_count=self.train_bars,
                    fold_index=fold,
                )
            )
            windows.append(
                SplitWindow(
                    split_type="test",
                    start=bars[test_start].timestamp,
                    end=bars[test_end - 1].timestamp,
                    bar_count=self.test_bars,
                    fold_index=fold,
                )
            )
            fold += 1
            start += self.step_bars
        return windows

    def fold_count(self, sequence: OHLCVSequence) -> int:
        n = len(sequence.bars)
        count = 0
        start = 0
        while start + self.train_bars + self.gap_bars + self.test_bars <= n:
            count += 1
            start += self.step_bars
        return count


@dataclass(frozen=True)
class ExpandingWindowSplitter:
    min_train_bars: int = 500
    test_bars: int = 100
    step_bars: int = 100
    gap_bars: int = 0

    def __post_init__(self) -> None:
        if self.min_train_bars <= 0:
            raise ValueError("min_train_bars must be positive")
        if self.test_bars <= 0:
            raise ValueError("test_bars must be positive")
        if self.step_bars <= 0:
            raise ValueError("step_bars must be positive")
        if self.gap_bars < 0:
            raise ValueError("gap_bars must be non-negative")

    def split(self, sequence: OHLCVSequence) -> list[SplitWindow]:
        bars = sequence.bars
        n = len(bars)
        windows: list[SplitWindow] = []
        fold = 0
        test_start_idx = self.min_train_bars + self.gap_bars
        while test_start_idx + self.test_bars <= n:
            windows.append(
                SplitWindow(
                    split_type="train",
                    start=bars[0].timestamp,
                    end=bars[test_start_idx - self.gap_bars - 1].timestamp,
                    bar_count=test_start_idx - self.gap_bars,
                    fold_index=fold,
                )
            )
            windows.append(
                SplitWindow(
                    split_type="test",
                    start=bars[test_start_idx].timestamp,
                    end=bars[test_start_idx + self.test_bars - 1].timestamp,
                    bar_count=self.test_bars,
                    fold_index=fold,
                )
            )
            fold += 1
            test_start_idx += self.step_bars
        return windows

    def fold_count(self, sequence: OHLCVSequence) -> int:
        n = len(sequence.bars)
        count = 0
        test_start_idx = self.min_train_bars + self.gap_bars
        while test_start_idx + self.test_bars <= n:
            count += 1
            test_start_idx += self.step_bars
        return count


@dataclass(frozen=True)
class RollingWindowSplitter:
    train_bars: int = 500
    test_bars: int = 100
    step_bars: int = 100
    gap_bars: int = 0

    def __post_init__(self) -> None:
        if self.train_bars <= 0:
            raise ValueError("train_bars must be positive")
        if self.test_bars <= 0:
            raise ValueError("test_bars must be positive")
        if self.step_bars <= 0:
            raise ValueError("step_bars must be positive")
        if self.gap_bars < 0:
            raise ValueError("gap_bars must be non-negative")

    def split(self, sequence: OHLCVSequence) -> list[SplitWindow]:
        bars = sequence.bars
        n = len(bars)
        windows: list[SplitWindow] = []
        fold = 0
        start = 0
        while start + self.train_bars + self.gap_bars + self.test_bars <= n:
            train_start = start
            train_end = start + self.train_bars
            test_start = train_end + self.gap_bars
            test_end = test_start + self.test_bars
            windows.append(
                SplitWindow(
                    split_type="train",
                    start=bars[train_start].timestamp,
                    end=bars[train_end - 1].timestamp,
                    bar_count=self.train_bars,
                    fold_index=fold,
                )
            )
            windows.append(
                SplitWindow(
                    split_type="test",
                    start=bars[test_start].timestamp,
                    end=bars[test_end - 1].timestamp,
                    bar_count=self.test_bars,
                    fold_index=fold,
                )
            )
            fold += 1
            start += self.step_bars
        return windows

    def fold_count(self, sequence: OHLCVSequence) -> int:
        n = len(sequence.bars)
        count = 0
        start = 0
        while start + self.train_bars + self.gap_bars + self.test_bars <= n:
            count += 1
            start += self.step_bars
        return count
