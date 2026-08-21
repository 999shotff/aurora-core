"""Production configuration for AURORA CORE backend.

Loads from environment variables with sensible defaults.
Never exposes secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductionConfig:
    """Production server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "info"
    cors_origins: list[str] = field(default_factory=lambda: ["https://aurora-core.vercel.app"])
    worker_count: int = 1
    timeout_seconds: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB


@dataclass(frozen=True)
class ProviderConfig:
    """Provider configuration."""
    data_mode: str = "demo"
    yahoo_api_key: str = ""
    timeout_seconds: int = 10
    max_retries: int = 3


@dataclass(frozen=True)
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    ttl_seconds: int = 60
    max_size: int = 256


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    burst: int = 10


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""
    production: ProductionConfig = field(default_factory=ProductionConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    version: str = "0.2.0"
    research_conclusion: str = "NO_DEPLOYMENT_SIGNAL"


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    cors_raw = os.environ.get("AURORA_CORS_ORIGINS", "https://aurora-core.vercel.app")
    cors = [o.strip() for o in cors_raw.split(",") if o.strip()]

    return AppConfig(
        production=ProductionConfig(
            host=os.environ.get("AURORA_HOST", "0.0.0.0"),
            port=int(os.environ.get("AURORA_PORT", "8000")),
            debug=os.environ.get("AURORA_DEBUG", "false").lower() == "true",
            log_level=os.environ.get("AURORA_LOG_LEVEL", "info"),
            cors_origins=cors,
        ),
        provider=ProviderConfig(
            data_mode=os.environ.get("AURORA_DATA_MODE", "demo"),
            yahoo_api_key=os.environ.get("AURORA_YAHOO_API_KEY", ""),
            timeout_seconds=int(os.environ.get("AURORA_PROVIDER_TIMEOUT_SECONDS", "10")),
            max_retries=int(os.environ.get("AURORA_PROVIDER_MAX_RETRIES", "3")),
        ),
        cache=CacheConfig(
            ttl_seconds=int(os.environ.get("AURORA_CACHE_TTL_SECONDS", "60")),
            max_size=int(os.environ.get("AURORA_CACHE_MAX_SIZE", "256")),
        ),
        rate_limit=RateLimitConfig(
            requests_per_minute=int(os.environ.get("AURORA_RATE_LIMIT_RPM", "60")),
            burst=int(os.environ.get("AURORA_RATE_LIMIT_BURST", "10")),
        ),
    )
