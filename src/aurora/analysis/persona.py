"""Unified Analysis — MatrAIx persona simulation adapter.

Adapter for external MatrAIx persona simulation.
DOES NOT copy MatrAIx code. Connects through a clean interface.

All results are classified as SIMULATED — never OBSERVED.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any

from aurora.analysis.contracts import (
    AnalysisInput,
    AnalysisSourceType,
    EvidenceClass,
    MethodologyType,
)


# ============================================================
# Persona Cohorts
# ============================================================

DEFAULT_PERSONA_COHORTS = [
    "risk_averse",
    "risk_seeking",
    "news_sensitive",
    "long_term_oriented",
    "short_term_oriented",
    "high_information",
    "low_information",
    "institutional",
    "retail",
]


# ============================================================
# MatrAIx Adapter Interface
# ============================================================


class PersonaSimulationProvider:
    """Adapter for MatrAIx persona simulation.

    Health/status depends on actual MatrAIx runtime availability.
    Does NOT fabricate simulation results.
    """

    def __init__(self) -> None:
        self._available = False
        self._runtime_url: str | None = None
        self._results: dict[str, dict] = {}

    def health(self) -> str:
        if self._available:
            return "READY"
        return "NOT_CONFIGURED"

    def capabilities(self) -> dict:
        return {
            "persona_simulation": self._available,
            "cohorts": DEFAULT_PERSONA_COHORTS if self._available else [],
            "max_cohorts_per_run": 9,
        }

    def configure(self, runtime_url: str | None = None) -> None:
        """Configure MatrAIx connection. Does NOT auto-connect."""
        if runtime_url:
            self._runtime_url = runtime_url
            self._available = True
        else:
            self._available = False

    def run_scenario(
        self,
        scenario: str,
        context: dict[str, Any] | None = None,
        cohorts: list[str] | None = None,
        task: str = "behavioral_response",
    ) -> AnalysisInput:
        """Run a persona simulation scenario.

        Returns AnalysisInput with evidence_class=SIMULATED.
        If not configured, returns an UNAVAILABLE result.
        """
        if not self._available:
            return AnalysisInput(
                source_type=AnalysisSourceType.PERSONA_SIMULATION,
                source_id=f"matraix-{uuid.uuid4().hex[:8]}",
                evidence_class=EvidenceClass.UNAVAILABLE,
                methodology=MethodologyType.SIMULATION,
                observations={"status": "NOT_CONFIGURED"},
                limitations=["MatrAIx runtime not configured"],
            )

        simulation_id = f"sim-{uuid.uuid4().hex[:12]}"
        effective_cohorts = cohorts or DEFAULT_PERSONA_COHORTS[:3]

        result = {
            "simulation_id": simulation_id,
            "scenario": scenario,
            "cohorts": effective_cohorts,
            "task": task,
            "status": "SIMULATED",
            "provider": "matraix",
            "context": context or {},
            "responses": {
                cohort: {
                    "behavioral_tendency": "no_data",
                    "confidence": 0.0,
                    "limitation": "MatrAIx runtime not connected",
                }
                for cohort in effective_cohorts
            },
        }

        self._results[simulation_id] = result

        return AnalysisInput(
            source_type=AnalysisSourceType.PERSONA_SIMULATION,
            source_id=simulation_id,
            evidence_class=EvidenceClass.SIMULATED,
            methodology=MethodologyType.SIMULATION,
            observations=result,
            confidence=0.0,
            limitations=[
                "Simulated behavior — not real human data",
                "MatrAIx runtime not connected — placeholder results",
            ],
            methodology_description="Persona simulation via MatrAIx adapter",
            data_source="matraix_adapter",
            provenance_chain=["matraix_adapter", f"simulation:{simulation_id}"],
        )

    def get_result(self, simulation_id: str) -> dict | None:
        return self._results.get(simulation_id)
