"""M26 Evidence Aggregation, Confluence, and Scenario Analysis Engine.

NO_DEPLOYMENT_SIGNAL -- This module produces structured research evidence,
confluence scoring, and scenario analysis. Nothing here constitutes a
trading signal, recommendation, or claim of predictive power.

All outputs are deterministic and use no future data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from aurora.features.market_context import (
    AlignmentState,
    DataQuality,
    DataQualityContext,
    LiquidityContext,
    MarketContext,
    MomentumContext,
    MomentumState,
    MultiTimeframeContext,
    StructureContext,
    StructureContextState,
    TrendContext,
    TrendDirection,
    TrendStrength,
    VolatilityContext,
    VolatilityRegime,
    VolumeContext,
    VolumeState,
)

METHODOLOGY_VERSION = "m26.0"


class EvidencePolarity(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNAVAILABLE = "unavailable"


class EvidenceStrength(Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    ABSENT = "absent"


class ConfluenceLevel(Enum):
    STRONG_AGREEMENT = "strong_agreement"
    MODERATE_AGREEMENT = "moderate_agreement"
    WEAK_AGREEMENT = "weak_agreement"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    MODERATE_DISAGREEMENT = "moderate_disagreement"
    STRONG_DISAGREEMENT = "strong_disagreement"
    INSUFFICIENT_DATA = "insufficient_data"


class ScenarioType(Enum):
    CONTINUATION = "continuation"
    REVERSAL = "reversal"
    RANGE = "range"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ConflictSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResearchClassification(Enum):
    FACT = "fact"
    OBSERVATION = "observation"
    CALCULATION = "calculation"
    INFERENCE = "inference"
    SCENARIO = "scenario"
    UNCERTAINTY = "uncertainty"


@dataclass(frozen=True)
class EvidenceItem:
    domain: str
    classification: ResearchClassification
    polarity: EvidencePolarity
    strength: EvidenceStrength
    value: str
    description: str
    source_indicator: str = ""


@dataclass(frozen=True)
class EvidenceAggregation:
    items: list[EvidenceItem]
    bullish_count: int
    bearish_count: int
    neutral_count: int
    unavailable_count: int
    total_evidence: int
    bullish_pct: float
    bearish_pct: float


@dataclass(frozen=True)
class ConfluenceResult:
    level: ConfluenceLevel
    score: float
    bullish_aligned: int
    bearish_aligned: int
    conflicting: int
    missing: int
    evidence_summary: list[str]


@dataclass(frozen=True)
class EnhancedConflict:
    conflict_type: str
    severity: ConflictSeverity
    domain_a: str
    state_a: str
    domain_b: str
    state_b: str
    description: str
    evidence: list[str]


@dataclass(frozen=True)
class ScenarioEvidence:
    domain: str
    supports: bool
    description: str


@dataclass(frozen=True)
class Scenario:
    scenario_type: ScenarioType
    name: str
    supporting_evidence: list[ScenarioEvidence]
    conflicting_evidence: list[ScenarioEvidence]
    invalidating_conditions: list[str]
    confidence: float
    relevant_timeframe: str
    explanation: str


@dataclass(frozen=True)
class ScenarioResult:
    scenarios: list[Scenario]
    primary_scenario: Scenario
    methodology_version: str


@dataclass(frozen=True)
class DataProvenance:
    provider: str
    asset: str
    timeframe: str
    retrieved_at: str
    data_timestamp: str | None
    freshness: str
    data_quality: str
    is_demo: bool
    methodology_version: str


@dataclass(frozen=True)
class ResearchIntegrity:
    no_deployment_signal: bool
    no_predictions: bool
    no_trading_signals: bool
    deterministic: bool
    no_future_data: bool
    classification: str
    disclaimer: str


@dataclass(frozen=True)
class MarketAnalysis:
    asset: str
    timeframe: str
    timestamp: str
    data_quality: DataQualityContext
    market_regime: str
    trend: TrendContext
    momentum: MomentumContext
    volatility: VolatilityContext
    volume: VolumeContext
    structure: StructureContext
    liquidity: LiquidityContext
    multi_timeframe: MultiTimeframeContext
    confluence: ConfluenceResult
    scenarios: ScenarioResult
    conflicts: list[EnhancedConflict]
    evidence: EvidenceAggregation
    uncertainty: list[str]
    methodology_version: str
    provenance: DataProvenance
    research_integrity: ResearchIntegrity


# ============================================================
# Evidence Aggregation
# ============================================================


def _classify_trend_evidence(trend: TrendContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    if trend.direction == TrendDirection.UPTREND:
        polarity = EvidencePolarity.BULLISH
    elif trend.direction == TrendDirection.DOWNTREND:
        polarity = EvidencePolarity.BEARISH
    else:
        polarity = EvidencePolarity.NEUTRAL

    strength = (
        EvidenceStrength.STRONG if trend.strength == TrendStrength.STRONG
        else EvidenceStrength.MODERATE if trend.strength == TrendStrength.MODERATE
        else EvidenceStrength.WEAK
    )
    items.append(EvidenceItem(
        domain="trend", classification=ResearchClassification.OBSERVATION,
        polarity=polarity, strength=strength, value=trend.direction.value,
        description=f"Trend: {trend.direction.value} ({trend.strength.value})",
        source_indicator="EMA/ADX/structure",
    ))
    if trend.ema_aligned:
        items.append(EvidenceItem(
            domain="trend", classification=ResearchClassification.CALCULATION,
            polarity=EvidencePolarity.BULLISH, strength=EvidenceStrength.MODERATE,
            value="aligned", description="EMA12 above EMA26",
            source_indicator="EMA",
        ))
    else:
        items.append(EvidenceItem(
            domain="trend", classification=ResearchClassification.CALCULATION,
            polarity=EvidencePolarity.BEARISH, strength=EvidenceStrength.MODERATE,
            value="not_aligned", description="EMA12 below EMA26",
            source_indicator="EMA",
        ))
    if trend.adx_value is not None:
        adx_str = f"ADX ({trend.adx_value:.1f})"
        if trend.adx_value > 25:
            items.append(EvidenceItem(
                domain="trend", classification=ResearchClassification.CALCULATION,
                polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.STRONG,
                value=f"{trend.adx_value:.1f}", description=f"{adx_str} indicates trend strength",
                source_indicator="ADX",
            ))
        else:
            items.append(EvidenceItem(
                domain="trend", classification=ResearchClassification.CALCULATION,
                polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.WEAK,
                value=f"{trend.adx_value:.1f}", description=f"{adx_str} indicates weak trend",
                source_indicator="ADX",
            ))
    return items


def _classify_momentum_evidence(momentum: MomentumContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    state_polarity = {
        MomentumState.BULLISH: EvidencePolarity.BULLISH,
        MomentumState.BEARISH: EvidencePolarity.BEARISH,
        MomentumState.NEUTRAL: EvidencePolarity.NEUTRAL,
        MomentumState.MIXED: EvidencePolarity.NEUTRAL,
        MomentumState.OVERBOUGHT: EvidencePolarity.BULLISH,
        MomentumState.OVERSOLD: EvidencePolarity.BEARISH,
    }
    items.append(EvidenceItem(
        domain="momentum", classification=ResearchClassification.OBSERVATION,
        polarity=state_polarity.get(momentum.state, EvidencePolarity.NEUTRAL),
        strength=EvidenceStrength.MODERATE, value=momentum.state.value,
        description=f"Momentum: {momentum.state.value}",
        source_indicator="RSI/MACD/Stochastic/CCI/ROC/Williams%R",
    ))
    if momentum.rsi_value is not None:
        rs = (EvidenceStrength.STRONG if momentum.rsi_zone in ("overbought", "oversold")
              else EvidenceStrength.MODERATE if momentum.rsi_zone in ("elevated", "depressed")
              else EvidenceStrength.WEAK)
        rp = EvidencePolarity.BULLISH if momentum.rsi_value > 50 else EvidencePolarity.BEARISH
        items.append(EvidenceItem(
            domain="momentum", classification=ResearchClassification.CALCULATION,
            polarity=rp, strength=rs, value=f"{momentum.rsi_value:.1f}",
            description=f"RSI(14) = {momentum.rsi_value:.1f} ({momentum.rsi_zone})",
            source_indicator="RSI",
        ))
    if momentum.macd_positive:
        items.append(EvidenceItem(
            domain="momentum", classification=ResearchClassification.CALCULATION,
            polarity=EvidencePolarity.BULLISH, strength=EvidenceStrength.MODERATE,
            value="positive", description="MACD line is positive", source_indicator="MACD",
        ))
    else:
        items.append(EvidenceItem(
            domain="momentum", classification=ResearchClassification.CALCULATION,
            polarity=EvidencePolarity.BEARISH, strength=EvidenceStrength.MODERATE,
            value="negative", description="MACD line is negative", source_indicator="MACD",
        ))
    return items


def _classify_volatility_evidence(volatility: VolatilityContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    items.append(EvidenceItem(
        domain="volatility", classification=ResearchClassification.OBSERVATION,
        polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.MODERATE,
        value=volatility.regime.value, description=f"Volatility: {volatility.regime.value}",
        source_indicator="ATR/BB",
    ))
    if volatility.atr_pct is not None and volatility.atr_pct > 0.04:
        items.append(EvidenceItem(
            domain="volatility", classification=ResearchClassification.CALCULATION,
            polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.STRONG,
            value=f"{volatility.atr_pct:.2%}", description=f"ATR {volatility.atr_pct:.2%} of price (elevated)",
            source_indicator="ATR",
        ))
    return items


def _classify_volume_evidence(volume: VolumeContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    if not volume.has_volume_data:
        items.append(EvidenceItem(
            domain="volume", classification=ResearchClassification.UNCERTAINTY,
            polarity=EvidencePolarity.UNAVAILABLE, strength=EvidenceStrength.ABSENT,
            value="unavailable", description="Volume data unavailable", source_indicator="volume",
        ))
        return items
    sp = {VolumeState.CONFIRMING: EvidencePolarity.BULLISH, VolumeState.WEAK: EvidencePolarity.NEUTRAL,
          VolumeState.MIXED: EvidencePolarity.NEUTRAL, VolumeState.DIVERGING: EvidencePolarity.BEARISH}
    items.append(EvidenceItem(
        domain="volume", classification=ResearchClassification.OBSERVATION,
        polarity=sp.get(volume.state, EvidencePolarity.NEUTRAL),
        strength=EvidenceStrength.MODERATE if volume.state == VolumeState.CONFIRMING else EvidenceStrength.WEAK,
        value=volume.state.value, description=f"Volume: {volume.state.value}",
        source_indicator="OBV/VWAP/MFI",
    ))
    return items


def _classify_structure_evidence(structure: StructureContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    sp = {StructureContextState.BULLISH: EvidencePolarity.BULLISH, StructureContextState.BEARISH: EvidencePolarity.BEARISH,
          StructureContextState.RANGE: EvidencePolarity.NEUTRAL, StructureContextState.TRANSITION: EvidencePolarity.NEUTRAL,
          StructureContextState.MIXED: EvidencePolarity.NEUTRAL}
    items.append(EvidenceItem(
        domain="structure", classification=ResearchClassification.OBSERVATION,
        polarity=sp.get(structure.state, EvidencePolarity.NEUTRAL), strength=EvidenceStrength.MODERATE,
        value=structure.state.value,
        description=f"Structure: {structure.state.value} (regime: {structure.regime.value})",
        source_indicator="swing/BOS/CHOch/SR",
    ))
    if structure.last_break:
        bp = EvidencePolarity.BULLISH if "bull" in structure.last_break.break_type.value else EvidencePolarity.BEARISH
        items.append(EvidenceItem(
            domain="structure", classification=ResearchClassification.OBSERVATION,
            polarity=bp, strength=EvidenceStrength.MODERATE,
            value=structure.last_break.break_type.value,
            description=f"Latest break: {structure.last_break.break_type.value}",
            source_indicator="structure_break",
        ))
    return items


def _classify_liquidity_evidence(liquidity: LiquidityContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    if liquidity.swept_count > 0:
        items.append(EvidenceItem(
            domain="liquidity", classification=ResearchClassification.OBSERVATION,
            polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.WEAK,
            value=f"{liquidity.swept_count}_swept",
            description=f"{liquidity.swept_count} liquidity level(s) swept",
            source_indicator="liquidity",
        ))
    if liquidity.unswept_count > 0:
        items.append(EvidenceItem(
            domain="liquidity", classification=ResearchClassification.OBSERVATION,
            polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.WEAK,
            value=f"{liquidity.unswept_count}_unswept",
            description=f"{liquidity.unswept_count} unswept liquidity level(s)",
            source_indicator="liquidity",
        ))
    return items


def _classify_mtf_evidence(mtf: MultiTimeframeContext) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    if mtf.alignment == AlignmentState.ALIGNED_BULLISH:
        items.append(EvidenceItem(
            domain="multi_timeframe", classification=ResearchClassification.OBSERVATION,
            polarity=EvidencePolarity.BULLISH, strength=EvidenceStrength.STRONG,
            value="aligned_bullish", description="Multiple timeframes aligned bullish",
            source_indicator="multi_timeframe",
        ))
    elif mtf.alignment == AlignmentState.ALIGNED_BEARISH:
        items.append(EvidenceItem(
            domain="multi_timeframe", classification=ResearchClassification.OBSERVATION,
            polarity=EvidencePolarity.BEARISH, strength=EvidenceStrength.STRONG,
            value="aligned_bearish", description="Multiple timeframes aligned bearish",
            source_indicator="multi_timeframe",
        ))
    elif mtf.alignment == AlignmentState.CONFLICTING:
        items.append(EvidenceItem(
            domain="multi_timeframe", classification=ResearchClassification.UNCERTAINTY,
            polarity=EvidencePolarity.NEUTRAL, strength=EvidenceStrength.WEAK,
            value="conflicting", description="Timeframes show conflicting signals",
            source_indicator="multi_timeframe",
        ))
    else:
        items.append(EvidenceItem(
            domain="multi_timeframe", classification=ResearchClassification.UNCERTAINTY,
            polarity=EvidencePolarity.UNAVAILABLE, strength=EvidenceStrength.ABSENT,
            value=mtf.alignment.value, description=f"MTF: {mtf.alignment.value}",
            source_indicator="multi_timeframe",
        ))
    return items


def aggregate_evidence(context: MarketContext) -> EvidenceAggregation:
    items: list[EvidenceItem] = []
    items.extend(_classify_trend_evidence(context.trend))
    items.extend(_classify_momentum_evidence(context.momentum))
    items.extend(_classify_volatility_evidence(context.volatility))
    items.extend(_classify_volume_evidence(context.volume))
    items.extend(_classify_structure_evidence(context.structure))
    items.extend(_classify_liquidity_evidence(context.liquidity))
    items.extend(_classify_mtf_evidence(context.multi_timeframe))
    bull = sum(1 for i in items if i.polarity == EvidencePolarity.BULLISH)
    bear = sum(1 for i in items if i.polarity == EvidencePolarity.BEARISH)
    neut = sum(1 for i in items if i.polarity == EvidencePolarity.NEUTRAL)
    unavail = sum(1 for i in items if i.polarity == EvidencePolarity.UNAVAILABLE)
    total = len(items)
    return EvidenceAggregation(
        items=items, bullish_count=bull, bearish_count=bear,
        neutral_count=neut, unavailable_count=unavail, total_evidence=total,
        bullish_pct=round(bull / total, 2) if total > 0 else 0.0,
        bearish_pct=round(bear / total, 2) if total > 0 else 0.0,
    )


# ============================================================
# Confluence Engine
# ============================================================


def compute_confluence(evidence: EvidenceAggregation) -> ConfluenceResult:
    if evidence.total_evidence == 0:
        return ConfluenceResult(
            level=ConfluenceLevel.INSUFFICIENT_DATA, score=0.0,
            bullish_aligned=0, bearish_aligned=0, conflicting=0,
            missing=evidence.unavailable_count, evidence_summary=["No evidence available"],
        )
    sw = {EvidenceStrength.STRONG: 1.0, EvidenceStrength.MODERATE: 0.6,
          EvidenceStrength.WEAK: 0.3, EvidenceStrength.ABSENT: 0.0}
    sn = 0.0
    sd = 0.0
    ba = 0
    bea = 0
    conf = 0
    for item in evidence.items:
        w = sw.get(item.strength, 0.5)
        if item.polarity == EvidencePolarity.BULLISH:
            sn += w
            ba += 1
        elif item.polarity == EvidencePolarity.BEARISH:
            sn -= w
            bea += 1
        elif item.polarity == EvidencePolarity.NEUTRAL:
            conf += 1
        sd += w
    score = round(sn / sd, 2) if sd > 0 else 0.0
    abs_s = abs(score)
    if abs_s >= 0.6:
        level = ConfluenceLevel.STRONG_AGREEMENT if score > 0 else ConfluenceLevel.STRONG_DISAGREEMENT
    elif abs_s >= 0.3:
        level = ConfluenceLevel.MODERATE_AGREEMENT if score > 0 else ConfluenceLevel.MODERATE_DISAGREEMENT
    elif abs_s >= 0.1:
        level = ConfluenceLevel.WEAK_AGREEMENT if score > 0 else ConfluenceLevel.MODERATE_DISAGREEMENT
    else:
        level = ConfluenceLevel.MIXED if ba > 0 and bea > 0 else ConfluenceLevel.NEUTRAL
    summary: list[str] = []
    if ba > 0:
        summary.append(f"{ba} bullish observation(s)")
    if bea > 0:
        summary.append(f"{bea} bearish observation(s)")
    if conf > 0:
        summary.append(f"{conf} neutral/uncertain")
    if evidence.unavailable_count > 0:
        summary.append(f"{evidence.unavailable_count} unavailable")
    return ConfluenceResult(
        level=level, score=score, bullish_aligned=ba, bearish_aligned=bea,
        conflicting=conf, missing=evidence.unavailable_count, evidence_summary=summary,
    )


# ============================================================
# Enhanced Conflict Detection
# ============================================================


def detect_enhanced_conflicts(context: MarketContext, evidence: EvidenceAggregation) -> list[EnhancedConflict]:
    conflicts: list[EnhancedConflict] = []
    if context.trend.direction == TrendDirection.UPTREND and context.momentum.state in (MomentumState.BEARISH, MomentumState.OVERSOLD):
        conflicts.append(EnhancedConflict(
            conflict_type="trend_momentum_divergence", severity=ConflictSeverity.HIGH,
            domain_a="trend", state_a=context.trend.direction.value,
            domain_b="momentum", state_b=context.momentum.state.value,
            description="Trend bullish but momentum bearish/oversold",
            evidence=[f"Trend: {context.trend.direction.value}", f"Momentum: {context.momentum.state.value}"],
        ))
    if context.trend.direction == TrendDirection.DOWNTREND and context.momentum.state in (MomentumState.BULLISH, MomentumState.OVERBOUGHT):
        conflicts.append(EnhancedConflict(
            conflict_type="trend_momentum_divergence", severity=ConflictSeverity.HIGH,
            domain_a="trend", state_a=context.trend.direction.value,
            domain_b="momentum", state_b=context.momentum.state.value,
            description="Trend bearish but momentum bullish/overbought",
            evidence=[f"Trend: {context.trend.direction.value}", f"Momentum: {context.momentum.state.value}"],
        ))
    if context.trend.direction == TrendDirection.UPTREND and context.structure.state == StructureContextState.BEARISH:
        conflicts.append(EnhancedConflict(
            conflict_type="trend_structure_divergence", severity=ConflictSeverity.MEDIUM,
            domain_a="trend", state_a=context.trend.direction.value,
            domain_b="structure", state_b=context.structure.state.value,
            description="Trend bullish but structure bearish",
            evidence=[f"Trend: {context.trend.direction.value}", f"Structure: {context.structure.state.value}"],
        ))
    if context.trend.direction == TrendDirection.DOWNTREND and context.structure.state == StructureContextState.BULLISH:
        conflicts.append(EnhancedConflict(
            conflict_type="trend_structure_divergence", severity=ConflictSeverity.MEDIUM,
            domain_a="trend", state_a=context.trend.direction.value,
            domain_b="structure", state_b=context.structure.state.value,
            description="Trend bearish but structure bullish",
            evidence=[f"Trend: {context.trend.direction.value}", f"Structure: {context.structure.state.value}"],
        ))
    if context.momentum.state == MomentumState.BULLISH and context.structure.state == StructureContextState.BEARISH:
        conflicts.append(EnhancedConflict(
            conflict_type="momentum_structure_divergence", severity=ConflictSeverity.MEDIUM,
            domain_a="momentum", state_a=context.momentum.state.value,
            domain_b="structure", state_b=context.structure.state.value,
            description="Momentum bullish but structure bearish",
            evidence=[f"Momentum: {context.momentum.state.value}", f"Structure: {context.structure.state.value}"],
        ))
    if context.volume.state == VolumeState.DIVERGING:
        conflicts.append(EnhancedConflict(
            conflict_type="volume_divergence", severity=ConflictSeverity.MEDIUM,
            domain_a="volume", state_a="diverging", domain_b="price", state_b="movement",
            description="Volume diverging from price direction",
            evidence=["OBV and price moving in opposite directions"],
        ))
    if context.multi_timeframe.alignment == AlignmentState.CONFLICTING:
        conflicts.append(EnhancedConflict(
            conflict_type="multi_timeframe_conflict", severity=ConflictSeverity.HIGH,
            domain_a="multi_timeframe", state_a="conflicting",
            domain_b="timeframes", state_b="mixed",
            description="Timeframes show conflicting directional bias",
            evidence=[f"Alignment: {context.multi_timeframe.alignment.value}"],
        ))
    if context.volatility.regime == VolatilityRegime.HIGH and context.structure.state == StructureContextState.RANGE:
        conflicts.append(EnhancedConflict(
            conflict_type="volatility_structure_mismatch", severity=ConflictSeverity.LOW,
            domain_a="volatility", state_a="high", domain_b="structure", state_b="range",
            description="High volatility with ranging structure",
            evidence=["Elevated ATR with no clear structure direction"],
        ))
    if context.data_quality.stale:
        conflicts.append(EnhancedConflict(
            conflict_type="stale_data", severity=ConflictSeverity.CRITICAL,
            domain_a="data_quality", state_a="stale", domain_b="analysis", state_b="all",
            description="Provider data is stale",
            evidence=[f"Provider: {context.data_quality.provider}"],
        ))
    if context.data_quality.quality == DataQuality.INSUFFICIENT:
        conflicts.append(EnhancedConflict(
            conflict_type="insufficient_data", severity=ConflictSeverity.HIGH,
            domain_a="data_quality", state_a="insufficient", domain_b="analysis", state_b="all",
            description=f"Only {context.data_quality.candle_count} candles available",
            evidence=[f"Candle count: {context.data_quality.candle_count}"],
        ))
    return conflicts


# ============================================================
# Scenario Engine
# ============================================================


def generate_scenarios(
    context: MarketContext, confluence: ConfluenceResult, evidence: EvidenceAggregation,
) -> ScenarioResult:
    scenarios: list[Scenario] = []
    bullish_items = [i for i in evidence.items if i.polarity == EvidencePolarity.BULLISH]
    bearish_items = [i for i in evidence.items if i.polarity == EvidencePolarity.BEARISH]

    if context.trend.direction in (TrendDirection.UPTREND, TrendDirection.DOWNTREND):
        is_up = context.trend.direction == TrendDirection.UPTREND
        support = [ScenarioEvidence(domain=i.domain, supports=True, description=i.description)
                   for i in evidence.items if (i.polarity == EvidencePolarity.BULLISH) == is_up][:5]
        conflict = [ScenarioEvidence(domain=i.domain, supports=False, description=i.description)
                    for i in evidence.items if (i.polarity == EvidencePolarity.BEARISH) == is_up][:5]
        inv = ["Bearish structure break (CHOCH)", "RSI below 30"] if is_up else [
            "Bullish structure break (CHOCH)", "RSI above 70"]
        conf_val = max(0.1, min(0.9, 0.5 + confluence.score * 0.4))
        scenarios.append(Scenario(
            scenario_type=ScenarioType.CONTINUATION,
            name=f"{context.trend.direction.value.title()} Continuation",
            supporting_evidence=support, conflicting_evidence=conflict,
            invalidating_conditions=inv, confidence=round(conf_val, 2),
            relevant_timeframe=context.timeframe,
            explanation=f"Current {context.trend.direction.value} may continue if evidence holds",
        ))

    rev_items = bearish_items if context.trend.direction == TrendDirection.UPTREND else bullish_items
    if rev_items and context.trend.direction in (TrendDirection.UPTREND, TrendDirection.DOWNTREND):
        rev_ev = [ScenarioEvidence(domain=i.domain, supports=True, description=i.description) for i in rev_items[:5]]
        conf_items = bullish_items if context.trend.direction == TrendDirection.UPTREND else bearish_items
        conf_ev = [ScenarioEvidence(domain=i.domain, supports=False, description=i.description) for i in conf_items[:3]]
        inv = ["Continued higher highs", "RSI above 50"] if context.trend.direction == TrendDirection.UPTREND else [
            "Continued lower lows", "RSI below 50"]
        scenarios.append(Scenario(
            scenario_type=ScenarioType.REVERSAL,
            name=f"{'Bearish' if context.trend.direction == TrendDirection.UPTREND else 'Bullish'} Reversal",
            supporting_evidence=rev_ev, conflicting_evidence=conf_ev,
            invalidating_conditions=inv,
            confidence=round(max(0.1, 0.5 - abs(confluence.score) * 0.3), 2),
            relevant_timeframe=context.timeframe,
            explanation=f"Counter-trend scenario with {len(rev_ev)} supporting observation(s)",
        ))

    if context.structure.state in (StructureContextState.RANGE, StructureContextState.MIXED):
        scenarios.append(Scenario(
            scenario_type=ScenarioType.RANGE, name="Range Continuation",
            supporting_evidence=[ScenarioEvidence(domain="structure", supports=True,
                                                  description=f"Structure: {context.structure.state.value}")],
            conflicting_evidence=[ScenarioEvidence(domain="trend", supports=False,
                                                   description=f"Trend: {context.trend.direction.value}")],
            invalidating_conditions=["Clear directional breakout", "Volume surge with direction"],
            confidence=round(max(0.1, 0.5 - abs(confluence.score) * 0.2), 2),
            relevant_timeframe=context.timeframe,
            explanation="Market may continue ranging",
        ))

    if context.volatility.regime in (VolatilityRegime.CONTRACTING, VolatilityRegime.LOW):
        scenarios.append(Scenario(
            scenario_type=ScenarioType.BREAKOUT,
            name="Volatility Breakout (Direction Uncertain)",
            supporting_evidence=[ScenarioEvidence(domain="volatility", supports=True,
                                                  description=f"Volatility: {context.volatility.regime.value}")],
            conflicting_evidence=[], invalidating_conditions=["Direction uncertain from volatility alone"],
            confidence=0.3, relevant_timeframe=context.timeframe,
            explanation="Contracting volatility may precede directional move",
        ))

    if evidence.total_evidence < 4 or context.data_quality.quality in (DataQuality.INSUFFICIENT, DataQuality.MISSING):
        scenarios.append(Scenario(
            scenario_type=ScenarioType.INSUFFICIENT_EVIDENCE, name="Insufficient Evidence",
            supporting_evidence=[], conflicting_evidence=[], invalidating_conditions=[],
            confidence=0.0, relevant_timeframe=context.timeframe,
            explanation=f"Only {evidence.total_evidence} evidence items — unreliable",
        ))

    primary = max(scenarios, key=lambda s: s.confidence) if scenarios else Scenario(
        scenario_type=ScenarioType.INSUFFICIENT_EVIDENCE, name="No Scenarios",
        supporting_evidence=[], conflicting_evidence=[], invalidating_conditions=[],
        confidence=0.0, relevant_timeframe=context.timeframe, explanation="No scenarios generated",
    )
    return ScenarioResult(scenarios=scenarios, primary_scenario=primary, methodology_version=METHODOLOGY_VERSION)


# ============================================================
# Uncertainty, Provenance, Research Integrity
# ============================================================


def _detect_uncertainty(context: MarketContext, evidence: EvidenceAggregation) -> list[str]:
    u: list[str] = []
    if context.data_quality.candle_count < 50:
        u.append(f"Limited history ({context.data_quality.candle_count} candles)")
    if context.data_quality.stale:
        u.append("Provider data may be stale")
    if evidence.unavailable_count > 0:
        u.append(f"{evidence.unavailable_count} evidence source(s) unavailable")
    if context.multi_timeframe.alignment in (AlignmentState.CONFLICTING, AlignmentState.INSUFFICIENT_DATA):
        u.append("Multi-timeframe alignment unclear")
    if evidence.total_evidence > 0 and abs(evidence.bullish_pct - evidence.bearish_pct) < 0.15:
        u.append("Evidence closely balanced between bullish and bearish")
    if context.volatility.regime == VolatilityRegime.HIGH:
        u.append("Elevated volatility increases uncertainty")
    if context.trend.direction == TrendDirection.TRANSITION:
        u.append("Market in transition — direction unclear")
    return u


def _build_provenance(context: MarketContext) -> DataProvenance:
    now = datetime.now(timezone.utc).isoformat()
    freshness = "stale" if context.data_quality.stale else (
        "limited" if context.data_quality.quality == DataQuality.INSUFFICIENT else "fresh")
    return DataProvenance(
        provider=context.data_quality.provider, asset=context.data_quality.asset,
        timeframe=context.data_quality.timeframe, retrieved_at=now,
        data_timestamp=context.data_quality.latest_timestamp, freshness=freshness,
        data_quality=context.data_quality.quality.value, is_demo="demo" in context.data_quality.provider.lower(),
        methodology_version=METHODOLOGY_VERSION,
    )


def _build_research_integrity() -> ResearchIntegrity:
    return ResearchIntegrity(
        no_deployment_signal=True, no_predictions=True, no_trading_signals=True,
        deterministic=True, no_future_data=True, classification="ANALYTICAL_RESEARCH",
        disclaimer="This is descriptive analytical research. It does not predict future prices or provide trading recommendations.",
    )


# ============================================================
# Main Entry Point
# ============================================================


def analyze_market_full(context: MarketContext) -> MarketAnalysis:
    evidence = aggregate_evidence(context)
    confluence = compute_confluence(evidence)
    conflicts = detect_enhanced_conflicts(context, evidence)
    scenarios = generate_scenarios(context, confluence, evidence)
    uncertainty = _detect_uncertainty(context, evidence)
    provenance = _build_provenance(context)
    integrity = _build_research_integrity()
    now = datetime.now(timezone.utc).isoformat()
    return MarketAnalysis(
        asset=context.asset, timeframe=context.timeframe, timestamp=now,
        data_quality=context.data_quality, market_regime=context.structure.regime.value,
        trend=context.trend, momentum=context.momentum, volatility=context.volatility,
        volume=context.volume, structure=context.structure, liquidity=context.liquidity,
        multi_timeframe=context.multi_timeframe, confluence=confluence, scenarios=scenarios,
        conflicts=conflicts, evidence=evidence, uncertainty=uncertainty,
        methodology_version=METHODOLOGY_VERSION, provenance=provenance,
        research_integrity=integrity,
    )
