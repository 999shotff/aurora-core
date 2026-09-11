"""AURORA Data Fabric — News Provider.

ABC for news data providers. One real implementation: NewsAPIProvider.
Uses NewsAPI.org (https://newsapi.org). Free tier: 100 requests/day.

Configuration:
    AURORA_NEWS_PROVIDER=newsapi
    AURORA_NEWS_API_KEY=<your-newsapi-key>

Never expose API keys to frontend/logs/provenance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.parse
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .schemas import (
    NewsItem,
    ProviderState,
    ProviderStatus,
    SourceReliability,
    _now_iso,
    classify_freshness,
)

logger = logging.getLogger("aurora.data.news")


class NewsProvider(ABC):
    """Abstract news data provider."""

    @abstractmethod
    def status(self) -> ProviderStatus:
        """Current provider status."""

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 20,
        language: str = "en",
    ) -> list[NewsItem]:
        """Search for news items. Never raises on failure."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""


class NewsAPIProvider(NewsProvider):
    """NewsAPI.org provider (https://newsapi.org).

    Free tier: 100 requests/day, 10 results per request.
    Requires API key from https://newsapi.org/register.
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("AURORA_NEWS_API_KEY", "")
        self._last_error: str | None = None
        self._error_count = 0
        self._last_success: datetime | None = None

    @property
    def name(self) -> str:
        return "newsapi"

    def status(self) -> ProviderStatus:
        if not self._api_key:
            return ProviderStatus(
                name=self.name,
                state=ProviderState.NOT_CONFIGURED,
                detail="Set AURORA_NEWS_API_KEY to enable news data",
            )
        if self._last_error:
            return ProviderStatus(
                name=self.name,
                state=ProviderState.DEGRADED if self._last_success else ProviderState.ERROR,
                detail=self._last_error,
                last_success=self._last_success,
                error_count=self._error_count,
            )
        return ProviderStatus(
            name=self.name,
            state=ProviderState.READY,
            detail="NewsAPI.org connected",
            last_success=self._last_success,
        )

    def search(
        self,
        query: str,
        max_results: int = 20,
        language: str = "en",
    ) -> list[NewsItem]:
        if not self._api_key:
            return []

        # Bounded query
        query = query.strip()[:200]
        max_results = min(max(max_results, 1), 10)  # NewsAPI free tier: max 10

        try:
            params = urllib.parse.urlencode({
                "q": query,
                "language": language,
                "pageSize": max_results,
                "sortBy": "publishedAt",
                "apiKey": self._api_key,
            })
            url = f"{self.BASE_URL}?{params}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AURORA-Core/1.0"},
                method="GET",
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            self._last_success = datetime.now(timezone.utc)
            self._last_error = None

            now = _now_iso()
            items: list[NewsItem] = []

            for article in data.get("articles", []):
                headline = article.get("title", "").strip()
                if not headline:
                    continue

                published_at = article.get("publishedAt")
                content_hash = hashlib.sha256(
                    (headline + (article.get("content") or "")).encode()
                ).hexdigest()[:16]

                item = NewsItem(
                    id=f"newsapi_{content_hash}",
                    headline=headline,
                    summary=article.get("description"),
                    publisher=article.get("source", {}).get("name"),
                    source_url=article.get("url"),
                    published_at=published_at,
                    retrieved_at=now,
                    source_type="news",
                    asset_refs=(),
                    freshness=classify_freshness(published_at),
                    reliability=SourceReliability.MEDIUM,
                    provenance=f"NewsAPI.org|{article.get('source', {}).get('name', 'unknown')}|{published_at or 'unknown'}",
                    content_hash=content_hash,
                )
                items.append(item)

            logger.info("NewsAPI search '%s': %d results", query, len(items))
            return items

        except urllib.error.HTTPError as exc:
            self._error_count += 1
            self._last_error = f"HTTP {exc.code}: {exc.reason}"
            logger.warning("NewsAPI HTTP error: %s", self._last_error)
            return []
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            self._error_count += 1
            self._last_error = str(exc)[:100]
            logger.warning("NewsAPI error: %s", self._last_error)
            return []


class UnavailableNewsProvider(NewsProvider):
    """Returns empty results. Used when no provider is configured."""

    @property
    def name(self) -> str:
        return "none"

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            state=ProviderState.NOT_CONFIGURED,
            detail="No news provider configured. Set AURORA_NEWS_PROVIDER and AURORA_NEWS_API_KEY.",
        )

    def search(self, query: str, max_results: int = 20, language: str = "en") -> list[NewsItem]:
        return []


def create_news_provider() -> NewsProvider:
    """Factory: create the configured news provider."""
    provider_name = os.environ.get("AURORA_NEWS_PROVIDER", "").strip().lower()

    if provider_name == "newsapi":
        return NewsAPIProvider()

    return UnavailableNewsProvider()
