"""
Research tools for LLM-2 grounded intelligence.

Wraps existing aurora.features into bounded research operations.
All tools are READ-only and deterministic.
"""

from __future__ import annotations

from typing import Any

from aurora.ai.tools.base import AITool, ToolPermission, ToolResult


class ResearchSearchTool(AITool):
    """Search extracted research claims."""

    @property
    def name(self) -> str:
        return "research.search_claims"

    @property
    def description(self) -> str:
        return "Search extracted claims from research PDFs"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_RESEARCH]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2},
                "claim_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "DEFINITION",
                            "OBSERVATION",
                            "RULE",
                            "HYPOTHESIS",
                            "EMPIRICAL_CLAIM",
                            "FORMULA",
                            "HISTORICAL_CLAIM",
                            "OPINION",
                            "UNKNOWN",
                        ],
                    },
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        query = parameters["query"]
        claim_types = parameters.get("claim_types")
        limit = parameters.get("limit", 10)

        try:
            from aurora.features.evidence import EvidenceAggregation

            agg = EvidenceAggregation()
            results = agg.search_claims(
                query=query, claim_types=claim_types, limit=limit
            )

            data = {
                "query": query,
                "claim_types": claim_types,
                "result_count": len(results) if results else 0,
                "results": results[:limit] if results else [],
                "status": "UNREVIEWED",
                "source": "evidence_aggregation",
            }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data=data,
                evidence_id=self._compute_evidence_id(data),
                execution_time_ms=0.0,
                evidence_type="observation",
                source_refs=[f"research:{query}"],
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={"query": query},
                evidence_id="",
                execution_time_ms=0.0,
                error=str(exc),
            )


class ResearchHypothesisTool(AITool):
    """Search research hypotheses."""

    @property
    def name(self) -> str:
        return "research.search_hypotheses"

    @property
    def description(self) -> str:
        return "Search extracted hypotheses from research PDFs"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_RESEARCH]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2},
                "status_filter": {
                    "type": "string",
                    "enum": ["UNTESTED", "SUPPORTED", "REJECTED", "INCONCLUSIVE"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        query = parameters["query"]
        status_filter = parameters.get("status_filter", "UNTESTED")
        limit = parameters.get("limit", 10)

        try:
            from aurora.features.evidence import EvidenceAggregation

            agg = EvidenceAggregation()
            results = agg.search_hypotheses(
                query=query, status_filter=status_filter, limit=limit
            )

            data = {
                "query": query,
                "status_filter": status_filter,
                "result_count": len(results) if results else 0,
                "results": results[:limit] if results else [],
                "note": "All hypotheses remain UNTESTED until evaluation pipeline",
                "source": "evidence_aggregation",
            }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data=data,
                evidence_id=self._compute_evidence_id(data),
                execution_time_ms=0.0,
                evidence_type="observation",
                source_refs=[f"hypothesis:{query}"],
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={"query": query},
                evidence_id="",
                execution_time_ms=0.0,
                error=str(exc),
            )


class ResearchDocumentTool(AITool):
    """Get document metadata."""

    @property
    def name(self) -> str:
        return "research.get_document"

    @property
    def description(self) -> str:
        return "Get metadata for a specific research document"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_RESEARCH]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "minLength": 1},
            },
            "required": ["document_id"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        document_id = parameters["document_id"]

        try:
            from aurora.features.evidence import EvidenceAggregation

            agg = EvidenceAggregation()
            doc = agg.get_document(document_id)

            if doc is None:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    data={"document_id": document_id},
                    evidence_id="",
                    execution_time_ms=0.0,
                    error=f"Document '{document_id}' not found",
                )

            data = {
                "document_id": document_id,
                "title": getattr(doc, "title", "Unknown"),
                "page_count": getattr(doc, "page_count", 0),
                "claim_count": getattr(doc, "claim_count", 0),
                "hypothesis_count": getattr(doc, "hypothesis_count", 0),
                "source_sha256": getattr(doc, "source_sha256", ""),
            }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data=data,
                evidence_id=self._compute_evidence_id(data),
                execution_time_ms=0.0,
                source_refs=[f"document:{document_id}"],
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={"document_id": document_id},
                evidence_id="",
                execution_time_ms=0.0,
                error=str(exc),
            )


# ── Exported Tool List ─────────────────────────────────────────────────────

RESEARCH_TOOLS: list[AITool] = [
    ResearchSearchTool(),
    ResearchHypothesisTool(),
    ResearchDocumentTool(),
]
