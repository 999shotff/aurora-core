"""Index engine — per-pixel spectral index computation.

Works on RasterScene objects with real numpy arrays.
Handles: zero denominator, NaN, infinity, nodata, missing bands, invalid ranges.
Every result records full provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from aurora.geo.raster.engine import RasterScene, RasterBand
from aurora.geo.domain import GeoIntegrityState


# ── Sentinel-2 band mappings ──

DATASET_BAND_MAP = {
    "S2L2A": {
        "NDVI": {"nir": "B08", "red": "B04"},
        "NDWI": {"green": "B03", "nir": "B08"},
        "NDBI": {"swir1": "B11", "nir": "B08"},
        "EVI": {"nir": "B08", "red": "B04", "blue": "B02"},
    },
    "S2L1C": {
        "NDVI": {"nir": "B08", "red": "B04"},
        "NDWI": {"green": "B03", "nir": "B08"},
        "NDBI": {"swir1": "B11", "nir": "B08"},
        "EVI": {"nir": "B08", "red": "B04", "blue": "B02"},
    },
    "MODIS": {
        "NDVI": {"nir": "25", "red": "1"},
        "NDWI": {"green": "6", "nir": "2"},
    },
    "nasa_gibs": {},
    "MODIS_Terra_CorrectedReflectance_TrueColor": {},
}


@dataclass(frozen=True)
class IndexResult:
    name: str
    data: np.ndarray
    valid_count: int
    total_count: int
    mean: float
    std: float
    min_val: float
    max_val: float
    supported: bool
    integrity_state: GeoIntegrityState
    formula: str
    source_bands: tuple[str, ...]
    methodology_version: str = "1.0"
    processing_library: str = "numpy"
    nodata_treatment: str = "NaN propagation"
    uncertainty: str = ""
    error: str = ""


def _safe_divide(
    numerator: np.ndarray,
    denominator: np.ndarray,
    nodata: float = np.nan,
) -> np.ndarray:
    """Divide with safe handling of zero denominator, NaN, infinity."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            np.abs(denominator) < 1e-10,
            nodata,
            numerator / denominator,
        )
    result = np.where(np.isinf(result), nodata, result)
    result = np.where(np.isnan(result), nodata, result)
    return result


def _get_valid_stats(data: np.ndarray, nodata: float = np.nan) -> dict[str, float]:
    """Compute statistics on valid (non-nodata) pixels."""
    valid = data[~np.isnan(data) & (data != nodata)]
    if len(valid) == 0:
        return {"mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan, "count": 0}
    return {
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "count": int(len(valid)),
    }


def _resolve_band(
    scene: RasterScene,
    band_key: str,
    dataset: str = "S2L2A",
) -> RasterBand | None:
    """Resolve a spectral band name to a RasterBand, trying multiple naming conventions."""
    dataset_map = DATASET_BAND_MAP.get(dataset, DATASET_BAND_MAP.get("S2L2A", {}))

    candidates = [band_key]
    for index_map in dataset_map.values():
        if isinstance(index_map, dict) and band_key in index_map:
            candidates.append(index_map[band_key])
            break

    alias_map = {
        "nir": ["NIR", "B08", "B8", "Red", "RED"],
        "red": ["RED", "B04", "B4", "Red"],
        "green": ["GREEN", "B03", "B3", "Green"],
        "blue": ["BLUE", "B02", "B2", "Blue"],
        "swir1": ["SWIR1", "B11", "B11", "Green"],
    }
    for alias_group in alias_map.values():
        if band_key.lower() in [a.lower() for a in alias_group]:
            candidates.extend(alias_group)

    for name in candidates:
        if name and name in scene.bands:
            return scene.bands[name]
    return None


def _has_valid_spectral_band(
    scene: RasterScene,
    band_key: str,
    band: RasterBand,
    dataset: str = "S2L2A",
) -> bool:
    """Check if a resolved band actually matches the required spectral range.

    GIBS RGB visualization channels (Red/Green/Blue) are NOT scientific spectral bands.
    NDVI requires Near-Infrared (NIR), not visible red.
    NDBI requires Short-Wave Infrared (SWIR), not visible green.
    """
    visible_bands = {"Red", "Green", "Blue", "red", "green", "blue"}
    nir_aliases = {"nir", "NIR", "B08", "B8", "B05", "B5"}
    swir_aliases = {"swir1", "SWIR1", "B11", "B11A", "B12", "B12A"}

    dataset_map = DATASET_BAND_MAP.get(dataset, {})
    mapped_name = None
    for index_map in dataset_map.values():
        if isinstance(index_map, dict) and band_key in index_map:
            mapped_name = index_map[band_key]
            break

    if mapped_name is None and band.name in visible_bands:
        if band_key.lower() in ("nir", "swir1", "swir2"):
            return False

    return True


def compute_ndvi(
    scene: RasterScene,
    dataset: str = "S2L2A",
) -> IndexResult:
    """NDVI = (NIR - RED) / (NIR + RED)

    Per-pixel computation on real raster arrays.
    Handles zero denominator, NaN, nodata.
    """
    nir_band = _resolve_band(scene, "nir", dataset)
    red_band = _resolve_band(scene, "red", dataset)

    if nir_band is None or red_band is None:
        missing = []
        if nir_band is None: missing.append("NIR")
        if red_band is None: missing.append("RED")
        return IndexResult(
            name="NDVI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(NIR - RED) / (NIR + RED)",
            source_bands=tuple(missing),
            error=f"Missing bands: {missing}. Available: {list(scene.bands.keys())}",
        )

    if not _has_valid_spectral_band(scene, "nir", nir_band, dataset):
        return IndexResult(
            name="NDVI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(NIR - RED) / (NIR + RED)",
            source_bands=(nir_band.name, red_band.name),
            error=(
                f"Required spectral band NIR (Near-Infrared) unavailable from source. "
                f"Resolved to '{nir_band.name}' which is not a valid NIR band. "
                f"GIBS provides RGB visualization imagery only, not scientific spectral data."
            ),
        )

    nir = nir_band.data
    red = red_band.data
    denominator = nir + red

    ndvi = _safe_divide(nir - red, denominator)

    stats = _get_valid_stats(ndvi)
    nodata_mask = np.isnan(ndvi) | (ndvi == scene.nodata)

    return IndexResult(
        name="NDVI",
        data=ndvi,
        valid_count=stats["count"],
        total_count=int(ndvi.size),
        mean=stats["mean"],
        std=stats["std"],
        min_val=stats["min"],
        max_val=stats["max"],
        supported=True,
        integrity_state=GeoIntegrityState.DATA_AVAILABLE,
        formula="(B08 - B04) / (B08 + B04)",
        source_bands=(nir_band.name, red_band.name),
        uncertainty="Surface reflectance assumed. Atmospheric correction quality varies.",
    )


def compute_ndwi(
    scene: RasterScene,
    dataset: str = "S2L2A",
) -> IndexResult:
    """NDWI = (GREEN - NIR) / (GREEN + NIR)"""
    green_band = _resolve_band(scene, "green", dataset)
    nir_band = _resolve_band(scene, "nir", dataset)

    if green_band is None or nir_band is None:
        missing = []
        if green_band is None: missing.append("GREEN")
        if nir_band is None: missing.append("NIR")
        return IndexResult(
            name="NDWI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(GREEN - NIR) / (GREEN + NIR)",
            source_bands=tuple(missing),
            error=f"Missing bands: {missing}",
        )

    if not _has_valid_spectral_band(scene, "nir", nir_band, dataset):
        return IndexResult(
            name="NDWI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(GREEN - NIR) / (GREEN + NIR)",
            source_bands=(green_band.name, nir_band.name),
            error=(
                f"Required spectral band NIR (Near-Infrared) unavailable from source. "
                f"Resolved to '{nir_band.name}' which is not a valid NIR band. "
                f"GIBS provides RGB visualization imagery only, not scientific spectral data."
            ),
        )

    green = green_band.data
    nir = nir_band.data
    ndwi = _safe_divide(green - nir, green + nir)
    stats = _get_valid_stats(ndwi)

    return IndexResult(
        name="NDWI",
        data=ndwi,
        valid_count=stats["count"],
        total_count=int(ndwi.size),
        mean=stats["mean"],
        std=stats["std"],
        min_val=stats["min"],
        max_val=stats["max"],
        supported=True,
        integrity_state=GeoIntegrityState.DATA_AVAILABLE,
        formula="(B03 - B08) / (B03 + B08)",
        source_bands=(green_band.name, nir_band.name),
        uncertainty="McFeeters (1996). Sensitive to built-up area false positives.",
    )


def compute_ndbi(
    scene: RasterScene,
    dataset: str = "S2L2A",
) -> IndexResult:
    """NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)"""
    swir_band = _resolve_band(scene, "swir1", dataset)
    nir_band = _resolve_band(scene, "nir", dataset)

    if swir_band is None or nir_band is None:
        missing = []
        if swir_band is None: missing.append("SWIR1")
        if nir_band is None: missing.append("NIR")
        return IndexResult(
            name="NDBI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(SWIR1 - NIR) / (SWIR1 + NIR)",
            source_bands=tuple(missing),
            error=f"Missing bands: {missing}",
        )

    if not _has_valid_spectral_band(scene, "swir1", swir_band, dataset):
        return IndexResult(
            name="NDBI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(SWIR1 - NIR) / (SWIR1 + NIR)",
            source_bands=(swir_band.name, nir_band.name),
            error=(
                f"Required spectral band SWIR1 (Short-Wave Infrared) unavailable from source. "
                f"Resolved to '{swir_band.name}' which is not a valid SWIR band. "
                f"GIBS provides RGB visualization imagery only, not scientific spectral data."
            ),
        )

    if not _has_valid_spectral_band(scene, "nir", nir_band, dataset):
        return IndexResult(
            name="NDBI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="(SWIR1 - NIR) / (SWIR1 + NIR)",
            source_bands=(swir_band.name, nir_band.name),
            error=(
                f"Required spectral band NIR (Near-Infrared) unavailable from source. "
                f"Resolved to '{nir_band.name}' which is not a valid NIR band. "
                f"GIBS provides RGB visualization imagery only, not scientific spectral data."
            ),
        )

    swir = swir_band.data
    nir = nir_band.data
    ndbi = _safe_divide(swir - nir, swir + nir)
    stats = _get_valid_stats(ndbi)

    return IndexResult(
        name="NDBI",
        data=ndbi,
        valid_count=stats["count"],
        total_count=int(ndbi.size),
        mean=stats["mean"],
        std=stats["std"],
        min_val=stats["min"],
        max_val=stats["max"],
        supported=True,
        integrity_state=GeoIntegrityState.DATA_AVAILABLE,
        formula="(B11 - B08) / (B11 + B08)",
        source_bands=(swir_band.name, nir_band.name),
        uncertainty="Zha et al. (2003). Positive values indicate built-up areas.",
    )


def compute_evi(
    scene: RasterScene,
    dataset: str = "S2L2A",
    gain: float = 2.5,
    offset: float = 0.1,
    soil_adjustment: float = 1.0,
) -> IndexResult:
    """EVI = G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)

    Enhanced Vegetation Index. More sensitive to high biomass.
    """
    nir_band = _resolve_band(scene, "nir", dataset)
    red_band = _resolve_band(scene, "red", dataset)
    blue_band = _resolve_band(scene, "blue", dataset)

    if not all([nir_band, red_band, blue_band]):
        missing = [b for b, band in [("NIR", nir_band), ("RED", red_band), ("BLUE", blue_band)] if band is None]
        return IndexResult(
            name="EVI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)",
            source_bands=tuple(missing),
            error=f"Missing bands: {missing}",
        )

    if not _has_valid_spectral_band(scene, "nir", nir_band, dataset):
        return IndexResult(
            name="EVI",
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.DATA_UNAVAILABLE,
            formula="G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)",
            source_bands=(nir_band.name, red_band.name, blue_band.name),
            error=(
                f"Required spectral band NIR (Near-Infrared) unavailable from source. "
                f"Resolved to '{nir_band.name}' which is not a valid NIR band. "
                f"GIBS provides RGB visualization imagery only, not scientific spectral data."
            ),
        )

    nir = nir_band.data
    red = red_band.data
    blue = blue_band.data

    numerator = gain * (nir - red)
    denominator = nir + 6.0 * red - 7.5 * blue + soil_adjustment
    evi = _safe_divide(numerator, denominator)
    evi = np.clip(evi, -1, 1)
    stats = _get_valid_stats(evi)

    return IndexResult(
        name="EVI",
        data=evi,
        valid_count=stats["count"],
        total_count=int(evi.size),
        mean=stats["mean"],
        std=stats["std"],
        min_val=stats["min"],
        max_val=stats["max"],
        supported=True,
        integrity_state=GeoIntegrityState.DATA_AVAILABLE,
        formula="2.5 * (B08 - B04) / (B08 + 6*B04 - 7.5*B02 + 1)",
        source_bands=(nir_band.name, red_band.name, blue_band.name),
        uncertainty="Huete et al. (2002). Sensitive to atmospheric and soil effects.",
    )


def compute_index(
    scene: RasterScene,
    index_name: str,
    dataset: str = "S2L2A",
) -> IndexResult:
    """Generic index computation dispatcher."""
    engines = {
        "NDVI": compute_ndvi,
        "NDWI": compute_ndwi,
        "NDBI": compute_ndbi,
        "EVI": compute_evi,
    }
    engine = engines.get(index_name)
    if engine is None:
        return IndexResult(
            name=index_name,
            data=np.array([]),
            valid_count=0, total_count=0,
            mean=np.nan, std=np.nan, min_val=np.nan, max_val=np.nan,
            supported=False,
            integrity_state=GeoIntegrityState.PROCESSING_FAILED,
            formula="",
            source_bands=(),
            error=f"Unknown index: {index_name}. Available: {list(engines.keys())}",
        )
    return engine(scene, dataset)
