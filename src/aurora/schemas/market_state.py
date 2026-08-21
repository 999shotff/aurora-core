from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Direction = Literal["bullish", "bearish", "neutral"]
DataQuality = Literal["live", "historical", "simulated", "inferred"]


class StructureState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: Direction = "neutral"
    swing_high: float | None = None
    swing_low: float | None = None
    bos: bool = False
    choch: bool = False


class LiquidityState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    buy_side_level: float | None = None
    sell_side_level: float | None = None
    buy_side_sweep: bool = False
    sell_side_sweep: bool = False
    strength: float = Field(default=0.0, ge=0.0, le=1.0)


class VolumeState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relative_volume: float | None = None
    delta: float | None = None
    delta_available: bool = False


class VolatilityState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    atr: float | None = None
    realized_volatility: float | None = None
    regime: str = "unknown"


class MarketState(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    schema_version: str = "0.1.0"
    asset: str
    timeframe: str
    timestamp: datetime
    data_quality: DataQuality
    price: float
    return_1h: float | None = None
    return_4h: float | None = None
    structure: StructureState = Field(default_factory=StructureState)
    liquidity: LiquidityState = Field(default_factory=LiquidityState)
    volume: VolumeState = Field(default_factory=VolumeState)
    volatility: VolatilityState = Field(default_factory=VolatilityState)
    vwap_distance_pct: float | None = None
    fibonacci_levels: dict[str, float] = Field(default_factory=dict)
    gann_features: dict[str, float | str | bool] = Field(default_factory=dict)
    news_features: dict[str, float | str | bool] = Field(default_factory=dict)
    research_features: dict[str, float | str | bool] = Field(default_factory=dict)
    historical_analogue_count: int = Field(default=0, ge=0)


class MarketStateSequence(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    asset: str
    timeframe: str
    snapshots: list[MarketState] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_sequence(self) -> "MarketStateSequence":
        if len(self.snapshots) < 1:
            raise ValueError("sequence must contain at least one snapshot")
        for s in self.snapshots:
            if s.asset != self.asset:
                raise ValueError(
                    f"snapshot asset '{s.asset}' != sequence asset '{self.asset}'"
                )
            if s.timeframe != self.timeframe:
                raise ValueError(
                    f"snapshot timeframe '{s.timeframe}' != sequence timeframe '{self.timeframe}'"
                )
        timestamps = [s.timestamp for s in self.snapshots]
        if timestamps != sorted(timestamps):
            raise ValueError("snapshots must be ordered by timestamp")
        if len(timestamps) != len(set(timestamps)):
            dupes = [t for t in timestamps if timestamps.count(t) > 1]
            raise ValueError(f"duplicate timestamps: {sorted(set(dupes))}")
        return self

    @property
    def latest(self) -> MarketState:
        return self.snapshots[-1]

    @property
    def window_size(self) -> int:
        return len(self.snapshots)

    def prices(self) -> list[float]:
        return [s.price for s in self.snapshots]

    def returns(self) -> list[float]:
        p = self.prices()
        if len(p) < 2:
            return []
        return [(p[i] - p[i - 1]) / p[i - 1] for i in range(1, len(p))]
