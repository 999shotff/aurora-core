"""AURORA Data Fabric — Provider Registry.

Manages news, macro, and research providers.
Single source of truth for provider instances.
"""

from __future__ import annotations

import logging
from typing import Any

from .schemas import ProviderStatus
from .news_provider import NewsProvider, create_news_provider
from .macro_provider import MacroProvider, create_macro_provider
from .research_provider import ResearchProvider, create_research_provider

logger = logging.getLogger("aurora.data.registry")


class DataFabricRegistry:
    """Registry for all data fabric providers."""

    def __init__(self) -> None:
        self._news: NewsProvider | None = None
        self._macro: MacroProvider | None = None
        self._research: ResearchProvider | None = None

    def initialize(self) -> None:
        """Initialize all providers. Called once at startup."""
        self._news = create_news_provider()
        self._macro = create_macro_provider()
        self._research = create_research_provider()
        logger.info(
            "Data fabric initialized: news=%s macro=%s research=%s",
            self._news.name,
            self._macro.name,
            self._research.name,
        )

    @property
    def news(self) -> NewsProvider:
        if self._news is None:
            self._news = create_news_provider()
        return self._news

    @property
    def macro(self) -> MacroProvider:
        if self._macro is None:
            self._macro = create_macro_provider()
        return self._macro

    @property
    def research(self) -> ResearchProvider:
        if self._research is None:
            self._research = create_research_provider()
        return self._research

    def all_status(self) -> list[ProviderStatus]:
        """Get status of all providers."""
        return [
            self.news.status(),
            self.macro.status(),
            self.research.status(),
        ]

    def summary(self) -> dict[str, Any]:
        """Get a summary dict of all provider states."""
        return {
            "news": {
                "name": self.news.name,
                "state": self.news.status().state.value,
                "detail": self.news.status().detail,
            },
            "macro": {
                "name": self.macro.name,
                "state": self.macro.status().state.value,
                "detail": self.macro.status().detail,
            },
            "research": {
                "name": self.research.name,
                "state": self.research.status().state.value,
                "detail": self.research.status().detail,
            },
        }


# Global singleton
_registry: DataFabricRegistry | None = None


def get_registry() -> DataFabricRegistry:
    global _registry
    if _registry is None:
        _registry = DataFabricRegistry()
        _registry.initialize()
    return _registry
