from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureProvenance:
    feature_name: str
    source_columns: list[str]
    lookback: int | None = None
    calculation_version: str = "1.0.0"
    warmup_policy: str = "none"
    method: str = "unknown"
    notes: str = ""

    def to_dict(self) -> dict[str, str | int | list[str] | None]:
        return {
            "feature_name": self.feature_name,
            "source_columns": self.source_columns,
            "lookback": self.lookback,
            "calculation_version": self.calculation_version,
            "warmup_policy": self.warmup_policy,
            "method": self.method,
            "notes": self.notes,
        }


FEATURE_REGISTRY: dict[str, FeatureProvenance] = {
    "return_1h": FeatureProvenance(
        feature_name="return_1h",
        source_columns=["close"],
        lookback=1,
        method="simple_return",
        warmup_policy="none",
    ),
    "return_4h": FeatureProvenance(
        feature_name="return_4h",
        source_columns=["close"],
        lookback=4,
        method="simple_return",
        warmup_policy="none",
    ),
    "sma": FeatureProvenance(
        feature_name="sma",
        source_columns=["close"],
        lookback=20,
        method="simple_moving_average",
        warmup_policy="insufficient_data_returns_none",
    ),
    "ema": FeatureProvenance(
        feature_name="ema",
        source_columns=["close"],
        lookback=20,
        method="exponential_moving_average",
        warmup_policy="sma_seed",
    ),
    "rsi": FeatureProvenance(
        feature_name="rsi",
        source_columns=["close"],
        lookback=14,
        method="wilder_smoothing",
        warmup_policy="insufficient_data_returns_none",
    ),
    "atr": FeatureProvenance(
        feature_name="atr",
        source_columns=["high", "low", "close"],
        lookback=14,
        method="average_true_range",
        warmup_policy="insufficient_data_returns_none",
    ),
    "rolling_mean": FeatureProvenance(
        feature_name="rolling_mean",
        source_columns=["close"],
        lookback=20,
        method="simple_moving_average",
        warmup_policy="insufficient_data_returns_none",
    ),
    "rolling_std": FeatureProvenance(
        feature_name="rolling_std",
        source_columns=["close"],
        lookback=20,
        method="population_standard_deviation",
        warmup_policy="insufficient_data_returns_none",
    ),
    "momentum": FeatureProvenance(
        feature_name="momentum",
        source_columns=["close"],
        lookback=10,
        method="price_momentum",
        warmup_policy="insufficient_data_returns_none",
    ),
    "volume_ratio": FeatureProvenance(
        feature_name="volume_ratio",
        source_columns=["volume"],
        lookback=20,
        method="volume_ratio_to_rolling_average",
        warmup_policy="insufficient_data_returns_none",
    ),
    "volatility": FeatureProvenance(
        feature_name="volatility",
        source_columns=["close"],
        lookback=20,
        method="rolling_standard_deviation",
        warmup_policy="insufficient_data_returns_none",
    ),
    "swing_range": FeatureProvenance(
        feature_name="swing_range",
        source_columns=["swing_high", "swing_low"],
        method="structural_range",
        warmup_policy="none",
    ),
    "price_position_in_range": FeatureProvenance(
        feature_name="price_position_in_range",
        source_columns=["price", "swing_high", "swing_low"],
        method="normalized_position",
        warmup_policy="none",
    ),
    "liquidity_strength": FeatureProvenance(
        feature_name="liquidity_strength",
        source_columns=["liquidity_strength"],
        method="direct_copy",
        warmup_policy="none",
    ),
}


def get_provenance(feature_name: str) -> FeatureProvenance | None:
    return FEATURE_REGISTRY.get(feature_name)


def register_provenance(provenance: FeatureProvenance) -> None:
    FEATURE_REGISTRY[provenance.feature_name] = provenance
