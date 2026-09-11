# AURORA Terminal — Unified Intelligence Workspace

## Overview

The Terminal is AURORA's primary workspace — a desktop-first intelligence workstation integrating all AURORA subsystems into a single, cohesive interface.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TerminalCommandBar                      │
│                        (Cmd+K)                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────┐  ┌──────────────────┐ │
│  │       Primary Workspace         │  │ Provider Status  │ │
│  │                                 │  │    (compact)     │ │
│  │  ┌─────────────────────────┐   │  ├──────────────────┤ │
│  │  │    Workspace Tabs       │   │  │  Secondary Tabs  │ │
│  │  │  Command|Market|Macro   │   │  │  Evidence|AI     │ │
│  │  │  Research|AI|Geo|Risk   │   │  │  Macro|News|Risk │ │
│  │  └─────────────────────────┘   │  ├──────────────────┤ │
│  │                                 │  │                  │ │
│  │       Primary Content           │  │  Secondary Panel │ │
│  │                                 │  │                  │ │
│  └─────────────────────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Workspace Tabs

| Tab | Content |
|-----|---------|
| Command Center | AI analysis input, assessment cards |
| Market | Market quick view, open full workspace |
| Macro | Macro data from FRED |
| Research | News and research documents |
| AI Intelligence | Reasoning panel, evidence graph |
| Geo | Geo observatory, Cesium globe |
| Risk | Portfolio risk management |

## Provider Status

Terminal shows real-time status for all providers:

- **AI** — LLM provider (Kimi-K3, stub, etc.)
- **COMPUTE** — GPU status
- **MARKET** — Market data feed
- **GEO** — Geo observatory
- **NEWS** — NewsAPI provider
- **MACRO** — FRED macro provider
- **RESEARCH** — arXiv research provider

Status values:
- `ready` — Connected and operational
- `degraded` — Partial failure
- `unavailable` — Not configured or failed

## Information Flow

```
MARKET
   ↓
NEWS
   ↓
MACRO
   ↓
RESEARCH
   ↓
EVIDENCE
   ↓
AI REASONING
   ↓
INVESTIGATION
   ↓
SYNTHESIS
```

## Data Integration

All data providers are backend-only:
- No API keys exposed to frontend
- All provider access through `/api/v1/data/*` endpoints
- Provenance preserved for every data point
- Freshness classification (CURRENT, RECENT, HISTORICAL, STALE)
- Evidence classification (OBSERVED, DERIVED, STATISTICAL, SIMULATED, HYPOTHESIS, UNAVAILABLE, MODEL_INFERENCE)

## Security

- No arbitrary code execution
- Command registry is allowlisted
- All targets are internal routes
- Provider status shows real backend state
- No fake data displayed — DATA_UNAVAILABLE when providers not connected

## Components

- `TerminalCommandBar` — Cmd+K command palette
- `ProviderStatusPanel` — Compact system status
- `MacroWorkspacePanel` — Macro data from FRED
- `NewsResearchPanel` — News and research documents
- `RiskPortfolioPanel` — Portfolio risk management
- `EvidenceGraphView` — Evidence visualization
- `ReasoningPanel` — AI reasoning display
