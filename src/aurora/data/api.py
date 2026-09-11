"""AURORA Data Fabric — API Endpoints.

Clean APIs for News, Macro, and Research data.
All provider access occurs backend-side. No API keys exposed.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from .registry import get_registry

router = APIRouter()
logger = logging.getLogger("aurora.data.api")


# ── News API ─────────────────────────────────────────────────────────────────


@router.get("/api/v1/news/status")
def news_status() -> dict[str, Any]:
    """News provider status. Never exposes API keys."""
    reg = get_registry()
    s = reg.news.status()
    return {
        "provider": s.name,
        "state": s.state.value,
        "detail": s.detail,
        "last_success": s.last_success.isoformat() if s.last_success else None,
        "error_count": s.error_count,
    }


@router.get("/api/v1/news/search")
def news_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=50, description="Max results"),
    language: str = Query(default="en", description="Language code"),
) -> dict[str, Any]:
    """Search news. Backend-only provider access. Never exposes API keys."""
    reg = get_registry()
    items = reg.news.search(q, max_results=max_results, language=language)
    return {
        "query": q,
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "headline": item.headline,
                "summary": item.summary,
                "publisher": item.publisher,
                "source_url": item.source_url,
                "published_at": item.published_at,
                "freshness": item.freshness.value,
                "reliability": item.reliability.value,
                "provenance": item.provenance,
                "asset_refs": item.asset_refs,
            }
            for item in items
        ],
    }


# ── Macro API ────────────────────────────────────────────────────────────────


@router.get("/api/v1/macro/status")
def macro_status() -> dict[str, Any]:
    """Macro provider status. Never exposes API keys."""
    reg = get_registry()
    s = reg.macro.status()
    return {
        "provider": s.name,
        "state": s.state.value,
        "detail": s.detail,
        "last_success": s.last_success.isoformat() if s.last_success else None,
        "error_count": s.error_count,
    }


@router.get("/api/v1/macro/series/{series_id}")
def macro_series(series_id: str) -> dict[str, Any]:
    """Get a macro series by ID. Backend-only provider access."""
    reg = get_registry()
    series = reg.macro.get_series(series_id)
    if series is None:
        return {"error": "Series not found or provider unavailable", "series_id": series_id}
    return {
        "series_id": series.series_id,
        "name": series.name,
        "category": series.category,
        "country": series.country,
        "unit": series.unit,
        "frequency": series.frequency,
        "source": series.source,
        "latest_value": series.latest_value,
        "latest_date": series.latest_date,
        "observations": [
            {
                "value": obs.value,
                "date": obs.observation_date,
                "freshness": obs.freshness.value,
                "status": obs.status,
            }
            for obs in series.observations
        ],
    }


@router.get("/api/v1/macro/search")
def macro_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=25, description="Max results"),
) -> dict[str, Any]:
    """Search macro series. Backend-only provider access."""
    reg = get_registry()
    results = reg.macro.search(q, max_results=max_results)
    return {
        "query": q,
        "count": len(results),
        "series": [
            {
                "series_id": s.series_id,
                "name": s.name,
                "category": s.category,
                "country": s.country,
                "unit": s.unit,
                "frequency": s.frequency,
                "source": s.source,
                "latest_value": s.latest_value,
                "latest_date": s.latest_date,
            }
            for s in results
        ],
    }


# ── Research API ─────────────────────────────────────────────────────────────


@router.get("/api/v1/research/status")
def research_status() -> dict[str, Any]:
    """Research provider status."""
    reg = get_registry()
    s = reg.research.status()
    return {
        "provider": s.name,
        "state": s.state.value,
        "detail": s.detail,
    }


@router.get("/api/v1/research/search")
def research_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    max_results: int = Query(default=10, ge=1, le=50, description="Max results"),
) -> dict[str, Any]:
    """Search research documents. Backend-only provider access."""
    reg = get_registry()
    items = reg.research.search(q, max_results=max_results)
    return {
        "query": q,
        "count": len(items),
        "items": [
            {
                "id": doc.id,
                "title": doc.title,
                "authors": list(doc.authors),
                "abstract": doc.abstract,
                "publisher": doc.publisher,
                "source_url": doc.source_url,
                "published_at": doc.published_at,
                "updated_at": doc.updated_at,
                "categories": list(doc.categories),
                "freshness": doc.freshness.value,
                "reliability": doc.reliability.value,
                "provenance": doc.provenance,
                "content_hash": doc.content_hash,
                "status": doc.status,
            }
            for doc in items
        ],
    }


# ── Data Fabric Overview ─────────────────────────────────────────────────────


@router.get("/api/v1/data/status")
def data_fabric_status() -> dict[str, Any]:
    """Combined status of all data fabric providers."""
    reg = get_registry()
    return {
        "status": "ok",
        "providers": reg.summary(),
    }
