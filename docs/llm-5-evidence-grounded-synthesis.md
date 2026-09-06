# LLM-5: Evidence-Grounded Synthesis & Decision Intelligence

**Status:** v0.1.0 EXPERIMENTAL  
**Type:** Deterministic synthesis with validation  
**Depends On:** LLM-1, LLM-3, LLM-4  

---

## What It Is

LLM-5 transforms validated investigation results and evidence into structured findings, hypotheses, uncertainty analysis, contradiction detection, scenarios, and decision-support summaries.

**It does NOT:**
- Make predictions
- Generate trading signals
- Make LLM-required decisions
- Connect to external services
- Automate trading

---

## Architecture

```
SynthesisRequest
    ↓
EvidenceAssessment ─── assess_evidences()
    ↓
FindingAssessment ─── _build_findings()
    ↓
ContradictionDetection ─── detect_contradictions()
    ↓
HypothesisGeneration ─── generate_hypotheses()
    ↓
UncertaintyAssessment ─── assess_uncertainty()
    ↓
ScenarioAnalysis ─── generate_scenarios()
    ↓
DecisionConsideration ─── generate_decision_considerations()
    ↓
EvidenceGapIdentification ─── _identify_gaps()
    ↓
ProvenanceTracking ─── build_provenance()
    ↓
MemoryUpdateProposals ─── _propose_memory_updates()
    ↓
ExecutiveSummary ─── _build_executive_summary()
    ↓
SynthesisResult
```

---

## Schemas

### SynthesisRequest

| Field | Type | Description |
|-------|------|-------------|
| request_id | str | Unique request identifier |
| question | str | The question to synthesize about (1-10000 chars) |
| investigation_id | str? | Linked investigation ID |
| evidence_ids | list[str] | Evidence IDs to synthesize |
| finding_ids | list[str] | Finding IDs to include |
| memory_ids | list[str] | Memory IDs to reference |
| domain | str | Domain: general, market, geo, research |
| comparison_context | str? | Context for hypothesis comparison |
| decision_context | str? | Context for decision considerations |

### SynthesisResult

| Field | Type | Description |
|-------|------|-------------|
| synthesis_id | str | Unique synthesis identifier |
| question | str | Original question |
| executive_summary | str | Natural language synthesis |
| key_findings | list[FindingAssessment] | Classified findings |
| hypotheses | list[Hypothesis] | Generated hypotheses |
| contradictions | list[ContradictionAssessment] | Detected contradictions |
| known_facts | list[str] | Established facts |
| supported_inferences | list[str] | Partially supported inferences |
| assumptions | list[str] | All identified assumptions |
| unknowns | list[str] | Unknown elements |
| scenarios | list[Scenario] | Generated scenarios |
| decision_considerations | list[DecisionConsideration] | Decision factors |
| evidence_gaps | list[EvidenceGap] | Missing evidence |
| limitations | list[str] | Known limitations |
| provenance | list[ProvenanceRecord] | Source provenance |
| memory_updates | list[MemoryUpdateProposal] | Proposed memory updates |
| synthesis_status | SynthesisStatus | FINAL status |
| evidence_assessments | list[EvidenceAssessment] | Evidence evaluations |
| uncertainty_assessments | list[UncertaintyAssessment] | Uncertainty classifications |
| causal_level | CausalLevel | Causal inference level |
| timestamp | float | UTC timestamp |

---

## Evidence Assessment

Each evidence item is assessed for:

- **Freshness:** RECENT, MODERATE, STALE, UNKNOWN
- **Relevance:** DIRECT, CONTEXTUAL, TANGENTIAL, UNCLEAR
- **Reliability:** HIGH, MODERATE, LOW, UNRELIABLE, UNKNOWN
- **Mode:** DIRECT, DERIVED, AGGREGATE, COMPILED, UNKNOWN

---

## Causal Levels

From strongest to weakest:

1. **MECHANISTIC_EVIDENCE** — Multiple supported findings
2. **TEMPORAL_ASSOCIATION** — At least one supported finding
3. **CORRELATION** — Weak or partially supported
4. **INSUFFICIENT** — No evidence or unsupported

---

## Contradiction Types

- **DIRECT** — Same claim, opposite conclusions
- **INDIRECT** — Different claims, logically inconsistent
- **SEMANTIC** — Conflicting wordings on same topic
- **TEMPORAL** — Same topic, different timeframes
- **PARTIAL** — Partial agreement with divergence

---

## Uncertainty Kinds

- **KNOWN** — Known unknowns with reduction path
- **SUPPORTED_INFERENCE** — Inference from evidence
- **ASSUMPTION** — Identified assumption
- **UNKNOWN** — Unknown unknown
- **CONTRADICTED** — Conflicting information
- **UNAVAILABLE** — Data not accessible

---

## API Endpoints

### `POST /api/v1/synthesis`

Execute evidence-grounded synthesis.

**Request:** SynthesisExecuteRequest  
**Response:** SynthesisResult

### `GET /api/v1/synthesis/{id}`

Get synthesis result by ID.

### `GET /api/v1/synthesis/health`

Health check for synthesis engine.

### `GET /api/v1/synthesis/audit`

Get audit log of synthesis executions.

---

## Frontend

Route: `/synthesis`

Components:
- Question input + domain selector
- Status badge (COMPLETE/PARTIAL/INDETERMINATE/INSUFFICIENT_EVIDENCE)
- Findings list with confidence badges
- Hypotheses with status icons (✔/○/✘)
- Contradictions with severity
- Uncertainty assessment cards
- Evidence gaps
- Decision considerations
- Provenance tree
- Limitations list

---

## Usage

```python
from aurora.ai.synthesis.engine import SynthesisEngine
from aurora.ai.synthesis.schemas import SynthesisRequest

engine = SynthesisEngine()

request = SynthesisRequest(
    request_id="req-001",
    question="Is the hypothesis supported?",
    evidence_ids=["ev-1", "ev-2"],
    domain="market",
)

result = engine.synthesize(
    request,
    evidence_items=[...],
    findings_raw=[...],
    memory_items=[...],
)

print(result.executive_summary)
print(f"Status: {result.synthesis_status}")
print(f"Causal: {result.causal_level}")
```

---

## Tests

26+ tests in `tests/test_llm5_synthesis.py`:

- Schema validation (14 tests)
- Evidence assessment (3 tests)
- Hypothesis generation (3 tests)
- Contradiction detection (2 tests)
- Uncertainty assessment (2 tests)
- Scenarios (2 tests)
- Decision (2 tests)
- Provenance (2 tests)
- Cache (4 tests)
- Engine (6 tests)

---

## Status Codes

| Code | Meaning |
|------|---------|
| COMPLETE | All findings resolved |
| PARTIAL | Some findings resolved |
| INDETERMINATE | Findings unresolved |
| INSUFFICIENT_EVIDENCE | No evidence provided |
| FAILED | Engine error |

---

## Confidence Levels

| Level | When Used |
|-------|-----------|
| VERY_HIGH | Multiple high-quality evidence, no contradictions |
| HIGH | Strong evidence, minor gaps |
| MODERATE | Some evidence, moderate gaps |
| LOW | Weak evidence, significant gaps |
| VERY_LOW | Minimal evidence |
| UNDETERMINED | Cannot assess |

---

## NO_DEPLOYMENT_SIGNAL

This module outputs structured analysis only. It does NOT:
- Make predictions
- Generate trading signals
- Make trading decisions
- Connect to brokers or exchanges
- Use real money

All synthesis results are informational only.
