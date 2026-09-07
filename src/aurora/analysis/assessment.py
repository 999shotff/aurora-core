"""Unified Analysis — UnifiedAssessment schema and orchestrator.

Single coherent assessment that reuses LLM-1→LLM-5.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aurora.analysis.contracts import (
    AnalysisCollection,
    AnalysisInput,
    AnalysisSourceType,
    EvidenceClass,
)


# ============================================================
# Unified Assessment Enums
# ============================================================


class DirectionalBias(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AssessmentStrength(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


# ============================================================
# Unified Assessment
# ============================================================


class UnifiedAssessment(BaseModel):
    """One unified analytical result for the user.

    Compatible with existing LLM-5 SynthesisResult.
    """

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(
        default_factory=lambda: f"ua-{uuid.uuid4().hex[:12]}"
    )
    question: str
    assessment: str = ""
    directional_bias: DirectionalBias = DirectionalBias.INSUFFICIENT_DATA
    strength: AssessmentStrength = AssessmentStrength.LOW
    confidence: str = "VERY_LOW"

    # Evidence breakdown
    evidence_summary: str = ""
    total_inputs: int = 0
    observed_count: int = 0
    derived_count: int = 0
    simulated_count: int = 0
    hypothesis_count: int = 0
    evidence_agreement_ratio: str = "0/0"

    # Factor breakdown
    supporting_factors: list[str] = Field(default_factory=list)
    contradicting_factors: list[str] = Field(default_factory=list)
    behavioral_factors: list[str] = Field(default_factory=list)
    cycle_hypotheses: list[str] = Field(default_factory=list)

    # Context
    regime: str = "UNKNOWN"
    uncertainty: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    # Provenance
    source_inputs: list[str] = Field(default_factory=list)
    provenance: list[dict[str, Any]] = Field(default_factory=list)

    # Metadata
    asset: str | None = None
    timeframe: str | None = None
    domain: str = "general"
    timestamp: float = Field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )
    computation_time_ms: float = 0.0


# ============================================================
# Unified Assessment Builder
# ============================================================


def build_unified_assessment(
    collection: AnalysisCollection,
    synthesis_result: dict | None = None,
) -> UnifiedAssessment:
    """Build a UnifiedAssessment from AnalysisCollection + optional LLM-5 output.

    Deterministic composition — does NOT fabricate analysis.
    """
    start = time.monotonic()

    observed = [i for i in collection.inputs if i.evidence_class == EvidenceClass.OBSERVED]
    derived = [i for i in collection.inputs if i.evidence_class == EvidenceClass.DERIVED]
    simulated = [i for i in collection.inputs if i.evidence_class == EvidenceClass.SIMULATED]
    hypotheses = [i for i in collection.inputs if i.evidence_class == EvidenceClass.HYPOTHESIS]

    # Extract regime from inputs
    regime_inputs = collection.get_by_type(AnalysisSourceType.REGIME_DETECTION)
    regime = regime_inputs[0].regime if regime_inputs else "UNKNOWN"

    # Extract supporting/contradicting from structure
    structure_inputs = collection.get_by_type(AnalysisSourceType.MARKET_STRUCTURE)
    supporting, contradicting = _extract_structure_factors(structure_inputs)

    # Extract behavioral factors
    behavioral = [
        f"Persona simulation: {s.observations.get('scenario', 'N/A')}"
        for s in simulated
    ]

    # Extract cycle hypotheses
    cycle_factors = [
        f"{c.observations.get('method', 'cycle')}: {c.observations.get('hypothesis', 'N/A')}"
        for c in collection.get_by_type(AnalysisSourceType.CYCLE_ANALYSIS)
    ]

    # Compute agreement
    total = len(collection.inputs)
    agreement = f"{len(observed) + len(derived)}/{total}" if total > 0 else "0/0"

    # Determine bias from indicators
    indicator_inputs = collection.get_by_type(AnalysisSourceType.MARKET_INDICATORS)
    bias = _determine_bias(indicator_inputs, structure_inputs)

    # Determine strength
    strength = _determine_strength(total, len(observed) + len(derived))

    # Determine confidence
    confidence = _determine_confidence(total, len(observed), len(derived))

    # Build limitations
    limitations = []
    if simulated:
        limitations.append(
            f"{len(simulated)} simulated input(s) — NOT real human behavior"
        )
    if hypotheses:
        limitations.append(
            f"{len(hypotheses)} unvalidated hypothesis/hypotheses"
        )

    elapsed = (time.monotonic() - start) * 1000

    return UnifiedAssessment(
        question=collection.question,
        assessment=_build_assessment_text(bias, strength, confidence, regime),
        directional_bias=bias,
        strength=strength,
        confidence=confidence,
        evidence_summary=f"{len(observed)} observed, {len(derived)} derived, {len(simulated)} simulated, {len(hypotheses)} hypothetical",
        total_inputs=total,
        observed_count=len(observed),
        derived_count=len(derived),
        simulated_count=len(simulated),
        hypothesis_count=len(hypotheses),
        evidence_agreement_ratio=agreement,
        supporting_factors=supporting,
        contradicting_factors=contradicting,
        behavioral_factors=behavioral,
        cycle_hypotheses=cycle_factors,
        regime=regime,
        uncertainty=_extract_uncertainties(collection, simulated, hypotheses),
        limitations=limitations,
        source_inputs=[i.source_id for i in collection.inputs],
        provenance=[
            {
                "source_id": i.source_id,
                "source_type": i.source_type.value,
                "evidence_class": i.evidence_class.value,
                "methodology": i.methodology.value,
            }
            for i in collection.inputs
        ],
        asset=collection.asset,
        timeframe=collection.timeframe,
        domain=collection.domain,
        computation_time_ms=elapsed,
    )


def _determine_bias(
    indicators: list[AnalysisInput],
    structure: list[AnalysisInput],
) -> DirectionalBias:
    if not indicators and not structure:
        return DirectionalBias.INSUFFICIENT_DATA

    bullish = 0
    bearish = 0

    for inp in indicators:
        trend = inp.features.get("trend_direction", "")
        if trend == "bullish":
            bullish += 1
        elif trend == "bearish":
            bearish += 1

    for inp in structure:
        regime = inp.structure.get("regime", "")
        if regime == "uptrend":
            bullish += 1
        elif regime == "downtrend":
            bearish += 1

    if bullish > 0 and bearish > 0:
        return DirectionalBias.MIXED
    if bullish > bearish:
        return DirectionalBias.UP
    if bearish > bullish:
        return DirectionalBias.DOWN
    return DirectionalBias.NEUTRAL


def _determine_strength(total: int, real_count: int) -> AssessmentStrength:
    if real_count >= 5:
        return AssessmentStrength.HIGH
    if real_count >= 2:
        return AssessmentStrength.MODERATE
    return AssessmentStrength.LOW


def _determine_confidence(total: int, observed: int, derived: int) -> str:
    real = observed + derived
    if real >= 5 and observed >= 2:
        return "MODERATE"
    if real >= 3:
        return "LOW"
    return "VERY_LOW"


def _extract_structure_factors(
    structure_inputs: list[AnalysisInput],
) -> tuple[list[str], list[str]]:
    supporting: list[str] = []
    contradicting: list[str] = []

    for inp in structure_inputs:
        regime = inp.structure.get("regime", "unknown")
        breaks = inp.structure.get("break_count", 0)
        sr_count = inp.structure.get("sr_levels_count", 0)

        if regime in ("uptrend", "downtrend"):
            supporting.append(f"Structure regime: {regime}")
        else:
            contradicting.append(f"Structure regime: {regime} (no clear direction)")

        if breaks > 0:
            supporting.append(f"{breaks} structure break(s) detected")
        if sr_count > 0:
            supporting.append(f"{sr_count} S/R level(s) active")

    return supporting, contradicting


def _extract_uncertainties(
    collection: AnalysisCollection,
    simulated: list[AnalysisInput],
    hypotheses: list[AnalysisInput],
) -> list[str]:
    uncertainties: list[str] = []

    if not simulated and not hypotheses:
        return ["No behavioral or cycle analysis performed"]

    if simulated:
        uncertainties.append(
            f"{len(simulated)} simulation(s) are SIMULATED — not real behavior"
        )

    if hypotheses:
        uncertainties.append(
            f"{len(hypotheses)} hypothesis/hypotheses are UNTESTED"
        )

    for inp in collection.inputs:
        for lim in inp.limitations:
            uncertainties.append(f"[{inp.source_id}] {lim}")

    return uncertainties[:10]


def _build_assessment_text(
    bias: DirectionalBias,
    strength: AssessmentStrength,
    confidence: str,
    regime: str,
) -> str:
    parts = [f"Directional bias: {bias.value}"]
    parts.append(f"Strength: {strength.value}")
    parts.append(f"Confidence: {confidence}")
    if regime != "UNKNOWN":
        parts.append(f"Regime: {regime}")
    return " | ".join(parts)
