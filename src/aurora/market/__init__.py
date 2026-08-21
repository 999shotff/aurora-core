"""Market data infrastructure for AURORA CORE.

Provider abstraction, normalization, validation, caching,
rate limiting, provenance tracking, REST API, WebSocket service.

NO prediction claims. DATA INFRASTRUCTURE ONLY.
"""

from aurora.market.cache import BoundedCache
from aurora.market.errors import (
    ERROR_AUTH_FAILURE,
    ERROR_INVALID_ASSET,
    ERROR_INVALID_TIMEFRAME,
    ERROR_MALFORMED_RESPONSE,
    ERROR_NETWORK_FAILURE,
    ERROR_PROVIDER_UNAVAILABLE,
    ERROR_RATE_LIMIT,
    ERROR_STALE_DATA,
    MarketDataError,
    error_with_context,
)
from aurora.market.normalization import ValidationResult, normalize_and_validate
from aurora.market.provenance import DataProvenance, create_provenance
from aurora.market.provider import (
    CandleData,
    DemoMarketDataProvider,
    MarketDataProvider,
    ProviderError,
    ProviderResponse,
    QuoteData,
    RealMarketDataProvider,
    create_provider,
)
from aurora.market.rate_limiter import RateLimiter, RequestThrottler, RetryPolicy

__all__ = [
    "ERROR_AUTH_FAILURE",
    "ERROR_INVALID_ASSET",
    "ERROR_INVALID_TIMEFRAME",
    "ERROR_MALFORMED_RESPONSE",
    "ERROR_NETWORK_FAILURE",
    "ERROR_PROVIDER_UNAVAILABLE",
    "ERROR_RATE_LIMIT",
    "ERROR_STALE_DATA",
    "BoundedCache",
    "CandleData",
    "DataProvenance",
    "DemoMarketDataProvider",
    "MarketDataError",
    "MarketDataProvider",
    "ProviderError",
    "ProviderResponse",
    "QuoteData",
    "RateLimiter",
    "RealMarketDataProvider",
    "RequestThrottler",
    "RetryPolicy",
    "ValidationResult",
    "create_provenance",
    "create_provider",
    "error_with_context",
    "normalize_and_validate",
]
