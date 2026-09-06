# LLM-3: Cognitive Memory

> **Phase:** 3 | **Status:** COMPLETE | **Tests:** 39/39 passing
> **NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.**

## Overview

LLM-3 adds a cognitive memory layer to AURORA CORE, enabling persistent, queryable, versioned memory across all research domains (market, geo, research). The memory system provides deterministic retrieval with explainable ranking, typed relationships, and working memory for session context.

## Architecture

```
src/aurora/memory/
  __init__.py      — Package exports
  schemas.py       — Domain model: MemoryRecord, MemoryType, MemoryStatus, WorkingMemory, etc.
  store.py         — File-based JSON persistence (follows ResearchStorage pattern)
  index.py         — Deterministic retrieval index (text, entity, domain, tag matching)
  retrieval.py     — Ranked retrieval with explainable scoring
  relationships.py — Typed relationship graph (reuses Evidence Graph pattern)
  manager.py       — High-level orchestrator integrating all components
  api.py           — FastAPI endpoints (11 routes)
```

## Memory Types

| Type | Purpose | Lifecycle |
|------|---------|-----------|
| `EPISODIC` | Time-stamped events: market observations, geo scenes, research findings | Created → Archived |
| `SEMANTIC` | General knowledge: domain rules, methodology patterns | Updated in place |
| `EVIDENCE` | Linked to specific evidence items: claims, observations | Versioned |
| `WORKING` | Session-scoped: current investigation context | Promoted or discarded |

## Memory Statuses

| Status | Meaning |
|--------|---------|
| `ACTIVE` | Current, valid memory |
| `UPDATED` | Superseded by newer version |
| `STALE` | No longer relevant |
| `SUPERSEDED` | Replaced by newer memory |
| `ARCHIVED` | Preserved but excluded from default search |

## Retrieval Ranking

Memory retrieval uses a weighted composite score:

| Factor | Weight | Description |
|--------|--------|-------------|
| `relevance` | 0.30 | Text match quality (title > content) |
| `entity_match` | 0.25 | Entity reference overlap |
| `domain_match` | 0.15 | Domain alignment |
| `recency` | 0.10 | Time since creation (decays over 30 days) |
| `provenance` | 0.10 | Source quality |
| `status` | 0.10 | Memory lifecycle status |

Each result includes `match_reasons` for explainability.

## Relationship Types

| Type | Meaning |
|------|---------|
| `SUPPORTS` | Target corroborates source |
| `CONTRADICTS` | Target conflicts with source |
| `DERIVED_FROM` | Target was derived from source |
| `REFINES` | Target is a refinement of source |
| `SUPERSEDES` | Target replaces source |
| `TEMPORALLY_RELATED` | Targets share temporal proximity |
| `SAME_ENTITY` | Targets reference the same entity |
| `SAME_INVESTIGATION` | Targets belong to same investigation |
| `RELATED_TO` | General relationship |

Contradiction detection identifies mutual CONTRADICTS edges automatically.

## Working Memory

Working memory maintains session-scoped context:

- `session_id` — Unique session identifier
- `user_query` — The query being investigated
- `domain` — Current domain focus
- `entities` — Entities encountered this session
- `unresolved_questions` — Questions still pending
- `relevant_findings` — Findings surfaced so far
- `active_hypotheses` — Hypotheses under consideration

Working memory can be **promoted** to permanent memory (EPISODIC) via `promote_working()`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/memory` | Create memory record |
| `GET` | `/api/v1/memory/{id}` | Get memory by ID |
| `GET` | `/api/v1/memory/search` | Search with ranking |
| `GET` | `/api/v1/memory/{id}/history` | Version history |
| `POST` | `/api/v1/memory/{id}/link` | Create relationship |
| `GET` | `/api/v1/memory/{id}/relationships` | Get relationships |
| `POST` | `/api/v1/memory/retrieve` | Retrieve for reasoning |
| `GET` | `/api/v1/memory/stats` | Memory statistics |
| `POST` | `/api/v1/memory/export` | Export all data |

## Design Decisions

1. **File-based storage** — JSON files following the existing ResearchStorage pattern. No database dependency.
2. **Deterministic index** — Text tokenization + inverted index. No vector database required.
3. **Explainable ranking** — Every retrieval result includes `match_reasons` for transparency.
4. **Evidence Graph reuse** — Relationship graph extends the pattern from `src/aurora/ai/evidence_graph.py`.
5. **Working memory promotion** — Session context can be persisted to permanent memory for continuity.
6. **No LLM dependency** — All memory operations are deterministic. LLM integration is optional.

## Constraints

- NO_DEPLOYMENT_SIGNAL — Memory system does not generate trading signals
- No fabricated data — All memories must have provenance
- UTC timestamps only
- Deterministic calculations outside the language model
- All methodologies enter the same testing framework with no special credibility
