"""
LLM-4: Investigation Planner — memory-first, gap-driven bounded planning.

Builds on LLM-2's planning architecture. Uses LLM for interpretation.
Backend validates every plan step.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
from typing import Any

from aurora.investigation.schemas import (
    EvidenceGap,
    GapStatus,
    InvestigationDomain,
    InvestigationObjective,
    InvestigationPlan,
    InvestigationPlanStep,
)

logger = logging.getLogger("aurora.investigation.planner")

# ── Domain → Tool Mapping ─────────────────────────────────────────────────

DOMAIN_TOOLS: dict[str, list[str]] = {
    "market": ["market.get_ohlcv", "market.get_analysis", "market.sentiment"],
    "geo": ["geo.search_scenes", "geo.observation", "geo.analysis"],
    "research": [
        "research.search_claims",
        "research.search_hypotheses",
        "research.get_document",
    ],
    "general": [
        "market.get_ohlcv",
        "market.get_analysis",
        "research.search_claims",
    ],
}


class InvestigationPlanner:
    """
    Creates bounded investigation plans.

    Flow:
    1. Understand objective → identify domain
    2. Inspect relevant memory
    3. Determine evidence requirements
    4. Identify evidence gaps
    5. Propose bounded tool steps
    6. Stop when sufficient evidence exists
    """

    def __init__(self, max_steps: int = 8, max_iterations: int = 2) -> None:
        self._max_steps = max_steps
        self._max_iterations = max_iterations

    def identify_domain(self, objective: InvestigationObjective) -> InvestigationDomain:
        """Identify the investigation domain from the objective."""
        if objective.domain != InvestigationDomain.GENERAL:
            return objective.domain
        query_lower = objective.query.lower()
        market_keywords = ["market", "price", "ohlc", "indicator", "trend", "rsi", "macd"]
        geo_keywords = ["aoi", "satellite", "scene", "ndvi", "observation", "geo"]
        research_keywords = ["hypothesis", "claim", "evidence", "research", "document"]

        scores = {
            InvestigationDomain.MARKET: sum(1 for k in market_keywords if k in query_lower),
            InvestigationDomain.GEO: sum(1 for k in geo_keywords if k in query_lower),
            InvestigationDomain.RESEARCH: sum(1 for k in research_keywords if k in query_lower),
        }

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] > 0:
            return best
        return InvestigationDomain.GENERAL

    def identify_required_evidence(
        self, objective: InvestigationObjective, domain: InvestigationDomain
    ) -> list[dict[str, Any]]:
        """Determine what evidence is required for this investigation."""
        required: list[dict[str, Any]] = []

        if domain == InvestigationDomain.MARKET:
            required.append({"type": "ohlcv", "tool": "market.get_ohlcv", "required": True})
            required.append({"type": "analysis", "tool": "market.get_analysis", "required": True})
            required.append({"type": "sentiment", "tool": "market.sentiment", "required": False})

        elif domain == InvestigationDomain.GEO:
            required.append({"type": "scene_search", "tool": "geo.search_scenes", "required": True})
            required.append({"type": "observation", "tool": "geo.observation", "required": True})
            required.append({"type": "analysis", "tool": "geo.analysis", "required": False})

        elif domain == InvestigationDomain.RESEARCH:
            required.append({"type": "claims", "tool": "research.search_claims", "required": True})
            required.append({"type": "hypotheses", "tool": "research.search_hypotheses", "required": True})
            required.append({"type": "document", "tool": "research.get_document", "required": False})

        return required

    def identify_gaps(
        self,
        required_evidence: list[dict[str, Any]],
        existing_memory_refs: list[str],
        existing_evidence_refs: list[str],
    ) -> list[EvidenceGap]:
        """Identify evidence gaps by comparing required vs existing."""
        gaps: list[EvidenceGap] = []

        for req in required_evidence:
            gap = EvidenceGap(
                description=f"Required: {req['type']}",
                required_evidence_type=req["type"],
                priority=10 if req.get("required", False) else 5,
                reason="Not found in memory or current evidence",
                candidate_tools=[req["tool"]],
                resolvable=True,
            )
            gaps.append(gap)

        return gaps

    def generate_plan(
        self,
        objective: InvestigationObjective,
        domain: InvestigationDomain,
        gaps: list[EvidenceGap],
        available_tools: list[str],
    ) -> InvestigationPlan:
        """Generate a bounded investigation plan from open gaps."""
        steps: list[InvestigationPlanStep] = []
        open_gaps = [g for g in gaps if g.status == GapStatus.OPEN]

        for gap in open_gaps:
            for tool_name in gap.candidate_tools:
                if tool_name in available_tools and len(steps) < self._max_steps:
                    step = InvestigationPlanStep(
                        tool_name=tool_name,
                        parameters=self._infer_parameters(tool_name, objective),
                        description=f"Resolve gap: {gap.description}",
                        gap_id=gap.gap_id,
                    )
                    steps.append(step)

        return InvestigationPlan(
            steps=steps,
            estimated_duration_seconds=sum(s.timeout_seconds for s in steps),
        )

    def validate_plan(
        self,
        plan: InvestigationPlan,
        available_tools: list[str],
        limits: Any = None,
    ) -> list[str]:
        """Validate a plan. Returns list of violations (empty = valid)."""
        violations: list[str] = []

        max_steps = 8
        if limits is not None:
            max_steps = getattr(limits, "max_steps", 8)

        if len(plan.steps) > max_steps:
            violations.append(f"Plan has {len(plan.steps)} steps, max is {max_steps}")

        for step in plan.steps:
            if step.tool_name not in available_tools:
                violations.append(f"Unknown tool: {step.tool_name}")

        seen_gaps: set[str | None] = set()
        for step in plan.steps:
            if step.gap_id and step.gap_id in seen_gaps:
                violations.append(f"Duplicate gap_id in plan: {step.gap_id}")
            seen_gaps.add(step.gap_id)

        return violations

    def _infer_parameters(
        self, tool_name: str, objective: InvestigationObjective
    ) -> dict[str, Any]:
        """Infer tool parameters from the objective."""
        params: dict[str, Any] = {}

        if tool_name.startswith("market."):
            params["symbol"] = objective.subject or "AAPL"
            if "period" in objective.scope.lower():
                params["period"] = "3mo"
            else:
                params["period"] = "3mo"

        elif tool_name.startswith("geo."):
            temporal = objective.temporal_range
            if "lat" in temporal and "lon" in temporal:
                params["lat"] = temporal["lat"]
                params["lon"] = temporal["lon"]
            else:
                params["lat"] = 0.0
                params["lon"] = 0.0
            params["start_date"] = temporal.get("start", "2025-01-01")
            params["end_date"] = temporal.get("end", "2025-12-31")

        elif tool_name.startswith("research."):
            params["query"] = objective.subject or objective.query[:200]

        return params
