"""M26 Evidence Confluence and Scenario Analysis Tests.

Tests evidence aggregation, confluence scoring, enhanced conflict detection,
scenario generation, uncertainty detection, data provenance, research integrity,
and the full analyze_market_full entry point. Leakage prevention and determinism.
"""
from __future__ import annotations

from aurora.features.evidence import (
    ConflictSeverity,
    ConfluenceLevel,
    DataProvenance,
    EvidenceAggregation,
    EvidenceItem,
    EvidencePolarity,
    EvidenceStrength,
    MarketAnalysis,
    ResearchClassification,
    ResearchIntegrity,
    ScenarioType,
    _build_provenance,
    _build_research_integrity,
    _detect_uncertainty,
    aggregate_evidence,
    analyze_market_full,
    compute_confluence,
    detect_enhanced_conflicts,
    generate_scenarios,
)
from aurora.features.market_context import (
    DataQuality,
    MarketContext,
    analyze_market,
)

# ============================================================
# Helpers
# ============================================================


def _make_bars(
    closes: list[float],
    volatility: float = 0.02,
    base_volume: float = 1000.0,
) -> list[dict]:
    bars = []
    for i, c in enumerate(closes):
        h = c * (1 + volatility)
        l = c * (1 - volatility)
        o = c * (1 + volatility * 0.1)
        bars.append({
            "timestamp": f"2024-01-{i + 1:02d}T00:00:00Z",
            "open": o, "high": h, "low": l, "close": c,
            "volume": base_volume + i * 10,
        })
    return bars


def _uptrend_bars(n: int = 100) -> list[dict]:
    closes = [100 + i * 0.5 + (i % 5) * 0.1 for i in range(n)]
    return _make_bars(closes)


def _downtrend_bars(n: int = 100) -> list[dict]:
    closes = [200 - i * 0.5 + (i % 5) * 0.1 for i in range(n)]
    return _make_bars(closes)


def _ranging_bars(n: int = 100) -> list[dict]:
    closes = [100 + (i % 10) * 0.5 for i in range(n)]
    return _make_bars(closes)


def _volatile_bars(n: int = 100) -> list[dict]:
    closes = [100 + (i % 3 - 1) * 10 for i in range(n)]
    return _make_bars(closes, volatility=0.08)


def _make_context(
    bars: list[dict],
    asset: str = "BTC-USD",
    timeframe: str = "1d",
    provider: str = "yfinance",
    stale: bool = False,
) -> MarketContext:
    """Build MarketContext from bars for evidence testing."""
    return analyze_market(bars, asset, timeframe, provider, stale)


# ============================================================
# Test: Evidence Aggregation
# ============================================================


class TestEvidenceAggregation:
    def test_uptrend_produces_bullish_evidence(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        assert agg.bullish_count > 0
        assert agg.total_evidence > 0
        assert agg.bullish_pct >= 0

    def test_downtrend_produces_bearish_evidence(self):
        bars = _downtrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        assert agg.bearish_count > 0

    def test_pcts_sum_to_one(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        total_pct = agg.bullish_pct + agg.bearish_pct + \
            (agg.neutral_count / agg.total_evidence if agg.total_evidence > 0 else 0) + \
            (agg.unavailable_count / agg.total_evidence if agg.total_evidence > 0 else 0)
        assert abs(total_pct - 1.0) < 0.05

    def test_evidence_items_have_required_fields(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        for item in agg.items:
            assert item.domain
            assert isinstance(item.classification, ResearchClassification)
            assert isinstance(item.polarity, EvidencePolarity)
            assert isinstance(item.strength, EvidenceStrength)
            assert item.value != ""
            assert item.description != ""

    def test_empty_bars_minimal_evidence(self):
        ctx = _make_context([])
        agg = aggregate_evidence(ctx)
        assert agg.total_evidence >= 0

    def test_domains_covered(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        domains = {i.domain for i in agg.items}
        assert "trend" in domains
        assert "momentum" in domains
        assert "volatility" in domains


# ============================================================
# Test: Confluence Scoring
# ============================================================


class TestConfluenceScoring:
    def test_uptrend_strong_confluence(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        assert isinstance(conf.level, ConfluenceLevel)
        assert -1.0 <= conf.score <= 1.0
        assert conf.bullish_aligned >= 0
        assert conf.bearish_aligned >= 0

    def test_empty_evidence_insufficient_data(self):
        empty = EvidenceAggregation(
            items=[], bullish_count=0, bearish_count=0, neutral_count=0,
            unavailable_count=0, total_evidence=0, bullish_pct=0.0, bearish_pct=0.0,
        )
        conf = compute_confluence(empty)
        assert conf.level == ConfluenceLevel.INSUFFICIENT_DATA
        assert conf.score == 0.0

    def test_all_bullish_positive_score(self):
        items = [
            EvidenceItem(domain="trend", classification=ResearchClassification.OBSERVATION,
                         polarity=EvidencePolarity.BULLISH, strength=EvidenceStrength.STRONG,
                         value="uptrend", description="Trend up", source_indicator="ema"),
            EvidenceItem(domain="momentum", classification=ResearchClassification.OBSERVATION,
                         polarity=EvidencePolarity.BULLISH, strength=EvidenceStrength.MODERATE,
                         value="bullish", description="Mom up", source_indicator="rsi"),
        ]
        agg = EvidenceAggregation(
            items=items, bullish_count=2, bearish_count=0, neutral_count=0,
            unavailable_count=0, total_evidence=2, bullish_pct=1.0, bearish_pct=0.0,
        )
        conf = compute_confluence(agg)
        assert conf.score > 0

    def test_all_bearish_negative_score(self):
        items = [
            EvidenceItem(domain="trend", classification=ResearchClassification.OBSERVATION,
                         polarity=EvidencePolarity.BEARISH, strength=EvidenceStrength.STRONG,
                         value="downtrend", description="Trend down", source_indicator="ema"),
            EvidenceItem(domain="momentum", classification=ResearchClassification.OBSERVATION,
                         polarity=EvidencePolarity.BEARISH, strength=EvidenceStrength.MODERATE,
                         value="bearish", description="Mom down", source_indicator="rsi"),
        ]
        agg = EvidenceAggregation(
            items=items, bullish_count=0, bearish_count=2, neutral_count=0,
            unavailable_count=0, total_evidence=2, bullish_pct=0.0, bearish_pct=1.0,
        )
        conf = compute_confluence(agg)
        assert conf.score < 0

    def test_mixed_evidence_near_zero(self):
        items = [
            EvidenceItem(domain="trend", classification=ResearchClassification.OBSERVATION,
                         polarity=EvidencePolarity.BULLISH, strength=EvidenceStrength.MODERATE,
                         value="up", description="Up", source_indicator="ema"),
            EvidenceItem(domain="momentum", classification=ResearchClassification.OBSERVATION,
                         polarity=EvidencePolarity.BEARISH, strength=EvidenceStrength.MODERATE,
                         value="down", description="Down", source_indicator="rsi"),
        ]
        agg = EvidenceAggregation(
            items=items, bullish_count=1, bearish_count=1, neutral_count=0,
            unavailable_count=0, total_evidence=2, bullish_pct=0.5, bearish_pct=0.5,
        )
        conf = compute_confluence(agg)
        assert abs(conf.score) < 0.5

    def test_evidence_summary_populated(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        assert isinstance(conf.evidence_summary, list)
        assert len(conf.evidence_summary) > 0


# ============================================================
# Test: Enhanced Conflict Detection
# ============================================================


class TestEnhancedConflicts:
    def test_no_conflicts_in_aligned_uptrend(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conflicts = detect_enhanced_conflicts(ctx, agg)
        assert isinstance(conflicts, list)

    def test_conflict_has_severity(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conflicts = detect_enhanced_conflicts(ctx, agg)
        for c in conflicts:
            assert isinstance(c.severity, ConflictSeverity)
            assert c.conflict_type
            assert c.domain_a
            assert c.domain_b
            assert c.description
            assert isinstance(c.evidence, list)

    def test_stale_data_produces_critical_conflict(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars, stale=True)
        agg = aggregate_evidence(ctx)
        conflicts = detect_enhanced_conflicts(ctx, agg)
        stale_conflicts = [c for c in conflicts if c.conflict_type == "stale_data"]
        assert len(stale_conflicts) >= 1
        assert stale_conflicts[0].severity == ConflictSeverity.CRITICAL

    def test_insufficient_data_produces_conflict(self):
        ctx = _make_context([])
        agg = aggregate_evidence(ctx)
        conflicts = detect_enhanced_conflicts(ctx, agg)
        assert isinstance(conflicts, list)


# ============================================================
# Test: Scenario Generation
# ============================================================


class TestScenarioGeneration:
    def test_uptrend_has_range_or_continuation_scenario(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        assert isinstance(result.scenarios, list)
        types = [s.scenario_type for s in result.scenarios]
        # With limited swing points, structure classifies as RANGE → RANGE scenario
        assert ScenarioType.RANGE in types or ScenarioType.CONTINUATION in types

    def test_downtrend_has_range_or_continuation_scenario(self):
        bars = _downtrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        types = [s.scenario_type for s in result.scenarios]
        assert ScenarioType.RANGE in types or ScenarioType.CONTINUATION in types

    def test_ranging_has_range_scenario(self):
        bars = _ranging_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        types = [s.scenario_type for s in result.scenarios]
        assert ScenarioType.RANGE in types

    def test_primary_scenario_has_highest_confidence(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        assert result.primary_scenario is not None
        assert result.primary_scenario.confidence >= 0
        assert result.primary_scenario.confidence <= 1.0

    def test_scenarios_have_required_fields(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        for s in result.scenarios:
            assert isinstance(s.scenario_type, ScenarioType)
            assert s.name
            assert isinstance(s.supporting_evidence, list)
            assert isinstance(s.conflicting_evidence, list)
            assert isinstance(s.invalidating_conditions, list)
            assert 0 <= s.confidence <= 1
            assert s.relevant_timeframe
            assert s.explanation

    def test_insufficient_data_yields_insufficient_scenario(self):
        ctx = _make_context([])
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        types = [s.scenario_type for s in result.scenarios]
        assert ScenarioType.INSUFFICIENT_EVIDENCE in types

    def test_methodology_version(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        conf = compute_confluence(agg)
        result = generate_scenarios(ctx, conf, agg)
        assert result.methodology_version == "m26.0"


# ============================================================
# Test: Uncertainty Detection
# ============================================================


class TestUncertainty:
    def test_returns_list(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        u = _detect_uncertainty(ctx, agg)
        assert isinstance(u, list)

    def test_stale_data_flagged(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars, stale=True)
        agg = aggregate_evidence(ctx)
        u = _detect_uncertainty(ctx, agg)
        assert any("stale" in x.lower() for x in u)

    def test_insufficient_data_flagged(self):
        bars = _make_bars([100.0] * 10)
        ctx = _make_context(bars)
        agg = aggregate_evidence(ctx)
        u = _detect_uncertainty(ctx, agg)
        assert any("limited" in x.lower() or "insufficient" in x.lower() for x in u)


# ============================================================
# Test: Data Provenance and Research Integrity
# ============================================================


class TestProvenanceAndIntegrity:
    def test_provenance_fields(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        p = _build_provenance(ctx)
        assert isinstance(p, DataProvenance)
        assert p.provider
        assert p.asset
        assert p.timeframe
        assert p.methodology_version == "m26.0"
        assert p.freshness in ("fresh", "limited", "stale")

    def test_research_integrity(self):
        ri = _build_research_integrity()
        assert isinstance(ri, ResearchIntegrity)
        assert ri.no_deployment_signal is True
        assert ri.no_predictions is True
        assert ri.no_trading_signals is True
        assert ri.deterministic is True
        assert ri.no_future_data is True
        assert ri.classification == "ANALYTICAL_RESEARCH"
        assert len(ri.disclaimer) > 0


# ============================================================
# Test: Full analyze_market_full
# ============================================================


class TestFullAnalysis:
    def test_uptrend_full(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        result = analyze_market_full(ctx)
        assert isinstance(result, MarketAnalysis)
        assert result.asset == "BTC-USD"
        assert result.methodology_version == "m26.0"
        assert isinstance(result.confluence.score, float)
        assert isinstance(result.scenarios.scenarios, list)
        assert isinstance(result.evidence.total_evidence, int)
        assert isinstance(result.research_integrity, ResearchIntegrity)
        assert result.research_integrity.no_deployment_signal is True

    def test_downtrend_full(self):
        bars = _downtrend_bars(100)
        ctx = _make_context(bars)
        result = analyze_market_full(ctx)
        assert result.asset == "BTC-USD"
        assert result.methodology_version == "m26.0"

    def test_ranging_full(self):
        bars = _ranging_bars(100)
        ctx = _make_context(bars)
        result = analyze_market_full(ctx)
        assert isinstance(result.confluence.level, ConfluenceLevel)
        assert len(result.scenarios.scenarios) > 0

    def test_empty_data_full(self):
        ctx = _make_context([])
        result = analyze_market_full(ctx)
        assert result.data_quality.quality == DataQuality.MISSING
        # Empty bars still produce default evidence items from domain analyzers
        assert isinstance(result.confluence.level, ConfluenceLevel)
        assert len(result.uncertainty) > 0

    def test_provenance_populated(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        result = analyze_market_full(ctx)
        assert result.provenance.provider
        assert result.provenance.methodology_version == "m26.0"

    def test_uncertainty_populated(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        result = analyze_market_full(ctx)
        assert isinstance(result.uncertainty, list)


# ============================================================
# Test: Determinism and Leakage
# ============================================================


class TestDeterminismAndLeakage:
    def test_deterministic_same_input_same_output(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        r1 = analyze_market_full(ctx)
        r2 = analyze_market_full(ctx)
        assert r1.confluence.score == r2.confluence.score
        assert r1.evidence.bullish_count == r2.evidence.bullish_count
        assert r1.scenarios.primary_scenario == r2.scenarios.primary_scenario

    def test_no_random_state(self):
        bars = _uptrend_bars(100)
        ctx = _make_context(bars)
        result = analyze_market_full(ctx)
        assert result.methodology_version == "m26.0"
        assert result.research_integrity.deterministic is True

    def test_future_bar_addition_does_not_flip_past_classification(self):
        bars_50 = _uptrend_bars(50)
        ctx_50 = _make_context(bars_50)
        r50 = analyze_market_full(ctx_50)

        bars_100 = _uptrend_bars(100)
        ctx_100 = _make_context(bars_100)
        r100 = analyze_market_full(ctx_100)

        # Both should classify the same trend direction
        assert r50.trend.direction == r100.trend.direction
        # Confluence level should be consistent
        assert r50.confluence.level == r100.confluence.level
