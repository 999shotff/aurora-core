# Ollama Provider — AURORA Intelligence Integration

## Architecture

```
AURORA Intelligence (LLM-1 → LLM-5)
        ↓
LLM Provider Interface (LLMProvider)
        ↓
OllamaProvider
        ↓
RuntimeManager
        ↓
Compute Fabric (ComputeManager)
        ↓
Google Colab Worker (HTTP polling)
        ↓
Ollama (localhost:11434)
        ↓
Tesla T4 GPU
        ↓
Qwen2.5:0.5b
        ↓
InferenceResult → LLM reasoning/analysis → Evidence-grounded output
```

## Configuration

Set environment variable:

```bash
AURORA_LLM_PROVIDER=ollama
```

Optional:
```bash
AURORA_LLM_MODEL=qwen2.5-0.5b-ollama  # default
```

The provider communicates with Ollama exclusively through the Compute Fabric. The frontend never directly contacts Ollama.

## Provider Selection

| Provider | When to Use |
|----------|------------|
| `stub` | Default, no LLM configured |
| `openai` | External OpenAI-compatible API |
| `ollama` | Local Ollama via Compute Fabric (Colab/Lightning GPU) |

If `AURORA_LLM_PROVIDER=ollama` and no worker is connected, the provider returns an explicit "unavailable" state. It never silently falls back to another provider.

## Compute Fabric Integration

The OllamaProvider uses the existing RuntimeManager, which:
1. Validates the model is in the approved registry
2. Finds a READY worker with sufficient VRAM
3. Dispatches `RUNTIME_LOAD` and `RUNTIME_INFER` jobs
4. Polls for completion
5. Returns normalized results

No direct worker communication from application code.

## Model Allowlist

Only approved models may be used:

| AURORA ID | Ollama Model | Runtime |
|-----------|-------------|---------|
| `qwen2.5-0.5b-ollama` | `qwen2.5:0.5b` | ollama |

Arbitrary model names, URLs, and commands are rejected.

## Request Flow

1. Validate request (sanitize input)
2. Select Ollama provider from registry
3. Resolve approved model from registry
4. Resolve runtime type (ollama)
5. Check Compute Fabric for READY workers
6. Submit bounded inference job
7. Wait for completion (existing job polling)
8. Receive InferenceResult
9. Validate provenance
10. Return provider response

## Provenance

Every model response retains:
- model_id, runtime_model_id
- provider, worker_id
- GPU, device, framework/runtime
- Timestamps, duration
- Input hash, output hash

Generated model text is classified as `MODEL_INFERENCE`. It is NOT `OBSERVED` and must never automatically become evidence.

## Security

- No arbitrary model names
- No arbitrary URLs
- No arbitrary code execution
- No shell execution
- No subprocess calls
- No unrestricted autonomous agents
- No trading execution
- No fabricated evidence
- No fabricated model output
- No automatic memory promotion

## Failure Behavior

| Failure | Response |
|---------|----------|
| Colab worker disconnected | Explicit error: "Worker not available" |
| Ollama unavailable | Explicit error: "Ollama not reachable" |
| Model unavailable | Explicit error: "Model not loaded" |
| GPU unavailable | Explicit error: "Insufficient VRAM" |
| Timeout | Explicit error: "Inference timed out" |

Never fabricates a model response. Never silently switches providers.

## Live Baseline (Manual Test Results)

| Metric | Value |
|--------|-------|
| Worker | colab-24db5bb74249-1788842404 |
| GPU | Tesla T4 |
| VRAM | 14912.7 MB |
| Ollama | READY |
| Model | qwen2.5:0.5b |
| Duration | 115.306s |
| Tokens | 51 |
| Tokens/sec | 0.4 |

These are manual live test results, not benchmark guarantees.

## Evidence Classification

| Classification | When |
|---------------|------|
| MODEL_INFERENCE | Generated model text |
| OBSERVED | Directly observed data |
| STATISTICAL | Statistical computation |
| HYPOTHESIS | Explicit hypothesis |

Model output is always `MODEL_INFERENCE`. It is never automatically promoted to `OBSERVED` or `VALIDATED`.
