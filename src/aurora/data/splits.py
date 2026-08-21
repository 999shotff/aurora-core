from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from aurora.schemas.market_data import OHLCVSequence

SplitName = Literal["train", "validation", "test"]


@dataclass(frozen=True)
class SplitAssignment:
    split: SplitName
    start: datetime
    end: datetime
    bar_count: int


@dataclass(frozen=True)
class TimeBasedSplitter:
    train_ratio: float = 0.7
    validation_ratio: float = 0.15
    test_ratio: float = 0.15

    def __post_init__(self) -> None:
        total = self.train_ratio + self.validation_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"ratios must sum to 1.0, got {total}")

    def split(
        self, sequence: OHLCVSequence
    ) -> dict[SplitName, OHLCVSequence]:
        bars = sequence.bars
        n = len(bars)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.validation_ratio)

        splits: dict[SplitName, OHLCVSequence] = {
            "train": OHLCVSequence(
                asset=sequence.asset,
                timeframe=sequence.timeframe,
                bars=bars[:train_end],
            ),
            "validation": OHLCVSequence(
                asset=sequence.asset,
                timeframe=sequence.timeframe,
                bars=bars[train_end:val_end],
            ),
            "test": OHLCVSequence(
                asset=sequence.asset,
                timeframe=sequence.timeframe,
                bars=bars[val_end:],
            ),
        }
        return splits

    def assignments(
        self, sequence: OHLCVSequence
    ) -> list[SplitAssignment]:
        bars = sequence.bars
        n = len(bars)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.validation_ratio)

        return [
            SplitAssignment(
                split="train",
                start=bars[0].timestamp,
                end=bars[train_end - 1].timestamp if train_end > 0 else bars[0].timestamp,
                bar_count=train_end,
            ),
            SplitAssignment(
                split="validation",
                start=bars[train_end].timestamp if train_end < n else bars[-1].timestamp,
                end=bars[val_end - 1].timestamp if val_end > train_end else bars[train_end].timestamp,
                bar_count=val_end - train_end,
            ),
            SplitAssignment(
                split="test",
                start=bars[val_end].timestamp if val_end < n else bars[-1].timestamp,
                end=bars[-1].timestamp,
                bar_count=n - val_end,
            ),
        ]

    def validate_no_leakage(
        self, splits: dict[SplitName, OHLCVSequence]
    ) -> bool:
        for name, seq in splits.items():
            for other_name, other_seq in splits.items():
                if name == other_name:
                    continue
                train_before = name == "train" and other_name in ("validation", "test")
                val_before_test = name == "validation" and other_name == "test"
                if (train_before or val_before_test) and seq.bars and other_seq.bars and seq.bars[-1].timestamp >= other_seq.bars[0].timestamp:
                    return False
        return True
