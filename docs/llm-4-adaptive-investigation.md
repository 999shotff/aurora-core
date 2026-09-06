# LLM-4: Adaptive Investigation Engine

> **Phase:** 4 | **Status:** COMPLETE | **Tests:** 64/64 passing, 2243 total suite
> **NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.**

## Overview

LLM-4 transforms AURORA from a sequential tool→evidence→LLM pipeline into an adaptive, memory-first, gap-driven investigation engine. It is a bounded, auditable system — not an autonomous agent.

## Architecture

```
src/aurora/investigation/
  __init__.py      — Package exports
  schemas.py       — Domain model: InvestigationRecord, Objective, Gap, Finding, Event, etc.
  errors.py        — Typed exceptions
  store.py         — File-based JSON persistence
  planner.py       — Memory-first, gap-driven bounded planner
  executor.py      — Bounded, auditable tool execution
  comparison.py    — Deterministic current vs historical comparison
  lifecycle.py     — State transitions and validation
  manager.py       — High-level orchestrator
  api.py           — FastAPI endpoints (11 routes)

frontend/src/
  pages/InvestigationCenter.tsx — Investigation workstation UI
  services/investigations.ts   — TypeScript API client
```

## Investigation Flow

```
USER OBJECTIVE
  ↓
INVESTIGATION PLANNER  (understand → identify domain → inspect memory)
  ↓
MEMORY INSPECTION      (search for previous investigations/evidence)
  ↓
EVIDENCE GAP ANALYSIS  (required vs existing → identify gaps)
  ↓
BOUNDED TOOL INVESTIGATION  (execute only gap-resolving tools)
  ↓
EVIDENCE GRAPH         (collect evidence with provenance)
  ↓
CURRENT vs HISTORICAL COMPARISON  (deterministic deltas)
  ↓
LLM SYNTHESIS          (explain findings, abstain if insufficient)
  ↓
GROUNDING VALIDATION   (verify claims against evidence)
  ↓
INVESTIGATION RESULT   (structured findings + uncertainties)
  ↓
MEMORY UPDATE          (promote to permanent memory)
  ↓
REPORT                 (auditable export)
```

## Investigation Statuses

| Status | Meaning |
|--------|---------|
| `DRAFT` | Created, not started |
| `PLANNING` | Analyzing objective, building plan |
| `MEMORY_RETRIEVAL` | Searching previous investigations |
| `GAP_ANALYSIS` | Identifying evidence gaps |
| `INVESTIGATING` | Executing tools |
| `ANALYZING` | Processing evidence |
| `COMPARING` | Comparing current vs historical |
| `SUFFICIENCY_CHECK` | Evaluating evidence sufficiency |
| `VALIDATING` | Grounding validation |
| `SYNTHESIZING` | LLM synthesis |
| `COMPLETE` | Investigation finished |
| `PARTIAL` | Finished with unresolved gaps |
| `ABSTAINED` | Cannot investigate (missing data) |
| `FAILED` | Execution failure |
| `CANCELLED` | User cancelled |

## Key Design Decisions

1. **Memory-first** — Always search memory before collecting new evidence.
2. **Gap-driven** — Only execute tools that resolve identified evidence gaps.
3. **Bounded execution** — Max 8 steps, 2 planning iterations, 300s timeout.
4. **Deterministic comparison** — Numerical deltas computed in code, not LLM.
5. **Audit trail** — Every state change logged with timestamp and references.
6. **Idempotency** — Duplicate start requests detected and rejected.
7. **Reopen** — PARTIAL investigations can be reopened when new data arrives.
8. **No hidden CoT** — LLM reasoning summary stored, never raw chain-of-thought.

## Evidence Sufficiency

| State | Condition |
|-------|-----------|
| `SUFFICIENT` | All gaps resolved |
| `PARTIALLY_SUFFICIENT` | No critical gaps, ≤2 open gaps |
| `INSUFFICIENT` | Critical gaps remain open |
| `CONFLICTED` | Contradictory evidence detected |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/investigations` | Create investigation |
| `GET` | `/api/v1/investigations` | List investigations |
| `GET` | `/api/v1/investigations/{id}` | Get investigation |
| `POST` | `/api/v1/investigations/{id}/start` | Start investigation |
| `POST` | `/api/v1/investigations/{id}/cancel` | Cancel investigation |
| `POST` | `/api/v1/investigations/{id}/reopen` | Reopen investigation |
| `GET` | `/api/v1/investigations/{id}/events` | Audit trail |
| `GET` | `/api/v1/investigations/{id}/findings` | Findings |
| `GET` | `/api/v1/investigations/{id}/result` | Investigation result |

## Security Constraints

- LLM cannot execute tools directly
- LLM cannot modify evidence
- LLM cannot validate unsupported claims
- Tool permissions enforced (READ-only)
- Step limits enforced (max 8)
- Timeout enforced (300s default)
- No arbitrary code execution
- No arbitrary network requests
- No secret access

## Constraints

- NO_DEPLOYMENT_SIGNAL — No trading signals
- No fabricated data
- No future information leakage
- UTC internally
- Deterministic calculations outside LLM
