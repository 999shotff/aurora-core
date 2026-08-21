"""Semantic deduplication interface.

Embeddings are not mandatory yet.
A future implementation can plug in embeddings.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DeduplicationResult:
    claims_before: int = 0
    claims_after: int = 0
    duplicates_found: int = 0
    duplicate_groups: list[list[int]] = field(default_factory=list)
    notes: str = ""


class SemanticDeduplicator(ABC):
    @abstractmethod
    def deduplicate(
        self,
        claims: list[dict],
        threshold: float = 0.85,
    ) -> DeduplicationResult:
        raise NotImplementedError

    @abstractmethod
    def similarity(self, claim_a: dict, claim_b: dict) -> float:
        raise NotImplementedError


class KeywordDeduplicator(SemanticDeduplicator):
    def __init__(self) -> None:
        self.name = "keyword"

    def similarity(self, claim_a: dict, claim_b: dict) -> float:
        text_a = claim_a.get("exact_source_text", "").lower()
        text_b = claim_b.get("exact_source_text", "").lower()
        if not text_a or not text_b:
            return 0.0
        words_a = set(text_a.split())
        words_b = set(text_b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    def deduplicate(
        self,
        claims: list[dict],
        threshold: float = 0.85,
    ) -> DeduplicationResult:
        n = len(claims)
        visited = set()
        groups: list[list[int]] = []
        for i in range(n):
            if i in visited:
                continue
            group = [i]
            for j in range(i + 1, n):
                if j in visited:
                    continue
                sim = self.similarity(claims[i], claims[j])
                if sim >= threshold:
                    group.append(j)
                    visited.add(j)
            if len(group) > 1:
                groups.append(group)
                visited.add(i)
        deduped = []
        seen_indices: set[int] = set()
        for i, claim in enumerate(claims):
            if i not in visited:
                deduped.append(claim)
                seen_indices.add(i)
        return DeduplicationResult(
            claims_before=n,
            claims_after=len(deduped),
            duplicates_found=n - len(deduped),
            duplicate_groups=groups,
            notes=f"keyword dedup, threshold={threshold}",
        )
