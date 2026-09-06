"""
Geo tools for LLM-2 grounded intelligence.

Wraps existing aurora.geo.services into bounded tool operations.
All tools are READ-only and deterministic.
Sentinel data requires AUTH_REQUIRED credentials.
"""

from __future__ import annotations

from typing import Any

from aurora.ai.tools.base import AITool, ToolPermission, ToolResult


class GeoSceneSearchTool(AITool):
    """Search for available geo imagery scenes."""

    @property
    def name(self) -> str:
        return "geo.search_scenes"

    @property
    def description(self) -> str:
        return "Search available satellite imagery scenes for a location and date range"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_GEO]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "minimum": -90, "maximum": 90},
                "lon": {"type": "number", "minimum": -180, "maximum": 180},
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"},
                "max_cloud_pct": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "default": 30,
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["lat", "lon", "start_date", "end_date"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        lat = parameters["lat"]
        lon = parameters["lon"]
        start_date = parameters["start_date"]
        end_date = parameters["end_date"]
        max_cloud = parameters.get("max_cloud_pct", 30)
        limit = parameters.get("limit", 10)

        try:
            from aurora.geo.services import sentinel_service

            scenes = sentinel_service.search_scenes(
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                max_cloud_pct=max_cloud,
                limit=limit,
            )

            data = {
                "lat": lat,
                "lon": lon,
                "start_date": start_date,
                "end_date": end_date,
                "max_cloud_pct": max_cloud,
                "scene_count": len(scenes) if scenes else 0,
                "scenes": scenes[:limit] if scenes else [],
                "data_source": "sentinel_hub",
                "pixel_access": "AUTH_REQUIRED",
            }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data=data,
                evidence_id=self._compute_evidence_id(data),
                execution_time_ms=0.0,
                source_refs=[
                    f"sentinel:{lat},{lon}:{start_date}/{end_date}"
                ],
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={"lat": lat, "lon": lon},
                evidence_id="",
                execution_time_ms=0.0,
                error=str(exc),
            )


class GeoObservationTool(AITool):
    """Retrieve observation data for a location (satellite, ground, subsurface)."""

    @property
    def name(self) -> str:
        return "geo.observation"

    @property
    def description(self) -> str:
        return "Get observation data for a geographic point from multiple sources"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_GEO]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "satellite",
                            "balloon",
                            "uav",
                            "ground_sensor",
                            "subsurface",
                        ],
                    },
                    "default": ["satellite"],
                },
                "date": {"type": "string", "format": "date"},
            },
            "required": ["lat", "lon"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        lat = parameters["lat"]
        lon = parameters["lon"]
        sources = parameters.get("sources", ["satellite"])
        date = parameters.get("date")

        observations = {}
        unavailable_sources = []

        for source in sources:
            if source == "satellite":
                # Sentinel pixel access requires AUTH
                unavailable_sources.append(
                    {"source": "satellite", "reason": "AUTH_REQUIRED"}
                )
            elif source in ("balloon", "uav", "ground_sensor", "subsurface"):
                unavailable_sources.append(
                    {"source": source, "reason": "DATA_SOURCE_NOT_CONNECTED"}
                )

        data = {
            "lat": lat,
            "lon": lon,
            "requested_sources": sources,
            "date": date,
            "observations": observations,
            "unavailable_sources": unavailable_sources,
            "data_status": "PARTIAL"
            if observations
            else "DATA_UNAVAILABLE",
        }

        return ToolResult(
            tool_name=self.name,
            status="success",
            data=data,
            evidence_id=self._compute_evidence_id(data),
            execution_time_ms=0.0,
            source_refs=[f"geo:{lat},{lon}:{date or 'latest'}"],
        )


class GeoAnalysisTool(AITool):
    """Run deterministic geo analysis (NDVI, NDWI, change detection)."""

    @property
    def name(self) -> str:
        return "geo.analysis"

    @property
    def description(self) -> str:
        return "Run deterministic geo analysis on satellite imagery"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_GEO, ToolPermission.RUN_DETERMINISTIC_ANALYSIS]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scene_id": {"type": "string"},
                "analysis_type": {
                    "type": "string",
                    "enum": [
                        "ndvi",
                        "ndwi",
                        "ndbi",
                        "evi",
                        "change_detection",
                        "time_series",
                    ],
                },
                "band_config": {
                    "type": "object",
                    "description": "Custom band mapping for GIBS (default fails for RGB-only data)",
                },
            },
            "required": ["scene_id", "analysis_type"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        scene_id = parameters["scene_id"]
        analysis_type = parameters["analysis_type"]

        # NDVI/NDWI/NDBI/EVI require non-RGB bands (NIR, SWIR)
        # GIBS provides RGB only → DATA_UNAVAILABLE
        rgb_only_analyses = {"ndvi", "ndwi", "ndbi", "evi"}

        if analysis_type in rgb_only_analyses:
            data = {
                "scene_id": scene_id,
                "analysis_type": analysis_type,
                "status": "DATA_UNAVAILABLE",
                "reason": f"{analysis_type.upper()} requires non-RGB bands (NIR/SWIR) not available in GIBS imagery",
                "available_for": "Sentinel Hub with AUTH credentials",
            }
        elif analysis_type == "change_detection":
            data = {
                "scene_id": scene_id,
                "analysis_type": "change_detection",
                "status": "REQUIRES_MULTI_DATE",
                "reason": "Change detection requires two or more scenes at different dates",
            }
        else:
            data = {
                "scene_id": scene_id,
                "analysis_type": analysis_type,
                "status": "NOT_IMPLEMENTED",
                "reason": f"Analysis '{analysis_type}' not yet implemented",
            }

        return ToolResult(
            tool_name=self.name,
            status="success",
            data=data,
            evidence_id=self._compute_evidence_id(data),
            execution_time_ms=0.0,
            evidence_type="analysis",
            source_refs=[f"geo_analysis:{scene_id}:{analysis_type}"],
        )


# ── Exported Tool List ─────────────────────────────────────────────────────

GEO_TOOLS: list[AITool] = [
    GeoSceneSearchTool(),
    GeoObservationTool(),
    GeoAnalysisTool(),
]
