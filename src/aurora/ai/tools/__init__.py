"""
LLM-2: Grounded Intelligence & Controlled Tool Orchestration
============================================================

Provides a bounded, permission-controlled tool registry with evidence-grounded
reasoning. All tools are deterministic and auditable. No LLM makes decisions —
only structures synthesis.
"""

from aurora.ai.tools.base import (
    AITool,
    ToolPermission,
    ToolResult,
    ToolRegistry,
    ToolStep,
    ToolSafetyLog,
)
from aurora.ai.tools.market import MARKET_TOOLS
from aurora.ai.tools.geo import GEO_TOOLS
from aurora.ai.tools.research import RESEARCH_TOOLS
from aurora.ai.tools.permissions import PermissionPolicy

__all__ = [
    "GEO_TOOLS",
    "MARKET_TOOLS",
    "RESEARCH_TOOLS",
    "AITool",
    "PermissionPolicy",
    "ToolPermission",
    "ToolRegistry",
    "ToolResult",
    "ToolSafetyLog",
    "ToolStep",
]
