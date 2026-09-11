"""AURORA Data Fabric — Research Provider.

ABC for research document providers. Real implementation: ArxivProvider.
Uses arXiv public API (http://export.arxiv.org/api/query).

Security:
    - Allowlisted endpoint only (export.arxiv.org)
    - Query length bounded to 200 characters
    - Result count bounded (1-50)
    - Request timeout 15s
    - Response size limited to 5MB
    - No credentials required (public API)
    - No executable content processed
"""

from __future__ import annotations

import hashlib
import logging
import os
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .schemas import (
    ProviderState,
    ProviderStatus,
    ResearchDocument,
    SourceReliability,
    classify_freshness,
)

logger = logging.getLogger("aurora.data.research")

# Security: Allowlisted arXiv endpoint only (HTTPS)
ALLOWED_BASE_URL = "https://export.arxiv.org/api/query"
REQUEST_TIMEOUT = 15  # seconds
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_QUERY_LENGTH = 200
MAX_RESULTS = 50


class ResearchProvider(ABC):
    """Abstract research data provider."""

    @abstractmethod
    def status(self) -> ProviderStatus:
        """Current provider status."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[ResearchDocument]:
        """Search for research documents. Never raises on failure."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""


class UnavailableResearchProvider(ResearchProvider):
    """Returns empty results. Used when no provider is configured."""

    @property
    def name(self) -> str:
        return "none"

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            state=ProviderState.NOT_CONFIGURED,
            detail="No research provider configured. Connect a document source to enable research intelligence.",
        )

    def search(self, query: str, max_results: int = 10) -> list[ResearchDocument]:
        return []


class ArxivProvider(ResearchProvider):
    """Real research provider using arXiv public API."""

    def __init__(self) -> None:
        self._last_success: datetime | None = None
        self._error_count = 0
        self._verified = False

    @property
    def name(self) -> str:
        return "arxiv"

    def status(self) -> ProviderStatus:
        """Return provider status. Only READY if actually verified."""
        if self._verified:
            return ProviderStatus(
                name=self.name,
                state=ProviderState.READY,
                detail="arXiv public API connected",
                last_success=self._last_success,
                error_count=self._error_count,
            )
        return ProviderStatus(
            name=self.name,
            state=ProviderState.CONNECTING,
            detail="Attempting to verify arXiv connection...",
            last_success=self._last_success,
            error_count=self._error_count,
        )

    def _validate_url(self, url: str) -> bool:
        """Ensure URL is within allowlist. Prevents SSRF."""
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc == "export.arxiv.org" and parsed.scheme in ("http", "https")

    def _validate_query(self, query: str) -> str:
        """Validate and sanitize query. Bounded length."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        query = query.strip()[:MAX_QUERY_LENGTH]
        return query

    def _parse_arxiv_response(self, xml_content: str) -> list[ResearchDocument]:
        """Parse arXiv Atom XML response into ResearchDocument objects."""
        documents = []
        try:
            root = ET.fromstring(xml_content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                try:
                    # Extract paper ID from the entry id URL
                    entry_id_elem = entry.find("atom:id", ns)
                    if entry_id_elem is None or entry_id_elem.text is None:
                        continue
                    entry_id = entry_id_elem.text.strip()

                    # Extract arXiv ID from the URL
                    # Format: http://arxiv.org/abs/2301.12345v1
                    arxiv_id = entry_id.split("/abs/")[-1]
                    if not arxiv_id:
                        continue

                    # Extract title
                    title_elem = entry.find("atom:title", ns)
                    title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled"

                    # Extract authors
                    authors = []
                    for author_elem in entry.findall("atom:author", ns):
                        name_elem = author_elem.find("atom:name", ns)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text.strip())

                    # Extract abstract/summary
                    summary_elem = entry.find("atom:summary", ns)
                    abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else None

                    # Extract published date
                    published_elem = entry.find("atom:published", ns)
                    published_at = published_elem.text.strip() if published_elem is not None and published_elem.text else None

                    # Extract updated date
                    updated_elem = entry.find("atom:updated", ns)
                    updated_at = updated_elem.text.strip() if updated_elem is not None and updated_elem.text else None

                    # Extract categories
                    categories = []
                    for cat_elem in entry.findall("atom:category", ns):
                        term = cat_elem.get("term")
                        if term:
                            categories.append(term)

                    # Build source URL
                    source_url = f"https://arxiv.org/abs/{arxiv_id}"

                    # Build provenance
                    provenance = f"arXiv|{arxiv_id}|{published_at or 'unknown'}"

                    # Classify freshness
                    freshness = classify_freshness(published_at)

                    # Create document
                    doc = ResearchDocument(
                        id=f"arxiv_{arxiv_id}",
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        publisher="arXiv",
                        source_url=source_url,
                        published_at=published_at,
                        updated_at=updated_at,
                        categories=categories,
                        freshness=freshness,
                        reliability=SourceReliability.HIGH,
                        provenance=provenance,
                        content_hash=hashlib.sha256(source_url.encode()).hexdigest()[:16],
                        status="retrieved",
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning("Failed to parse arXiv entry: %s", e)
                    continue

        except ET.ParseError as e:
            logger.error("Failed to parse arXiv XML response: %s", e)

        return documents

    def search(self, query: str, max_results: int = 10) -> list[ResearchDocument]:
        """Search arXiv. Never raises on failure. Returns empty list on error."""
        try:
            query = self._validate_query(query)
            max_results = max(1, min(max_results, MAX_RESULTS))

            # Build search URL with security validation
            params = urllib.parse.urlencode({
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending",
            })
            url = f"{ALLOWED_BASE_URL}?{params}"

            # Final URL validation
            if not self._validate_url(url):
                logger.error("URL validation failed for arXiv request")
                return []

            # Make request with timeout and size limit
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "AURORA/1.0 (research-data-fabric)")

            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                # Check response size
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                    logger.error("arXiv response too large: %s bytes", content_length)
                    return []

                content = response.read(MAX_RESPONSE_SIZE + 1)
                if len(content) > MAX_RESPONSE_SIZE:
                    logger.error("arXiv response exceeded size limit")
                    return []

                xml_content = content.decode("utf-8", errors="replace")

            # Parse response
            documents = self._parse_arxiv_response(xml_content)
            self._last_success = datetime.now(timezone.utc)
            self._verified = True
            logger.info("arXiv search returned %d documents for query: %s", len(documents), query[:50])
            return documents

        except urllib.error.URLError as e:
            self._error_count += 1
            logger.warning("arXiv request failed (URL error): %s", e)
            return []
        except TimeoutError:
            self._error_count += 1
            logger.warning("arXiv request timed out")
            return []
        except ValueError as e:
            logger.warning("Invalid query for arXiv: %s", e)
            return []
        except Exception as e:
            self._error_count += 1
            logger.warning("arXiv search failed: %s", e)
            return []


def create_research_provider() -> ResearchProvider:
    """Factory: create the configured research provider.

    Configuration:
        AURORA_RESEARCH_PROVIDER=arxiv (to enable arXiv)
    """
    provider_type = os.environ.get("AURORA_RESEARCH_PROVIDER", "").strip().lower()

    if provider_type == "arxiv":
        return ArxivProvider()

    return UnavailableResearchProvider()
