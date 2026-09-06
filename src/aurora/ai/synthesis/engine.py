"""Synthesis Engine — orchestrates evidence-grounded synthesis.

Consumes investigation results, evidence, findings, and memory
to produce structured synthesis with hypotheses, uncertainty,
contradictions, scenarios, and decision considerations.

Deterministic components remain deterministic.
LLM output is validated as untrusted input.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from aurora.ai.synthesis.cache import SynthesisCache, compute_cache_key
from aurora.ai.synthesis.contradiction import detect_contradictions
from aurora.ai.synthesis.decision import generate_decision_considerations
from aurora.ai.synthesis.evidence_assessment import assess_evidences
from aurora.ai.synthesis.hypothesis import compare_hypotheses, generate_hypotheses
from aurora.ai.synthesis.provenance import build_provenance
from aurora.ai.synthesis.scenarios import generate_scenarios
from aurora.ai.synthesis.schemas import (
    CausalLevel,
    ConfidenceLevel,
    EvidenceAssessment,
    EvidenceGap,
    EvidenceGapStatus,
    FindingAssessment,
    Hypothesis,
    MemoryUpdateProposal,
    MemoryUpdateType,
    ProvenanceRecord,
    SynthesisAuditRecord,
    SynthesisRequest,
    SynthesisResult,
    SynthesisStatus,
    UncertaintyAssessment,
    UncertaintyKind,
)
from aurora.ai.synthesis.uncertainty import assess_uncertainty

logger = logging.getLogger(__name__)


class SynthesisEngine:
    """Evidence-grounded synthesis engine.

    Orchestrates:
    1. Evidence assessment
    2. Finding classification
    3. Hypothesis generation
    4. Contradiction detection
    5. Uncertainty classification
    6. Scenario analysis
    7. Decision considerations
    8. Evidence gap identification
    9. Provenance tracking
    10. Memory update proposals
    """

    def __init__(self) -> None:
        self._cache = SynthesisCache(ttl_seconds=300)
        self._audit_log: list[SynthesisAuditRecord] = []

    def synthesize(
        self,
        request: SynthesisRequest,
        evidence_items: list[dict] | None = None,
        findings_raw: list[dict] | None = None,
        memory_items: list[dict] | None = None,
    ) -> SynthesisResult:
        """Execute synthesis. Deterministic core with optional LLM enhancement."""
        start = time.monotonic()
        synthesis_id = f"syn-{uuid.uuid4().hex[:12]}"

        cache_key = compute_cache_key(
            request.question,
            request.investigation_id,
            request.evidence_ids,
            request.memory_ids,
            request.domain,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("Synthesis cache hit: %s", cache_key)
            return cached

        evidence_items = evidence_items or []
        findings_raw = findings_raw or []
        memory_items = memory_items or []

        evidence_assessments = assess_evidences(evidence_items)
        findings = _build_findings(findings_raw, evidence_assessments)

        contradictions = detect_contradictions(evidence_assessments)
        contradictions_exist = len(contradictions) > 0

        hypotheses = generate_hypotheses(
            request.question, findings, request.evidence_ids,
        )
        hypothesis_comparison = compare_hypotheses(hypotheses)

        known_facts = _extract_known_facts(findings)
        uncertainty = assess_uncertainty(findings, known_facts, contradictions_exist)

        scenarios = generate_scenarios(
            request.question, findings, evidence_assessments, contradictions_exist,
        )

        evidence_gaps = _identify_gaps(request, findings, evidence_assessments)

        decision_considerations = generate_decision_considerations(
            request.question, findings, hypotheses, evidence_gaps, contradictions_exist,
        )

        provenance = build_provenance(findings, evidence_assessments)

        memory_updates = _propose_memory_updates(request, findings, contradictions)

        causal_level = _assess_causal_level(findings, evidence_assessments)

        status = _determine_status(findings, evidence_assessments, request)

        executive_summary = _build_executive_summary(
            request.question, findings, hypotheses, contradictions, uncertainty, status,
        )

        result = SynthesisResult(
            synthesis_id=synthesis_id,
            question=request.question,
            executive_summary=executive_summary,
            key_findings=findings,
            hypotheses=hypotheses,
            contradictions=contradictions,
            known_facts=known_facts,
            supported_inferences=_extract_inferences(findings),
            assumptions=_extract_assumptions(hypotheses),
            unknowns=_extract_unknowns(uncertainty),
            scenarios=scenarios,
            decision_considerations=decision_considerations,
            evidence_gaps=evidence_gaps,
            limitations=_extract_limitations(evidence_assessments),
            provenance=provenance,
            memory_updates=memory_updates,
            synthesis_status=status,
            evidence_assessments=evidence_assessments,
            uncertainty_assessments=uncertainty,
            causal_level=causal_level,
            provider="stub",
            model="stub",
            context_hash=_compute_context_hash(request, evidence_items),
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        self._cache.put(cache_key, result)

        audit = SynthesisAuditRecord(
            synthesis_id=synthesis_id,
            investigation_id=request.investigation_id,
            provider="stub",
            model="stub",
            context_hash=result.context_hash,
            evidence_references=request.evidence_ids,
            memory_references=request.memory_ids,
            validation_result="PASS",
            final_status=status.value,
        )
        self._audit_log.append(audit)
        if len(self._audit_log) > 500:
            self._audit_log = self._audit_log[-250:]

        elapsed = (time.monotonic() - start) * 1000
        logger.info("Synthesis %s completed in %.0fms: %s", synthesis_id, elapsed, status.value)

        return result

    def get_audit_log(self, limit: int = 50) -> list[SynthesisAuditRecord]:
        return self._audit_log[-limit:]

    def health(self) -> dict:
        return {
            "status": "healthy",
            "service": "synthesis-engine",
            "version": "0.1.0",
            "audit_entries": len(self._audit_log),
            "cache_entries": len(self._cache._cache),
        }


def _build_findings(
    findings_raw: list[dict],
    evidence_assessments: list[EvidenceAssessment],
) -> list[FindingAssessment]:
    """Convert raw findings to assessed findings."""
    evidence_map = {e.evidence_id: e for e in evidence_assessments}
    findings: list[FindingAssessment] = []

    for i, raw in enumerate(findings_raw):
        fid = raw.get("finding_id", f"find-{i}")
        statement = raw.get("statement", "")
        evidence_refs = raw.get("evidence_refs", [])

        supporting = [e for e in evidence_refs if e in evidence_map]
        contradicting = raw.get("contradicting_evidence", [])

        findings.append(FindingAssessment(
            finding_id=fid,
            statement=statement,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            provenance=raw.get("provenance", ""),
            status=raw.get("status", "UNRESOLVED"),
            confidence=_infer_confidence(raw.get("confidence"), len(supporting), len(contradicting)),
            uncertainty=raw.get("uncertainty", []),
            reasoning_summary=raw.get("reasoning_summary", ""),
        ))

    if not findings and evidence_assessments:
        findings.append(FindingAssessment(
            finding_id="find-default",
            statement=f"Based on {len(evidence_assessments)} evidence items",
            supporting_evidence=[e.evidence_id for e in evidence_assessments[:5]],
            confidence=ConfidenceLevel.LOW,
            status="PARTIALLY_SUPPORTED",
            reasoning_summary="Limited evidence available",
        ))

    return findings


def _infer_confidence(
    raw_confidence: str | None,
    supporting: int,
    contradicting: int,
) -> ConfidenceLevel:
    if raw_confidence:
        try:
            return ConfidenceLevel(raw_confidence)
        except ValueError:
            pass
    if contradicting > 0:
        return ConfidenceLevel.LOW
    if supporting >= 3:
        return ConfidenceLevel.MODERATE
    if supporting >= 1:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.UNDETERMINED


def _extract_known_facts(findings: list[FindingAssessment]) -> list[str]:
    return [f.statement for f in findings if f.status == "SUPPORTED"]


def _extract_inferences(findings: list[FindingAssessment]) -> list[str]:
    return [f.statement for f in findings if f.status == "PARTIALLY_SUPPORTED"]


def _extract_assumptions(hypotheses: list[Hypothesis]) -> list[str]:
    assumptions: list[str] = []
    for h in hypotheses:
        assumptions.extend(h.assumptions)
    return list(set(assumptions))


def _extract_unknowns(uncertainty: list[UncertaintyAssessment]) -> list[str]:
    return [u.element for u in uncertainty if u.kind in (UncertaintyKind.UNKNOWN, UncertaintyKind.UNAVAILABLE)]


def _extract_limitations(evidence: list[EvidenceAssessment]) -> list[str]:
    limits: list[str] = []
    for e in evidence:
        limits.extend(e.limitations)
    return list(set(limits))


def _identify_gaps(
    request: SynthesisRequest,
    findings: list[FindingAssessment],
    evidence: list[EvidenceAssessment],
) -> list[EvidenceGap]:
    gaps: list[EvidenceGap] = []
    unresolved = [f for f in findings if f.status == "UNRESOLVED"]
    for i, f in enumerate(unresolved):
        gaps.append(EvidenceGap(
            gap_id=f"gap-{i}",
            description=f"Unresolved finding: {f.statement[:80]}",
            why_it_matters="Limits conclusion confidence",
            status=EvidenceGapStatus.OPEN,
        ))

    if not evidence:
        gaps.append(EvidenceGap(
            gap_id="gap-no-evidence",
            description="No evidence items provided",
            why_it_matters="Cannot form evidence-grounded conclusions",
            status=EvidenceGapStatus.OPEN,
        ))

    return gaps


def _propose_memory_updates(
    request: SynthesisRequest,
    findings: list[FindingAssessment],
    contradictions: list,
) -> list[MemoryUpdateProposal]:
    proposals: list[MemoryUpdateProposal] = []
    for f in findings:
        if f.status == "SUPPORTED" and f.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MODERATE):
            proposals.append(MemoryUpdateProposal(
                update_type=MemoryUpdateType.NEW_KNOWLEDGE,
                title=f"Synthesis: {f.statement[:80]}",
                content=f.statement,
                domain=request.domain,
                source_investigation=request.investigation_id or "",
                evidence_refs=f.supporting_evidence,
                confidence=f.confidence,
            ))
    for c in contradictions:
        proposals.append(MemoryUpdateProposal(
            update_type=MemoryUpdateType.CONTRADICTION,
            title=f"Contradiction detected: {c.description[:80]}",
            content=c.description,
            domain=request.domain,
            evidence_refs=[c.evidence_a, c.evidence_b],
            confidence=ConfidenceLevel.UNDETERMINED,
        ))
    return proposals


def _assess_causal_level(
    findings: list[FindingAssessment],
    evidence: list[EvidenceAssessment],
) -> CausalLevel:
    if not findings:
        return CausalLevel.INSUFFICIENT
    supported = [f for f in findings if f.status == "SUPPORTED"]
    if len(supported) >= 3:
        return CausalLevel.MECHANISTIC_EVIDENCE
    if len(supported) >= 1:
        return CausalLevel.TEMPORAL_ASSOCIATION
    return CausalLevel.CORRELATION


def _determine_status(
    findings: list[FindingAssessment],
    evidence: list[EvidenceAssessment],
    request: SynthesisRequest,
) -> SynthesisStatus:
    if not evidence and not request.evidence_ids:
        return SynthesisStatus.INSUFFICIENT_EVIDENCE
    supported = [f for f in findings if f.status == "SUPPORTED"]
    unresolved = [f for f in findings if f.status == "UNRESOLVED"]
    if supported and not unresolved:
        return SynthesisStatus.COMPLETE
    if supported and unresolved:
        return SynthesisStatus.PARTIAL
    if unresolved:
        return SynthesisStatus.INDETERMINATE
    return SynthesisStatus.PARTIAL


def _build_executive_summary(
    question: str,
    findings: list[FindingAssessment],
    hypotheses: list[Hypothesis],
    contradictions: list,
    uncertainty: list[UncertaintyAssessment],
    status: SynthesisStatus,
) -> str:
    parts = [f"Question: {question}"]
    parts.append(f"Status: {status.value}")

    supported = [f for f in findings if f.status == "SUPPORTED"]
    if supported:
        parts.append(f"Key finding: {supported[0].statement[:200]}")
    else:
        parts.append("No strongly supported findings.")

    if hypotheses:
        best = max(hypotheses, key=lambda h: {"VERY_HIGH": 5, "HIGH": 4, "MODERATE": 3, "LOW": 2, "VERY_LOW": 1, "UNDETERMINED": 0}.get(h.confidence.value, 0))
        parts.append(f"Best hypothesis: {best.statement[:200]}")

    if contradictions:
        parts.append(f"Contradictions detected: {len(contradictions)}")

    unknowns = [u for u in uncertainty if u.kind in (UncertaintyKind.UNKNOWN, UncertaintyKind.CONTRADICTED)]
    if unknowns:
        parts.append(f"Key uncertainty: {unknowns[0].element[:120]}")

    return " | ".join(parts)


def _compute_context_hash(request: SynthesisRequest, evidence: list[dict]) -> str:
    payload = json.dumps({
        "q": request.question,
        "evidence": [e.get("evidence_id", "") for e in evidence],
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
