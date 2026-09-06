"""
Geo Analysis Workflow for LLM-2.

Orchestrates: scene search → observation → analysis → synthesis.
"""

from __future__ import annotations

from typing import Any

from aurora.ai.tools.base import ToolRegistry
from aurora.ai.evidence_graph import EvidenceGraph, EvidenceNode
from aurora.ai.tools.permissions import PermissionPolicy


class GeoWorkflow:
    """
    Deterministic geo analysis workflow.

    Steps:
    1. Search available scenes
    2. Get observation data
    3. Run analysis (if data available)
    4. Synthesize evidence
    """

    def __init__(self, registry: ToolRegistry, evidence_graph: EvidenceGraph) -> None:
        self._registry = registry
        self._graph = evidence_graph

    def execute(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        goal: str = "",
    ) -> dict[str, Any]:
        """
        Execute the geo workflow for a location.

        Returns aggregated evidence and analysis.
        """
        results: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "start_date": start_date,
            "end_date": end_date,
            "steps": [],
        }

        # Step 1: Search scenes
        search_result = self._registry.execute(
            "geo.search_scenes",
            {
                "lat": lat,
                "lon": lon,
                "start_date": start_date,
                "end_date": end_date,
            },
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="geo_workflow",
        )
        results["steps"].append({"tool": "geo.search_scenes", "status": search_result.status})

        if search_result.status == "success":
            node = EvidenceNode(
                evidence_id=search_result.evidence_id,
                tool_name="geo.search_scenes",
                evidence_type="observation",
                data_summary=f"Scene search for {lat},{lon}",
                source_refs=search_result.source_refs,
            )
            self._graph.add_node(node)

        # Step 2: Get observations
        obs_result = self._registry.execute(
            "geo.observation",
            {"lat": lat, "lon": lon, "sources": ["satellite"], "date": start_date},
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="geo_workflow",
        )
        results["steps"].append({"tool": "geo.observation", "status": obs_result.status})

        if obs_result.status == "success":
            node = EvidenceNode(
                evidence_id=obs_result.evidence_id,
                tool_name="geo.observation",
                evidence_type="observation",
                data_summary=f"Observation for {lat},{lon}",
                source_refs=obs_result.source_refs,
            )
            self._graph.add_node(node)

        # Step 3: Analysis (if scene available)
        scenes = (
            search_result.data.get("scenes", [])
            if search_result.status == "success"
            else []
        )
        if scenes:
            scene_id = scenes[0].get("id", "unknown") if isinstance(scenes[0], dict) else str(scenes[0])
            analysis_result = self._registry.execute(
                "geo.analysis",
                {"scene_id": scene_id, "analysis_type": "ndvi"},
                allowed_permissions=PermissionPolicy.ALLOWED,
                planning_context="geo_workflow",
            )
            results["steps"].append({"tool": "geo.analysis", "status": analysis_result.status})

            if analysis_result.status == "success":
                node = EvidenceNode(
                    evidence_id=analysis_result.evidence_id,
                    tool_name="geo.analysis",
                    evidence_type="analysis",
                    data_summary=f"Analysis for scene {scene_id}",
                    source_refs=analysis_result.source_refs,
                )
                self._graph.add_node(node)

        # Aggregate results
        results["evidence"] = {
            "scenes": search_result.data if search_result.status == "success" else None,
            "observations": obs_result.data if obs_result.status == "success" else None,
        }
        results["graph_summary"] = self._graph.summary()

        return results
