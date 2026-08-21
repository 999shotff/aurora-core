from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TargetType = Literal[
    "future_return",
    "future_direction",
    "volatility",
    "maximum_favorable_excursion",
    "maximum_adverse_excursion",
]


class TargetDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    target_id: str
    target_type: TargetType
    horizon_bars: int = Field(gt=0)
    calculation: str = ""
    timestamp_convention: str = "end_of_horizon"
    requires_future_data: bool = True
    description: str = ""


class TargetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    target_id: str
    target_type: TargetType
    value: float
    timestamp: datetime
    target_start_timestamp: datetime
    target_end_timestamp: datetime
    horizon_bars: int
    valid: bool = True
    error: str = ""


@dataclass(frozen=True)
class TargetCalculator:
    definitions: dict[str, TargetDefinition]

    def compute(
        self,
        target_id: str,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        timestamps: list[datetime],
        index: int,
    ) -> TargetResult:
        if target_id not in self.definitions:
            raise KeyError(f"Unknown target: {target_id}")
        defn = self.definitions[target_id]
        end_idx = index + defn.horizon_bars
        if end_idx >= len(closes):
            return TargetResult(
                target_id=target_id,
                target_type=defn.target_type,
                value=0.0,
                timestamp=timestamps[index],
                target_start_timestamp=timestamps[index],
                target_end_timestamp=timestamps[-1],
                horizon_bars=defn.horizon_bars,
                valid=False,
                error="Insufficient future data",
            )
        if defn.target_type == "future_return":
            value = compute_future_return(closes, index, defn.horizon_bars)
        elif defn.target_type == "future_direction":
            value = compute_future_direction(closes, index, defn.horizon_bars)
        elif defn.target_type == "volatility":
            value = compute_volatility(highs, lows, closes, index, defn.horizon_bars)
        elif defn.target_type == "maximum_favorable_excursion":
            value = compute_maximum_favorable_excursion(highs, index, defn.horizon_bars)
        elif defn.target_type == "maximum_adverse_excursion":
            value = compute_maximum_adverse_excursion(lows, index, defn.horizon_bars)
        else:
            raise ValueError(f"Unknown target type: {defn.target_type}")
        return TargetResult(
            target_id=target_id,
            target_type=defn.target_type,
            value=value,
            timestamp=timestamps[index],
            target_start_timestamp=timestamps[index],
            target_end_timestamp=timestamps[end_idx],
            horizon_bars=defn.horizon_bars,
            valid=True,
        )


def compute_future_return(
    closes: list[float], index: int, horizon: int
) -> float:
    entry = closes[index]
    exit_price = closes[index + horizon]
    if entry == 0.0:
        return 0.0
    return (exit_price - entry) / entry


def compute_future_direction(
    closes: list[float], index: int, horizon: int
) -> float:
    entry = closes[index]
    exit_price = closes[index + horizon]
    if exit_price > entry:
        return 1.0
    elif exit_price < entry:
        return -1.0
    return 0.0


def compute_volatility(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    index: int,
    horizon: int,
) -> float:
    window = closes[index : index + horizon + 1]
    if len(window) < 2:
        return 0.0
    returns = [(window[i] - window[i - 1]) / window[i - 1] if window[i - 1] != 0 else 0.0 for i in range(1, len(window))]
    mean_ret = sum(returns) / len(returns)
    var = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    return var**0.5


def compute_maximum_favorable_excursion(
    highs: list[float], index: int, horizon: int
) -> float:
    entry = highs[index]
    future_highs = highs[index + 1 : index + horizon + 1]
    if not future_highs:
        return 0.0
    max_price = max(future_highs)
    if entry == 0.0:
        return 0.0
    return (max_price - entry) / entry


def compute_maximum_adverse_excursion(
    lows: list[float], index: int, horizon: int
) -> float:
    entry = lows[index]
    future_lows = lows[index + 1 : index + horizon + 1]
    if not future_lows:
        return 0.0
    min_price = min(future_lows)
    if entry == 0.0:
        return 0.0
    return (min_price - entry) / entry
