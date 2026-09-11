"""AURORA Terminal — Backend Tests.

Tests for terminal overview, status, command routing, and security.
"""

import pytest
from fastapi.testclient import TestClient

from aurora.terminal.api import router, COMMAND_REGISTRY


@pytest.fixture
def client():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ── Terminal Status ──────────────────────────────────────────────────────────


class TestTerminalStatus:
    def test_status_returns_ok(self, client):
        response = client.get("/api/v1/terminal/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert "providers" in data

    def test_status_has_all_required_categories(self, client):
        response = client.get("/api/v1/terminal/status")
        data = response.json()
        categories = [p["category"] for p in data["providers"]]
        assert "AI" in categories
        assert "COMPUTE" in categories
        assert "MARKET" in categories
        assert "GEO" in categories
        assert "NEWS" in categories
        assert "MACRO" in categories

    def test_status_provider_fields(self, client):
        response = client.get("/api/v1/terminal/status")
        data = response.json()
        for provider in data["providers"]:
            assert "category" in provider
            assert "name" in provider
            assert "detail" in provider
            assert "status" in provider
            assert "gpu_required" in provider

    def test_status_news_unavailable(self, client):
        response = client.get("/api/v1/terminal/status")
        data = response.json()
        news = [p for p in data["providers"] if p["category"] == "NEWS"]
        assert len(news) == 1
        assert news[0]["status"] == "unavailable"
        assert news[0]["detail"] == "DATA_UNAVAILABLE"

    def test_status_macro_unavailable(self, client):
        response = client.get("/api/v1/terminal/status")
        data = response.json()
        macro = [p for p in data["providers"] if p["category"] == "MACRO"]
        assert len(macro) == 1
        assert macro[0]["status"] == "unavailable"
        assert macro[0]["detail"] == "DATA_UNAVAILABLE"


# ── Terminal Overview ─────────────────────────────────────────────────────────


class TestTerminalOverview:
    def test_overview_returns_ok(self, client):
        response = client.get("/api/v1/terminal/overview")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "modules" in data

    def test_overview_has_modules(self, client):
        response = client.get("/api/v1/terminal/overview")
        data = response.json()
        modules = data["modules"]
        assert isinstance(modules, dict)


# ── Command Router ───────────────────────────────────────────────────────────


class TestCommandRouter:
    def test_empty_command_returns_error(self, client):
        response = client.post("/api/v1/terminal/command", json={"command": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Empty command" in data["error"]

    def test_direct_command_match(self, client):
        response = client.post("/api/v1/terminal/command", json={"command": "OPEN_MARKET"})
        data = response.json()
        assert data["status"] == "ok"
        assert data["action"] == "navigate"
        assert data["target"] == "/market"

    def test_direct_command_case_insensitive(self, client):
        response = client.post("/api/v1/terminal/command", json={"command": "open_market"})
        data = response.json()
        assert data["status"] == "ok"
        assert data["target"] == "/market"

    def test_fuzzy_match_single(self, client):
        response = client.post("/api/v1/terminal/command", json={"command": "market"})
        data = response.json()
        assert data["status"] == "ok"
        assert data["target"] == "/market"

    def test_unrecognized_command(self, client):
        response = client.post("/api/v1/terminal/command", json={"command": "DO_SOMETHING_RANDOM"})
        data = response.json()
        assert data["status"] == "error"
        assert "Unknown command" in data["error"]
        assert "hint" in data

    def test_all_commands_navigate(self, client):
        for cmd_key in COMMAND_REGISTRY:
            response = client.post("/api/v1/terminal/command", json={"command": cmd_key})
            data = response.json()
            assert data["status"] == "ok", f"Command {cmd_key} should succeed"
            assert data["action"] == "navigate"
            assert data["target"].startswith("/")

    def test_missing_command_field(self, client):
        response = client.post("/api/v1/terminal/command", json={})
        data = response.json()
        assert data["status"] == "error"
        assert "Empty command" in data["error"]

    def test_no_arbitrary_code_execution(self, client):
        dangerous_commands = [
            "rm -rf /",
            "import os; os.system('ls')",
            "__import__('subprocess').call(['ls'])",
            "eval('print(1)')",
            "exec('import os')",
        ]
        for cmd in dangerous_commands:
            response = client.post("/api/v1/terminal/command", json={"command": cmd})
            data = response.json()
            assert data["status"] == "error", f"Dangerous command '{cmd}' should be rejected"


# ── Command Registry Security ────────────────────────────────────────────────


class TestCommandRegistrySecurity:
    def test_registry_is_allowlisted(self):
        allowed_commands = {
            "OPEN_MARKET",
            "OPEN_GEO",
            "OPEN_INTELLIGENCE",
            "OPEN_INVESTIGATIONS",
            "OPEN_SYNTHESIS",
            "OPEN_EVIDENCE",
            "OPEN_MEMORY",
            "OPEN_COMPUTE",
            "OPEN_REPORTS",
            "OPEN_NEURAL",
            "OPEN_RESEARCH",
            "OPEN_INDICATORS",
            "OPEN_SETTINGS",
            "OPEN_COMMAND_CENTER",
        }
        assert set(COMMAND_REGISTRY.keys()) == allowed_commands

    def test_all_targets_are_internal_routes(self):
        for cmd, info in COMMAND_REGISTRY.items():
            assert info["target"].startswith("/"), f"{cmd} target must start with /"
            assert "http" not in info["target"], f"{cmd} target must not contain http"
            assert ".." not in info["target"], f"{cmd} target must not contain path traversal"

    def test_no_shell_commands_in_registry(self):
        for cmd, info in COMMAND_REGISTRY.items():
            assert "shell" not in info["description"].lower()
            assert "exec" not in info["description"].lower()
            assert "run" not in info["description"].lower()


# ── Provenance ───────────────────────────────────────────────────────────────


class TestProvenance:
    def test_status_preserves_source(self, client):
        response = client.get("/api/v1/terminal/status")
        data = response.json()
        for provider in data["providers"]:
            assert "category" in provider
            assert "name" in provider
            assert "status" in provider

    def test_overview_preserves_timestamp(self, client):
        response = client.get("/api/v1/terminal/overview")
        data = response.json()
        assert isinstance(data["timestamp"], float)
        assert data["timestamp"] > 0
