# AURORA Unified Intelligence Terminal

**Status:** v0.1.0  
**Type:** Architectural consolidation  
**Depends On:** LLM-1→LLM-5, Compute Fabric, Market Observatory

---

## What It Is

Consolidates all AURORA intelligence subsystems into ONE coherent terminal.
Introduces shared analysis contracts, evidence classification, unified
orchestration, and a professional terminal workspace.

**It does NOT:**
- Rebuild LLM-1 through LLM-5
- Replace the Compute Fabric
- Create a second AI architecture
- Make predictions
- Generate trading signals
- Fabricate data

---

## Architecture

```
                         AURORA CORE
                              |
                    AURORA TERMINAL
                              |
       +----------------------+----------------------+
       |                      |                      |
     MARKET                RESEARCH              INTELLIGENCE
       |                      |                      |
  Price / OHLCV              News                LLM-1 → LLM-5
  Indicators                 Documents           Investigations
  Structure                  Macro               Memory
  Volume                     Evidence             Evidence Graph
  Volatility                                      Synthesis
       |                      |                      |
       +----------------------+----------------------+
                              |
                     ANALYSIS SOURCES
                              |
         +--------------------+--------------------+
         |                    |                    |
      Technical             Cycles             Behavioral
         |                    |                    |
     RSI/MACD/etc         Gann/etc             MatrAIx
     market structure     seasonality           personas
     volume               spectral              scenarios
     volatility            temporal
         |                    |                    |
         +--------------------+--------------------+
                              |
                       AURORA AI BRAIN
                      Existing LLM-1→LLM-5
                              |
                              ▼
                  EVIDENCE-GROUNDED SYNTHESIS
                              |
                              ▼
                    UNIFIED ASSESSMENT
```

---

## Evidence Classification

Every analytical contribution MUST be classified:

| Class | Description | Example |
|-------|-------------|---------|
| OBSERVED | Direct real-world observation | News article, price data |
| DERIVED | Computed from observations | RSI, MACD, structure |
| STATISTICAL | Statistical test result | Correlation test |
| SIMULATED | Behavioral simulation | MatrAIx persona response |
| HYPOTHESIS | Unvalidated hypothesis | Gann cycle, astrology |
| UNAVAILABLE | Data not available | Missing source |

**SIMULATED and HYPOTHESIS data must NEVER masquerade as OBSERVED.**

---

## Shared Analysis Contract

### AnalysisInput

```python
AnalysisInput(
    source_type=MARKET_INDICATORS,
    source_id="indicators-BTC",
    evidence_class=DERIVED,
    methodology=DETERMINISTIC,
    asset="BTC",
    timeframe="1d",
    indicators={"rsi": 65, "macd": ...},
    confidence=0.7,
    limitations=["Derived from historical data"],
)
```

### AnalysisCollection

```python
AnalysisCollection(
    question="What is the market outlook?",
    inputs=[...],  # All analysis contributions
    asset="BTC",
    timeframe="1d",
)
```

---

## Unified Assessment

```python
UnifiedAssessment(
    question="What is the market outlook?",
    directional_bias=UP,
    strength=MODERATE,
    confidence=LOW,
    evidence_summary="2 observed, 3 derived, 1 simulated",
    supporting_factors=[...],
    contradicting_factors=[...],
    behavioral_factors=[...],  # SIMULATED — clearly labeled
    cycle_hypotheses=[...],    # HYPOTHESIS — clearly labeled
    regime=TRENDING_UP,
    uncertainty=[...],
    limitations=[...],
    provenance=[...],  # Full traceability
)
```

---

## MatrAIx Integration

MatrAIx is integrated through an adapter, NOT by copying code.

- **Role:** Human-behavior / psychology simulation
- **Evidence class:** Always SIMULATED
- **Status:** NOT_CONFIGURED (no runtime connected)
- **Use case:** "What might different simulated populations do?"

Cohorts: risk_averse, risk_seeking, news_sensitive, long_term, short_term, etc.

---

## Cycle/Hypothesis Framework

Reusable interface for temporal/cyclical analysis:

- Gann time cycles
- Gann geometric relationships
- Seasonality
- Calendar effects
- Spectral/Fourier analysis
- Historical patterns

All results are classified as HYPOTHESIS — never guaranteed predictions.

Status: EXPLORATORY (stub implementations).

---

## Regime Detection

Deterministic/statistical regime classification:

- TRENDING_UP / TRENDING_DOWN
- RANGE_BOUND
- HIGH_VOLATILITY / LOW_VOLATILITY
- EXPANSION / CONTRACTION
- STRUCTURAL_BREAK
- UNKNOWN

Uses existing `features/structure.py` market structure engine.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/analysis/unified` | Run unified analysis |
| GET | `/api/v1/analysis/unified/{id}` | Get assessment |
| GET | `/api/v1/analysis/unified/health` | Health check |

---

## Frontend

Routes:
- `/terminal` — AURORA Terminal (unified workspace)
- `/` — Command Center (evolved)

Terminal features:
- Global search / question input
- Primary assessment card with directional bias
- Expandable evidence detail
- Supporting/contradicting factors
- Behavioral simulation (labeled SIMULATED)
- Cycle hypotheses (labeled HYPOTHESIS)
- Provenance traceability
- Compute status indicator
- Responsive layout

---

## How LLM-1→LLM-5 Interact

```
User Question
      ↓
UnifiedOrchestrator
      ↓
Collects: indicators + structure + context + regime
      ↓
Adds: research evidence, memory items
      ↓
Adds: MatrAIx simulation (if requested)
      ↓
Adds: cycle hypotheses (if requested)
      ↓
Builds AnalysisCollection
      ↓
Builds UnifiedAssessment
      ↓
(Optionally) feeds into LLM-5 SynthesisResult
      ↓
Returns to user
```

---

## Security

- No secrets in frontend
- No provider API keys exposed
- No arbitrary code execution
- Simulation data clearly labeled SIMULATED
- Hypotheses clearly labeled HYPOTHESIS
- Provenance cannot be silently altered
- Invalid source references rejected

---

## Known Limitations

- MatrAIx runtime not connected (stub adapter)
- Cycle providers are stubs (no real Gann/seasonality)
- No real news feed connected
- No real research document ingestion
- Terminal is initial implementation
- No persistent assessment storage

---

## NO_DEPLOYMENT_SIGNAL

This module produces analytical assessments, NOT predictions.
The output is research intelligence with exposed uncertainty.
It must never communicate certainty the system does not possess.
