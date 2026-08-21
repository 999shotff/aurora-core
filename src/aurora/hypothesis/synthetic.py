from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field


class SyntheticBar(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    signal: float = 0.0


class SyntheticDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    name: str
    description: str
    bars: list[SyntheticBar]
    known_signal: bool
    known_leakage: bool = False
    has_regime_change: bool = False
    signal_strength: float = 0.0
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


@dataclass(frozen=True)
class SyntheticGenerator:
    seed: int = 42

    def _hash(self, idx: int) -> float:
        h = hashlib.sha256(f"{self.seed}_{idx}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF

    def _hash_normal(self, idx: int) -> float:
        u1 = max(self._hash(idx), 1e-10)
        u2 = self._hash(idx + 10000)
        return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)

    def generate_with_known_signal(
        self, n_bars: int = 500, signal_strength: float = 0.3
    ) -> SyntheticDataset:
        bars: list[SyntheticBar] = []
        base_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        for i in range(n_bars):
            noise = self._hash_normal(i) * 0.02
            signal = signal_strength * (1.0 if self._hash(i) > 0.5 else -1.0)
            ret = signal + noise
            new_price = price * (1 + ret)
            vol = 1000 + self._hash(i + 5000) * 500
            bars.append(
                SyntheticBar(
                    timestamp=base_time + timedelta(hours=i),
                    open=price,
                    high=max(price, new_price) * (1 + abs(self._hash(i + 10000)) * 0.01),
                    low=min(price, new_price) * (1 - abs(self._hash(i + 20000)) * 0.01),
                    close=new_price,
                    volume=vol,
                    signal=signal,
                )
            )
            price = new_price
        return SyntheticDataset(
            name="known_signal",
            description="Dataset with a known predictive feature embedded in the data",
            bars=bars,
            known_signal=True,
            signal_strength=signal_strength,
        )

    def generate_without_signal(self, n_bars: int = 500) -> SyntheticDataset:
        bars: list[SyntheticBar] = []
        base_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        for i in range(n_bars):
            noise = self._hash_normal(i) * 0.02
            new_price = price * (1 + noise)
            vol = 1000 + self._hash(i + 5000) * 500
            bars.append(
                SyntheticBar(
                    timestamp=base_time + timedelta(hours=i),
                    open=price,
                    high=max(price, new_price) * (1 + abs(self._hash(i + 10000)) * 0.01),
                    low=min(price, new_price) * (1 - abs(self._hash(i + 20000)) * 0.01),
                    close=new_price,
                    volume=vol,
                    signal=0.0,
                )
            )
            price = new_price
        return SyntheticDataset(
            name="no_signal",
            description="Dataset with no predictive features — pure noise",
            bars=bars,
            known_signal=False,
            signal_strength=0.0,
        )

    def generate_with_leakage(self, n_bars: int = 500) -> SyntheticDataset:
        bars: list[SyntheticBar] = []
        base_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        for i in range(n_bars):
            noise = self._hash_normal(i) * 0.02
            new_price = price * (1 + noise)
            vol = 1000 + self._hash(i + 5000) * 500
            future_return = (new_price - price) / price if price > 0 else 0.0
            bars.append(
                SyntheticBar(
                    timestamp=base_time + timedelta(hours=i),
                    open=price,
                    high=max(price, new_price) * (1 + abs(self._hash(i + 10000)) * 0.01),
                    low=min(price, new_price) * (1 - abs(self._hash(i + 20000)) * 0.01),
                    close=new_price,
                    volume=vol,
                    signal=future_return,
                )
            )
            price = new_price
        return SyntheticDataset(
            name="leakage",
            description="Dataset where signal contains future information (leakage)",
            bars=bars,
            known_signal=True,
            known_leakage=True,
            signal_strength=1.0,
        )

    def generate_with_regime_change(self, n_bars: int = 500) -> SyntheticDataset:
        bars: list[SyntheticBar] = []
        base_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        regime_change_idx = n_bars // 2
        for i in range(n_bars):
            if i < regime_change_idx:
                noise = self._hash_normal(i) * 0.01
                trend = 0.001
            else:
                noise = self._hash_normal(i) * 0.04
                trend = -0.002
            ret = trend + noise
            new_price = price * (1 + ret)
            vol = 1000 + self._hash(i + 5000) * 500
            bars.append(
                SyntheticBar(
                    timestamp=base_time + timedelta(hours=i),
                    open=price,
                    high=max(price, new_price) * (1 + abs(self._hash(i + 10000)) * 0.01),
                    low=min(price, new_price) * (1 - abs(self._hash(i + 20000)) * 0.01),
                    close=new_price,
                    volume=vol,
                    signal=0.0,
                )
            )
            price = new_price
        return SyntheticDataset(
            name="regime_change",
            description="Dataset with a regime change at the midpoint",
            bars=bars,
            known_signal=False,
            has_regime_change=True,
            signal_strength=0.0,
            metadata={"regime_change_index": regime_change_idx},
        )

    def generate_all(self) -> list[SyntheticDataset]:
        return [
            self.generate_with_known_signal(),
            self.generate_without_signal(),
            self.generate_with_leakage(),
            self.generate_with_regime_change(),
        ]
