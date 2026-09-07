"""Compute Fabric — provider registry.

Manages provider instances. Singleton pattern matching existing codebase.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import logging

from aurora.compute.provider import ComputeProvider
from aurora.compute.providers.cpu import CPUProvider
from aurora.compute.providers.colab import ColabProvider
from aurora.compute.providers.lightning import LightningProvider
from aurora.compute.schemas import ComputeProviderType

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry of compute providers."""

    def __init__(self) -> None:
        self._providers: dict[str, ComputeProvider] = {}
        self._init_default_providers()

    def _init_default_providers(self) -> None:
        cpu = CPUProvider()
        self._providers[cpu.provider_id] = cpu

        colab = ColabProvider()
        self._providers[colab.provider_id] = colab

        lightning = LightningProvider()
        self._providers[lightning.provider_id] = lightning

    def get(self, provider_id: str) -> ComputeProvider | None:
        return self._providers.get(provider_id)

    def get_by_type(self, provider_type: ComputeProviderType) -> ComputeProvider | None:
        for p in self._providers.values():
            if p.provider_type == provider_type:
                return p
        return None

    def list_providers(self) -> list[ComputeProvider]:
        return list(self._providers.values())

    def register(self, provider: ComputeProvider) -> None:
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> bool:
        if provider_id in self._providers and provider_id != "cpu":
            del self._providers[provider_id]
            return True
        return False
