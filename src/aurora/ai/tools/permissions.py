"""
Permission policy for LLM-2 tool orchestration.

Defines which tools are allowed and which are explicitly denied.
No tool may trade, modify data, delete records, or execute arbitrary code.
"""

from __future__ import annotations

from aurora.ai.tools.base import ToolPermission


class PermissionPolicy:
    """
    Immutable permission policy.

    READ_* tools are allowed for evidence gathering.
    RUN_DETERMINISTIC_ANALYSIS is allowed for computational analysis.
    All mutation/external-side-effect permissions are DENIED.
    """

    # Tools the LLM can invoke
    ALLOWED: frozenset[ToolPermission] = frozenset(
        {
            ToolPermission.READ_MARKET,
            ToolPermission.READ_GEO,
            ToolPermission.READ_RESEARCH,
            ToolPermission.RUN_DETERMINISTIC_ANALYSIS,
            ToolPermission.WRITE_INVESTIGATION,
            ToolPermission.EXPORT_DATA,
        }
    )

    # Explicitly denied — never granted regardless of context
    DENIED: frozenset[ToolPermission] = frozenset(
        {
            ToolPermission.TRADE,
            ToolPermission.MODIFY,
            ToolPermission.DELETE,
            ToolPermission.ARBITRARY_CODE,
            ToolPermission.NETWORK_EXTERNAL,
            ToolPermission.WRITE_RESEARCH,
        }
    )

    # Maximum tools that can be called per reasoning turn
    MAX_TOOLS_PER_TURN: int = 8

    # Maximum planning iterations
    MAX_PLANNING_ITERATIONS: int = 2

    # Maximum steps in a single plan
    MAX_PLAN_STEPS: int = 8

    # Maximum synthesis calls per reasoning turn
    MAX_SYNTHESIS_CALLS: int = 1

    # Maximum total tool calls per session (guard against runaway)
    MAX_TOTAL_TOOL_CALLS: int = 50

    @classmethod
    def can_use(cls, permission: ToolPermission) -> bool:
        """Check if a permission is allowed."""
        if permission in cls.DENIED:
            return False
        return permission in cls.ALLOWED

    @classmethod
    def validate_permissions(
        cls, permissions: list[ToolPermission]
    ) -> tuple[bool, list[str]]:
        """
        Validate that a set of permissions is allowed.

        Returns (is_valid, list_of_violations).
        """
        violations = []
        for perm in permissions:
            if perm in cls.DENIED:
                violations.append(f"DENIED: {perm.value}")
            elif perm not in cls.ALLOWED:
                violations.append(f"NOT_ALLOWED: {perm.value}")
        return len(violations) == 0, violations
