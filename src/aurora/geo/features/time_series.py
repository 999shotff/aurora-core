"""Time series engine — multi-temporal observation management.

Supports: date ordering, missing dates, irregular intervals,
quality filtering, temporal statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

from aurora.geo.domain import (
    GeoIntegrityState,
    GeoTimeSeries,
    GeoTimeSeriesPoint,
)
from aurora.geo.raster.engine import RasterScene
from aurora.geo.features.index_engine import IndexResult


@dataclass(frozen=True)
class TimeSeriesStats:
    mean: float
    std: float
    min_val: float
    max_val: float
    count: int
    trend_slope: float
    trend_r_squared: float
    anomaly_count: int
    missing_count: int
    date_range_days: int


class GeoTimeSeriesEngine:
    """Manages multi-temporal geospatial observations."""

    def __init__(self, series_id: str, metric: str, unit: str = "") -> None:
        self.series_id = series_id
        self.metric = metric
        self.unit = unit
        self._points: list[GeoTimeSeriesPoint] = []
        self._scenes: list[tuple[datetime, RasterScene]] = []

    @property
    def count(self) -> int:
        return len(self._points)

    @property
    def is_empty(self) -> bool:
        return len(self._points) == 0

    def add_observation(
        self,
        timestamp: datetime,
        scene: RasterScene,
        index_result: IndexResult,
        cloud_pct: float = 0.0,
    ) -> None:
        """Add a raster observation and its computed index to the time series."""
        value = index_result.mean if index_result.supported else np.nan
        confidence = 1.0 - (cloud_pct / 100.0 * 0.8)

        if not index_result.supported:
            integrity = GeoIntegrityState.DATA_UNAVAILABLE
        elif cloud_pct > 80:
            integrity = GeoIntegrityState.LOW_CONFIDENCE
        elif confidence < 0.3:
            integrity = GeoIntegrityState.LOW_CONFIDENCE
        else:
            integrity = GeoIntegrityState.DATA_AVAILABLE

        point = GeoTimeSeriesPoint(
            timestamp=timestamp,
            value=value,
            confidence=confidence,
            cloud_pct=cloud_pct,
            integrity_state=integrity,
        )

        self._points.append(point)
        self._scenes.append((timestamp, scene))
        self._points.sort(key=lambda p: p.timestamp)

    def add_scalar(
        self,
        timestamp: datetime,
        value: float,
        confidence: float = 1.0,
        cloud_pct: float = 0.0,
        integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE,
    ) -> None:
        """Add a pre-computed scalar value to the time series."""
        point = GeoTimeSeriesPoint(
            timestamp=timestamp,
            value=value,
            confidence=confidence,
            cloud_pct=cloud_pct,
            integrity_state=integrity_state,
        )
        self._points.append(point)
        self._points.sort(key=lambda p: p.timestamp)

    def filter_by_quality(
        self,
        min_confidence: float = 0.0,
        max_cloud_pct: float = 100.0,
        exclude_states: tuple[GeoIntegrityState, ...] = (),
    ) -> list[GeoTimeSeriesPoint]:
        """Return points matching quality criteria."""
        return [
            p for p in self._points
            if p.confidence >= min_confidence
            and p.cloud_pct <= max_cloud_pct
            and p.integrity_state not in exclude_states
        ]

    def filter_by_date_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[GeoTimeSeriesPoint]:
        """Return points within date range."""
        result = self._points
        if start:
            result = [p for p in result if p.timestamp >= start]
        if end:
            result = [p for p in result if p.timestamp <= end]
        return result

    def compute_stats(
        self,
        min_confidence: float = 0.0,
        max_cloud_pct: float = 100.0,
    ) -> TimeSeriesStats:
        """Compute temporal statistics on the time series."""
        filtered = [
            p for p in self._points
            if p.confidence >= min_confidence
            and p.cloud_pct <= max_cloud_pct
            and p.integrity_state == GeoIntegrityState.DATA_AVAILABLE
        ]

        if len(filtered) < 2:
            return TimeSeriesStats(
                mean=np.nan, std=np.nan,
                min_val=np.nan, max_val=np.nan,
                count=len(filtered),
                trend_slope=0.0, trend_r_squared=0.0,
                anomaly_count=0,
                missing_count=len(self._points) - len(filtered),
                date_range_days=0,
            )

        values = np.array([p.value for p in filtered])
        mean = float(np.mean(values))
        std = float(np.std(values))

        days = np.array([
            (p.timestamp - filtered[0].timestamp).total_seconds() / 86400
            for p in filtered
        ])

        if len(days) >= 2 and np.std(days) > 0:
            slope, intercept = np.polyfit(days, values, 1)
            predicted = slope * days + intercept
            ss_res = np.sum((values - predicted) ** 2)
            ss_tot = np.sum((values - mean) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        else:
            slope = 0.0
            r_squared = 0.0

        if std > 0:
            z_scores = np.abs((values - mean) / std)
            anomaly_count = int(np.sum(z_scores > 2.0))
        else:
            anomaly_count = 0

        date_range = (filtered[-1].timestamp - filtered[0].timestamp).days

        return TimeSeriesStats(
            mean=mean,
            std=std,
            min_val=float(np.min(values)),
            max_val=float(np.max(values)),
            count=len(filtered),
            trend_slope=float(slope),
            trend_r_squared=float(r_squared),
            anomaly_count=anomaly_count,
            missing_count=len(self._points) - len(filtered),
            date_range_days=date_range,
        )

    def to_geo_time_series(self) -> GeoTimeSeries:
        """Export to the domain GeoTimeSeries model."""
        return GeoTimeSeries(
            series_id=self.series_id,
            aoi=None,  # type: ignore
            metric=self.metric,
            unit=self.unit,
            points=tuple(self._points),
        )

    def detect_missing_dates(
        self,
        expected_interval_days: int = 5,
        tolerance_days: int = 2,
    ) -> list[tuple[datetime, datetime]]:
        """Detect gaps in the time series."""
        if len(self._points) < 2:
            return []

        gaps = []
        for i in range(1, len(self._points)):
            gap = (self._points[i].timestamp - self._points[i - 1].timestamp).days
            if gap > expected_interval_days + tolerance_days:
                gaps.append((self._points[i - 1].timestamp, self._points[i].timestamp))
        return gaps

    def interpolate_missing(
        self,
        method: str = "linear",
    ) -> list[GeoTimeSeriesPoint]:
        """Interpolate missing values. Only when explicitly configured."""
        valid = [
            p for p in self._points
            if p.integrity_state == GeoIntegrityState.DATA_AVAILABLE
            and not np.isnan(p.value)
        ]

        if len(valid) < 2:
            return list(self._points)

        valid_times = np.array([
            (p.timestamp - valid[0].timestamp).total_seconds() / 86400
            for p in valid
        ])
        valid_values = np.array([p.value for p in valid])

        all_times = [
            (p.timestamp - valid[0].timestamp).total_seconds() / 86400
            for p in self._points
        ]

        interpolated = list(self._points)
        for i, point in enumerate(interpolated):
            if point.integrity_state != GeoIntegrityState.DATA_AVAILABLE or np.isnan(point.value):
                t = all_times[i]
                new_val = float(np.interp(t, valid_times, valid_values))
                interpolated[i] = GeoTimeSeriesPoint(
                    timestamp=point.timestamp,
                    value=new_val,
                    confidence=0.5,
                    cloud_pct=point.cloud_pct,
                    integrity_state=GeoIntegrityState.DATA_AVAILABLE,
                )

        return interpolated
