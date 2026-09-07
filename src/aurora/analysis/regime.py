"""Unified Analysis — regime detection.

Deterministic/statistical regime classification.
Extends existing MarketRegime from features/structure.py.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegimeType(str, Enum):
    """Extended regime classification."""

    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGE_BOUND = "RANGE_BOUND"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    EXPANSION = "EXPANSION"
    CONTRACTION = "CONTRACTION"
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    STRUCTURAL_BREAK = "STRUCTURAL_BREAK"
    UNKNOWN = "UNKNOWN"


class RegimeAnalysis(BaseModel):
    """Regime detection result."""

    model_config = ConfigDict(extra="forbid")

    regime: RegimeType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_data: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    transition_from: RegimeType | None = None


def detect_regime(
    market_context: dict[str, Any],
) -> RegimeAnalysis:
    """Detect market regime from existing MarketContext data.

    Deterministic — uses existing structure/volatility/trend data.
    """
    trend = market_context.get("trend", {})
    volatility = market_context.get("volatility", {})
    structure = market_context.get("structure", {})

    trend_direction = trend.get("direction", "neutral")
    trend_strength = trend.get("strength", 0.0)
    vol_regime = volatility.get("regime", "normal")
    structure_regime = structure.get("regime", "ranging")

    if vol_regime == "expansion":
        regime = RegimeType.EXPANSION
    elif vol_regime == "contraction":
        regime = RegimeType.CONTRACTION
    elif vol_regime == "high":
        regime = RegimeType.HIGH_VOLATILITY
    elif vol_regime == "low":
        regime = RegimeType.LOW_VOLATILITY
    elif trend_direction == "bullish" and trend_strength > 0.6:
        regime = RegimeType.TRENDING_UP
    elif trend_direction == "bearish" and trend_strength > 0.6:
        regime = RegimeType.TRENDING_DOWN
    elif structure_regime == "ranging":
        regime = RegimeType.RANGE_BOUND
    else:
        regime = RegimeType.UNKNOWN

    return RegimeAnalysis(
        regime=regime,
        confidence=0.5,
        supporting_data={
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "volatility_regime": vol_regime,
            "structure_regime": structure_regime,
        },
        limitations=[
            "Regime classification is deterministic — not a prediction",
            "Regime is context, not a forecast",
        ],
    )
