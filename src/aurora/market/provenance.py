"""Data provenance tracking.

Every market-data response identifies: provider, asset, timeframe,
retrieved_at, data_timestamp, source_status, demo/live status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DataProvenance:
    """Provenance record for market data."""
    provider: str
    asset: str
    timeframe: str
    retrieved_at: str
    data_timestamp: str
    source_status: str  # "ok", "unavailable", "error"
    is_demo: bool
    candle_count: int = 0
    validation_errors: list[str] = field(default_factory=list)
    error_code: str = ""
    error_message: str = ""


def create_provenance(
    provider: str,
    asset: str,
    timeframe: str,
    is_demo: bool,
    source_status: str,
    candle_count: int = 0,
    data_timestamp: str = "",
    validation_errors: list[str] | None = None,
    error_code: str = "",
    error_message: str = "",
) -> DataProvenance:
    """Create a provenance record."""
    return DataProvenance(
        provider=provider,
        asset=asset,
        timeframe=timeframe,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        data_timestamp=data_timestamp,
        source_status=source_status,
        is_demo=is_demo,
        candle_count=candle_count,
        validation_errors=validation_errors or [],
        error_code=error_code,
        error_message=error_message,
    )
