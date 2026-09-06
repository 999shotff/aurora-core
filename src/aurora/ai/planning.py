"""
Controlled Planning for LLM-2 Grounded Intelligence.

Generates bounded reasoning plans with tool steps.
Limits: 8 max steps, 2 planning iterations, 1 synthesis call.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from aurora.ai.tools.base import ReasoningPlan, ToolStep
from aurora.ai.tools.permissions import PermissionPolicy


class PlanRequest(BaseModel):
    """Request to generate a reasoning plan."""

    model_config = {"extra": "forbid"}

    goal: str = Field(description="What the plan should discover")
    available_tools: list[str] = Field(description="Tools available for planning")
    context_summary: str = Field(default="", description="Brief context summary")
    iteration: int = Field(default=1, description="Current planning iteration")


class PlanValidation(BaseModel):
    """Result of validating a plan."""

    model_config = {"extra": "forbid"}

    valid: bool
    violations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class PlanGenerator:
    """
    Generates bounded reasoning plans.

    Plans are deterministic and auditable. The LLM proposes tool steps,
    but the generator validates all constraints.
    """

    def __init__(self, tool_names: list[str]) -> None:
        self._tool_names = tool_names

    def generate_plan(self, request: PlanRequest) -> ReasoningPlan:
        """
        Generate a reasoning plan from a goal.

        The plan is validated against all constraints before returning.
        """
        if request.iteration > PermissionPolicy.MAX_PLANNING_ITERATIONS:
            raise ValueError(
                f"Planning iteration {request.iteration} exceeds max "
                f"{PermissionPolicy.MAX_PLANNING_ITERATIONS}"
            )

        # Build minimal plan from goal analysis
        steps = self._infer_steps(request.goal, request.available_tools)

        plan = ReasoningPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            goal=request.goal,
            steps=steps,
            synthesis_call=True,
            total_timeout_seconds=120.0,
        )

        # Validate
        validation = self.validate(plan)
        if not validation.valid:
            # Trim to valid subset
            plan.steps = plan.steps[: PermissionPolicy.MAX_PLAN_STEPS]

        return plan

    def _infer_steps(
        self, goal: str, available_tools: list[str]
    ) -> list[ToolStep]:
        """
        Infer tool steps from goal using keyword matching.

        This is deterministic — no LLM involved.
        """
        goal_lower = goal.lower()
        steps: list[ToolStep] = []
        step_counter = 0

        def _next_step_id() -> str:
            nonlocal step_counter
            step_counter += 1
            return f"step-{step_counter}"

        # Market data gathering
        if any(
            kw in goal_lower
            for kw in ["price", "market", "stock", "ohlcv", "ticker"]
        ):
            if "market.get_ohlcv" in available_tools:
                steps.append(
                    ToolStep(
                        step_id=_next_step_id(),
                        tool_name="market.get_ohlcv",
                        parameters={"symbol": "AUTO", "period": "3mo"},
                        description="Retrieve OHLCV market data",
                    )
                )

        # Technical analysis
        if any(
            kw in goal_lower
            for kw in ["analysis", "indicator", "rsi", "macd", "bollinger", "technical"]
        ):
            if "market.get_analysis" in available_tools:
                steps.append(
                    ToolStep(
                        step_id=_next_step_id(),
                        tool_name="market.get_analysis",
                        parameters={"symbol": "AUTO"},
                        depends_on=[s.step_id for s in steps[:1]] if steps else [],
                        description="Run deterministic technical analysis",
                    )
                )

        # Geo imagery
        if any(
            kw in goal_lower
            for kw in ["satellite", "geo", "imagery", "ndvi", "change", "location"]
        ):
            if "geo.search_scenes" in available_tools:
                steps.append(
                    ToolStep(
                        step_id=_next_step_id(),
                        tool_name="geo.search_scenes",
                        parameters={"lat": 0, "lon": 0, "start_date": "AUTO", "end_date": "AUTO"},
                        description="Search available geo imagery",
                    )
                )

        # Research
        if any(
            kw in goal_lower
            for kw in ["research", "paper", "hypothesis", "claim", "evidence", "study"]
        ):
            if "research.search_claims" in available_tools:
                steps.append(
                    ToolStep(
                        step_id=_next_step_id(),
                        tool_name="research.search_claims",
                        parameters={"query": "AUTO"},
                        description="Search extracted research claims",
                    )
                )

        # If no steps inferred, create a minimal generic step
        if not steps and available_tools:
            first_tool = available_tools[0]
            steps.append(
                ToolStep(
                    step_id=_next_step_id(),
                    tool_name=first_tool,
                    parameters={},
                    description=f"Execute {first_tool} for goal",
                )
            )

        return steps[: PermissionPolicy.MAX_PLAN_STEPS]

    def validate(self, plan: ReasoningPlan) -> PlanValidation:
        """Validate a plan against all constraints."""
        violations = []
        suggestions = []

        # Step count limit
        if len(plan.steps) > PermissionPolicy.MAX_PLAN_STEPS:
            violations.append(
                f"Plan has {len(plan.steps)} steps, max is {PermissionPolicy.MAX_PLAN_STEPS}"
            )

        # Check tool existence
        for step in plan.steps:
            if step.tool_name not in self._tool_names:
                violations.append(f"Step '{step.step_id}' uses unknown tool '{step.tool_name}'")

        # Check dependency validity
        step_ids = {s.step_id for s in plan.steps}
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    violations.append(
                        f"Step '{step.step_id}' depends on unknown step '{dep}'"
                    )

        # Check circular dependencies
        if self._has_cycle(plan.steps):
            violations.append("Plan contains circular dependency")

        # Check timeout
        total_tool_timeout = sum(s.timeout_seconds for s in plan.steps)
        if total_tool_timeout > plan.total_timeout_seconds:
            suggestions.append(
                f"Tool timeouts ({total_tool_timeout:.0f}s) exceed plan timeout "
                f"({plan.total_timeout_seconds:.0f}s)"
            )

        return PlanValidation(
            valid=len(violations) == 0,
            violations=violations,
            suggestions=suggestions,
        )

    @staticmethod
    def _has_cycle(steps: list[ToolStep]) -> bool:
        """Detect circular dependencies using DFS."""
        graph: dict[str, list[str]] = {s.step_id: s.depends_on for s in steps}
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for neighbor in graph.get(node, []):
                if dfs(neighbor):
                    return True
            in_stack.remove(node)
            return False

        return any(dfs(sid) for sid in graph if sid not in visited)
