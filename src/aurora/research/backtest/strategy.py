from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from aurora.research.backtest.data_model import Bar, Dataset


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass(frozen=True)
class Signal:
    side: Side
    strength: float = 1.0
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.side != Side.FLAT and not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"strength must be in [0,1], got {self.strength}")
        if self.stop_loss is not None and self.take_profit is not None:
            if self.side == Side.LONG and self.stop_loss >= self.take_profit:
                raise ValueError(
                    f"LONG stop_loss ({self.stop_loss}) must be < take_profit ({self.take_profit})"
                )
            if self.side == Side.SHORT and self.stop_loss <= self.take_profit:
                raise ValueError(
                    f"SHORT stop_loss ({self.stop_loss}) must be > take_profit ({self.take_profit})"
                )


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    version: str = "1.0"
    parameters: dict[str, str | int | float | bool] = field(default_factory=dict)
    lookback: int = 0
    description: str = ""


class Strategy(Protocol):
    def config(self) -> StrategyConfig: ...

    def on_bar(
        self,
        bar: Bar,
        history: list[Bar],
        position: float,
        equity: float,
    ) -> Signal: ...

    def on_start(self, dataset: Dataset) -> None: ...

    def on_end(self) -> None: ...


@runtime_checkable
class StrategyBase(Strategy, Protocol):
    _config: StrategyConfig

    def config(self) -> StrategyConfig:
        return self._config
