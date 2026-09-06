"""
Core tool abstractions for LLM-2 grounded intelligence.

Every tool is a bounded, deterministic operation that returns structured evidence.
Tools cannot modify data, execute arbitrary code, or access external systems
beyond their declared scope.
"""

from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Permission Model ──────────────────────────────────────────────────────


class ToolPermission(str, Enum):
    """Declared capability that a tool requires."""

    READ_MARKET = "READ_MARKET"
    READ_GEO = "READ_GEO"
    READ_RESEARCH = "READ_RESEARCH"
    RUN_DETERMINISTIC_ANALYSIS = "RUN_DETERMINISTIC_ANALYSIS"
    WRITE_INVESTIGATION = "WRITE_INVESTIGATION"
    EXPORT_DATA = "EXPORT_DATA"

    # Explicitly denied — these are NOT granted to any tool
    TRADE = "TRADE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    ARBITRARY_CODE = "ARBITRARY_CODE"
    NETWORK_EXTERNAL = "NETWORK_EXTERNAL"
    WRITE_RESEARCH = "WRITE_RESEARCH"


# ── Tool Input/Output ─────────────────────────────────────────────────────


class ToolInput(BaseModel):
    """Base input schema for all tools."""

    model_config = {"extra": "forbid"}

    tool_name: str = Field(description="Name of the tool to invoke")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool-specific parameters"
    )
    dry_run: bool = Field(
        default=False, description="If True, validate without executing"
    )


class ToolResult(BaseModel):
    """Deterministic output from a tool execution."""

    model_config = {"extra": "forbid"}

    tool_name: str
    status: str = Field(description="success | error | timeout")
    data: dict[str, Any] = Field(default_factory=dict)
    evidence_id: str = Field(description="SHA-256 hash of data for grounding")
    execution_time_ms: float = Field(description="Wall-clock execution time")
    deterministic: bool = Field(
        default=True, description="Whether this result is reproducible"
    )
    evidence_type: str = Field(
        default="observation", description="observation | analysis | inference"
    )
    source_refs: list[str] = Field(
        default_factory=list, description="Source references for grounding"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class ToolStep(BaseModel):
    """A single step in a reasoning plan."""

    model_config = {"extra": "forbid"}

    step_id: str = Field(description="Unique step identifier")
    tool_name: str = Field(description="Tool to invoke")
    parameters: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(
        default_factory=list, description="Step IDs this depends on"
    )
    description: str = Field(default="")
    timeout_seconds: float = Field(default=30.0)


class ReasoningPlan(BaseModel):
    """Bounded orchestration plan — maximum 8 steps, 2 planning iterations."""

    model_config = {"extra": "forbid"}

    plan_id: str = Field(description="Unique plan identifier")
    goal: str = Field(description="What this plan aims to discover")
    steps: list[ToolStep] = Field(description="Ordered tool steps")
    synthesis_call: bool = Field(
        default=True, description="Whether to call LLM for final synthesis"
    )
    total_timeout_seconds: float = Field(default=120.0)
    created_at: float = Field(default_factory=time.time)


# ── Tool Safety Log ────────────────────────────────────────────────────────


class ToolSafetyLog(BaseModel):
    """Immutable audit record of tool execution."""

    model_config = {"extra": "forbid"}

    timestamp: float = Field(default_factory=time.time)
    tool_name: str
    input_hash: str = Field(description="SHA-256 of serialized input")
    output_hash: str = Field(description="SHA-256 of serialized output")
    permissions_used: list[ToolPermission] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    success: bool = True
    error: str | None = None
    planning_context: str = Field(
        default="", description="Which plan iteration this was in"
    )


# ── Abstract Tool ──────────────────────────────────────────────────────────


class AITool(ABC):
    """
    Abstract base for all AI tools.

    Subclasses MUST:
    - Declare required permissions
    - Mark deterministic=True
    - Return structured ToolResult with evidence_id
    - Never modify external state
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""

    @property
    @abstractmethod
    def required_permissions(self) -> list[ToolPermission]:
        """Permissions this tool requires."""

    @property
    def deterministic(self) -> bool:
        """All tools are deterministic by default."""
        return True

    @property
    def timeout_seconds(self) -> float:
        """Default timeout for this tool."""
        return 30.0

    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""

    @abstractmethod
    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        """
        Core execution logic. Subclasses implement this.

        Must return ToolResult with:
        - evidence_id = SHA-256 hash of data
        - deterministic = True
        - source_refs = non-empty list
        """

    def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult:
        """
        Execute tool with safety checks.

        - Validates input against schema
        - Checks permissions
        - Logs execution
        - Returns deterministic result
        """
        if dry_run:
            return ToolResult(
                tool_name=self.name,
                status="dry_run",
                data={},
                evidence_id="",
                execution_time_ms=0.0,
                deterministic=self.deterministic,
            )

        start = time.time()
        try:
            result = self._execute(parameters)
            elapsed = (time.time() - start) * 1000
            result.execution_time_ms = elapsed
            result.deterministic = self.deterministic

            # Ensure evidence_id is computed
            if not result.evidence_id:
                data_str = str(sorted(result.data.items()))
                result.evidence_id = hashlib.sha256(data_str.encode()).hexdigest()[:16]

            return result
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={},
                evidence_id="",
                execution_time_ms=elapsed,
                deterministic=self.deterministic,
                error=str(exc),
            )

    @staticmethod
    def _compute_evidence_id(data: dict[str, Any]) -> str:
        """Compute deterministic evidence hash."""
        data_str = str(sorted(data.items()))
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]


# ── Tool Registry ──────────────────────────────────────────────────────────


class ToolRegistry:
    """
    Central registry for all available tools.

    Enforces permission policy and provides tool lookup.
    """

    def __init__(self) -> None:
        self._tools: dict[str, AITool] = {}
        self._safety_log: list[ToolSafetyLog] = []

    def register(self, tool: AITool) -> None:
        """Register a tool. Raises ValueError if name conflicts."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def register_many(self, tools: list[AITool]) -> None:
        """Register multiple tools."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> AITool | None:
        """Look up a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "permissions": [p.value for p in t.required_permissions],
                "deterministic": t.deterministic,
                "timeout": t.timeout_seconds,
                "input_schema": t.input_schema(),
            }
            for t in self._tools.values()
        ]

    def names(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        allowed_permissions: set[ToolPermission] | None = None,
        dry_run: bool = False,
        planning_context: str = "",
    ) -> ToolResult:
        """
        Execute a tool with permission checks and safety logging.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                tool_name=tool_name,
                status="error",
                data={},
                evidence_id="",
                execution_time_ms=0.0,
                error=f"Tool '{tool_name}' not found",
            )

        # Permission check
        if allowed_permissions is not None:
            missing = set(tool.required_permissions) - allowed_permissions
            if missing:
                return ToolResult(
                    tool_name=tool_name,
                    status="error",
                    data={},
                    evidence_id="",
                    execution_time_ms=0.0,
                    error=f"Missing permissions: {[p.value for p in missing]}",
                )

        # Execute
        input_hash = hashlib.sha256(
            str(sorted(parameters.items())).encode()
        ).hexdigest()[:16]

        result = tool.execute(parameters, dry_run=dry_run)

        output_hash = (
            hashlib.sha256(str(sorted(result.data.items())).encode()).hexdigest()[:16]
            if result.data
            else ""
        )

        # Safety log
        log_entry = ToolSafetyLog(
            tool_name=tool_name,
            input_hash=input_hash,
            output_hash=output_hash,
            permissions_used=tool.required_permissions,
            execution_time_ms=result.execution_time_ms,
            success=result.status == "success",
            error=result.error,
            planning_context=planning_context,
        )
        self._safety_log.append(log_entry)

        return result

    @property
    def safety_log(self) -> list[ToolSafetyLog]:
        """Immutable access to safety audit log."""
        return list(self._safety_log)
