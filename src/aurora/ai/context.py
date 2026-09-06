"""AURORA Reasoning Core — Deterministic Context Builder.

Collects evidence, preserves provenance, enforces limits,
produces stable deterministic serialization and context hash.
"""

from __future__ import annotations

import hashlib
import json

from aurora.ai.schemas import (
    EvidenceRecord,
    ReasoningContext,
    ReasoningDomain,
    ReasoningRequest,
)

MAX_CONTEXT_ITEMS = 50
MAX_EVIDENCE_CLAIM_LENGTH = 2000


def build_context(
    request: ReasoningRequest,
    evidence: list[EvidenceRecord],
    domain_summary: str = "",
) -> ReasoningContext:
    """Build a bounded, deterministic context package.

    1. Filter and validate evidence
    2. Enforce context limits
    3. Produce stable serialization
    4. Generate context hash
    """
    filtered = _filter_evidence(evidence, request)
    trimmed = _enforce_limits(filtered)
    ordered = _order_deterministically(trimmed)

    context = ReasoningContext(
        request_id=request.request_id,
        evidence_items=ordered,
        total_evidence=len(ordered),
        domain_summary=domain_summary,
        constraints=request.constraints,
    )

    context_hash = _compute_hash(context)
    context.context_hash = context_hash

    return context


def _filter_evidence(
    evidence: list[EvidenceRecord],
    request: ReasoningRequest,
) -> list[EvidenceRecord]:
    """Remove invalid, empty, or irrelevant evidence."""
    filtered: list[EvidenceRecord] = []
    for item in evidence:
        if not item.claim or not item.claim.strip():
            continue
        if len(item.claim) > MAX_EVIDENCE_CLAIM_LENGTH:
            item = item.model_copy(update={"claim": item.claim[:MAX_EVIDENCE_CLAIM_LENGTH]})
        if item.domain != request.domain and item.domain != ReasoningDomain.GENERAL:
            continue
        filtered.append(item)
    return filtered


def _enforce_limits(evidence: list[EvidenceRecord]) -> list[EvidenceRecord]:
    """Enforce max context items by priority (confidence desc, then recency)."""
    if len(evidence) <= MAX_CONTEXT_ITEMS:
        return evidence
    sorted_evidence = sorted(
        evidence,
        key=lambda e: (e.confidence, e.timestamp or ""),
        reverse=True,
    )
    return sorted_evidence[:MAX_CONTEXT_ITEMS]


def _order_deterministically(evidence: list[EvidenceRecord]) -> list[EvidenceRecord]:
    """Sort evidence for stable output."""
    return sorted(
        evidence,
        key=lambda e: (e.source.value, e.evidence_id),
    )


def _compute_hash(context: ReasoningContext) -> str:
    """Compute a deterministic SHA-256 hash of the context."""
    canonical = json.dumps(
        {
            "request_id": context.request_id,
            "evidence": [
                {
                    "id": e.evidence_id,
                    "source": e.source.value,
                    "claim": e.claim,
                    "value": e.value,
                    "confidence": e.confidence,
                }
                for e in context.evidence_items
            ],
            "constraints": context.constraints,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def serialize_context(context: ReasoningContext) -> str:
    """Serialize context to a stable JSON string for the LLM prompt."""
    return json.dumps(
        {
            "request_id": context.request_id,
            "domain_summary": context.domain_summary,
            "constraints": context.constraints,
            "evidence_count": context.total_evidence,
            "evidence": [
                {
                    "id": e.evidence_id,
                    "source": e.source.value,
                    "domain": e.domain.value,
                    "claim": e.claim,
                    "value": e.value,
                    "timestamp": e.timestamp,
                    "confidence": e.confidence,
                    "provenance": e.provenance,
                    "quality": e.quality,
                }
                for e in context.evidence_items
            ],
        },
        sort_keys=True,
        indent=2,
    )
