"""
LLM-3: Memory Retriever — deterministic ranking and retrieval.

Ranking factors:
- RELEVANCE (text match quality)
- ENTITY_MATCH (entity reference overlap)
- DOMAIN_MATCH (domain alignment)
- RECENCY (time since creation)
- PROVENANCE (source quality)
- STATUS (memory lifecycle status)
"""

from __future__ import annotations

import time

from aurora.memory.index import MemoryIndex
from aurora.memory.schemas import MemoryRecord, MemorySearchResult, MemoryStatus


# ── Ranking Weights ────────────────────────────────────────────────────────

WEIGHTS = {
    "relevance": 0.30,
    "entity_match": 0.25,
    "domain_match": 0.15,
    "recency": 0.10,
    "provenance": 0.10,
    "status": 0.10,
}

STATUS_SCORES = {
    MemoryStatus.ACTIVE: 1.0,
    MemoryStatus.UPDATED: 0.9,
    MemoryStatus.STALE: 0.4,
    MemoryStatus.SUPERSEDED: 0.2,
    MemoryStatus.ARCHIVED: 0.1,
}

DEFAULT_TOP_K = 10
MAX_TOP_K = 50


class MemoryRetriever:
    """
    Deterministic memory retrieval with explainable ranking.

    Returns MemorySearchResult with score and match_reasons.
    """

    def __init__(self, index: MemoryIndex) -> None:
        self._index = index

    def retrieve(
        self,
        query: str = "",
        entity_id: str | None = None,
        domain: str | None = None,
        top_k: int = DEFAULT_TOP_K,
        include_archived: bool = False,
    ) -> list[MemorySearchResult]:
        """
        Retrieve and rank memory records.

        Args:
            query: Text query for relevance scoring
            entity_id: Optional entity ID to match
            domain: Optional domain filter
            top_k: Number of results to return (max 50)
            include_archived: Whether to include archived memories

        Returns:
            Ranked list of MemorySearchResult
        """
        top_k = min(top_k, MAX_TOP_K)

        # Collect candidates
        candidate_ids: set[str] | None = None

        if query:
            candidate_ids = self._index.search_tokens(query)

        if entity_id:
            entity_matches = self._index.search_entities(entity_id)
            if candidate_ids is None:
                candidate_ids = entity_matches
            else:
                candidate_ids &= entity_matches

        if domain:
            domain_matches = self._index.search_domain(domain)
            if candidate_ids is None:
                candidate_ids = domain_matches
            else:
                candidate_ids &= domain_matches

        # If no filters, use all records
        if candidate_ids is None:
            candidate_ids = {r.memory_id for r in self._index.list_all()}

        # Score and rank
        results: list[MemorySearchResult] = []
        for mid in candidate_ids:
            record = self._index.get(mid)
            if record is None:
                continue
            if not include_archived and record.status == MemoryStatus.ARCHIVED:
                continue

            score, reasons = self._score(record, query, entity_id, domain)
            results.append(MemorySearchResult(
                memory=record,
                score=score,
                match_reasons=reasons,
            ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _score(
        self,
        record: MemoryRecord,
        query: str,
        entity_id: str | None,
        domain: str | None,
    ) -> tuple[float, list[str]]:
        """Compute composite score with explanation."""
        reasons: list[str] = []
        scores: dict[str, float] = {}

        # Relevance
        if query:
            query_lower = query.lower()
            title_match = query_lower in record.title.lower()
            content_match = query_lower in record.content.lower()
            if title_match:
                scores["relevance"] = 1.0
                reasons.append("Title match")
            elif content_match:
                scores["relevance"] = 0.7
                reasons.append("Content match")
            else:
                scores["relevance"] = 0.0
        else:
            scores["relevance"] = 0.5  # Neutral when no query

        # Entity match
        if entity_id:
            if entity_id in record.entity_refs:
                scores["entity_match"] = 1.0
                reasons.append(f"Entity match: {entity_id}")
            else:
                scores["entity_match"] = 0.0
        else:
            scores["entity_match"] = 0.5

        # Domain match
        if domain:
            if record.domain == domain:
                scores["domain_match"] = 1.0
                reasons.append(f"Domain match: {domain}")
            else:
                scores["domain_match"] = 0.0
        else:
            scores["domain_match"] = 0.5

        # Recency
        age_hours = (time.time() - record.created_at) / 3600
        scores["recency"] = max(0.0, 1.0 - (age_hours / (24 * 30)))  # Decays over 30 days
        if age_hours < 24:
            reasons.append("Recent (within 24h)")

        # Provenance
        if record.provenance:
            scores["provenance"] = min(1.0, len(record.provenance) / 100)
        else:
            scores["provenance"] = 0.2

        # Status
        scores["status"] = STATUS_SCORES.get(record.status, 0.5)
        if record.status != MemoryStatus.ACTIVE:
            reasons.append(f"Status: {record.status.value}")

        # Composite score
        composite = sum(
            scores.get(k, 0.0) * v for k, v in WEIGHTS.items()
        )

        return round(composite, 4), reasons
