"""OHLC data normalization and validation.

Normalizes provider responses into canonical AURORA contracts.
Validates: OHLC ordering, prices, timestamps, duplicates, impossible candles.
Reject invalid data rather than silently repairing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aurora.market.provider import CandleData


@dataclass(frozen=True)
class ValidationResult:
    """Result of OHLC validation."""
    valid: bool
    candles: list[CandleData]
    rejected_count: int
    errors: list[str]


def validate_candle(candle: CandleData, index: int) -> list[str]:
    """Validate a single candle. Returns list of error messages."""
    errors: list[str] = []
    prefix = f"bar[{index}]"

    if candle.open <= 0:
        errors.append(f"{prefix}: open must be positive, got {candle.open}")
    if candle.high <= 0:
        errors.append(f"{prefix}: high must be positive, got {candle.high}")
    if candle.low <= 0:
        errors.append(f"{prefix}: low must be positive, got {candle.low}")
    if candle.close <= 0:
        errors.append(f"{prefix}: close must be positive, got {candle.close}")
    if candle.volume < 0:
        errors.append(f"{prefix}: volume must be non-negative, got {candle.volume}")

    if candle.high < candle.low:
        errors.append(f"{prefix}: high ({candle.high}) < low ({candle.low})")
    if candle.high < candle.open:
        errors.append(f"{prefix}: high ({candle.high}) < open ({candle.open})")
    if candle.high < candle.close:
        errors.append(f"{prefix}: high ({candle.high}) < close ({candle.close})")
    if candle.low > candle.open:
        errors.append(f"{prefix}: low ({candle.low}) > open ({candle.open})")
    if candle.low > candle.close:
        errors.append(f"{prefix}: low ({candle.low}) > close ({candle.close})")

    try:
        dt = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            errors.append(f"{prefix}: timestamp must be timezone-aware (got naive: {candle.timestamp})")
    except (ValueError, TypeError):
        errors.append(f"{prefix}: invalid timestamp format: {candle.timestamp}")

    return errors


def normalize_and_validate(
    candles: list[CandleData],
    symbol: str = "",
    deduplicate: bool = True,
) -> ValidationResult:
    """Normalize and validate a list of candles.

    Checks:
    - Positive prices
    - OHLC ordering (high >= all others, low <= all others)
    - Timestamp validity
    - Timestamp ordering (strictly increasing)
    - Duplicate timestamps
    - Volume non-negative
    """
    if not candles:
        return ValidationResult(valid=True, candles=[], rejected_count=0, errors=[])

    all_errors: list[str] = []
    valid_candles: list[CandleData] = []

    for i, candle in enumerate(candles):
        errs = validate_candle(candle, i)
        if errs:
            all_errors.extend(errs)
        else:
            valid_candles.append(candle)

    if deduplicate:
        seen: set[str] = set()
        deduped: list[CandleData] = []
        for c in valid_candles:
            if c.timestamp not in seen:
                seen.add(c.timestamp)
                deduped.append(c)
            else:
                all_errors.append(f"Duplicate timestamp: {c.timestamp}")
        valid_candles = deduped

    if len(valid_candles) > 1:
        prev_ts = _parse_ts(valid_candles[0].timestamp)
        for i in range(1, len(valid_candles)):
            curr_ts = _parse_ts(valid_candles[i].timestamp)
            if curr_ts is not None and prev_ts is not None and curr_ts <= prev_ts:
                    all_errors.append(
                        f"Timestamp not strictly increasing: {valid_candles[i-1].timestamp} -> {valid_candles[i].timestamp}"
                    )
            prev_ts = curr_ts

    rejected = len(candles) - len(valid_candles)
    return ValidationResult(
        valid=len(all_errors) == 0,
        candles=valid_candles,
        rejected_count=rejected,
        errors=all_errors,
    )


def _parse_ts(ts: str) -> datetime | None:
    """Parse ISO timestamp to datetime."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
