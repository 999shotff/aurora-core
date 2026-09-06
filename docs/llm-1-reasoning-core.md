# LLM-1: Reasoning Core

## Architecture

The AURORA Reasoning Core adds an LLM-powered reasoning/synthesis layer on top of the existing deterministic analysis engine.

```
User Query
    ↓
Task Router (domain + evidence sources)
    ↓
Evidence Assembly (deterministic engines)
    ↓
Context Builder (bounded, hashed, deterministic)
    ↓
LLM Provider (stub / OpenAI-compatible)
    ↓
Response Validation (schema + grounding)
    ↓
Structured ReasoningResponse
```

**Critical invariant:** The deterministic engines remain the source of truth for all numerical data, indicators, market structure, timestamps, data quality, provenance, and evidence records. The LLM is a reasoning/synthesis component — it cannot modify, override, or invent data.

## Request Lifecycle

1. **Input sanitization** — prompt injection detection
2. **Task routing** — domain determination, evidence source selection
3. **Evidence assembly** — gather from deterministic engines (market, geo, research)
4. **Context building** — filter, limit, serialize, hash
5. **LLM generation** — bounded context → structured JSON response
6. **Response validation** — schema check, grounding validation
7. **Abstention check** — if evidence insufficient, abstain

## Provider Interface

```python
class LLMProvider(ABC):
    name: str
    is_available: bool
    generate(messages, max_tokens, temperature, timeout) -> str
    capabilities() -> ProviderCapabilities
```

Providers:
- **StubProvider** — deterministic fallback, no LLM needed
- **OpenAICompatibleProvider** — adapter for OpenAI, Anthropic (via proxy), local servers

Registry reads from environment:
- `AURORA_LLM_PROVIDER` — provider name (default: `stub`)
- `AURORA_LLM_API_KEY` — API key (never committed)
- `AURORA_LLM_BASE_URL` — base URL for OpenAI-compatible APIs
- `AURORA_LLM_MODEL` — model name

## Schemas

All models use `extra="forbid"` — no unvalidated data passes through.

- `ReasoningRequest` — user query, domain, task type, constraints
- `EvidenceRecord` — evidence item with source, domain, claim, confidence, provenance
- `ReasoningContext` — bounded evidence package with context hash
- `ReasoningResponse` — answer, summary, reasoning points, uncertainties, conflicts, grounding score
- `ReasoningPoint` — individual reasoning step with evidence grounding

## Grounding

Every reasoning point is classified as:
- `SUPPORTED_BY_EVIDENCE` — traceable to evidence IDs
- `INFERENCE` — logical inference from evidence
- `UNCERTAIN` — explicitly uncertain
- `ABSTAINED` — could not determine

Grounding score = fraction of points with evidence refs.

## Abstention

Abstention is a first-class capability. The system abstains when:
- No evidence is available
- Provider is unavailable
- Evidence is insufficient for the query
- Context limit exceeded

## Security

- Prompt injection detection on user input
- Instruction injection detection in evidence text
- Secret detection and redaction
- Research documents treated as DATA, not instructions
- No API keys exposed to frontend

## Task Router

Supported tasks:
- `ANALYZE_MARKET` / `EXPLAIN_MARKET`
- `ANALYZE_GEO` / `EXPLAIN_GEO`
- `SUMMARIZE_RESEARCH` / `COMPARE_EVIDENCE` / `EXPLAIN_EVIDENCE`
- `GENERAL_RESEARCH`

Domain inference from query text using keyword matching.

## API

```
POST /api/v1/reason
GET  /api/v1/reason/health
```

Request body:
```json
{
  "query": "Explain the market trend",
  "domain": "market",
  "task": "ANALYZE_MARKET",
  "evidence": [
    {
      "evidence_id": "ev_001",
      "source": "market_analysis",
      "domain": "market",
      "claim": "Trend is uptrend",
      "value": "uptrend"
    }
  ]
}
```

Response:
```json
{
  "request_id": "req_abc123",
  "status": "COMPLETE",
  "answer": "...",
  "summary": "...",
  "reasoning_points": [...],
  "uncertainties": [...],
  "conflicts": [...],
  "abstention_reason": null,
  "provider": "stub",
  "model": "",
  "grounding_score": 0.85
}
```

## Frontend

`frontend/src/services/reasoning.ts` — TypeScript client for the reasoning API.

## Testing

49 tests covering:
- Schema validation (forbid extra fields, required fields)
- Context builder (filtering, limits, deterministic hashing)
- Provider registry (stub, missing provider)
- Evidence grounding (refs, unsupported claims)
- Abstention (no evidence, provider unavailable)
- Security (injection, secrets)
- Task routing (market, geo, research, general)
- Market/Geo/Research connectors
- API endpoint (health, reasoning)
- Service integration

## Configuration

```
AURORA_LLM_PROVIDER=stub          # stub | openai | custom
AURORA_LLM_API_KEY=               # Never commit
AURORA_LLM_BASE_URL=https://api.openai.com/v1
AURORA_LLM_MODEL=gpt-4o-mini
```

If no provider is configured, `DETERMINISTIC_ONLY` mode is fully functional.

## Files Changed

| File | Purpose |
|------|---------|
| `src/aurora/ai/__init__.py` | Package exports |
| `src/aurora/ai/schemas.py` | Domain models (Pydantic) |
| `src/aurora/ai/errors.py` | Error types |
| `src/aurora/ai/providers.py` | Provider interface, registry, stub, OpenAI adapter |
| `src/aurora/ai/context.py` | Deterministic context builder |
| `src/aurora/ai/grounding.py` | Evidence grounding validation |
| `src/aurora/ai/security.py` | Prompt injection, secret detection |
| `src/aurora/ai/router.py` | Task routing |
| `src/aurora/ai/service.py` | Main reasoning service |
| `src/aurora/ai/api.py` | FastAPI endpoint |
| `src/aurora/ai/connectors/__init__.py` | Connector exports |
| `src/aurora/ai/connectors/market.py` | Market evidence connector |
| `src/aurora/ai/connectors/geo.py` | Geo evidence connector |
| `src/aurora/ai/connectors/research.py` | Research evidence connector |
| `src/aurora/market/api.py` | Mounted reason_app routes |
| `frontend/src/services/reasoning.ts` | Frontend reasoning client |
| `.env.example` | LLM provider config vars |
| `tests/test_llm1_reasoning.py` | 49 comprehensive tests |

## Limitations

- No live provider testing in this milestone (stub only)
- No multi-turn conversation (stateless requests)
- No streaming responses
- No autonomous tool execution
- Grounding validation is heuristic, not semantic
- No cost tracking per request

## Next Milestones

- **LLM-2**: Live provider integration testing
- **LLM-3**: Streaming responses, multi-turn context
- **LLM-4**: Cost tracking, rate limit management
