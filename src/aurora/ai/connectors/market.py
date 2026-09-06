"""AURORA Reasoning Core — Market Reasoning Connector.

Connects the LLM layer to the existing MarketContext engine.
Flow: OHLCV → indicators → structure → MarketContext → evidence → LLM → structured explanation.
"""

from __future__ import annotations

from aurora.ai.schemas import (
    EvidenceRecord,
    EvidenceSource,
    ReasoningDomain,
    ReasoningRequest,
    TaskType,
)
from aurora.features.evidence import MarketAnalysis


def market_analysis_to_evidence(analysis: MarketAnalysis) -> list[EvidenceRecord]:
    """Convert a deterministic MarketAnalysis to evidence records for the LLM.

    The LLM receives these as facts. It cannot modify indicator values.
    """
    evidence: list[EvidenceRecord] = []
    ev_id = 0

    def _add(domain: str, claim: str, value: str = "", confidence: float = 1.0) -> None:
        nonlocal ev_id
        ev_id += 1
        evidence.append(EvidenceRecord(
            evidence_id=f"mkt_{ev_id:03d}",
            source=EvidenceSource.MARKET_ANALYSIS,
            domain=ReasoningDomain.MARKET,
            claim=claim,
            value=value,
            timestamp=analysis.timestamp,
            confidence=confidence,
            provenance=f"provider={analysis.provenance.provider} asset={analysis.asset} tf={analysis.timeframe}",
            quality="deterministic",
        ))

    _add("trend", f"Trend direction: {analysis.trend.direction.value}", analysis.trend.direction.value)
    _add("trend", f"Trend strength: {analysis.trend.strength.value}", analysis.trend.strength.value)
    _add("trend", f"EMA aligned: {analysis.trend.ema_aligned}", str(analysis.trend.ema_aligned))
    if analysis.trend.adx_value is not None:
        _add("trend", f"ADX value: {analysis.trend.adx_value:.1f}", f"{analysis.trend.adx_value:.1f}")

    _add("momentum", f"Momentum state: {analysis.momentum.state.value}", analysis.momentum.state.value)
    _add("momentum", f"RSI: {analysis.momentum.rsi_value:.1f}" if analysis.momentum.rsi_value else "RSI: unavailable",
         f"{analysis.momentum.rsi_value:.1f}" if analysis.momentum.rsi_value else "unavailable",
         confidence=0.9 if analysis.momentum.rsi_value else 0.0)

    _add("volatility", f"Volatility regime: {analysis.volatility.regime.value}", analysis.volatility.regime.value)
    if analysis.volatility.atr_value is not None:
        _add("volatility", f"ATR: {analysis.volatility.atr_value:.4f}", f"{analysis.volatility.atr_value:.4f}")

    _add("volume", f"Volume state: {analysis.volume.state.value}", analysis.volume.state.value)

    _add("structure", f"Structure context: {analysis.structure.state.value}", analysis.structure.state.value)

    if analysis.liquidity:
        _add("liquidity", f"Liquidity state: {analysis.liquidity.regime.value}", analysis.liquidity.regime.value)

    if analysis.multi_timeframe:
        _add("multi_timeframe", f"MTF alignment: {analysis.multi_timeframe.alignment.value}", analysis.multi_timeframe.alignment.value)

    for conflict in analysis.conflicts:
        ev_id += 1
        evidence.append(EvidenceRecord(
            evidence_id=f"mkt_{ev_id:03d}",
            source=EvidenceSource.MARKET_ANALYSIS,
            domain=ReasoningDomain.MARKET,
            claim=f"Conflict: {conflict.description}",
            value=f"severity={conflict.severity.value}",
            timestamp=analysis.timestamp,
            confidence=0.5,
            provenance=f"conflict_type={conflict.conflict_type}",
            quality="deterministic",
        ))

    for scenario in analysis.scenarios.scenarios:
        ev_id += 1
        evidence.append(EvidenceRecord(
            evidence_id=f"mkt_{ev_id:03d}",
            source=EvidenceSource.MARKET_ANALYSIS,
            domain=ReasoningDomain.MARKET,
            claim=f"Scenario: {scenario.name} — {scenario.explanation}",
            value=f"type={scenario.scenario_type.value} confidence={scenario.confidence:.2f}",
            timestamp=analysis.timestamp,
            confidence=scenario.confidence,
            provenance="scenario_generation",
            quality="deterministic",
        ))

    return evidence


def build_market_request(
    asset: str,
    timeframe: str,
    query: str,
    request_id: str,
) -> ReasoningRequest:
    """Build a ReasoningRequest for market analysis."""
    return ReasoningRequest(
        request_id=request_id,
        user_query=query,
        domain=ReasoningDomain.MARKET,
        task_type=TaskType.ANALYZE_MARKET,
        context_ids=[f"{asset}:{timeframe}"],
    )
