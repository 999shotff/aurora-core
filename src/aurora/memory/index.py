"""
LLM-3: Memory Index — deterministic retrieval index.

Provides text matching, entity matching, domain matching, temporal relevance.
No vector database required for initial implementation.
"""

from __future__ import annotations

import re

from aurora.memory.schemas import MemoryRecord


class MemoryIndex:
    """
    Deterministic memory retrieval index.

    Supports:
    - Exact text matching
    - Normalized text matching
    - Entity matching
    - Domain matching
    - Tag matching
    - Temporal relevance
    - Status weighting
    """

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}
        self._token_index: dict[str, set[str]] = {}
        self._entity_index: dict[str, set[str]] = {}
        self._domain_index: dict[str, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}

    def add(self, record: MemoryRecord) -> None:
        """Add a record to the index."""
        self._records[record.memory_id] = record

        # Token index
        tokens = self._tokenize(record.title + " " + record.content)
        for token in tokens:
            self._token_index.setdefault(token, set()).add(record.memory_id)

        # Entity index
        for entity_id in record.entity_refs:
            self._entity_index.setdefault(entity_id, set()).add(record.memory_id)

        # Domain index
        self._domain_index.setdefault(record.domain, set()).add(record.memory_id)

        # Tag index
        for tag in record.tags:
            self._tag_index.setdefault(tag.lower(), set()).add(record.memory_id)

    def remove(self, memory_id: str) -> None:
        """Remove a record from the index."""
        record = self._records.pop(memory_id, None)
        if record is None:
            return

        # Remove from token index
        tokens = self._tokenize(record.title + " " + record.content)
        for token in tokens:
            if token in self._token_index:
                self._token_index[token].discard(memory_id)
                if not self._token_index[token]:
                    del self._token_index[token]

        # Remove from entity index
        for entity_id in record.entity_refs:
            if entity_id in self._entity_index:
                self._entity_index[entity_id].discard(memory_id)
                if not self._entity_index[entity_id]:
                    del self._entity_index[entity_id]

        # Remove from domain index
        if record.domain in self._domain_index:
            self._domain_index[record.domain].discard(memory_id)
            if not self._domain_index[record.domain]:
                del self._domain_index[record.domain]

        # Remove from tag index
        for tag in record.tags:
            key = tag.lower()
            if key in self._tag_index:
                self._tag_index[key].discard(memory_id)
                if not self._tag_index[key]:
                    del self._tag_index[key]

    def search_tokens(self, query: str) -> set[str]:
        """Search by text tokens."""
        tokens = self._tokenize(query)
        if not tokens:
            return set()
        result = None
        for token in tokens:
            matches = self._token_index.get(token, set())
            if result is None:
                result = matches.copy()
            else:
                result |= matches
        return result or set()

    def search_entities(self, entity_id: str) -> set[str]:
        """Search by entity reference."""
        return self._entity_index.get(entity_id, set())

    def search_domain(self, domain: str) -> set[str]:
        """Search by domain."""
        return self._domain_index.get(domain, set())

    def search_tags(self, tag: str) -> set[str]:
        """Search by tag."""
        return self._tag_index.get(tag.lower(), set())

    def get(self, memory_id: str) -> MemoryRecord | None:
        """Get a record by ID."""
        return self._records.get(memory_id)

    def list_all(self) -> list[MemoryRecord]:
        """List all indexed records."""
        return list(self._records.values())

    def size(self) -> int:
        """Index size."""
        return len(self._records)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenize text for indexing."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        tokens = set(text.split())
        # Remove very short tokens
        return {t for t in tokens if len(t) > 1}
