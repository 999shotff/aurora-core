"""
LLM-3: Cognitive Memory — AURORA persistent structured memory system.

Provides:
- Episodic memory (investigations/events)
- Semantic memory (durable knowledge)
- Evidence memory (references to existing evidence)
- Working memory (current investigation context)
- Memory lifecycle, versioning, relationships
- Deterministic retrieval and ranking
- Conflict detection
- Provenance tracking

MEMORY IS NOT TRUTH. Every memory preserves source, provenance, timestamp, status.
"""

from aurora.memory.schemas import (
    MemoryType,
    MemoryStatus,
    MemoryRecord,
    MemoryVersion,
    MemoryConflict,
    MemoryConflictState,
    EntityReference,
    WorkingMemory,
    MemorySearchResult,
    MemoryExport,
)
from aurora.memory.store import MemoryStore
from aurora.memory.index import MemoryIndex
from aurora.memory.retrieval import MemoryRetriever
from aurora.memory.relationships import MemoryRelationshipGraph
from aurora.memory.manager import MemoryManager

__all__ = [
    "EntityReference",
    "MemoryConflict",
    "MemoryConflictState",
    "MemoryExport",
    "MemoryIndex",
    "MemoryManager",
    "MemoryRecord",
    "MemoryRelationshipGraph",
    "MemoryRetriever",
    "MemorySearchResult",
    "MemoryStatus",
    "MemoryStore",
    "MemoryType",
    "MemoryVersion",
    "WorkingMemory",
]
