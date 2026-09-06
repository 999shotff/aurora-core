# LLM-2: Grounded Intelligence & Controlled Tool Orchestration

## Status: COMPLETE
## Commit: feat(ai): add grounded intelligence orchestration

## Architecture Overview

LLM-2 extends LLM-1's evidence-grounded reasoning with a controlled tool orchestration layer. The LLM proposes tool steps, but execution is bounded by strict permission policies and safety validations.

### Core Principles

1. **Tools are READ-only** — no trade execution, no data modification, no arbitrary code
2. **Bounded planning** — max 8 steps, 2 planning iterations, 1 synthesis call
3. **Evidence graph** — tracks all relationships between evidence items
4. **Safety logging** — immutable audit trail of all tool executions
5. **Grounding validation** — every citation must reference real evidence

## Components

### Tool Registry (`src/aurora/ai/tools/`)

```
tools/
├── __init__.py          # Package exports
├── base.py              # AITool ABC, ToolRegistry, ToolResult, ToolStep
├── permissions.py       # PermissionPolicy (ALLOWED/DENIED sets)
├── market.py            # Market tools (OHLCV, analysis, sentiment)
├── geo.py               # Geo tools (scene search, observation, analysis)
└── research.py          # Research tools (claims, hypotheses, documents)
```

### Available Tools (9 total)

| Tool | Domain | Permissions |
|------|--------|-------------|
| `market.get_ohlcv` | Market | READ_MARKET |
| `market.get_analysis` | Market | READ_MARKET, RUN_DETERMINISTIC_ANALYSIS |
| `market.sentiment` | Market | READ_MARKET |
| `geo.search_scenes` | Geo | READ_GEO |
| `geo.observation` | Geo | READ_GEO |
| `geo.analysis` | Geo | READ_GEO, RUN_DETERMINISTIC_ANALYSIS |
| `research.search_claims` | Research | READ_RESEARCH |
| `research.search_hypotheses` | Research | READ_RESEARCH |
| `research.get_document` | Research | READ_RESEARCH |

### Permission Policy

**ALLOWED:**
- `READ_MARKET`, `READ_GEO`, `READ_RESEARCH`
- `RUN_DETERMINISTIC_ANALYSIS`
- `WRITE_INVESTIGATION`, `EXPORT_DATA`

**DENIED (never granted):**
- `TRADE`, `MODIFY`, `DELETE`
- `ARBITRARY_CODE`, `NETWORK_EXTERNAL`
- `WRITE_RESEARCH`

### Planning System (`src/aurora/ai/planning.py`)

- Generates bounded reasoning plans from goals
- Validates against all constraints before execution
- Detects circular dependencies
- Limits: 8 steps max, 2 planning iterations

### Evidence Graph (`src/aurora/ai/evidence_graph.py`)

Tracks relationships between evidence items:
- `SUPPORTS` — evidence corroborates another
- `CONTRADICTS` — evidence conflicts with another
- `DERIVED_FROM` — evidence was computed from another

Features:
- Contradiction detection (mutual contradictions)
- Evidence chain traversal (DERIVED_FROM backward)
- Graph serialization for frontend visualization

### Extended Grounding (`src/aurora/ai/grounding_ext.py`)

Validates LLM responses against evidence graph:
- Fake evidence ID rejection
- Unsourced numerical claim detection
- Source reference consistency checks
- Partial data status awareness

### Extended Security (`src/aurora/ai/security_ext.py`)

Tool-specific injection defense:
- Tool parameter injection detection
- Output sanitization (instruction removal)
- Plan step validation
- Workflow boundary enforcement

### Workflows (`src/aurora/ai/workflows/`)

Domain-specific tool orchestration:
- **Market**: OHLCV → analysis → sentiment → synthesis
- **Geo**: scene search → observation → analysis → synthesis
- **Research**: claims → hypotheses → documents → synthesis

### Service Integration (`src/aurora/ai/service.py`)

New methods:
- `process_with_tools(request, domain, goal)` — full tool-orchestrated reasoning
- `execute_workflow(domain, **kwargs)` — raw workflow execution
- `list_tools()` — available tool registry
- `get_safety_log()` — audit trail
- `get_evidence_graph()` — current graph state

### API Endpoints (`src/aurora/ai/api.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/reason/tool` | POST | Tool-orchestrated reasoning (LLM-2) |
| `/api/v1/reason/workflow` | POST | Domain workflow execution |
| `/api/v1/reason/tools` | GET | List available tools |
| `/api/v1/reason/evidence-graph` | GET | Current evidence graph |
| `/api/v1/reason/safety-log` | GET | Tool safety audit log |

### Frontend Components (`frontend/src/components/llm2/`)

- `ReasoningPanel.tsx` — Query input + structured response display
- `EvidenceGraphView.tsx` — Real-time evidence graph visualization
- `ToolStatus.tsx` — Tool registry + safety log display

### Frontend Service (`frontend/src/services/reasoning.ts`)

New functions:
- `reasonWithTools(params)` — Tool-orchestrated reasoning
- `executeWorkflow(params)` — Domain workflow execution
- `listTools()` — Available tools
- `getEvidenceGraph()` — Evidence graph data
- `getSafetyLog()` — Safety audit log

## Test Coverage

81 new tests in `tests/test_llm2_tools.py`:
- Tool registry (12 tests)
- Permission policy (13 tests)
- Tool implementations (11 tests)
- Planning system (8 tests)
- Evidence graph (8 tests)
- Extended grounding (5 tests)
- Tool security (9 tests)
- Workflows (3 tests)
- Permission constants (7 tests)
- Model tests (5 tests)

Total: 130 tests passing (49 LLM-1 + 81 LLM-2)

## Constraints

- All tools are deterministic and auditable
- No LLM makes decisions — only structures synthesis
- No trades executed, no data modified
- Evidence graph tracks all relationships
- Safety log provides immutable audit trail
- Prompt injection defense on all tool inputs/outputs
- Bounded planning prevents runaway orchestration
