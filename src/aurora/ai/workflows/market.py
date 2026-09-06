"""
Market Analysis Workflow for LLM-2.

Orchestrates: data gathering → technical analysis → sentiment → synthesis.
"""

from __future__ import annotations

from typing import Any

from aurora.ai.tools.base import ToolRegistry
from aurora.ai.evidence_graph import EvidenceGraph, EvidenceNode, RelationshipType
from aurora.ai.tools.permissions import PermissionPolicy


class MarketWorkflow:
    """
    Deterministic market analysis workflow.

    Steps:
    1. Get OHLCV data
    2. Run technical analysis
    3. Gather sentiment (if available)
    4. Synthesize evidence
    """

    def __init__(self, registry: ToolRegistry, evidence_graph: EvidenceGraph) -> None:
        self._registry = registry
        self._graph = evidence_graph

    def execute(
        self, symbol: str, goal: str = "", period: str = "3mo"
    ) -> dict[str, Any]:
        """
        Execute the market workflow for a symbol.

        Returns aggregated evidence and analysis.
        """
        results: dict[str, Any] = {"symbol": symbol, "steps": []}

        # Step 1: Get OHLCV data
        ohlcv_result = self._registry.execute(
            "market.get_ohlcv",
            {"symbol": symbol, "period": period},
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="market_workflow",
        )
        results["steps"].append({"tool": "market.get_ohlcv", "status": ohlcv_result.status})

        if ohlcv_result.status == "success":
            node = EvidenceNode(
                evidence_id=ohlcv_result.evidence_id,
                tool_name="market.get_ohlcv",
                evidence_type="observation",
                data_summary=f"OHLCV data for {symbol}",
                source_refs=ohlcv_result.source_refs,
            )
            self._graph.add_node(node)

        # Step 2: Technical analysis
        analysis_result = self._registry.execute(
            "market.get_analysis",
            {"symbol": symbol, "period": period},
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="market_workflow",
        )
        results["steps"].append({"tool": "market.get_analysis", "status": analysis_result.status})

        if analysis_result.status == "success":
            node = EvidenceNode(
                evidence_id=analysis_result.evidence_id,
                tool_name="market.get_analysis",
                evidence_type="analysis",
                data_summary=f"Technical analysis for {symbol}",
                source_refs=analysis_result.source_refs,
            )
            self._graph.add_node(node)

            # Link analysis as DERIVED_FROM OHLCV
            if ohlcv_result.status == "success" and ohlcv_result.evidence_id:
                from aurora.ai.evidence_graph import EvidenceRelationship

                rel = EvidenceRelationship(
                    source_id=ohlcv_result.evidence_id,
                    target_id=analysis_result.evidence_id,
                    relationship=RelationshipType.DERIVED_FROM,
                    description="Technical analysis derived from OHLCV data",
                )
                self._graph.add_relationship(rel)

        # Step 3: Sentiment
        sentiment_result = self._registry.execute(
            "market.sentiment",
            {"symbol": symbol},
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="market_workflow",
        )
        results["steps"].append({"tool": "market.sentiment", "status": sentiment_result.status})

        if sentiment_result.status == "success":
            node = EvidenceNode(
                evidence_id=sentiment_result.evidence_id,
                tool_name="market.sentiment",
                evidence_type="observation",
                data_summary=f"Sentiment for {symbol}",
                source_refs=sentiment_result.source_refs,
            )
            self._graph.add_node(node)

        # Aggregate results
        results["evidence"] = {
            "ohlcv": ohlcv_result.data if ohlcv_result.status == "success" else None,
            "analysis": analysis_result.data if analysis_result.status == "success" else None,
            "sentiment": sentiment_result.data if sentiment_result.status == "success" else None,
        }
        results["graph_summary"] = self._graph.summary()

        return results
