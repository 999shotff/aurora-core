"""AURORA Data Fabric — Backend Tests.

Tests for provider registry, schemas, API endpoints, security, and provenance.
"""

import pytest
from fastapi.testclient import TestClient

from aurora.data.schemas import (
    Freshness,
    NewsItem,
    MacroObservation,
    MacroSeries,
    ResearchDocument,
    ProviderState,
    ProviderStatus,
    classify_freshness,
)
from aurora.data.news_provider import UnavailableNewsProvider, create_news_provider
from aurora.data.macro_provider import UnavailableMacroProvider, create_macro_provider
from aurora.data.research_provider import UnavailableResearchProvider, ArxivProvider, create_research_provider
from aurora.data.registry import DataFabricRegistry, get_registry


# ── Schemas ──────────────────────────────────────────────────────────────────


class TestFreshness:
    def test_classify_unknown_without_timestamp(self):
        assert classify_freshness(None) == Freshness.UNKNOWN

    def test_classify_current(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=30)).isoformat()
        assert classify_freshness(recent) == Freshness.CURRENT

    def test_classify_recent(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(hours=12)).isoformat()
        assert classify_freshness(yesterday) == Freshness.RECENT

    def test_classify_historical(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=10)).isoformat()
        assert classify_freshness(old) == Freshness.HISTORICAL

    def test_classify_stale(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        very_old = (now - timedelta(days=60)).isoformat()
        assert classify_freshness(very_old) == Freshness.STALE


class TestNewsItem:
    def test_create_minimal(self):
        item = NewsItem(id="test_1", headline="Test headline")
        assert item.id == "test_1"
        assert item.headline == "Test headline"
        assert item.freshness == Freshness.UNKNOWN

    def test_create_full(self):
        item = NewsItem(
            id="test_2",
            headline="Full item",
            summary="Summary",
            publisher="Reuters",
            source_url="https://example.com",
            published_at="2025-01-01T00:00:00Z",
            freshness=Freshness.CURRENT,
            reliability="HIGH",
            provenance="Reuters|2025-01-01",
        )
        assert item.publisher == "Reuters"
        assert item.freshness == Freshness.CURRENT


class TestMacroSeries:
    def test_create_series(self):
        series = MacroSeries(
            series_id="CPIAUCSL",
            name="US CPI",
            category="inflation",
            latest_value=307.0,
            latest_date="2025-01-01",
        )
        assert series.series_id == "CPIAUCSL"
        assert series.latest_value == 307.0


class TestResearchDocument:
    def test_create_doc(self):
        doc = ResearchDocument(
            id="doc_1",
            title="Test Document",
            publisher="NBER",
        )
        assert doc.id == "doc_1"
        assert doc.title == "Test Document"

    def test_create_arxiv_doc(self):
        doc = ResearchDocument(
            id="arxiv_2301.12345",
            title="Test Paper",
            authors=("Author 1", "Author 2"),
            abstract="This is a test abstract",
            publisher="arXiv",
            source_url="https://arxiv.org/abs/2301.12345",
            published_at="2023-01-01T00:00:00Z",
            categories=("cs.AI", "cs.LG"),
            freshness=Freshness.HISTORICAL,
            reliability="HIGH",
            provenance="arXiv|2301.12345|2023-01-01T00:00:00Z",
            status="retrieved",
        )
        assert doc.authors == ("Author 1", "Author 2")
        assert doc.abstract == "This is a test abstract"
        assert doc.categories == ("cs.AI", "cs.LG")


# ── Providers ────────────────────────────────────────────────────────────────


class TestUnavailableProviders:
    def test_unavailable_news_status(self):
        p = UnavailableNewsProvider()
        s = p.status()
        assert s.state == ProviderState.NOT_CONFIGURED
        assert p.search("test") == []

    def test_unavailable_macro_status(self):
        p = UnavailableMacroProvider()
        s = p.status()
        assert s.state == ProviderState.NOT_CONFIGURED
        assert p.get_series("CPIAUCSL") is None
        assert p.search("inflation") == []

    def test_unavailable_research_status(self):
        p = UnavailableResearchProvider()
        s = p.status()
        assert s.state == ProviderState.NOT_CONFIGURED
        assert p.search("test") == []


class TestProviderFactory:
    def test_create_news_provider_default(self):
        import os
        os.environ.pop("AURORA_NEWS_PROVIDER", None)
        p = create_news_provider()
        assert isinstance(p, UnavailableNewsProvider)

    def test_create_macro_provider_default(self):
        import os
        os.environ.pop("AURORA_MACRO_PROVIDER", None)
        p = create_macro_provider()
        assert isinstance(p, UnavailableMacroProvider)

    def test_create_research_provider_default(self):
        import os
        os.environ.pop("AURORA_RESEARCH_PROVIDER", None)
        p = create_research_provider()
        assert isinstance(p, UnavailableResearchProvider)

    def test_create_research_provider_arxiv(self):
        import os
        os.environ["AURORA_RESEARCH_PROVIDER"] = "arxiv"
        p = create_research_provider()
        assert isinstance(p, ArxivProvider)
        os.environ.pop("AURORA_RESEARCH_PROVIDER", None)


# ── ArxivProvider Security ───────────────────────────────────────────────────


class TestArxivProvider:
    def test_arxiv_status_initial(self):
        p = ArxivProvider()
        s = p.status()
        assert s.state == ProviderState.CONNECTING
        assert p.name == "arxiv"

    def test_arxiv_validate_url_allowlisted(self):
        p = ArxivProvider()
        assert p._validate_url("http://export.arxiv.org/api/query?test=1") is True

    def test_arxiv_validate_url_not_allowlisted(self):
        p = ArxivProvider()
        assert p._validate_url("http://evil.com/api/query") is False
        assert p._validate_url("https://export.arxiv.org.evil.com/api/query") is False

    def test_arxiv_validate_query_empty(self):
        p = ArxivProvider()
        with pytest.raises(ValueError):
            p._validate_query("")

    def test_arxiv_validate_query_long(self):
        p = ArxivProvider()
        long_query = "a" * 300
        validated = p._validate_query(long_query)
        assert len(validated) <= 200

    def test_arxiv_search_empty_without_connection(self):
        p = ArxivProvider()
        results = p.search("test")
        # Should not crash, returns empty or actual results
        assert isinstance(results, list)

    def test_arxiv_search_bounded_results(self):
        p = ArxivProvider()
        results = p.search("test", max_results=5)
        assert isinstance(results, list)
        assert len(results) <= 5


# ── Registry ─────────────────────────────────────────────────────────────────


class TestRegistry:
    def test_registry_initializes(self):
        reg = DataFabricRegistry()
        reg.initialize()
        assert reg.news is not None
        assert reg.macro is not None
        assert reg.research is not None

    def test_registry_all_status(self):
        reg = DataFabricRegistry()
        reg.initialize()
        statuses = reg.all_status()
        assert len(statuses) == 3

    def test_registry_summary(self):
        reg = DataFabricRegistry()
        reg.initialize()
        summary = reg.summary()
        assert "news" in summary
        assert "macro" in summary
        assert "research" in summary

    def test_registry_singleton(self):
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2


# ── API ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    from fastapi import FastAPI
    from aurora.data.api import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestNewsAPI:
    def test_news_status(self, client):
        response = client.get("/api/v1/news/status")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "state" in data
        assert data["state"] in [s.value for s in ProviderState]

    def test_news_search(self, client):
        response = client.get("/api/v1/news/search", params={"q": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert "items" in data

    def test_news_search_empty_query(self, client):
        response = client.get("/api/v1/news/search", params={"q": ""})
        assert response.status_code == 422  # Validation error


class TestMacroAPI:
    def test_macro_status(self, client):
        response = client.get("/api/v1/macro/status")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "state" in data

    def test_macro_series(self, client):
        response = client.get("/api/v1/macro/series/CPIAUCSL")
        assert response.status_code == 200
        data = response.json()
        assert "series_id" in data or "error" in data

    def test_macro_search(self, client):
        response = client.get("/api/v1/macro/search", params={"q": "inflation"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "inflation"


class TestResearchAPI:
    def test_research_status(self, client):
        response = client.get("/api/v1/research/status")
        assert response.status_code == 200
        data = response.json()
        # Should be NOT_CONFIGURED or READY depending on env
        assert data["state"] in [s.value for s in ProviderState]

    def test_research_search(self, client):
        response = client.get("/api/v1/research/search", params={"q": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert "items" in data


class TestDataFabricStatus:
    def test_data_status(self, client):
        response = client.get("/api/v1/data/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "providers" in data


# ── Security ─────────────────────────────────────────────────────────────────


class TestSecurity:
    def test_no_api_key_in_news_status(self, client):
        response = client.get("/api/v1/news/status")
        data = response.json()
        # Ensure no actual API key values are present
        # Only env var names in documentation are acceptable
        assert "sk-" not in str(data)
        assert "Bearer" not in str(data)

    def test_no_api_key_in_macro_status(self, client):
        response = client.get("/api/v1/macro/status")
        data = response.json()
        assert "sk-" not in str(data)
        assert "Bearer" not in str(data)

    def test_news_search_bounded_query(self, client):
        long_query = "a" * 300
        response = client.get("/api/v1/news/search", params={"q": long_query})
        # Should either truncate or reject
        assert response.status_code in [200, 422]

    def test_macro_search_bounded_query(self, client):
        long_query = "a" * 300
        response = client.get("/api/v1/macro/search", params={"q": long_query})
        assert response.status_code in [200, 422]

    def test_research_search_bounded_query(self, client):
        long_query = "a" * 300
        response = client.get("/api/v1/research/search", params={"q": long_query})
        assert response.status_code in [200, 422]


# ── Terminal Research Integration ─────────────────────────────────────────────


class TestTerminalIntegration:
    def test_terminal_status_includes_research(self, client):
        # Mock terminal status endpoint
        from fastapi import FastAPI
        from aurora.terminal.api import router as terminal_router

        app = FastAPI()
        app.include_router(terminal_router)
        terminal_client = TestClient(app)

        response = terminal_client.get("/api/v1/terminal/status")
        assert response.status_code == 200
        data = response.json()
        providers = data.get("providers", [])
        categories = [p["category"] for p in providers]
        assert "RESEARCH" in categories
        assert "NEWS" in categories
        assert "MACRO" in categories
