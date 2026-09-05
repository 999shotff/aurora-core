"""Multi-source observation asset domain models.

Extends the Geo Observatory beyond satellite imagery to a general
Asset/Observation abstraction covering satellites, balloons/HAPs, UAVs,
ground sensors, and subsurface assets.

Hard rule, consistent with the rest of aurora.geo: no fabricated telemetry,
positions, measurements, or readings. Every asset and observation carries an
explicit AssetAvailability so the UI can render LIVE / REGISTERED / DEMO /
STALE / UNAVAILABLE truthfully instead of implying data that doesn't exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AssetType(str, Enum):
    SATELLITE = "satellite"
    BALLOON = "balloon"
    UAV = "uav"
    GROUND_SENSOR = "ground_sensor"
    SUBSURFACE = "subsurface"


class AssetAvailability(str, Enum):
    """How this asset/observation's data was obtained — never assume LIVE."""
    LIVE = "LIVE"
    DERIVED = "DERIVED"
    REGISTERED = "REGISTERED"   # asset/platform is known, but has no observation feed connected
    DEMO = "DEMO"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class ObservationType(str, Enum):
    IMAGERY = "imagery"
    POSITION = "position"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    HUMIDITY = "humidity"
    AIR_QUALITY = "air_quality"
    VIBRATION = "vibration"
    SEISMIC = "seismic"
    SOIL = "soil"
    GENERIC = "generic"


@dataclass(frozen=True)
class AssetLocation:
    """Position is optional per-field — never synthesize a coordinate."""
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None   # positive = above ground/sea level
    depth_m: float | None = None      # positive = below surface (subsurface assets)


@dataclass(frozen=True)
class Asset:
    """A registered observation platform. Being registered does NOT imply
    it currently has live data — see `availability`."""
    asset_id: str
    asset_type: AssetType
    name: str
    source: str                        # provider/system name, e.g. "GIBS", "Sentinel-2", "Not connected"
    availability: AssetAvailability
    location: AssetLocation = field(default_factory=AssetLocation)
    status: str = "unknown"
    capabilities: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    last_observation_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.availability in (AssetAvailability.LIVE, AssetAvailability.DERIVED) and self.source.strip().lower() in ("", "none", "not connected"):
            raise ValueError(f"Asset {self.asset_id} claims {self.availability} but has no real source")


@dataclass(frozen=True)
class AssetObservation:
    """A single reading/observation tied to an asset. `value` is None when
    no real measurement exists — the presence of this record does not by
    itself imply real data; check `availability`."""
    observation_id: str
    asset_id: str
    asset_type: AssetType
    observation_type: ObservationType
    timestamp: datetime
    availability: AssetAvailability
    source: str
    value: float | str | None = None
    unit: str = ""
    location: AssetLocation = field(default_factory=AssetLocation)
    confidence: float = 0.0
    limitations: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.availability in (AssetAvailability.LIVE, AssetAvailability.DERIVED) and self.value is None:
            raise ValueError(f"Observation {self.observation_id} claims {self.availability} but has no value")
        if self.timestamp.tzinfo is None:
            raise ValueError(f"Observation {self.observation_id} timestamp must be timezone-aware")
        if self.timestamp > datetime.now(timezone.utc):
            raise ValueError(f"Observation {self.observation_id} has a future timestamp — not permitted")


@dataclass(frozen=True)
class SourceConflict:
    """Two observations disagree — preserved explicitly, never averaged away."""
    observation_ids: tuple[str, str]
    field_name: str
    values: tuple[str, str]
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    note: str = ""


def sort_observations_chronologically(observations: list[AssetObservation]) -> list[AssetObservation]:
    """Sort strictly by timestamp value — never by a formatted display string."""
    return sorted(observations, key=lambda o: o.timestamp)


def detect_conflict(a: AssetObservation, b: AssetObservation, field_name: str = "value", tolerance: float = 0.0) -> SourceConflict | None:
    """Flag disagreement between two observations of the same field rather
    than silently averaging incompatible readings."""
    av, bv = a.value, b.value
    if av is None or bv is None:
        return None
    if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
        if abs(av - bv) > tolerance:
            return SourceConflict(
                observation_ids=(a.observation_id, b.observation_id),
                field_name=field_name,
                values=(str(av), str(bv)),
                note=f"{a.source} vs {b.source} disagree on {field_name}",
            )
        return None
    if str(av) != str(bv):
        return SourceConflict(
            observation_ids=(a.observation_id, b.observation_id),
            field_name=field_name,
            values=(str(av), str(bv)),
            note=f"{a.source} vs {b.source} disagree on {field_name}",
        )
    return None


def observation_to_evidence_dict(obs: AssetObservation, investigation_id: str | None = None) -> dict:
    """Convert an AssetObservation into the shape the Evidence system expects.
    Preserves source, timestamp, provenance, confidence, and limitations —
    never drops them for brevity."""
    confidence_band = "high" if obs.confidence >= 0.75 else "medium" if obs.confidence >= 0.4 else "low"
    return {
        "id": f"ev_{obs.observation_id}",
        "investigationId": investigation_id,
        "title": f"{obs.asset_type.value.replace('_', ' ').title()} observation — {obs.observation_type.value}",
        "description": f"{obs.observation_type.value} observation from asset {obs.asset_id} via {obs.source}.",
        "sourceType": _asset_type_to_evidence_source_type(obs.asset_type),
        "source": obs.source,
        "timestamp": obs.timestamp.isoformat(),
        "confidence": confidence_band,
        "status": "unverified",
        "availability": obs.availability.value,
        "metadata": {
            "assetId": obs.asset_id,
            "observationType": obs.observation_type.value,
            "value": "" if obs.value is None else str(obs.value),
            "unit": obs.unit,
            **({"limitations": "; ".join(obs.limitations)} if obs.limitations else {}),
        },
    }


def _asset_type_to_evidence_source_type(asset_type: AssetType) -> str:
    return {
        AssetType.SATELLITE: "satellite",
        AssetType.BALLOON: "derived-metric",
        AssetType.UAV: "derived-metric",
        AssetType.GROUND_SENSOR: "derived-metric",
        AssetType.SUBSURFACE: "derived-metric",
    }[asset_type]
