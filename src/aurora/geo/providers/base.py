"""Geo provider abstraction — capability discovery and data access.

Providers are interchangeable. No single provider is required.
Open-data sources preferred. API keys via environment only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aurora.geo.domain import (
    AOI,
    BoundingBox,
    GeoDatasetInfo,
    GeoObservation,
    GeoProviderCapabilities,
    GeoScene,
    GeoIntegrityState,
)


@dataclass(frozen=True)
class GeoSearchResult:
    scenes: tuple[GeoScene, ...] = ()
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    provider: str = ""
    aoi: AOI | None = None
    date_range: tuple[datetime, datetime] | None = None
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE
    error: str = ""


class GeoProvider(ABC):
    """Base interface for geospatial data providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def is_open_data(self) -> bool: ...

    @abstractmethod
    def get_capabilities(self) -> GeoProviderCapabilities: ...

    @abstractmethod
    def search_scenes(
        self,
        aoi: AOI,
        start_date: datetime,
        end_date: datetime,
        dataset: str = "",
        max_cloud_pct: float = 30.0,
        resolution_m: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> GeoSearchResult: ...

    @abstractmethod
    def get_observation(
        self,
        scene: GeoScene,
        aoi: AOI,
    ) -> GeoObservation: ...

    def health_check(self) -> bool:
        try:
            caps = self.get_capabilities()
            return len(caps.datasets) >= 1
        except Exception:
            return False


class GeoProviderRegistry:
    """Registry of available geo providers."""

    def __init__(self) -> None:
        self._providers: dict[str, GeoProvider] = {}

    def register(self, provider: GeoProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> GeoProvider | None:
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def list_all_capabilities(self) -> dict[str, GeoProviderCapabilities]:
        return {
            name: p.get_capabilities()
            for name, p in self._providers.items()
        }


def create_default_registry() -> GeoProviderRegistry:
    """Create registry with all available providers."""
    registry = GeoProviderRegistry()

    try:
        from aurora.geo.providers.sentinel import SentinelProvider
        registry.register(SentinelProvider())
    except Exception:
        pass

    try:
        from aurora.geo.providers.gibs import GIBSProvider
        registry.register(GIBSProvider())
    except Exception:
        pass

    try:
        from aurora.geo.providers.skyfi import SkyFiProvider
        registry.register(SkyFiProvider())
    except Exception:
        pass

    return registry
