"""AURORA Data Fabric — Macro Provider.

ABC for macroeconomic data providers. One real implementation: FREDProvider.
Uses FRED (https://fred.stlouisfed.org). Free tier: 120 requests/minute.

Configuration:
    AURORA_MACRO_PROVIDER=fred
    AURORA_FRED_API_KEY=<your-fred-key>

Never expose API keys to frontend/logs/provenance.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from .schemas import (
    MacroObservation,
    MacroSeries,
    ProviderState,
    ProviderStatus,
    _now_iso,
    classify_freshness,
)

logger = logging.getLogger("aurora.data.macro")


class MacroProvider(ABC):
    """Abstract macro data provider."""

    @abstractmethod
    def status(self) -> ProviderStatus:
        """Current provider status."""

    @abstractmethod
    def get_series(self, series_id: str) -> MacroSeries | None:
        """Get a macro series by ID. Never raises on failure."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[MacroSeries]:
        """Search for macro series. Never raises on failure."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""


# FRED series mapping for common indicators
FRED_SERIES: dict[str, dict[str, str]] = {
    "CPIAUCSL": {"name": "Consumer Price Index for All Urban Consumers", "category": "inflation", "country": "US", "unit": "Index 1982-1984=100", "frequency": "Monthly"},
    "CPILFESL": {"name": "Core CPI (Less Food & Energy)", "category": "inflation", "country": "US", "unit": "Index 1982-1984=100", "frequency": "Monthly"},
    "FEDFUNDS": {"name": "Federal Funds Effective Rate", "category": "interest-rates", "country": "US", "unit": "Percent", "frequency": "Monthly"},
    "DGS10": {"name": "10-Year Treasury Constant Maturity Rate", "category": "yields", "country": "US", "unit": "Percent", "frequency": "Daily"},
    "DGS2": {"name": "2-Year Treasury Constant Maturity Rate", "category": "yields", "country": "US", "unit": "Percent", "frequency": "Daily"},
    "UNRATE": {"name": "Unemployment Rate", "category": "employment", "country": "US", "unit": "Percent", "frequency": "Monthly"},
    "PAYEMS": {"name": "Total Nonfarm Payrolls", "category": "employment", "country": "US", "unit": "Thousands of Persons", "frequency": "Monthly"},
    "GDP": {"name": "Gross Domestic Product", "category": "gdp", "country": "US", "unit": "Billions of Dollars", "frequency": "Quarterly"},
    "A191RL1Q225SBEA": {"name": "Real GDP Growth Rate", "category": "gdp", "country": "US", "unit": "Percent Change", "frequency": "Quarterly"},
    "DXY": {"name": "Trade Weighted U.S. Dollar Index", "category": "currencies", "country": "US", "unit": "Index", "frequency": "Daily"},
    "GOLDAMGBD228NLBM": {"name": "Gold Price", "category": "commodities", "country": "Global", "unit": "USD per Troy Ounce", "frequency": "Daily"},
    "DCOILWTICO": {"name": "Crude Oil WTI", "category": "commodities", "country": "Global", "unit": "USD per Barrel", "frequency": "Daily"},
    "DGS10Y": {"name": "10-Year Government Bond Yield", "category": "yields", "country": "US", "unit": "Percent", "frequency": "Daily"},
}


class FREDProvider(MacroProvider):
    """FRED (Federal Reserve Economic Data) provider.
    https://fred.stlouisfed.org. Free tier: 120 requests/minute.
    """

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    SEARCH_URL = "https://api.stlouisfed.org/fred/series/search"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("AURORA_FRED_API_KEY", "")
        self._last_error: str | None = None
        self._error_count = 0
        self._last_success: datetime | None = None

    @property
    def name(self) -> str:
        return "fred"

    def status(self) -> ProviderStatus:
        if not self._api_key:
            return ProviderStatus(
                name=self.name,
                state=ProviderState.NOT_CONFIGURED,
                detail="Set AURORA_FRED_API_KEY to enable macro data",
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
            detail="FRED connected",
            last_success=self._last_success,
        )

    def get_series(self, series_id: str) -> MacroSeries | None:
        if not self._api_key:
            return None

        series_id = series_id.strip()[:20]

        try:
            params = urllib.parse.urlencode({
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 10,
            })
            url = f"{self.BASE_URL}?{params}"

            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            self._last_success = datetime.now(timezone.utc)
            self._last_error = None

            meta = FRED_SERIES.get(series_id, {})
            now = _now_iso()

            observations: list[MacroObservation] = []
            for obs in data.get("observations", []):
                value_str = obs.get("value", ".")
                if value_str == ".":
                    value = None
                else:
                    try:
                        value = float(value_str)
                    except ValueError:
                        value = None

                obs_date = obs.get("date")
                observations.append(MacroObservation(
                    series_id=series_id,
                    name=meta.get("name", series_id),
                    country=meta.get("country", "US"),
                    value=value,
                    unit=meta.get("unit", ""),
                    frequency=meta.get("frequency", ""),
                    observation_date=obs_date,
                    source="FRED",
                    retrieved_at=now,
                    provenance=f"FRED|{series_id}|{obs_date}",
                    freshness=classify_freshness(obs_date),
                    status="OK" if value is not None else "MISSING",
                ))

            latest = observations[0] if observations else None

            return MacroSeries(
                series_id=series_id,
                name=meta.get("name", series_id),
                category=meta.get("category", "unknown"),
                country=meta.get("country", "US"),
                unit=meta.get("unit", ""),
                frequency=meta.get("frequency", ""),
                source="FRED",
                latest_value=latest.value if latest else None,
                latest_date=latest.observation_date if latest else None,
                observations=tuple(observations),
            )

        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)[:100]
            logger.warning("FRED error for %s: %s", series_id, self._last_error)
            return None

    def search(self, query: str, max_results: int = 10) -> list[MacroSeries]:
        if not self._api_key:
            return []

        query = query.strip()[:200]
        max_results = min(max(max_results, 1), 25)

        try:
            params = urllib.parse.urlencode({
                "search_text": query,
                "api_key": self._api_key,
                "file_type": "json",
                "limit": max_results,
            })
            url = f"{self.SEARCH_URL}?{params}"

            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            self._last_success = datetime.now(timezone.utc)
            self._last_error = None

            now = _now_iso()
            results: list[MacroSeries] = []

            for series in data.get("seriess", []):
                sid = series.get("id", "")
                meta = FRED_SERIES.get(sid, {})
                results.append(MacroSeries(
                    series_id=sid,
                    name=series.get("title", sid),
                    category=meta.get("category", "unknown"),
                    country=series.get("country", ""),
                    unit=series.get("units", ""),
                    frequency=series.get("frequency_short", ""),
                    source="FRED",
                ))

            logger.info("FRED search '%s': %d results", query, len(results))
            return results

        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)[:100]
            logger.warning("FRED search error: %s", self._last_error)
            return []


class UnavailableMacroProvider(MacroProvider):
    """Returns empty results. Used when no provider is configured."""

    @property
    def name(self) -> str:
        return "none"

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            state=ProviderState.NOT_CONFIGURED,
            detail="No macro provider configured. Set AURORA_MACRO_PROVIDER and AURORA_FRED_API_KEY.",
        )

    def get_series(self, series_id: str) -> MacroSeries | None:
        return None

    def search(self, query: str, max_results: int = 10) -> list[MacroSeries]:
        return []


def create_macro_provider() -> MacroProvider:
    """Factory: create the configured macro provider."""
    provider_name = os.environ.get("AURORA_MACRO_PROVIDER", "").strip().lower()

    if provider_name == "fred":
        return FREDProvider()

    return UnavailableMacroProvider()
