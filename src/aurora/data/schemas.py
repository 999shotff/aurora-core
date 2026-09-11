"""AURORA Data Fabric — shared schemas.

News, Macro, and Research data types with provenance and freshness.
All fields use None/UNAVAILABLE when source doesn't provide them.
Never fabricate missing fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


# ── Provider Status ──────────────────────────────────────────────────────────


class ProviderState(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONNECTING = "CONNECTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    DISCONNECTED = "DISCONNECTED"


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    state: ProviderState
    detail: str = ""
    last_success: datetime | None = None
    error_count: int = 0


# ── Freshness ────────────────────────────────────────────────────────────────


class Freshness(str, Enum):
    CURRENT = "CURRENT"
    RECENT = "RECENT"
    HISTORICAL = "HISTORICAL"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


def classify_freshness(published_at: str | None, now: datetime | None = None) -> Freshness:
    """Classify freshness based on published timestamp."""
    if not published_at:
        return Freshness.UNKNOWN
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if now is None:
            now = datetime.now(timezone.utc)
        age = (now - pub).total_seconds()
        if age < 3600:  # < 1 hour
            return Freshness.CURRENT
        if age < 86400:  # < 1 day
            return Freshness.RECENT
        if age < 2592000:  # < 30 days
            return Freshness.HISTORICAL
        return Freshness.STALE
    except (ValueError, TypeError):
        return Freshness.UNKNOWN


# ── Source Reliability ────────────────────────────────────────────────────────


class SourceReliability(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


# ── News ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NewsItem:
    id: str
    headline: str
    summary: str | None = None
    publisher: str | None = None
    source_url: str | None = None
    published_at: str | None = None
    retrieved_at: str = ""
    source_type: str = "news"
    asset_refs: tuple[str, ...] = ()
    freshness: Freshness = Freshness.UNKNOWN
    reliability: SourceReliability = SourceReliability.UNKNOWN
    provenance: str = ""
    content_hash: str | None = None


# ── Macro ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MacroObservation:
    series_id: str
    name: str
    country: str = ""
    region: str = ""
    value: float | None = None
    unit: str = ""
    frequency: str = ""
    observation_date: str | None = None
    release_date: str | None = None
    source: str = ""
    retrieved_at: str = ""
    provenance: str = ""
    freshness: Freshness = Freshness.UNKNOWN
    status: str = "OK"


@dataclass(frozen=True)
class MacroSeries:
    series_id: str
    name: str
    category: str
    country: str = ""
    unit: str = ""
    frequency: str = ""
    source: str = ""
    latest_value: float | None = None
    latest_date: str | None = None
    observations: tuple[MacroObservation, ...] = ()


# ── Research ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ResearchDocument:
    id: str
    title: str
    authors: tuple[str, ...] = ()
    abstract: str | None = None
    source_url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    categories: tuple[str, ...] = ()
    retrieved_at: str = ""
    content_hash: str | None = None
    provenance: str = ""
    summary: str | None = None
    asset_refs: tuple[str, ...] = ()
    freshness: Freshness = Freshness.UNKNOWN
    reliability: SourceReliability = SourceReliability.UNKNOWN
    status: str = ""


# ── Utility ──────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
