from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from aurora.schemas.market_data import OHLCVBar


@dataclass
class Rejection:
    row_index: int
    reason: str
    raw_values: dict[str, str | float | None] | None = None


@dataclass
class ValidationReport:
    asset: str
    timeframe: str
    source: str
    rows_received: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    duplicate_count: int = 0
    missing_timestamp_count: int = 0
    invalid_ohlc_count: int = 0
    time_range_start: datetime | None = None
    time_range_end: datetime | None = None
    rejections: list[Rejection] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "asset": self.asset,
            "timeframe": self.timeframe,
            "source": self.source,
            "rows_received": self.rows_received,
            "rows_accepted": self.rows_accepted,
            "rows_rejected": self.rows_rejected,
            "rejection_reasons": self.rejection_reasons,
            "duplicate_count": self.duplicate_count,
            "missing_timestamp_count": self.missing_timestamp_count,
            "invalid_ohlc_count": self.invalid_ohlc_count,
            "time_range_start": self.time_range_start.isoformat() if self.time_range_start else None,
            "time_range_end": self.time_range_end.isoformat() if self.time_range_end else None,
        }


def validate_ohlcv(
    bars: list[OHLCVBar],
    asset: str,
    timeframe: str,
    source: str = "unknown",
    expected_frequency_minutes: int | None = None,
) -> tuple[list[OHLCVBar], ValidationReport]:
    report = ValidationReport(asset=asset, timeframe=timeframe, source=source)
    report.rows_received = len(bars)

    seen_timestamps: set[datetime] = set()
    accepted: list[OHLCVBar] = []

    for i, bar in enumerate(bars):
        reasons: list[str] = []

        if bar.timestamp in seen_timestamps:
            report.duplicate_count += 1
            reasons.append("duplicate_timestamp")
        seen_timestamps.add(bar.timestamp)

        if bar.high < bar.low:
            report.invalid_ohlc_count += 1
            reasons.append("high_less_than_low")
        if bar.high < bar.open or bar.high < bar.close:
            report.invalid_ohlc_count += 1
            reasons.append("high_less_than_open_or_close")
        if bar.low > bar.open or bar.low > bar.close:
            report.invalid_ohlc_count += 1
            reasons.append("low_greater_than_open_or_close")

        if not (bar.open > 0 and bar.high > 0 and bar.low > 0 and bar.close > 0):
            report.invalid_ohlc_count += 1
            reasons.append("non_positive_ohlc")

        if reasons:
            report.rows_rejected += 1
            for r in reasons:
                report.rejection_reasons[r] = report.rejection_reasons.get(r, 0) + 1
            report.rejections.append(Rejection(row_index=i, reason="; ".join(reasons)))
        else:
            accepted.append(bar)
            report.rows_accepted += 1

    if accepted:
        timestamps = [b.timestamp for b in accepted]
        report.time_range_start = min(timestamps)
        report.time_range_end = max(timestamps)

        if expected_frequency_minutes and len(timestamps) >= 2:
            sorted_ts = sorted(timestamps)
            for j in range(1, len(sorted_ts)):
                gap = (sorted_ts[j] - sorted_ts[j - 1]).total_seconds() / 60.0
                expected_gap = expected_frequency_minutes
                if abs(gap - expected_gap) > expected_gap * 0.01:
                    report.missing_timestamp_count += 1

    return accepted, report
