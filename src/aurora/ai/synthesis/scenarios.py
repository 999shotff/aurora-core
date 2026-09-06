"""Scenario Analysis — bounded conditional scenarios.

Scenarios are conditional, not predictions.
Each lists assumptions, evidence basis, triggers, and implications.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib

from aurora.ai.synthesis.schemas import (
    ConfidenceLevel,
    EvidenceAssessment,
    FindingAssessment,
    Scenario,
)


def generate_scenarios(
    question: str,
    findings: list[FindingAssessment],
    evidence: list[EvidenceAssessment],
    contradictions_exist: bool,
) -> list[Scenario]:
    """Generate bounded conditional scenarios from findings."""
    scenarios: list[Scenario] = []

    supported = [f for f in findings if f.status == "SUPPORTED"]
    unsupported = [f for f in findings if f.status in ("UNRESOLVED", "CONTRADICTED")]

    if supported:
        scenarios.append(Scenario(
            scenario_id=_scenario_id(question, "A"),
            label="If current evidence holds",
            assumptions=["Existing evidence remains valid", "No new contradictory data emerges"],
            evidence_basis=[eid for f in supported for eid in f.supporting_evidence][:5],
            trigger_conditions=["Evidence quality maintained", "Source remains operational"],
            implications=[f.statement for f in supported[:3]],
            uncertainty=[f.statement for f in unsupported[:2]] if unsupported else [],
        ))

    if contradictions_exist:
        scenarios.append(Scenario(
            scenario_id=_scenario_id(question, "B"),
            label="If contradictions are resolved in favor of conflicting evidence",
            assumptions=["Conflicting source proves more reliable", "Provenance evaluation favors alternative"],
            evidence_basis=[eid for f in unsupported for eid in f.supporting_evidence][:5],
            trigger_conditions=["Source reliability reassessed", "New corroborating evidence"],
            implications=["Previous conclusion may need revision"],
            uncertainty=["Resolution basis depends on source quality assessment"],
        ))

    scenarios.append(Scenario(
        scenario_id=_scenario_id(question, "C"),
        label="If additional evidence becomes available",
        assumptions=["New evidence is relevant and reliable"],
        evidence_basis=[],
        trigger_conditions=["New data source connected", "Additional observations collected"],
        implications=["Uncertainty may decrease", "Hypothesis ranking may change"],
        uncertainty=["Cannot predict what new evidence will show"],
    ))

    return scenarios


def _scenario_id(question: str, label: str) -> str:
    h = hashlib.sha256(f"{question}:scenario:{label}".encode()).hexdigest()[:12]
    return f"scn-{h}"
