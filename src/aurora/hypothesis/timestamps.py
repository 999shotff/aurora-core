from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeatureTimestamp(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    feature_name: str
    feature_timestamp: datetime
    prediction_timestamp: datetime
    target_start_timestamp: datetime | None = None
    target_end_timestamp: datetime | None = None
    lookback_bars: int = 0
    is_valid: bool = True
    validation_error: str = ""


class TargetTimestamp(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    target_id: str
    target_start_timestamp: datetime
    target_end_timestamp: datetime
    horizon_bars: int
    valid: bool = True
    error: str = ""


@dataclass(frozen=True)
class TimestampValidator:
    max_lookback_bars: int = 1000

    def validate_feature(
        self,
        feature_timestamp: datetime,
        prediction_timestamp: datetime,
        feature_name: str = "",
    ) -> FeatureTimestamp:
        is_valid = feature_timestamp <= prediction_timestamp
        error = "" if is_valid else (
            f"Feature '{feature_name}' timestamp {feature_timestamp} "
            f"after prediction timestamp {prediction_timestamp}"
        )
        return FeatureTimestamp(
            feature_name=feature_name,
            feature_timestamp=feature_timestamp,
            prediction_timestamp=prediction_timestamp,
            is_valid=is_valid,
            validation_error=error,
        )

    def validate_target(
        self,
        feature_timestamp: datetime,
        target_start: datetime,
        target_end: datetime,
        horizon_bars: int,
        target_id: str = "",
    ) -> TargetTimestamp:
        valid = target_start >= feature_timestamp
        error = "" if valid else (
            f"Target '{target_id}' starts at {target_start} "
            f"but feature is at {feature_timestamp}"
        )
        return TargetTimestamp(
            target_id=target_id,
            target_start_timestamp=target_start,
            target_end_timestamp=target_end,
            horizon_bars=horizon_bars,
            valid=valid,
            error=error,
        )

    def validate_batch(
        self,
        feature_timestamps: list[datetime],
        prediction_timestamps: list[datetime],
        feature_names: list[str] | None = None,
    ) -> list[FeatureTimestamp]:
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(feature_timestamps))]
        return [
            self.validate_feature(ft, pt, fn)
            for ft, pt, fn in zip(feature_timestamps, prediction_timestamps, feature_names)
        ]

    def all_valid(self, results: list[FeatureTimestamp]) -> bool:
        return all(r.is_valid for r in results)

    def all_targets_valid(self, results: list[TargetTimestamp]) -> bool:
        return all(r.valid for r in results)
