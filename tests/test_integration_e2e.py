"""
Phase 12: LLM Stack Integration Tests

Tests the complete chain:
  USER REQUEST -> REASONING CORE -> CONTEXT BUILDER -> MEMORY RETRIEVAL ->
  TASK ROUTING -> BOUNDED TOOL PLANNING -> EVIDENCE COLLECTION ->
  EVIDENCE GRAPH -> INVESTIGATION ENGINE -> COMPARISON / SUFFICIENCY ->
  SYNTHESIS -> FINDINGS / RESULT -> MEMORY UPDATE -> AUDIT TRAIL

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Shared TestClient for the full application."""
    from aurora.market.api import app
    return TestClient(app, raise_server_exceptions=False)


# ============================================================
# Health & Reasoning Endpoints
# ============================================================


class TestReasoningChain:
    def test_reason_health(self, client):
        resp = client.get("/api/v1/reason/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "aurora-reasoning"
        assert "providers" in data

    def test_reason_endpoint(self, client):
        resp = client.post("/api/v1/reason", json={
            "query": "What is the current state of BTC?",
            "domain": "market",
            "task": "GENERAL_RESEARCH",
            "evidence": [
                {"claim": "BTC is trading above 50000", "source": "test", "confidence": 0.8},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("COMPLETED", "ABSTAINED")
        assert "answer" in data
        assert "context_hash" in data
        assert "grounding_score" in data

    def test_reason_abstains_without_evidence(self, client):
        resp = client.post("/api/v1/reason", json={
            "query": "Will BTC hit 100k tomorrow?",
            "domain": "market",
            "task": "GENERAL_RESEARCH",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ABSTAINED"
        assert data["abstention_reason"] is not None

    def test_reason_rejects_future_prediction(self, client):
        resp = client.post("/api/v1/reason", json={
            "query": "Predict BTC price next week",
            "domain": "market",
            "task": "GENERAL_RESEARCH",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ABSTAINED"


# ============================================================
# Tool Registry (LLM-2)
# ============================================================


class TestToolRegistry:
    def test_list_tools(self, client):
        resp = client.get("/api/v1/reason/tools")
        assert resp.status_code == 200
        data = resp.json()
        tools = data["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "market.get_ohlcv" in tool_names

    def test_tools_have_permissions(self, client):
        resp = client.get("/api/v1/reason/tools")
        data = resp.json()
        for tool in data["tools"]:
            assert "permissions" in tool
            assert isinstance(tool["permissions"], list)

    def test_evidence_graph_endpoint(self, client):
        resp = client.get("/api/v1/reason/evidence-graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data

    def test_safety_log_endpoint(self, client):
        resp = client.get("/api/v1/reason/safety-log")
        assert resp.status_code == 200
        data = resp.json()
        assert "log" in data
        assert "total_entries" in data


# ============================================================
# Tool-Orchestrated Reasoning (LLM-2)
# ============================================================


class TestToolReasoning:
    def test_tool_reason_with_query(self, client):
        resp = client.post("/api/v1/reason/tool", json={
            "query": "List available market assets",
            "domain": "market",
            "goal": "enumerate assets",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("COMPLETED", "ABSTAINED", "FAILED", "COMPLETE")
        assert "tools_executed" in data
        assert "evidence_refs" in data

    def test_workflow_endpoint(self, client):
        resp = client.post("/api/v1/reason/workflow", json={
            "domain": "market",
            "params": {"asset": "BTC"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("success", "error")


# ============================================================
# Memory System (LLM-3)
# ============================================================


class TestMemoryChain:
    def test_create_memory(self, client):
        resp = client.post("/api/v1/memory", json={
            "memory_type": "EVIDENCE",
            "domain": "market",
            "title": "BTC market observation",
            "content": "BTC traded above 50000 with increased volume",
            "source": "integration_test",
            "confidence": 0.75,
            "tags": ["btc", "volume"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["memory_id"] is not None
        assert data["memory_type"] == "EVIDENCE"

    def test_get_memory(self, client):
        resp = client.post("/api/v1/memory", json={
            "memory_type": "EPISODIC",
            "domain": "market",
            "title": "BTC test get",
            "content": "Test getting a memory record",
            "source": "integration_test",
        })
        mid = resp.json()["memory_id"]
        resp = client.get(f"/api/v1/memory/{mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["memory_id"] == mid

    def test_search_memory(self, client):
        resp = client.get("/api/v1/memory/search", params={"query": "BTC"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_memory_stats(self, client):
        resp = client.get("/api/v1/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert data["total"] > 0

    def test_memory_retrieve(self, client):
        resp = client.post("/api/v1/memory/retrieve", json={
            "query": "BTC market data",
            "domain": "market",
            "top_k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_memory_link(self, client):
        mid1 = client.post("/api/v1/memory", json={
            "memory_type": "EVIDENCE",
            "domain": "market",
            "title": "Link test source",
            "content": "Source memory for link test",
            "source": "integration_test",
        }).json()["memory_id"]
        mid2 = client.post("/api/v1/memory", json={
            "memory_type": "EVIDENCE",
            "domain": "market",
            "title": "Link test target",
            "content": "Target memory for link test",
            "source": "integration_test",
        }).json()["memory_id"]
        resp = client.post(f"/api/v1/memory/{mid1}/link", json={
            "target_id": mid2,
            "relationship": "SUPPORTS",
            "description": "test link",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "linked"

    def test_memory_export(self, client):
        resp = client.post("/api/v1/memory/export")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert "versions" in data
        assert "conflicts" in data
        assert "exported_at" in data


# ============================================================
# Investigation Engine (LLM-4)
# ============================================================


class TestInvestigationChain:
    def _create(self, client, query: str = "Analyze BTC market structure") -> str:
        resp = client.post("/api/v1/investigations", json={
            "query": query,
            "domain": "market",
            "subject": "BTC",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "investigation_id" in data
        return data["investigation_id"]

    def test_create_investigation(self, client):
        iid = self._create(client)
        assert iid is not None

    def test_list_investigations(self, client):
        resp = client.get("/api/v1/investigations")
        assert resp.status_code == 200
        data = resp.json()
        assert "investigations" in data
        assert "total" in data

    def test_get_investigation(self, client):
        iid = self._create(client)
        resp = client.get(f"/api/v1/investigations/{iid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["investigation_id"] == iid

    def test_start_investigation(self, client):
        iid = self._create(client)
        resp = client.post(f"/api/v1/investigations/{iid}/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("INVESTIGATING", "COMPLETE", "PARTIAL", "ABSTAINED", "FAILED")

    def test_cancel_investigation(self, client):
        iid = self._create(client)
        resp = client.post(f"/api/v1/investigations/{iid}/cancel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CANCELLED"

    def test_events_audit_trail(self, client):
        iid = self._create(client)
        client.post(f"/api/v1/investigations/{iid}/start")
        resp = client.get(f"/api/v1/investigations/{iid}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert len(data["events"]) > 0
        for evt in data["events"]:
            assert "event_type" in evt
            assert "timestamp" in evt
            assert "summary" in evt

    def test_findings_endpoint(self, client):
        iid = self._create(client)
        client.post(f"/api/v1/investigations/{iid}/start")
        resp = client.get(f"/api/v1/investigations/{iid}/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data

    def test_result_endpoint(self, client):
        iid = self._create(client)
        client.post(f"/api/v1/investigations/{iid}/start")
        resp = client.get(f"/api/v1/investigations/{iid}/result")
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data

    def test_idempotency(self, client):
        key = "idempotency_test_key_001"
        resp1 = client.post("/api/v1/investigations", json={
            "query": "Idempotency check",
            "domain": "general",
            "idempotency_key": key,
        })
        assert resp1.status_code == 200
        resp2 = client.post("/api/v1/investigations", json={
            "query": "Idempotency check",
            "domain": "general",
            "idempotency_key": key,
        })
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert "error" in data2

    def test_reopen_completed_investigation(self, client):
        iid = self._create(client)
        client.post(f"/api/v1/investigations/{iid}/start")
        get_resp = client.get(f"/api/v1/investigations/{iid}")
        status = get_resp.json()["status"]
        if status in ("COMPLETE", "PARTIAL", "ABSTAINED", "FAILED"):
            resp = client.post(f"/api/v1/investigations/{iid}/reopen")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "INVESTIGATING"

    def test_reopen_cancelled_rejected(self, client):
        iid = self._create(client)
        client.post(f"/api/v1/investigations/{iid}/cancel")
        resp = client.post(f"/api/v1/investigations/{iid}/reopen")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


# ============================================================
# Cross-Module: Investigation -> Memory
# ============================================================


class TestInvestigationMemoryIntegration:
    def test_investigation_creates_memory_entries(self, client):
        stats_before = client.get("/api/v1/memory/stats").json()
        iid = client.post("/api/v1/investigations", json={
            "query": "Memory integration test",
            "domain": "general",
        }).json()["investigation_id"]
        client.post(f"/api/v1/investigations/{iid}/start")
        stats_after = client.get("/api/v1/memory/stats").json()
        assert stats_after["total"] >= stats_before["total"]


# ============================================================
# Bounded Execution Limits
# ============================================================


class TestBoundedExecution:
    def test_investigation_completes_within_time(self, client):
        start = time.time()
        iid = client.post("/api/v1/investigations", json={
            "query": "Quick analysis",
            "domain": "general",
        }).json()["investigation_id"]
        client.post(f"/api/v1/investigations/{iid}/start")
        elapsed = time.time() - start
        assert elapsed < 30.0, f"Investigation took {elapsed:.1f}s, should be under 30s"

    def test_evidence_sufficiency_states(self, client):
        iid = client.post("/api/v1/investigations", json={
            "query": "Check sufficiency",
            "domain": "general",
        }).json()["investigation_id"]
        resp = client.post(f"/api/v1/investigations/{iid}/start")
        data = resp.json()
        valid_statuses = {
            "DRAFT", "PLANNING", "MEMORY_RETRIEVAL", "GAP_ANALYSIS",
            "INVESTIGATING", "ANALYZING", "COMPARING", "SUFFICIENCY_CHECK",
            "VALIDATING", "SYNTHESIZING", "COMPLETE", "PARTIAL",
            "ABSTAINED", "FAILED", "CANCELLED",
        }
        assert data["status"] in valid_statuses


# ============================================================
# Geo Endpoints
# ============================================================


class TestGeoEndpoints:
    def test_health(self, client):
        resp = client.get("/api/v1/geo/health")
        assert resp.status_code == 200

    def test_assets(self, client):
        resp = client.get("/api/v1/geo/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert "assets" in data


# ============================================================
# Market Endpoints
# ============================================================


class TestMarketEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_assets(self, client):
        resp = client.get("/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert "assets" in data
        assert len(data["assets"]) > 0
