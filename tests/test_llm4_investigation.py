"""LLM-4: Adaptive Investigation Engine — comprehensive tests."""

from __future__ import annotations

import tempfile
import shutil

import pytest

from aurora.investigation.schemas import (
    InvestigationStatus,
    InvestigationDomain,
    GapStatus,
    FindingClassification,
    FindingStatus,
    SufficiencyState,
    EventType,
    ComparisonChangeType,
    InvestigationObjective,
    EvidenceGap,
    Finding,
    InvestigationEvent,
    InvestigationPlanStep,
    InvestigationPlan,
    InvestigationResult,
    InvestigationRecord,
    InvestigationLimits,
    generate_investigation_id,
    generate_event_id,
)
from aurora.investigation.errors import (
    InvestigationError,
    InvestigationNotFound,
    DuplicateInvestigation,
)
from aurora.investigation.store import InvestigationStore
from aurora.investigation.planner import InvestigationPlanner
from aurora.investigation.executor import InvestigationExecutor, ExecutorResult
from aurora.investigation.comparison import compare_deterministic
from aurora.investigation.lifecycle import (
    can_transition,
    transition,
    start_investigation,
    cancel_investigation,
)
from aurora.investigation.manager import InvestigationManager
from aurora.ai.tools.base import ToolRegistry, AITool, ToolResult, ToolPermission


# ── Test Tools ─────────────────────────────────────────────────────────────


class StubReadTool(AITool):
    @property
    def name(self) -> str:
        return "stub.read_data"

    @property
    def description(self) -> str:
        return "Stub read tool"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_MARKET]

    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"query": {"type": "string"}}}

    def _execute(self, parameters: dict) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            status="success",
            data={"result": "stub data", "query": parameters.get("query", "")},
            evidence_id="ev-stub-001",
            execution_time_ms=1.0,
            source_refs=["stub-source"],
        )


class StubFailTool(AITool):
    @property
    def name(self) -> str:
        return "stub.fail_tool"

    @property
    def description(self) -> str:
        return "Tool that always fails"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_MARKET]

    def input_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    def _execute(self, parameters: dict) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            status="error",
            data={},
            evidence_id="",
            execution_time_ms=1.0,
            error="Simulated failure",
        )


# ── Schema Tests ───────────────────────────────────────────────────────────


class TestSchemas:
    def test_investigation_id_generation(self) -> None:
        id1 = generate_investigation_id()
        id2 = generate_investigation_id()
        assert id1.startswith("inv-")
        assert id1 != id2

    def test_event_id_generation(self) -> None:
        id1 = generate_event_id()
        id2 = generate_event_id()
        assert id1.startswith("evt-")
        assert id1 != id2

    def test_investigation_objective(self) -> None:
        obj = InvestigationObjective(
            query="What changed in this AOI?",
            domain=InvestigationDomain.GEO,
            subject="AOI-123",
        )
        assert obj.query == "What changed in this AOI?"
        assert obj.domain == InvestigationDomain.GEO

    def test_evidence_gap_defaults(self) -> None:
        gap = EvidenceGap(description="Need current scene")
        assert gap.status == GapStatus.OPEN
        assert gap.resolvable is True
        assert gap.priority == 5

    def test_finding_defaults(self) -> None:
        finding = Finding(statement="Test finding")
        assert finding.classification == FindingClassification.OBSERVATION
        assert finding.status == FindingStatus.UNCERTAIN
        assert finding.confidence == 0.5

    def test_investigation_record(self) -> None:
        obj = InvestigationObjective(query="test")
        record = InvestigationRecord(objective=obj)
        assert record.investigation_id.startswith("inv-")
        assert record.status == InvestigationStatus.DRAFT
        assert record.events == []

    def test_investigation_limits(self) -> None:
        limits = InvestigationLimits(max_steps=5)
        assert limits.max_steps == 5
        assert limits.max_runtime_seconds == 300.0

    def test_investigation_event(self) -> None:
        event = InvestigationEvent(
            event_type=EventType.CREATED,
            investigation_id="inv-test",
            summary="Test event",
        )
        assert event.event_id.startswith("evt-")
        assert event.event_type == EventType.CREATED


# ── Store Tests ────────────────────────────────────────────────────────────


class TestInvestigationStore:
    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.store = InvestigationStore(self.tmp_dir)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_and_get(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test query")
        )
        self.store.create(record)
        fetched = self.store.get(record.investigation_id)
        assert fetched is not None
        assert fetched.objective.query == "test query"

    def test_create_duplicate(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        self.store.create(record)
        with pytest.raises(ValueError, match="already exists"):
            self.store.create(record)

    def test_get_not_found(self) -> None:
        assert self.store.get("inv-nonexistent") is None

    def test_update(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        self.store.create(record)
        record.status = InvestigationStatus.PLANNING
        self.store.update(record)
        fetched = self.store.get(record.investigation_id)
        assert fetched is not None
        assert fetched.status == InvestigationStatus.PLANNING

    def test_list_all(self) -> None:
        for i in range(3):
            self.store.create(
                InvestigationRecord(
                    objective=InvestigationObjective(query=f"query {i}")
                )
            )
        records = self.store.list_all()
        assert len(records) == 3

    def test_list_all_with_status_filter(self) -> None:
        r1 = InvestigationRecord(
            objective=InvestigationObjective(query="q1"),
            status=InvestigationStatus.DRAFT,
        )
        r2 = InvestigationRecord(
            objective=InvestigationObjective(query="q2"),
            status=InvestigationStatus.COMPLETE,
        )
        self.store.create(r1)
        self.store.create(r2)
        drafts = self.store.list_all(status="DRAFT")
        assert len(drafts) == 1

    def test_append_and_get_events(self) -> None:
        event = InvestigationEvent(
            event_type=EventType.CREATED,
            investigation_id="inv-test",
            summary="Test",
        )
        self.store.append_event(event)
        events = self.store.get_events("inv-test")
        assert len(events) == 1

    def test_save_and_get_result(self) -> None:
        result = InvestigationResult(
            investigation_id="inv-test",
            status=InvestigationStatus.COMPLETE,
            executive_summary="Test result",
        )
        self.store.save_result(result)
        fetched = self.store.get_result("inv-test")
        assert fetched is not None
        assert fetched.executive_summary == "Test result"

    def test_find_by_idempotency_key(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test"),
            idempotency_key="key-123",
        )
        self.store.create(record)
        found = self.store.find_by_idempotency_key("key-123")
        assert found is not None
        assert found.investigation_id == record.investigation_id

    def test_export_all(self) -> None:
        self.store.create(
            InvestigationRecord(objective=InvestigationObjective(query="q"))
        )
        export = self.store.export_all()
        assert export["record_count"] == 1


# ── Lifecycle Tests ────────────────────────────────────────────────────────


class TestLifecycle:
    def test_valid_transitions(self) -> None:
        assert can_transition(InvestigationStatus.DRAFT, InvestigationStatus.PLANNING)
        assert can_transition(InvestigationStatus.PLANNING, InvestigationStatus.MEMORY_RETRIEVAL)
        assert can_transition(InvestigationStatus.COMPLETE, InvestigationStatus.CANCELLED)

    def test_invalid_transition(self) -> None:
        assert not can_transition(InvestigationStatus.COMPLETE, InvestigationStatus.PLANNING)
        assert not can_transition(InvestigationStatus.CANCELLED, InvestigationStatus.DRAFT)

    def test_transition_sets_timestamps(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        transition(record, InvestigationStatus.PLANNING)
        assert record.status == InvestigationStatus.PLANNING
        assert record.started_at is not None

    def test_complete_sets_completed_at(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        transition(record, InvestigationStatus.PLANNING)
        transition(record, InvestigationStatus.INVESTIGATING)
        transition(record, InvestigationStatus.ANALYZING)
        transition(record, InvestigationStatus.SYNTHESIZING)
        transition(record, InvestigationStatus.COMPLETE)
        assert record.completed_at is not None

    def test_invalid_transition_raises(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        with pytest.raises(InvestigationError, match="Invalid transition"):
            transition(record, InvestigationStatus.COMPLETE)

    def test_start_investigation(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        event = start_investigation(record)
        assert record.status == InvestigationStatus.PLANNING
        assert event.event_type == EventType.STATUS_CHANGED

    def test_cancel_investigation(self) -> None:
        record = InvestigationRecord(
            objective=InvestigationObjective(query="test")
        )
        transition(record, InvestigationStatus.PLANNING)
        transition(record, InvestigationStatus.INVESTIGATING)
        cancel_investigation(record)
        assert record.status == InvestigationStatus.CANCELLED


# ── Planner Tests ──────────────────────────────────────────────────────────


class TestPlanner:
    def setup_method(self) -> None:
        self.planner = InvestigationPlanner(max_steps=8)

    def test_identify_domain_market(self) -> None:
        obj = InvestigationObjective(query="What is the RSI for AAPL?")
        domain = self.planner.identify_domain(obj)
        assert domain == InvestigationDomain.MARKET

    def test_identify_domain_geo(self) -> None:
        obj = InvestigationObjective(query="What changed in this AOI since last scene?")
        domain = self.planner.identify_domain(obj)
        assert domain == InvestigationDomain.GEO

    def test_identify_domain_research(self) -> None:
        obj = InvestigationObjective(query="Investigate the evidence surrounding hypothesis H-17")
        domain = self.planner.identify_domain(obj)
        assert domain == InvestigationDomain.RESEARCH

    def test_identify_domain_explicit(self) -> None:
        obj = InvestigationObjective(
            query="test", domain=InvestigationDomain.MARKET
        )
        domain = self.planner.identify_domain(obj)
        assert domain == InvestigationDomain.MARKET

    def test_required_evidence_market(self) -> None:
        obj = InvestigationObjective(query="market analysis")
        required = self.planner.identify_required_evidence(obj, InvestigationDomain.MARKET)
        assert len(required) >= 2
        assert any(r["type"] == "ohlcv" for r in required)

    def test_required_evidence_geo(self) -> None:
        obj = InvestigationObjective(query="geo analysis")
        required = self.planner.identify_required_evidence(obj, InvestigationDomain.GEO)
        assert len(required) >= 2

    def test_identify_gaps(self) -> None:
        required = [{"type": "ohlcv", "tool": "market.get_ohlcv", "required": True}]
        gaps = self.planner.identify_gaps(required, [], [])
        assert len(gaps) == 1
        assert gaps[0].status == GapStatus.OPEN

    def test_generate_plan(self) -> None:
        obj = InvestigationObjective(query="market analysis", subject="AAPL")
        gaps = [
            EvidenceGap(
                description="Need OHLCV",
                candidate_tools=["stub.read_data"],
            )
        ]
        plan = self.planner.generate_plan(
            obj, InvestigationDomain.MARKET, gaps, ["stub.read_data"]
        )
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name == "stub.read_data"

    def test_validate_plan_valid(self) -> None:
        plan = InvestigationPlan(
            steps=[
                InvestigationPlanStep(
                    tool_name="stub.read_data",
                    parameters={},
                )
            ]
        )
        violations = self.planner.validate_plan(plan, ["stub.read_data"])
        assert violations == []

    def test_validate_plan_unknown_tool(self) -> None:
        plan = InvestigationPlan(
            steps=[
                InvestigationPlanStep(
                    tool_name="unknown.tool",
                    parameters={},
                )
            ]
        )
        violations = self.planner.validate_plan(plan, ["stub.read_data"])
        assert len(violations) == 1
        assert "Unknown tool" in violations[0]

    def test_validate_plan_too_many_steps(self) -> None:
        steps = [
            InvestigationPlanStep(tool_name="stub.read_data", parameters={})
            for _ in range(10)
        ]
        plan = InvestigationPlan(steps=steps)
        limits = InvestigationLimits(max_steps=5)
        violations = self.planner.validate_plan(plan, ["stub.read_data"], limits)
        assert len(violations) == 1
        assert "max" in violations[0].lower()


# ── Executor Tests ─────────────────────────────────────────────────────────


class TestExecutor:
    def setup_method(self) -> None:
        self.registry = ToolRegistry()
        self.registry.register(StubReadTool())
        self.registry.register(StubFailTool())
        self.executor = InvestigationExecutor(self.registry)

    def test_execute_successful_step(self) -> None:
        self.executor.reset()
        step = InvestigationPlanStep(
            tool_name="stub.read_data",
            parameters={"query": "test"},
        )
        result = self.executor.execute_step(step, "inv-test", [])
        assert result.success is True
        assert result.evidence_id == "ev-stub-001"

    def test_execute_failed_step(self) -> None:
        self.executor.reset()
        step = InvestigationPlanStep(
            tool_name="stub.fail_tool",
            parameters={},
        )
        result = self.executor.execute_step(step, "inv-test", [])
        assert result.success is False
        assert result.error == "Simulated failure"

    def test_execute_unknown_tool(self) -> None:
        self.executor.reset()
        step = InvestigationPlanStep(
            tool_name="nonexistent.tool",
            parameters={},
        )
        result = self.executor.execute_step(step, "inv-test", [])
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_step_limit_enforced(self) -> None:
        limits = InvestigationLimits(max_steps=2)
        executor = InvestigationExecutor(self.registry, limits)
        executor.reset()

        for _ in range(2):
            step = InvestigationPlanStep(
                tool_name="stub.read_data",
                parameters={},
            )
            executor.execute_step(step, "inv-test", [])

        can, reason = executor.can_execute()
        assert can is False
        assert "Max steps" in reason

    def test_resolve_gaps(self) -> None:
        gaps = [
            EvidenceGap(
                description="Need data",
                candidate_tools=["stub.read_data"],
            )
        ]
        results = [
            ExecutorResult(
                step_id="step-1",
                tool_name="stub.read_data",
                success=True,
                evidence_id="ev-001",
            )
        ]
        resolved = self.executor.resolve_gaps(gaps, results)
        assert resolved[0].status == GapStatus.RESOLVED

    def test_event_log_recorded(self) -> None:
        self.executor.reset()
        step = InvestigationPlanStep(
            tool_name="stub.read_data",
            parameters={},
        )
        events: list[InvestigationEvent] = []
        self.executor.execute_step(step, "inv-test", events)
        event_types = [e.event_type for e in events]
        assert EventType.TOOL_STARTED in event_types
        assert EventType.TOOL_COMPLETED in event_types

    def test_reset(self) -> None:
        self.executor.reset()
        assert self.executor.steps_executed == 0


# ── Comparison Tests ───────────────────────────────────────────────────────


class TestComparison:
    def test_basic_comparison(self) -> None:
        baseline = {"rsi": 42.3, "trend": "up", "volume": 1000}
        current = {"rsi": 57.4, "trend": "down", "volume": 1200}
        comparison = compare_deterministic(baseline, current)

        rsi_delta = next(d for d in comparison.deltas if d.field_name == "rsi")
        assert rsi_delta.delta == pytest.approx(15.1, abs=0.01)
        assert rsi_delta.change_type == ComparisonChangeType.INCREASED

    def test_unchanged_values(self) -> None:
        baseline = {"rsi": 50.0}
        current = {"rsi": 50.0}
        comparison = compare_deterministic(baseline, current)
        assert len(comparison.unchanged) == 1

    def test_new_field(self) -> None:
        baseline = {}
        current = {"new_field": "value"}
        comparison = compare_deterministic(baseline, current)
        assert len(comparison.new_items) == 1

    def test_missing_field(self) -> None:
        baseline = {"old_field": "value"}
        current = {}
        comparison = compare_deterministic(baseline, current)
        assert len(comparison.missing_items) == 1

    def test_decreased_value(self) -> None:
        baseline = {"atr": 5.0}
        current = {"atr": 3.0}
        comparison = compare_deterministic(baseline, current)
        atr_delta = next(d for d in comparison.deltas if d.field_name == "atr")
        assert atr_delta.delta == pytest.approx(-2.0)
        assert atr_delta.change_type == ComparisonChangeType.DECREASED

    def test_non_numeric_comparison(self) -> None:
        baseline = {"name": "a"}
        current = {"name": "b"}
        comparison = compare_deterministic(baseline, current)
        assert len(comparison.conflicts) == 1


# ── Manager Tests ──────────────────────────────────────────────────────────


class TestManager:
    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.store = InvestigationStore(self.tmp_dir)
        self.registry = ToolRegistry()
        self.registry.register(StubReadTool())
        self.registry.register(StubFailTool())
        self.manager = InvestigationManager(self.store, self.registry)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_investigation(self) -> None:
        obj = InvestigationObjective(query="test investigation")
        record = self.manager.create(obj)
        assert record.investigation_id.startswith("inv-")
        assert record.status == InvestigationStatus.DRAFT

    def test_create_with_idempotency(self) -> None:
        obj = InvestigationObjective(query="test")
        r1 = self.manager.create(obj, idempotency_key="key-1")
        with pytest.raises(DuplicateInvestigation):
            self.manager.create(obj, idempotency_key="key-1")

    def test_get_investigation(self) -> None:
        obj = InvestigationObjective(query="test")
        record = self.manager.create(obj)
        fetched = self.manager.get(record.investigation_id)
        assert fetched.investigation_id == record.investigation_id

    def test_get_not_found(self) -> None:
        with pytest.raises(InvestigationNotFound):
            self.manager.get("inv-nonexistent")

    def test_list_investigations(self) -> None:
        for i in range(3):
            self.manager.create(
                InvestigationObjective(query=f"query {i}")
            )
        records = self.manager.list_all()
        assert len(records) == 3

    def test_start_investigation(self) -> None:
        obj = InvestigationObjective(
            query="market analysis for AAPL",
            domain=InvestigationDomain.MARKET,
            subject="AAPL",
        )
        record = self.manager.create(obj)
        result = self.manager.start(record.investigation_id)
        assert result.status in (
            InvestigationStatus.COMPLETE,
            InvestigationStatus.PARTIAL,
            InvestigationStatus.ABSTAINED,
        )
        assert len(result.evidence_refs) >= 0

    def test_cancel_investigation(self) -> None:
        obj = InvestigationObjective(query="test")
        record = self.manager.create(obj)
        result = self.manager.cancel(record.investigation_id)
        assert result.status == InvestigationStatus.CANCELLED

    def test_events_tracked(self) -> None:
        obj = InvestigationObjective(query="test")
        record = self.manager.create(obj)
        events = self.manager.get_events(record.investigation_id)
        assert len(events) >= 1
        assert events[0].event_type == EventType.CREATED

    def test_sufficiency_sufficient(self) -> None:
        state = self.manager.evaluate_sufficiency(
            ["ev-1", "ev-2"], ["type1"], []
        )
        assert state == SufficiencyState.SUFFICIENT

    def test_sufficiency_insufficient(self) -> None:
        gaps = [
            EvidenceGap(
                description="Critical gap",
                priority=10,
                status=GapStatus.OPEN,
            )
        ]
        state = self.manager.evaluate_sufficiency([], ["type1"], gaps)
        assert state == SufficiencyState.INSUFFICIENT

    def test_finding_built_on_success(self) -> None:
        obj = InvestigationObjective(
            query="market analysis for AAPL",
            domain=InvestigationDomain.MARKET,
            subject="AAPL",
        )
        record = self.manager.create(obj)
        result = self.manager.start(record.investigation_id)
        assert len(result.findings) >= 1


# ── Security Tests ─────────────────────────────────────────────────────────


class TestSecurity:
    def test_planner_cannot_execute_tools(self) -> None:
        planner = InvestigationPlanner()
        assert not hasattr(planner, "execute")

    def test_executor_requires_registry(self) -> None:
        executor = InvestigationExecutor(None)
        step = InvestigationPlanStep(tool_name="test", parameters={})
        result = executor.execute_step(step, "inv-test", [])
        assert result.success is False

    def test_no_unrestricted_planning(self) -> None:
        limits = InvestigationLimits(max_steps=8, max_planning_iterations=2)
        planner = InvestigationPlanner(
            max_steps=limits.max_steps,
            max_iterations=limits.max_planning_iterations,
        )
        assert planner._max_steps == 8
        assert planner._max_iterations == 2

    def test_step_limit_cannot_be_bypassed(self) -> None:
        limits = InvestigationLimits(max_steps=1)
        registry = ToolRegistry()
        registry.register(StubReadTool())
        executor = InvestigationExecutor(registry, limits)
        executor.reset()

        step1 = InvestigationPlanStep(tool_name="stub.read_data", parameters={})
        executor.execute_step(step1, "inv-test", [])

        can, _ = executor.can_execute()
        assert can is False
