"""AURORA Terminal — aggregation API.

Thin orchestration layer that composes existing backend services.
No duplicate logic. Every datum preserves source/provenance.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("aurora.terminal.api")

router = APIRouter()

_start_time = time.time()


# ── Provider Status ──────────────────────────────────────────────────────────


def _check_provider(name: str, url: str, timeout: float = 3.0) -> dict[str, Any]:
    """Check a provider endpoint and return status dict."""
    import urllib.request
    import urllib.error
    import json

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            return {
                "name": name,
                "status": "connected",
                "detail": data.get("status", "ok"),
            }
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        return {
            "name": name,
            "status": "unavailable",
            "detail": str(exc)[:100],
        }


@router.get("/api/v1/terminal/status")
def terminal_status() -> dict[str, Any]:
    """Global system status for all AURORA subsystems.

    Returns real status from each provider. No fabrication.
    """
    base = os.environ.get("AURORA_INTERNAL_BASE", "http://127.0.0.1:8000")

    providers = []

    # AI / Reasoning provider
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/api/v1/reason/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            providers.append({
                "category": "AI",
                "name": data.get("default_provider", "unknown"),
                "detail": "REMOTE API" if data.get("real_provider_configured") else "STUB",
                "status": "ready" if data.get("status") == "healthy" else "degraded",
                "gpu_required": False,
            })
    except Exception:
        providers.append({
            "category": "AI",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    # Compute provider
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/api/v1/compute/status", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            providers.append({
                "category": "COMPUTE",
                "name": data.get("provider", "unknown"),
                "detail": data.get("runtime", "unknown"),
                "status": "ready" if data.get("enabled") else "offline",
                "gpu_required": data.get("gpu_required", False),
            })
    except Exception:
        providers.append({
            "category": "COMPUTE",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    # Market provider
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            market_status = data.get("status", "unknown")
            providers.append({
                "category": "MARKET",
                "name": data.get("provider", "unknown"),
                "detail": "LIVE" if market_status == "healthy" else "DEGRADED",
                "status": "ready" if market_status == "healthy" else "degraded",
                "gpu_required": False,
            })
    except Exception:
        providers.append({
            "category": "MARKET",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    # Geo provider
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/api/v1/geo/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            providers.append({
                "category": "GEO",
                "name": "geo-observatory",
                "detail": data.get("status", "unknown").upper(),
                "status": "ready" if data.get("status") == "healthy" else "degraded",
                "gpu_required": False,
            })
    except Exception:
        providers.append({
            "category": "GEO",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    # News — real provider status from data fabric
    try:
        from aurora.data.registry import get_registry
        reg = get_registry()
        news_status = reg.news.status()
        providers.append({
            "category": "NEWS",
            "name": news_status.name,
            "detail": news_status.state.value,
            "status": "ready" if news_status.state.value == "READY" else
                       "degraded" if news_status.state.value == "DEGRADED" else "unavailable",
            "gpu_required": False,
        })
    except Exception:
        providers.append({
            "category": "NEWS",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    # Macro — real provider status from data fabric
    try:
        from aurora.data.registry import get_registry
        reg = get_registry()
        macro_status = reg.macro.status()
        providers.append({
            "category": "MACRO",
            "name": macro_status.name,
            "detail": macro_status.state.value,
            "status": "ready" if macro_status.state.value == "READY" else
                       "degraded" if macro_status.state.value == "DEGRADED" else "unavailable",
            "gpu_required": False,
        })
    except Exception:
        providers.append({
            "category": "MACRO",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    # Research — real provider status from data fabric
    try:
        from aurora.data.registry import get_registry
        reg = get_registry()
        research_status = reg.research.status()
        providers.append({
            "category": "RESEARCH",
            "name": research_status.name,
            "detail": research_status.state.value,
            "status": "ready" if research_status.state.value == "READY" else
                       "degraded" if research_status.state.value == "DEGRADED" else "unavailable",
            "gpu_required": False,
        })
    except Exception:
        providers.append({
            "category": "RESEARCH",
            "name": "unavailable",
            "detail": "UNAVAILABLE",
            "status": "unavailable",
            "gpu_required": False,
        })

    return {
        "status": "ok",
        "uptime_seconds": time.time() - _start_time,
        "providers": providers,
    }


# ── Terminal Overview ─────────────────────────────────────────────────────────


@router.get("/api/v1/terminal/overview")
def terminal_overview() -> dict[str, Any]:
    """Aggregated overview of all AURORA subsystems.

    Composes data from existing services. No duplicate logic.
    """
    base = os.environ.get("AURORA_INTERNAL_BASE", "http://127.0.0.1:8000")
    overview: dict[str, Any] = {
        "timestamp": time.time(),
        "modules": {},
    }

    # Reasoning summary
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/api/v1/reason/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            overview["modules"]["reasoning"] = {
                "status": data.get("status"),
                "provider": data.get("default_provider"),
                "tools": data.get("llm2_tools", 0),
                "evidence_nodes": data.get("evidence_nodes", 0),
            }
    except Exception:
        overview["modules"]["reasoning"] = {"status": "unavailable"}

    # Investigation summary
    try:
        import urllib.request
        import json

        req = urllib.request.Request(
            f"{base}/api/v1/investigations?limit=10", method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("investigations", [])
            overview["modules"]["investigations"] = {
                "status": "ok",
                "count": len(items),
                "active": sum(1 for i in items if i.get("status") == "in_progress"),
            }
    except Exception:
        overview["modules"]["investigations"] = {"status": "unavailable"}

    # Memory summary
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/api/v1/memory/stats", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            overview["modules"]["memory"] = {
                "status": "ok",
                "total_records": data.get("total_records", 0),
            }
    except Exception:
        overview["modules"]["memory"] = {"status": "unavailable"}

    # Synthesis summary
    try:
        import urllib.request
        import json

        req = urllib.request.Request(
            f"{base}/api/v1/synthesis/health", method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            overview["modules"]["synthesis"] = {
                "status": data.get("status", "unknown"),
            }
    except Exception:
        overview["modules"]["synthesis"] = {"status": "unavailable"}

    # Compute summary
    try:
        import urllib.request
        import json

        req = urllib.request.Request(f"{base}/api/v1/compute/status", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            overview["modules"]["compute"] = {
                "status": "ok" if data.get("enabled") else "offline",
                "provider": data.get("provider"),
                "mode": data.get("mode"),
            }
    except Exception:
        overview["modules"]["compute"] = {"status": "unavailable"}

    return overview


# ── Command Router ────────────────────────────────────────────────────────────

# Allowlisted command registry — no arbitrary execution
COMMAND_REGISTRY: dict[str, dict[str, Any]] = {
    "OPEN_MARKET": {"target": "/market", "description": "Open Market Observatory"},
    "OPEN_GEO": {"target": "/geo", "description": "Open Geo Observatory"},
    "OPEN_INTELLIGENCE": {"target": "/intelligence", "description": "Open Intelligence"},
    "OPEN_INVESTIGATIONS": {"target": "/investigations", "description": "Open Investigations"},
    "OPEN_SYNTHESIS": {"target": "/synthesis", "description": "Open Synthesis"},
    "OPEN_EVIDENCE": {"target": "/evidence", "description": "Open Evidence"},
    "OPEN_MEMORY": {"target": "/memory", "description": "Open Memory"},
    "OPEN_COMPUTE": {"target": "/compute", "description": "Open Compute Fabric"},
    "OPEN_REPORTS": {"target": "/reports", "description": "Open Reports"},
    "OPEN_NEURAL": {"target": "/neural", "description": "Open Neural Field"},
    "OPEN_RESEARCH": {"target": "/research", "description": "Open Research"},
    "OPEN_INDICATORS": {"target": "/indicators", "description": "Open Indicators"},
    "OPEN_SETTINGS": {"target": "/settings", "description": "Open Settings"},
    "OPEN_COMMAND_CENTER": {"target": "/", "description": "Open Command Center"},
}


@router.post("/api/v1/terminal/command")
def execute_command(body: dict[str, Any]) -> dict[str, Any]:
    """Route a terminal command to the appropriate module.

    Commands are allowlisted. No arbitrary execution.
    Returns navigation target or error.
    """
    raw_cmd = (body.get("command") or "").strip().upper()

    if not raw_cmd:
        return {"status": "error", "error": "Empty command"}

    # Direct command match
    if raw_cmd in COMMAND_REGISTRY:
        cmd = COMMAND_REGISTRY[raw_cmd]
        return {
            "status": "ok",
            "action": "navigate",
            "target": cmd["target"],
            "description": cmd["description"],
        }

    # Fuzzy match — check if any registered command contains the input
    matches = []
    for key, cmd in COMMAND_REGISTRY.items():
        if raw_cmd in key or key in raw_cmd:
            matches.append({"command": key, **cmd})

    if len(matches) == 1:
        return {
            "status": "ok",
            "action": "navigate",
            "target": matches[0]["target"],
            "description": matches[0]["description"],
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "action": "suggest",
            "matches": matches,
        }

    # Unrecognized command
    return {
        "status": "error",
        "error": f"Unknown command: {raw_cmd}",
        "hint": "Available commands: " + ", ".join(sorted(COMMAND_REGISTRY.keys())),
    }
