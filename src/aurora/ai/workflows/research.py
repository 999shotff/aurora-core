"""
Research Workflow for LLM-2.

Orchestrates: claim search → hypothesis search → document lookup → synthesis.
"""

from __future__ import annotations

from typing import Any

from aurora.ai.tools.base import ToolRegistry
from aurora.ai.evidence_graph import EvidenceGraph, EvidenceNode
from aurora.ai.tools.permissions import PermissionPolicy


class ResearchWorkflow:
    """
    Deterministic research workflow.

    Steps:
    1. Search claims
    2. Search hypotheses
    3. Get document details
    4. Synthesize evidence
    """

    def __init__(self, registry: ToolRegistry, evidence_graph: EvidenceGraph) -> None:
        self._registry = registry
        self._graph = evidence_graph

    def execute(self, query: str, goal: str = "") -> dict[str, Any]:
        """
        Execute the research workflow for a query.

        Returns aggregated evidence from research sources.
        """
        results: dict[str, Any] = {"query": query, "steps": []}

        # Step 1: Search claims
        claims_result = self._registry.execute(
            "research.search_claims",
            {"query": query, "limit": 10},
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="research_workflow",
        )
        results["steps"].append({"tool": "research.search_claims", "status": claims_result.status})

        if claims_result.status == "success":
            node = EvidenceNode(
                evidence_id=claims_result.evidence_id,
                tool_name="research.search_claims",
                evidence_type="observation",
                data_summary=f"Claims search: {query}",
                source_refs=claims_result.source_refs,
            )
            self._graph.add_node(node)

        # Step 2: Search hypotheses
        hypotheses_result = self._registry.execute(
            "research.search_hypotheses",
            {"query": query, "limit": 10},
            allowed_permissions=PermissionPolicy.ALLOWED,
            planning_context="research_workflow",
        )
        results["steps"].append({"tool": "research.search_hypotheses", "status": hypotheses_result.status})

        if hypotheses_result.status == "success":
            node = EvidenceNode(
                evidence_id=hypotheses_result.evidence_id,
                tool_name="research.search_hypotheses",
                evidence_type="observation",
                data_summary=f"Hypotheses search: {query}",
                source_refs=hypotheses_result.source_refs,
            )
            self._graph.add_node(node)

        # Step 3: Get document details (if claims found)
        claims_data = claims_result.data if claims_result.status == "success" else {}
        claim_list = claims_data.get("results", [])
        if claim_list and isinstance(claim_list[0], dict):
            doc_id = claim_list[0].get("document_id")
            if doc_id:
                doc_result = self._registry.execute(
                    "research.get_document",
                    {"document_id": doc_id},
                    allowed_permissions=PermissionPolicy.ALLOWED,
                    planning_context="research_workflow",
                )
                results["steps"].append({"tool": "research.get_document", "status": doc_result.status})

                if doc_result.status == "success":
                    node = EvidenceNode(
                        evidence_id=doc_result.evidence_id,
                        tool_name="research.get_document",
                        evidence_type="observation",
                        data_summary=f"Document: {doc_id}",
                        source_refs=doc_result.source_refs,
                    )
                    self._graph.add_node(node)

        # Aggregate results
        results["evidence"] = {
            "claims": claims_result.data if claims_result.status == "success" else None,
            "hypotheses": hypotheses_result.data if hypotheses_result.status == "success" else None,
        }
        results["graph_summary"] = self._graph.summary()

        return results
