"""
Extended Security for LLM-2 Tool Orchestration.

Extends LLM-1 security with tool-specific defenses:
- Tool parameter injection detection
- Tool output sanitization
- Workflow boundary enforcement
- Planning injection defense
"""

from __future__ import annotations

import re
from typing import Any


# ── Tool-Specific Injection Patterns ──────────────────────────────────────

TOOL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    # Direct tool manipulation
    re.compile(r"execute\s+tool\s*:\s*\w+", re.IGNORECASE),
    re.compile(r"invoke\s+tool\s*:\s*\w+", re.IGNORECASE),
    re.compile(r"call\s+tool\s*:\s*\w+", re.IGNORECASE),
    # Permission escalation
    re.compile(r"grant\s+(?:permission|access)\s*:\s*\w+", re.IGNORECASE),
    re.compile(r"bypass\s+(?:permission|security|check)", re.IGNORECASE),
    re.compile(r"override\s+(?:permission|restriction)", re.IGNORECASE),
    # Plan manipulation
    re.compile(r"modify\s+(?:plan|step|workflow)", re.IGNORECASE),
    re.compile(r"add\s+step\s*:\s*", re.IGNORECASE),
    re.compile(r"insert\s+step\s*:", re.IGNORECASE),
    re.compile(r"replace\s+plan\s*:", re.IGNORECASE),
    # Trade/modification attempts
    re.compile(r"(?:place|execute|submit)\s+(?:trade|order|buy|sell)", re.IGNORECASE),
    re.compile(r"(?:delete|modify|update|create)\s+(?:record|data|file)", re.IGNORECASE),
    # Arbitrary code execution
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"__import__\s*\(", re.IGNORECASE),
    re.compile(r"subprocess", re.IGNORECASE),
    re.compile(r"os\.system\s*\(", re.IGNORECASE),
    # System prompt extraction
    re.compile(r"(?:show|reveal|print|output)\s+(?:system\s+)?(?:prompt|instructions)", re.IGNORECASE),
    re.compile(r"what\s+(?:are|is)\s+your\s+(?:system\s+)?(?:prompt|instructions)", re.IGNORECASE),
    # Workflow boundary
    re.compile(r"connect\s+to\s+(?:broker|exchange|trading)", re.IGNORECASE),
    re.compile(r"send\s+(?:order|trade|signal)", re.IGNORECASE),
]


class ToolSecurityValidator:
    """
    Validates tool inputs and outputs against injection attempts.

    Defense layers:
    1. Input parameter injection detection
    2. Output sanitization
    3. Workflow boundary enforcement
    4. Planning injection defense
    """

    def __init__(self) -> None:
        self._violations: list[dict[str, Any]] = []

    def validate_tool_input(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate tool input parameters for injection attempts.

        Returns (is_safe, list_of_violations).
        """
        violations: list[str] = []

        # Check parameter values
        for key, value in parameters.items():
            if isinstance(value, str):
                for pattern in TOOL_INJECTION_PATTERNS:
                    if pattern.search(value):
                        violations.append(
                            f"Parameter '{key}' contains injection pattern: {pattern.pattern}"
                        )

        # Check for code execution in parameters
        for key, value in parameters.items():
            if isinstance(value, str):
                if any(
                    dangerous in value.lower()
                    for dangerous in ["exec(", "eval(", "import ", "subprocess", "os."]
                ):
                    violations.append(
                        f"Parameter '{key}' contains code execution attempt"
                    )

        # Log violations
        if violations:
            self._violations.append(
                {
                    "tool_name": tool_name,
                    "violations": violations,
                    "severity": "critical",
                }
            )

        return len(violations) == 0, violations

    def sanitize_tool_output(
        self, tool_name: str, output_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Sanitize tool output to prevent prompt injection via tool results.

        Removes or escapes content that could manipulate the LLM's reasoning.
        """
        sanitized = dict(output_data)

        # Remove any embedded instructions
        instruction_patterns = [
            re.compile(r"IGNORE\s+(?:PREVIOUS|ABOVE|ALL)\s+INSTRUCTIONS?", re.IGNORECASE),
            re.compile(r"DISREGARD\s+(?:PREVIOUS|ABOVE|ALL)", re.IGNORECASE),
            re.compile(r"YOU\s+ARE\s+NOW\s+A", re.IGNORECASE),
            re.compile(r"ACT\s+AS\s+IF", re.IGNORECASE),
        ]

        for key, value in sanitized.items():
            if isinstance(value, str):
                for pattern in instruction_patterns:
                    if pattern.search(value):
                        sanitized[key] = pattern.sub("[SANITIZED]", value)

        return sanitized

    def validate_plan_step(
        self, tool_name: str, parameters: dict[str, Any], allowed_tools: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Validate a plan step against allowed tools and constraints.
        """
        violations: list[str] = []

        # Check tool is allowed
        if tool_name not in allowed_tools:
            violations.append(f"Tool '{tool_name}' is not in allowed tools list")

        # Check for tool chaining that could bypass permissions
        if "depends_on" in parameters:
            deps = parameters["depends_on"]
            if isinstance(deps, list) and len(deps) > 3:
                violations.append("Excessive dependency chain detected")

        return len(violations) == 0, violations

    @property
    def violations(self) -> list[dict[str, Any]]:
        """Immutable access to violation log."""
        return list(self._violations)

    def summary(self) -> str:
        """Human-readable security summary."""
        if not self._violations:
            return "No security violations detected"
        lines = [f"Security violations: {len(self._violations)}"]
        for v in self._violations:
            lines.append(f"  [{v['severity']}] {v['tool_name']}: {len(v['violations'])} violations")
        return "\n".join(lines)
