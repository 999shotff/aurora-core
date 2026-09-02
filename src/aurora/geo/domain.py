"""Geo domain models — immutable, validated types for geospatial research.

Every model retains provenance, timestamps, source, processing method, and uncertainty.
No fabricated data. No predictions. Research evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal


# ── Enums ──

class GeoQualityGrade(str, Enum):
    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    POOR = "POOR"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"


class GeoIntegrityState(str, Enum):
    DATA_AVAILABLE = "DATA_AVAILABLE"
    DATA_STALE = "DATA_STALE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_RESOLUTION = "INSUFFICIENT_RESOLUTION"
    INSUFFICIENT_TEMPORAL_COVERAGE = "INSUFFICIENT_TEMPORAL_COVERAGE"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class GeoChangeType(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CHANGE = "no_change"
    UNCERTAIN = "uncertain"


class GeoBand(str, Enum):
    RED = "B04"
    GREEN = "B03"
    BLUE = "B02"
    NIR = "B08"
    SWIR1 = "B11"
    SWIR2 = "B12"
    TIR = "B10"
    CLOUD_MASK = "SCL"
    AEROSOL = "B01"
    WATER_VAPOR = "B09"
    CIRRUS = "B10"
    UNKNOWN = "UNKNOWN"


# ── Core Geometry ──

@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"latitude must be in [-90, 90], got {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"longitude must be in [-180, 180], got {self.longitude}")


@dataclass(frozen=True)
class BoundingBox:
    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if self.south >= self.north:
            raise ValueError(f"south ({self.south}) must be < north ({self.north})")
        if not (-90.0 <= self.south <= 90.0 and -90.0 <= self.north <= 90.0):
            raise ValueError("latitude must be in [-90, 90]")
        if not (-180.0 <= self.west <= 180.0 and -180.0 <= self.east <= 180.0):
            raise ValueError("longitude must be in [-180, 180]")

    @property
    def center(self) -> GeoPoint:
        lat = (self.south + self.north) / 2
        lon = (self.west + self.east) / 2
        return GeoPoint(latitude=lat, longitude=lon)

    @property
    def area_km2(self) -> float:
        import math
        lat_rad = math.radians((self.south + self.north) / 2)
        dlat = (self.north - self.south) * 111.32
        dlon = (self.east - self.west) * 111.32 * math.cos(lat_rad)
        return abs(dlat * dlon)

    def contains(self, point: GeoPoint) -> bool:
        return (
            self.south <= point.latitude <= self.north
            and self.west <= point.longitude <= self.east
        )

    def intersects(self, other: BoundingBox) -> bool:
        return not (
            self.east < other.west
            or self.west > other.east
            or self.north < other.south
            or self.south > other.north
        )


@dataclass(frozen=True)
class AOI:
    name: str
    bbox: BoundingBox
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: tuple[str, ...] = ()

    @property
    def center(self) -> GeoPoint:
        return self.bbox.center

    @property
    def area_km2(self) -> float:
        return self.bbox.area_km2


# ── CRS ──

@dataclass(frozen=True)
class CRS:
    code: str = "EPSG:4326"
    name: str = "WGS 84"

    def __post_init__(self) -> None:
        if not self.code.startswith("EPSG:"):
            raise ValueError(f"CRS code must start with EPSG:, got {self.code}")


# ── Raster Metadata ──

@dataclass(frozen=True)
class GeoRasterMetadata:
    width_pixels: int
    height_pixels: int
    pixel_size_m: float
    crs: CRS = field(default_factory=CRS)
    bands: tuple[str, ...] = ()
    no_data_value: float = float("nan")
    file_format: str = "GeoTIFF"
    file_size_bytes: int = 0

    def __post_init__(self) -> None:
        if self.width_pixels <= 0 or self.height_pixels <= 0:
            raise ValueError("pixel dimensions must be positive")
        if self.pixel_size_m <= 0:
            raise ValueError("pixel_size_m must be positive")


# ── Cloud / Quality ──

@dataclass(frozen=True)
class CloudInfo:
    cloud_pct: float = 0.0
    cloud_mask_available: bool = False
    snow_pct: float = 0.0
    shadow_pct: float = 0.0

    def __post_init__(self) -> None:
        for attr in ("cloud_pct", "snow_pct", "shadow_pct"):
            v = getattr(self, attr)
            if not (0.0 <= v <= 100.0):
                raise ValueError(f"{attr} must be in [0, 100], got {v}")


@dataclass(frozen=True)
class GeoQualityReport:
    grade: GeoQualityGrade = GeoQualityGrade.GOOD
    cloud_info: CloudInfo = field(default_factory=CloudInfo)
    missing_pixels_pct: float = 0.0
    noise_level: float = 0.0
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE
    notes: tuple[str, ...] = ()

    @property
    def quality_score(self) -> float:
        if self.grade == GeoQualityGrade.UNAVAILABLE:
            return 0.0
        cloud_penalty = self.cloud_info.cloud_pct / 100.0 * 0.5
        missing_penalty = self.missing_pixels_pct / 100.0 * 0.3
        return max(0.0, 1.0 - cloud_penalty - missing_penalty)


# ── Provenance ──

@dataclass(frozen=True)
class GeoProvenance:
    provider: str
    dataset: str
    acquisition_time: datetime
    processing_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processing_method: str = "raw"
    methodology_version: str = "1.0"
    source_url: str = ""
    crs: CRS = field(default_factory=CRS)
    spatial_resolution_m: float = 0.0
    temporal_resolution_hours: float = 0.0
    source_sha256: str = ""
    is_demo: bool = False
    uncertainty: str = ""
    notes: tuple[str, ...] = ()


# ── Observation ──

@dataclass(frozen=True)
class GeoScene:
    scene_id: str
    provider: str
    dataset: str
    acquisition_time: datetime
    bbox: BoundingBox
    cloud_info: CloudInfo = field(default_factory=CloudInfo)
    resolution_m: float = 10.0
    bands: tuple[str, ...] = ()
    quality: GeoQualityReport = field(default_factory=GeoQualityReport)
    provenance: GeoProvenance | None = None
    thumbnail_url: str = ""
    metadata_url: str = ""
    download_url: str = ""

    @property
    def age_days(self) -> float:
        now = datetime.now(timezone.utc)
        delta = now - self.acquisition_time
        return delta.total_seconds() / 86400


@dataclass(frozen=True)
class GeoObservation:
    observation_id: str
    scene: GeoScene
    aoi: AOI
    raster_metadata: GeoRasterMetadata | None = None
    derived_values: dict[str, float] = field(default_factory=dict)
    processing_chain: tuple[str, ...] = ()
    confidence: float = 0.0
    uncertainty: str = ""
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE
    notes: tuple[str, ...] = ()

    @property
    def source(self) -> str:
        return self.scene.provider

    @property
    def acquisition_timestamp(self) -> datetime:
        return self.scene.acquisition_time


@dataclass(frozen=True)
class GeoRasterBand:
    band: str
    values: tuple[float, ...] = ()
    no_data_mask: tuple[bool, ...] = ()
    min_value: float = 0.0
    max_value: float = 0.0
    mean_value: float = 0.0


# ── Change Detection ──

@dataclass(frozen=True)
class GeoChange:
    change_id: str
    aoi: AOI
    before: GeoObservation
    after: GeoObservation
    change_type: GeoChangeType
    changed_area_km2: float = 0.0
    unchanged_area_km2: float = 0.0
    magnitude: float = 0.0
    spatial_extent_pct: float = 0.0
    confidence: float = 0.0
    methodology: str = "pixel_difference"
    methodology_version: str = "1.0"
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE
    derived_feature: str = ""
    uncertainty: str = ""
    notes: tuple[str, ...] = ()


# ── Time Series ──

@dataclass(frozen=True)
class GeoTimeSeriesPoint:
    timestamp: datetime
    value: float
    confidence: float = 0.0
    cloud_pct: float = 0.0
    integrity_state: GeoIntegrityState = GeoIntegrityState.DATA_AVAILABLE


@dataclass(frozen=True)
class GeoTimeSeries:
    series_id: str
    aoi: AOI
    metric: str
    unit: str = ""
    points: tuple[GeoTimeSeriesPoint, ...] = ()
    provenance: GeoProvenance | None = None
    methodology: str = ""
    methodology_version: str = "1.0"

    @property
    def count(self) -> int:
        return len(self.points)

    @property
    def date_range(self) -> tuple[datetime, datetime] | None:
        if not self.points:
            return None
        return (self.points[0].timestamp, self.points[-1].timestamp)


# ── Provider ──

@dataclass(frozen=True)
class GeoDatasetInfo:
    dataset_id: str
    name: str
    description: str = ""
    resolution_m: float = 10.0
    temporal_resolution_hours: float = 168.0
    bands: tuple[str, ...] = ()
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    cloud_cover_max_pct: float = 100.0
    bbox: BoundingBox | None = None


@dataclass(frozen=True)
class GeoProviderCapabilities:
    provider: str
    datasets: tuple[GeoDatasetInfo, ...] = ()
    supported_formats: tuple[str, ...] = ("GeoTIFF",)
    max_aoi_km2: float = 10000.0
    requires_api_key: bool = False
    is_open_data: bool = False
    rate_limit_per_minute: int = 60
    provenance_url: str = ""


# ── Evidence Integration ──

@dataclass(frozen=True)
class GeoEvidence:
    evidence_id: str
    observation: GeoObservation
    feature_name: str
    feature_value: float
    feature_unit: str = ""
    change_detected: bool = False
    change_magnitude: float = 0.0
    confidence: float = 0.0
    uncertainty: str = ""
    interpretation: str = ""
    methodology: str = ""
    methodology_version: str = "1.0"
    domain: str = "geospatial"
    notes: tuple[str, ...] = ()
