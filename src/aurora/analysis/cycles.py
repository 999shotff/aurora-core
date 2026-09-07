"""Unified Analysis — cycle/hypothesis framework.

Reusable interface for temporal/cyclical analysis methods.
All results are classified as HYPOTHESIS — never OBSERVED.

Methods include: Gann cycles, seasonality, calendar effects,
spectral analysis, Fourier analysis, recurring patterns.

NO_DEPLOYMENT_SIGNAL. No guaranteed predictions.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aurora.analysis.contracts import (
    AnalysisInput,
    AnalysisSourceType,
    EvidenceClass,
    MethodologyType,
)


# ============================================================
# Cycle Analysis Types
# ============================================================


class CycleMethod(str, Enum):
    GANN_TIME = "GANN_TIME"
    GANN_GEOMETRIC = "GANN_GEOMETRIC"
    SEASONALITY = "SEASONALITY"
    CALENDAR_EFFECT = "CALENDAR_EFFECT"
    SPECTRAL = "SPECTRAL"
    FOURIER = "FOURIER"
    HISTORICAL_PATTERN = "HISTORICAL_PATTERN"
    CUSTOM = "CUSTOM"


class HypothesisStatus(str, Enum):
    UNTESTED = "UNTESTED"
    EXPLORATORY = "EXPLORATORY"
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNRESOLVED = "UNRESOLVED"


# ============================================================
# Cycle Analysis Result
# ============================================================


class CycleAnalysisResult(BaseModel):
    """Output from a cycle/hypothesis analysis provider."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str = Field(default_factory=lambda: f"cycle-{uuid.uuid4().hex[:12]}")
    method: CycleMethod
    hypothesis: str
    input_window: str = ""
    observed_pattern: str = ""
    validation_method: str = ""
    in_sample_result: str = ""
    out_of_sample_result: str = ""
    robustness: str = ""
    sample_size: int | None = None
    limitations: list[str] = Field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.UNTESTED
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Cycle Analysis Provider Interface
# ============================================================


class CycleAnalysisProvider:
    """Base interface for cycle/hypothesis analysis providers."""

    def health(self) -> str:
        return "READY"

    def capabilities(self) -> dict:
        return {"methods": [m.value for m in CycleMethod]}

    def analyze(
        self,
        method: CycleMethod,
        asset: str,
        data: dict[str, Any],
        window: str = "1y",
    ) -> CycleAnalysisResult:
        """Run cycle analysis. Returns HYPOTHESIS-classified result."""
        return CycleAnalysisResult(
            method=method,
            hypothesis=f"{method.value} analysis for {asset}",
            input_window=window,
            status=HypothesisStatus.UNTESTED,
            limitations=["Deterministic stub — no real cycle analysis implemented"],
        )

    def to_analysis_input(self, result: CycleAnalysisResult) -> AnalysisInput:
        """Convert cycle result to unified AnalysisInput envelope."""
        return AnalysisInput(
            source_type=AnalysisSourceType.CYCLE_ANALYSIS,
            source_id=result.analysis_id,
            evidence_class=EvidenceClass.HYPOTHESIS,
            methodology=MethodologyType.HYPOTHETICAL,
            observations={
                "method": result.method.value,
                "hypothesis": result.hypothesis,
                "status": result.status.value,
                "in_sample": result.in_sample_result,
                "out_of_sample": result.out_of_sample_result,
            },
            confidence=result.confidence,
            sample_size=result.sample_size,
            limitations=result.limitations,
            methodology_description=f"{result.method.value} cycle analysis",
            provenance_chain=[f"cycle_provider:{result.method.value}"],
        )


# ============================================================
# Gann Cycle Provider
# ============================================================


class GannCycleProvider(CycleAnalysisProvider):
    """Gann time cycle and geometric analysis.

    Results are HYPOTHESIS — never guaranteed predictions.
    """

    def analyze(
        self,
        method: CycleMethod,
        asset: str,
        data: dict[str, Any],
        window: str = "1y",
    ) -> CycleAnalysisResult:
        return CycleAnalysisResult(
            method=method,
            hypothesis=f"Gann {method.value} analysis suggests potential cycle inflection for {asset}",
            input_window=window,
            observed_pattern="Pattern detection requires real implementation",
            validation_method="In-sample backtest",
            in_sample_result="EXPLORATORY",
            out_of_sample_result="UNTESTED",
            robustness="Low — stub implementation",
            status=HypothesisStatus.EXPLORATORY,
            confidence=0.1,
            limitations=[
                "Stub implementation — no real Gann analysis",
                "All Gann results are HYPOTHESIS, not evidence",
                "Requires real cycle detection implementation",
            ],
            metadata={"provider": "gann_stub"},
        )


# ============================================================
# Seasonality Provider
# ============================================================


class SeasonalityProvider(CycleAnalysisProvider):
    """Calendar/seasonality effect analysis.

    Results are HYPOTHESIS — never guaranteed predictions.
    """

    def analyze(
        self,
        method: CycleMethod,
        asset: str,
        data: dict[str, Any],
        window: str = "1y",
    ) -> CycleAnalysisResult:
        return CycleAnalysisResult(
            method=CycleMethod.SEASONALITY,
            hypothesis=f"Seasonality analysis for {asset}",
            input_window=window,
            status=HypothesisStatus.EXPLORATORY,
            confidence=0.1,
            limitations=[
                "Stub implementation — no real seasonality data",
                "Calendar effects are HYPOTHESIS, not guaranteed patterns",
            ],
            metadata={"provider": "seasonality_stub"},
        )
