"""Structured error types for market data pipeline.

Explicit errors for: provider unavailable, invalid asset, invalid timeframe,
rate limit, auth failure, malformed response, stale data, network failure.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketDataError:
    """Structured market data error with code and metadata."""
    code: str
    message: str
    provider: str
    asset: str
    timeframe: str
    retryable: bool
    status_code: int = 500


ERROR_PROVIDER_UNAVAILABLE = MarketDataError(
    code="PROVIDER_UNAVAILABLE", message="Market data provider is unavailable",
    provider="", asset="", timeframe="", retryable=True, status_code=503,
)

ERROR_INVALID_ASSET = MarketDataError(
    code="INVALID_ASSET", message="Unknown or unsupported asset",
    provider="", asset="", timeframe="", retryable=False, status_code=404,
)

ERROR_INVALID_TIMEFRAME = MarketDataError(
    code="INVALID_TIMEFRAME", message="Invalid or unsupported timeframe",
    provider="", asset="", timeframe="", retryable=False, status_code=400,
)

ERROR_RATE_LIMIT = MarketDataError(
    code="RATE_LIMIT", message="Provider rate limit exceeded",
    provider="", asset="", timeframe="", retryable=True, status_code=429,
)

ERROR_AUTH_FAILURE = MarketDataError(
    code="AUTH_FAILURE", message="Provider authentication failed",
    provider="", asset="", timeframe="", retryable=False, status_code=401,
)

ERROR_MALFORMED_RESPONSE = MarketDataError(
    code="MALFORMED_RESPONSE", message="Provider returned malformed data",
    provider="", asset="", timeframe="", retryable=True, status_code=502,
)

ERROR_STALE_DATA = MarketDataError(
    code="STALE_DATA", message="Data is stale or expired",
    provider="", asset="", timeframe="", retryable=True, status_code=504,
)

ERROR_NETWORK_FAILURE = MarketDataError(
    code="NETWORK_FAILURE", message="Network connection failed",
    provider="", asset="", timeframe="", retryable=True, status_code=503,
)


def error_with_context(
    base: MarketDataError,
    *,
    provider: str = "",
    asset: str = "",
    timeframe: str = "",
    message: str = "",
) -> MarketDataError:
    """Create a copy of an error with additional context."""
    return MarketDataError(
        code=base.code,
        message=message or base.message,
        provider=provider or base.provider,
        asset=asset or base.asset,
        timeframe=timeframe or base.timeframe,
        retryable=base.retryable,
        status_code=base.status_code,
    )
