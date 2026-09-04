"""Raster engine — pure-Python raster processing with numpy.

No rasterio/GDAL dependency. Works on arrays of floats.
Every transformation records provenance.
Never silently modifies source data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import numpy as np

from aurora.geo.domain import (
    CRS,
    BoundingBox,
    GeoProvenance,
    GeoRasterMetadata,
)


class RasterDType(str, Enum):
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    UINT8 = "uint8"
    UINT16 = "uint16"
    INT16 = "int16"


@dataclass(frozen=True)
class RasterBand:
    name: str
    data: np.ndarray
    nodata: float = np.nan
    dtype: RasterDType = RasterDType.FLOAT32

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape

    @property
    def valid_count(self) -> int:
        return int(np.sum(~np.isnan(self.data) & (self.data != self.nodata)))

    @property
    def mean(self) -> float:
        valid = self.data[~np.isnan(self.data) & (self.data != self.nodata)]
        return float(np.mean(valid)) if len(valid) > 0 else np.nan

    @property
    def std(self) -> float:
        valid = self.data[~np.isnan(self.data) & (self.data != self.nodata)]
        return float(np.std(valid)) if len(valid) > 0 else np.nan

    @property
    def min_val(self) -> float:
        valid = self.data[~np.isnan(self.data) & (self.data != self.nodata)]
        return float(np.min(valid)) if len(valid) > 0 else np.nan

    @property
    def max_val(self) -> float:
        valid = self.data[~np.isnan(self.data) & (self.data != self.nodata)]
        return float(np.max(valid)) if len(valid) > 0 else np.nan

    def copy(self) -> RasterBand:
        return RasterBand(
            name=self.name,
            data=self.data.copy(),
            nodata=self.nodata,
            dtype=self.dtype,
        )


@dataclass
class RasterScene:
    bands: dict[str, RasterBand]
    crs: CRS = field(default_factory=CRS)
    bbox: BoundingBox | None = None
    pixel_size_m: float = 10.0
    width: int = 0
    height: int = 0
    nodata: float = np.nan
    provenance: GeoProvenance | None = None
    acquisition_time: datetime | None = None

    def __post_init__(self) -> None:
        if self.width == 0 and self.bands:
            first = next(iter(self.bands.values()))
            self.height, self.width = first.data.shape
        if self.acquisition_time is None and self.provenance:
            self.acquisition_time = self.provenance.acquisition_time

    @property
    def band_names(self) -> list[str]:
        return list(self.bands.keys())

    def get_band(self, name: str) -> RasterBand | None:
        return self.bands.get(name)

    def has_bands(self, names: list[str]) -> bool:
        return all(n in self.bands for n in names)

    def to_metadata(self) -> GeoRasterMetadata:
        return GeoRasterMetadata(
            width_pixels=self.width,
            height_pixels=self.height,
            pixel_size_m=self.pixel_size_m,
            crs=self.crs,
            bands=tuple(self.bands.keys()),
            no_data_value=self.nodata,
        )


def create_raster_from_arrays(
    band_data: dict[str, np.ndarray],
    crs: CRS | None = None,
    bbox: BoundingBox | None = None,
    pixel_size_m: float = 10.0,
    nodata: float = np.nan,
    provenance: GeoProvenance | None = None,
) -> RasterScene:
    """Create a RasterScene from numpy arrays.

    Validates shapes, records provenance.
    """
    if not band_data:
        raise ValueError("band_data must not be empty")

    shapes = {name: arr.shape for name, arr in band_data.items()}
    first_shape = next(iter(shapes.values()))
    for name, shape in shapes.items():
        if shape != first_shape:
            raise ValueError(
                f"Band shape mismatch: {name} has {shape}, expected {first_shape}"
            )

    bands = {
        name: RasterBand(
            name=name,
            data=arr.astype(np.float64) if arr.dtype.kind != 'f' else arr,
            nodata=nodata,
        )
        for name, arr in band_data.items()
    }

    return RasterScene(
        bands=bands,
        crs=crs or CRS(),
        bbox=bbox,
        pixel_size_m=pixel_size_m,
        width=first_shape[1] if len(first_shape) > 1 else first_shape[0],
        height=first_shape[0],
        nodata=nodata,
        provenance=provenance,
    )


def clip_raster_to_bbox(
    scene: RasterScene,
    bbox: BoundingBox,
) -> RasterScene:
    """Clip raster bands to a bounding box.

    Requires scene to have bbox set. Returns new RasterScene.
    Records operation in provenance.
    """
    if scene.bbox is None:
        raise ValueError("Scene has no bbox — cannot clip")

    src = scene.bbox
    dst = bbox

    if not src.intersects(dst):
        raise ValueError("Target bbox does not intersect source bbox")

    h, w = scene.height, scene.width
    lat_range = src.north - src.south
    lon_range = src.east - src.west

    if lat_range <= 0 or lon_range <= 0:
        raise ValueError("Source bbox has zero or negative range")

    row_start = max(0, int((dst.south - src.south) / lat_range * h))
    row_end = min(h, int((dst.north - src.south) / lat_range * h))
    col_start = max(0, int((dst.west - src.west) / lon_range * w))
    col_end = min(w, int((dst.east - src.west) / lon_range * w))

    clipped_bands = {}
    for name, band in scene.bands.items():
        clipped_data = band.data[row_start:row_end, col_start:col_end].copy()
        clipped_bands[name] = RasterBand(
            name=name, data=clipped_data, nodata=band.nodata
        )

    if scene.provenance:
        p = scene.provenance
        new_prov = GeoProvenance(
            provider=p.provider,
            dataset=p.dataset,
            acquisition_time=p.acquisition_time,
            processing_time=datetime.now(timezone.utc),
            processing_method=f"{p.processing_method}+clip",
            methodology_version=p.methodology_version,
            source_url=p.source_url,
            crs=p.crs,
            spatial_resolution_m=p.spatial_resolution_m,
            temporal_resolution_hours=p.temporal_resolution_hours,
            source_sha256=p.source_sha256,
            is_demo=p.is_demo,
            uncertainty=p.uncertainty,
            notes=p.notes + (f"Clipped to bbox {bbox}",),
        )
    else:
        new_prov = GeoProvenance(
            provider="unknown",
            dataset="unknown",
            acquisition_time=datetime.now(timezone.utc),
            processing_time=datetime.now(timezone.utc),
            processing_method="clip",
            notes=(f"Clipped to bbox {bbox}",),
        )

    return RasterScene(
        bands=clipped_bands,
        crs=scene.crs,
        bbox=dst,
        pixel_size_m=scene.pixel_size_m,
        width=clipped_bands[next(iter(clipped_bands))].data.shape[1]
        if clipped_bands
        else 0,
        height=clipped_bands[next(iter(clipped_bands))].data.shape[0]
        if clipped_bands
        else 0,
        nodata=scene.nodata,
        provenance=new_prov,
    )


def resample_raster(
    scene: RasterScene,
    target_height: int,
    target_width: int,
) -> RasterScene:
    """Resample raster to target dimensions using nearest-neighbor.

    Records operation in provenance.
    """
    resampled_bands = {}
    for name, band in scene.bands.items():
        src_h, src_w = band.data.shape
        row_idx = np.clip(
            (np.arange(target_height) * src_h / target_height).astype(int),
            0, src_h - 1
        )
        col_idx = np.clip(
            (np.arange(target_width) * src_w / target_width).astype(int),
            0, src_w - 1
        )
        resampled_data = band.data[np.ix_(row_idx, col_idx)].copy()
        resampled_bands[name] = RasterBand(
            name=name, data=resampled_data, nodata=band.nodata
        )

    new_prov = None
    if scene.provenance:
        p = scene.provenance
        new_prov = GeoProvenance(
            provider=p.provider,
            dataset=p.dataset,
            acquisition_time=p.acquisition_time,
            processing_time=datetime.now(timezone.utc),
            processing_method=f"{p.processing_method}+resample({target_height}x{target_width})",
            methodology_version=p.methodology_version,
            source_url=p.source_url,
            crs=p.crs,
            spatial_resolution_m=p.spatial_resolution_m * (scene.height / target_height),
            temporal_resolution_hours=p.temporal_resolution_hours,
            source_sha256=p.source_sha256,
            is_demo=p.is_demo,
            uncertainty=p.uncertainty + f" Resampled from {src_h}x{src_w} to {target_height}x{target_width}.",
            notes=p.notes + (f"Resampled to {target_height}x{target_width}",),
        )
    else:
        new_prov = GeoProvenance(
            provider="unknown",
            dataset="unknown",
            acquisition_time=datetime.now(timezone.utc),
            processing_time=datetime.now(timezone.utc),
            processing_method=f"resample({target_height}x{target_width})",
            notes=(f"Resampled to {target_height}x{target_width}",),
        )

    return RasterScene(
        bands=resampled_bands,
        crs=scene.crs,
        bbox=scene.bbox,
        pixel_size_m=scene.pixel_size_m * (scene.height / target_height)
        if scene.height > 0
        else scene.pixel_size_m,
        width=target_width,
        height=target_height,
        nodata=scene.nodata,
        provenance=new_prov,
    )


def mask_nodata(
    scene: RasterScene,
    mask_band: str = "SCL",
    invalid_values: tuple[float, ...] = (0, 1, 2, 3, 8, 9, 10, 11),
) -> RasterScene:
    """Mask invalid pixels using a scene classification band.

    Sets pixels matching invalid_values to nodata.
    Records operation in provenance.
    """
    if mask_band not in scene.bands:
        return scene

    scl = scene.bands[mask_band].data
    mask = np.zeros_like(scl, dtype=bool)
    for val in invalid_values:
        mask |= (scl == val)

    masked_bands = {}
    for name, band in scene.bands.items():
        if name == mask_band:
            masked_bands[name] = band.copy()
            continue
        masked_data = band.data.copy()
        masked_data[mask] = np.nan
        masked_bands[name] = RasterBand(
            name=name, data=masked_data, nodata=band.nodata
        )

    new_prov = None
    if scene.provenance:
        p = scene.provenance
        new_prov = GeoProvenance(
            provider=p.provider,
            dataset=p.dataset,
            acquisition_time=p.acquisition_time,
            processing_time=datetime.now(timezone.utc),
            processing_method=f"{p.processing_method}+cloud_mask({mask_band})",
            methodology_version=p.methodology_version,
            source_url=p.source_url,
            crs=p.crs,
            spatial_resolution_m=p.spatial_resolution_m,
            temporal_resolution_hours=p.temporal_resolution_hours,
            source_sha256=p.source_sha256,
            is_demo=p.is_demo,
            uncertainty=p.uncertainty + f" Cloud-masked using {mask_band}.",
            notes=p.notes + (f"Masked invalid pixels from {mask_band}",),
        )
    else:
        new_prov = GeoProvenance(
            provider="unknown",
            dataset="unknown",
            acquisition_time=datetime.now(timezone.utc),
            processing_time=datetime.now(timezone.utc),
            processing_method=f"cloud_mask({mask_band})",
            notes=(f"Masked invalid pixels from {mask_band}",),
        )

    return RasterScene(
        bands=masked_bands,
        crs=scene.crs,
        bbox=scene.bbox,
        pixel_size_m=scene.pixel_size_m,
        width=scene.width,
        height=scene.height,
        nodata=scene.nodata,
        provenance=new_prov,
    )


def compute_band_stats(
    scene: RasterScene,
    band_name: str,
) -> dict[str, float]:
    """Compute per-band statistics: mean, std, min, max, valid_count."""
    band = scene.get_band(band_name)
    if band is None:
        return {"error": 1.0}

    valid = band.data[~np.isnan(band.data) & (band.data != band.nodata)]
    if len(valid) == 0:
        return {
            "mean": np.nan,
            "std": np.nan,
            "min": np.nan,
            "max": np.nan,
            "valid_count": 0.0,
            "total_count": float(band.data.size),
        }

    return {
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "valid_count": float(len(valid)),
        "total_count": float(band.data.size),
    }
