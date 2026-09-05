"""Asset/observation service — the single place that decides what's real.

Satellites are backed by the actual provider registry (Sentinel/GIBS/SkyFi),
so a "REGISTERED" satellite asset reflects a genuinely configured provider.
Balloons, UAVs, ground sensors, and subsurface assets have no connected data
source anywhere in this codebase — this module says so explicitly rather
than returning empty lists silently, so the UI can render "DATA SOURCE NOT
CONNECTED" truthfully instead of a blank panel that looks broken.
"""

from __future__ import annotations

from dataclasses import dataclass

from aurora.geo.assets import (
    Asset,
    AssetAvailability,
    AssetLocation,
    AssetObservation,
    AssetType,
)
from aurora.geo.providers.base import create_default_registry


@dataclass(frozen=True)
class AssetCategorySummary:
    asset_type: AssetType
    connected: bool
    asset_count: int
    observation_count: int
    note: str


def list_satellite_assets() -> list[Asset]:
    """One Asset per registered provider — platform-level metadata only.
    No orbital telemetry is fabricated; capabilities come from the
    provider's real `get_capabilities()` call."""
    registry = create_default_registry()
    assets: list[Asset] = []
    for name in registry.list_providers():
        provider = registry.get(name)
        if provider is None:
            continue
        try:
            caps = provider.get_capabilities()
            capability_list = tuple(getattr(caps, "supported_bands", ()) or ())
        except Exception:
            capability_list = ()
        assets.append(
            Asset(
                asset_id=f"sat_{name.lower()}",
                asset_type=AssetType.SATELLITE,
                name=name,
                source=name,
                availability=AssetAvailability.REGISTERED,
                location=AssetLocation(),
                status="registered",
                capabilities=capability_list,
                metadata={"is_open_data": str(getattr(provider, "is_open_data", False))},
                last_observation_at=None,
                evidence_refs=(),
                limitations=(
                    ("Registered provider — no scene has been fetched for this asset yet. "
                    "Use Geo Observatory scene search to pull a real observation."),
                ),
            )
        )
    return assets


def list_satellite_observations() -> list[AssetObservation]:
    """No observations are pre-fetched here — a satellite "observation" only
    exists once a scene search actually runs (see the existing /geo/observations
    endpoint). This intentionally returns an empty list rather than fabricating
    acquisitions."""
    return []


def _unconnected_category(asset_type: AssetType) -> AssetCategorySummary:
    return AssetCategorySummary(
        asset_type=asset_type,
        connected=False,
        asset_count=0,
        observation_count=0,
        note="DATA SOURCE NOT CONNECTED",
    )


def list_balloon_assets() -> list[Asset]:
    return []


def list_uav_assets() -> list[Asset]:
    return []


def list_ground_sensor_assets() -> list[Asset]:
    return []


def list_subsurface_assets() -> list[Asset]:
    return []


def get_category_summary(asset_type: AssetType) -> AssetCategorySummary:
    if asset_type == AssetType.SATELLITE:
        assets = list_satellite_assets()
        observations = list_satellite_observations()
        return AssetCategorySummary(
            asset_type=AssetType.SATELLITE,
            connected=len(assets) > 0,
            asset_count=len(assets),
            observation_count=len(observations),
            note="Providers registered; no scenes fetched yet" if assets else "DATA SOURCE NOT CONNECTED",
        )
    return _unconnected_category(asset_type)


def get_all_category_summaries() -> list[AssetCategorySummary]:
    return [get_category_summary(t) for t in AssetType]


def list_all_assets(asset_type: AssetType | None = None) -> list[Asset]:
    by_type = {
        AssetType.SATELLITE: list_satellite_assets,
        AssetType.BALLOON: list_balloon_assets,
        AssetType.UAV: list_uav_assets,
        AssetType.GROUND_SENSOR: list_ground_sensor_assets,
        AssetType.SUBSURFACE: list_subsurface_assets,
    }
    if asset_type is not None:
        return by_type[asset_type]()
    result: list[Asset] = []
    for fn in by_type.values():
        result.extend(fn())
    return result


def get_asset(asset_id: str) -> Asset | None:
    for asset in list_all_assets():
        if asset.asset_id == asset_id:
            return asset
    return None


def list_all_observations(asset_type: AssetType | None = None) -> list[AssetObservation]:
    if asset_type is None or asset_type == AssetType.SATELLITE:
        return list_satellite_observations()
    return []
