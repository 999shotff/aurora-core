"""Unified Analysis — Orchestrator.

Single pipeline that reuses LLM-1→LLM-5, Market Observatory,
Evidence Graph, and new analysis sources.

NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aurora.analysis.assessment import UnifiedAssessment, build_unified_assessment
from aurora.analysis.contracts import (
    AnalysisCollection,
    AnalysisInput,
    AnalysisSourceType,
    EvidenceClass,
    MethodologyType,
)
from aurora.analysis.cycles import CycleAnalysisProvider, GannCycleProvider, SeasonalityProvider
from aurora.analysis.persona import PersonaSimulationProvider
from aurora.analysis.regime import RegimeType, detect_regime

logger = logging.getLogger(__name__)


class UnifiedOrchestrator:
    """Orchestrates all analysis sources into a unified assessment.

    Reuses existing LLM-1→LLM-5 pipeline.
    Does NOT duplicate existing investigation/synthesis logic.
    """

    def __init__(self) -> None:
        self._persona = PersonaSimulationProvider()
        self._gann = GannCycleProvider()
        self._seasonality = SeasonalityProvider()
        self._analysis_store: dict[str, UnifiedAssessment] = {}

    @property
    def persona_provider(self) -> PersonaSimulationProvider:
        return self._persona

    def health(self) -> dict:
        return {
            "status": "healthy",
            "service": "unified-orchestrator",
            "version": "0.1.0",
            "persona_status": self._persona.health(),
            "gann_status": self._gann.health(),
            "seasonality_status": self._seasonality.health(),
        }

    def analyze(
        self,
        question: str,
        market_context: dict[str, Any] | None = None,
        indicator_data: dict[str, Any] | None = None,
        structure_data: dict[str, Any] | None = None,
        research_evidence: list[dict] | None = None,
        memory_items: list[dict] | None = None,
        run_persona: bool = False,
        run_cycles: bool = False,
        asset: str | None = None,
        timeframe: str | None = None,
        domain: str = "general",
    ) -> UnifiedAssessment:
        """Run unified analysis pipeline.

        Collects inputs from all available sources,
        builds AnalysisCollection, produces UnifiedAssessment.
        """
        start = time.monotonic()
        inputs: list[AnalysisInput] = []

        # 1. Market indicators
        if indicator_data:
            inputs.append(self._build_indicator_input(indicator_data, asset, timeframe))

        # 2. Market structure
        if structure_data:
            inputs.append(self._build_structure_input(structure_data, asset, timeframe))

        # 3. Market context
        if market_context:
            inputs.append(self._build_context_input(market_context, asset, timeframe))

        # 4. Regime detection
        if market_context:
            regime = detect_regime(market_context)
            inputs.append(AnalysisInput(
                source_type=AnalysisSourceType.REGIME_DETECTION,
                source_id=f"regime-{asset or 'unknown'}",
                evidence_class=EvidenceClass.DERIVED,
                methodology=MethodologyType.DETERMINISTIC,
                regime=regime.regime.value,
                confidence=regime.confidence,
                observations=regime.supporting_data,
                limitations=regime.limitations,
            ))

        # 5. Research evidence
        if research_evidence:
            for ev in research_evidence[:5]:
                inputs.append(AnalysisInput(
                    source_type=AnalysisSourceType.RESEARCH_EVIDENCE,
                    source_id=ev.get("id", f"research-{len(inputs)}"),
                    evidence_class=EvidenceClass.OBSERVED,
                    methodology=MethodologyType.HUMAN_INPUT,
                    observations=ev,
                    confidence=ev.get("confidence", 0.5),
                ))

        # 6. Memory retrieval
        if memory_items:
            for mem in memory_items[:3]:
                inputs.append(AnalysisInput(
                    source_type=AnalysisSourceType.MEMORY_RETRIEVAL,
                    source_id=mem.get("id", f"mem-{len(inputs)}"),
                    evidence_class=EvidenceClass.DERIVED,
                    methodology=MethodologyType.DETERMINISTIC,
                    observations=mem,
                    confidence=0.5,
                ))

        # 7. Persona simulation (if requested)
        if run_persona:
            sim_result = self._persona.run_scenario(
                scenario=f"Market scenario for {asset or 'unknown'}",
                context={"asset": asset, "timeframe": timeframe, "market": market_context or {}},
            )
            inputs.append(sim_result)

        # 8. Cycle analysis (if requested)
        if run_cycles:
            gann_result = self._gann.analyze(
                method=__import__("aurora.analysis.cycles", fromlist=["CycleMethod"]).CycleMethod.GANN_TIME,
                asset=asset or "unknown",
                data=market_context or {},
            )
            inputs.append(self._gann.to_analysis_input(gann_result))

            season_result = self._seasonality.analyze(
                method=__import__("aurora.analysis.cycles", fromlist=["CycleMethod"]).CycleMethod.SEASONALITY,
                asset=asset or "unknown",
                data=market_context or {},
            )
            inputs.append(self._seasonality.to_analysis_input(season_result))

        # Build collection and assessment
        collection = AnalysisCollection(
            question=question,
            inputs=inputs,
            asset=asset,
            timeframe=timeframe,
            domain=domain,
        )

        assessment = build_unified_assessment(collection)
        assessment.computation_time_ms = (time.monotonic() - start) * 1000

        self._analysis_store[assessment.assessment_id] = assessment

        logger.info(
            "Unified assessment %s: bias=%s strength=%s confidence=%s inputs=%d (%.0fms)",
            assessment.assessment_id,
            assessment.directional_bias.value,
            assessment.strength.value,
            assessment.confidence,
            assessment.total_inputs,
            assessment.computation_time_ms,
        )

        return assessment

    def get_assessment(self, assessment_id: str) -> UnifiedAssessment | None:
        return self._analysis_store.get(assessment_id)

    def _build_indicator_input(
        self, data: dict[str, Any], asset: str | None, timeframe: str | None
    ) -> AnalysisInput:
        return AnalysisInput(
            source_type=AnalysisSourceType.MARKET_INDICATORS,
            source_id=f"indicators-{asset or 'unknown'}",
            evidence_class=EvidenceClass.DERIVED,
            methodology=MethodologyType.DETERMINISTIC,
            asset=asset,
            timeframe=timeframe,
            indicators=data.get("indicators", {}),
            features=data.get("features", {}),
            observations=data.get("summary", {}),
            confidence=0.7,
            limitations=["Indicator values are derived from historical data"],
        )

    def _build_structure_input(
        self, data: dict[str, Any], asset: str | None, timeframe: str | None
    ) -> AnalysisInput:
        return AnalysisInput(
            source_type=AnalysisSourceType.MARKET_STRUCTURE,
            source_id=f"structure-{asset or 'unknown'}",
            evidence_class=EvidenceClass.DERIVED,
            methodology=MethodologyType.DETERMINISTIC,
            asset=asset,
            timeframe=timeframe,
            structure=data,
            observations={
                "regime": data.get("regime", "unknown"),
                "break_count": len(data.get("breaks", [])),
                "sr_levels_count": len(data.get("support_resistance", [])),
            },
            confidence=0.6,
            limitations=["Structure analysis is deterministic — not a prediction"],
        )

    def _build_context_input(
        self, data: dict[str, Any], asset: str | None, timeframe: str | None
    ) -> AnalysisInput:
        return AnalysisInput(
            source_type=AnalysisSourceType.MARKET_CONTEXT,
            source_id=f"context-{asset or 'unknown'}",
            evidence_class=EvidenceClass.DERIVED,
            methodology=MethodologyType.DETERMINISTIC,
            asset=asset,
            timeframe=timeframe,
            observations=data.get("explanation", {}),
            features=data.get("trend", {}),
            confidence=0.6,
            limitations=["Market context is derived from historical data"],
        )
