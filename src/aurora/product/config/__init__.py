"""Application configuration for AURORA CORE product layer.

All configuration is local. No cloud deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ServerConfig:
    """Backend server configuration."""
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    reload: bool = False


@dataclass(frozen=True)
class DataConfig:
    """Data source configuration."""
    provider: str = "yfinance"
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    default_period: str = "5y"
    default_interval: str = "1d"


@dataclass(frozen=True)
class ChartConfig:
    """Chart rendering configuration."""
    default_theme: str = "dark"
    default_timeframe: str = "1d"
    max_bars: int = 5000
    default_bars: int = 200
    responsive: bool = True


@dataclass(frozen=True)
class WebSocketConfig:
    """WebSocket configuration."""
    enabled: bool = True
    max_connections: int = 100
    ping_interval: int = 30


@dataclass(frozen=True)
class AuroraConfig:
    """Top-level application configuration."""
    server: ServerConfig = field(default_factory=ServerConfig)
    data: DataConfig = field(default_factory=DataConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    research_conclusion: str = "NO_DEPLOYMENT_SIGNAL"
    version: str = "0.1.0"


DEFAULT_CONFIG = AuroraConfig()
