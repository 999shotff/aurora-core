# Compute Fabric v2 — Real GPU Worker Activation

AURORA CORE's Compute Fabric orchestrates GPU/CPU compute through user-controlled workers.

## Architecture

```
                         AURORA CORE (Control Plane)
                              |
                       ComputeManager
                              |
               +--------------+--------------+
               |              |              |
              CPU          Colab Worker   Lightning Worker
               |              |              |
               |           GPU Runtime     GPU Runtime
               |              |              |
               +--------------+--------------+
                              |
                         Job Protocol
                              |
                    AI / ML Workloads
```

AURORA backend is the **control plane**. GPU workers are **execution planes**.
AURORA does NOT move itself onto GPU workers.

## Worker Protocol v2

Versioned, structured, validated messages:

| Message | Direction | Purpose |
|---------|-----------|---------|
| `REGISTER` | Worker → Backend | Worker registers with capabilities |
| `REGISTER_ACK` | Backend → Worker | Accept/reject with heartbeat config |
| `HEARTBEAT` | Worker → Backend | Periodic liveness + runtime state |
| `HEARTBEAT_ACK` | Backend → Worker | Ack + pending jobs + shutdown signal |
| `CAPABILITIES` | Worker → Backend | Updated capabilities (GPU info) |
| `HEALTH` | Worker → Backend | Detailed health check |
| `JOB_SUBMIT` | Backend → Worker | Submit structured workload |
| `JOB_ACCEPTED` | Worker → Backend | Worker accepts job |
| `JOB_STARTED` | Worker → Backend | Job execution started |
| `JOB_PROGRESS` | Worker → Backend | Progress update (0.0–1.0) |
| `JOB_LOG` | Worker → Backend | Log line for job |
| `JOB_RESULT` | Worker → Backend | Job completed with result |
| `JOB_FAILED` | Worker → Backend | Job failed with error |
| `JOB_CANCEL` | Backend → Worker | Cancel running job |
| `SHUTDOWN` | Worker → Backend | Graceful shutdown |

## Provider Status Model

### Provider
```
NOT_CONFIGURED → CONFIGURED → CONNECTING → AUTHENTICATING → HEALTH_CHECK → READY → BUSY → DISCONNECTED
                                                                                     ↘ DEGRADED
                                                                                     ↘ ERROR
```

### Worker
```
OFFLINE → CONNECTING → AUTHENTICATING → READY → BUSY → DISCONNECTED
                                                      ↘ UNHEALTHY
                                                      ↘ SHUTTING_DOWN
```

## GPU Discovery

GPU information is **only from real runtime reporting**:
- PyTorch `torch.cuda` API
- `nvidia-smi` fallback
- Worker-reported capabilities

If unavailable: `UNKNOWN`. **Never fabricated.**

## Security

- Worker token: `AURORA_COMPUTE_WORKER_TOKEN` env var (backend-side only)
- Frontend never receives worker authentication secrets
- No arbitrary Python/shell execution accepted
- Only structured workloads: INFERENCE, EMBEDDINGS, VISION, TRAINING, BENCHMARK
- Payload validation blocks: shell, exec, eval, subprocess, os.system, compile
- Provider credentials stored server-side only

## Setup

### Google Colab

1. Set `AURORA_COMPUTE_WORKER_TOKEN` on your backend
2. Set `AURORA_COLAB_WORKER_ENABLED=true` on your backend
3. Open `workers/google_colab/aurora_colab_worker.ipynb` in Colab
4. Start GPU runtime (Runtime → Change runtime type → GPU)
5. Configure `AURORA_BACKEND_URL` and `AURORA_WORKER_TOKEN` in notebook
6. Run all cells

Worker connects → reports GPU → AURORA marks READY → accepts jobs.

### Lightning AI

1. Set `AURORA_COMPUTE_WORKER_TOKEN` on your backend
2. Set `AURORA_LIGHTNING_ENDPOINT` and `AURORA_LIGHTNING_API_KEY` on backend
3. On your Lightning instance: `pip install requests torch`
4. Set `AURORA_BACKEND_URL` and `AURORA_WORKER_TOKEN` env vars
5. Run `python workers/lightning/worker.py`

## Compute Modes

| Mode | Behavior |
|------|----------|
| `AUTO` | Use healthy GPU worker if available, else CPU |
| `CPU` | CPU only |
| `GOOGLE_COLAB` | Colab only (NOT_AVAILABLE if disconnected) |
| `LIGHTNING` | Lightning only (NOT_AVAILABLE if disconnected) |

Explicit modes do NOT silently fall back to CPU.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/compute/status` | Overall compute status |
| GET | `/api/v1/compute/providers` | All provider info |
| GET | `/api/v1/compute/health` | Health check |
| POST | `/api/v1/compute/enable` | Enable compute |
| POST | `/api/v1/compute/disable` | Disable compute |
| POST | `/api/v1/compute/mode` | Change mode |
| POST | `/api/v1/compute/jobs` | Submit job |
| GET | `/api/v1/compute/jobs` | List jobs |
| GET | `/api/v1/compute/jobs/{id}` | Get job |
| POST | `/api/v1/compute/jobs/{id}/cancel` | Cancel job |
| POST | `/api/v1/compute/benchmark` | Run GPU benchmark |
| POST | `/api/v1/compute/workers/register` | Register worker |
| POST | `/api/v1/compute/workers/{id}/heartbeat` | Worker heartbeat |
| POST | `/api/v1/compute/workers/{id}/capabilities` | Update capabilities |
| GET | `/api/v1/compute/workers/{id}/health` | Worker health |
| POST | `/api/v1/compute/workers/{id}/shutdown` | Shutdown worker |
| GET | `/api/v1/compute/audit` | Audit log |

## Benchmark

The GPU benchmark runs matrix multiplication to verify real GPU connectivity:

- **Input**: matrix_size, iterations
- **Output**: execution_time, GFLOPS, result_checksum, GPU info
- **Checksum**: SHA-256 of parameters (reproducible)
- **Status**: PASSED/FAILED/NOT_RUN

## Model Runtime Abstraction

The Model Runtime provides lifecycle management for ML models on GPU workers:

```
RuntimeManager → ComputeManager → Colab/Lightning Worker → GPU Runtime
```

### Runtime Lifecycle
```
UNAVAILABLE → DISCOVERING → READY → LOADING → READY (model loaded)
                                        ↘ ERROR
                     READY → UNLOADING → READY (model unloaded)
```

### Model Registry

5 approved models by default:

| Model | VRAM | Max Tokens | Best For |
|-------|------|-----------|----------|
| `smollm2-1.7b` | 2 GB | 8192 | Low-VRAM, fast inference |
| `phi-3.5-mini` | 4 GB | 131072 | Strong reasoning, small size |
| `mistral-7b` | 7 GB | 32768 | Strong reasoning per parameter |
| `qwen2.5-7b` | 7 GB | 32768 | Multilingual, coding |
| `llama-3.1-8b` | 8 GB | 131072 | General reasoning, instruction-tuned |

### Runtime API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/runtime/health` | Runtime health |
| GET | `/api/v1/runtime/runtimes` | List active runtimes |
| GET | `/api/v1/runtime/runtimes/{id}` | Get runtime details |
| POST | `/api/v1/runtime/runtimes/discover` | Discover runtime on worker |
| POST | `/api/v1/runtime/runtimes/load` | Load model on worker |
| POST | `/api/v1/runtime/runtimes/unload` | Unload model from worker |
| POST | `/api/v1/runtime/runtimes/{id}/health` | Runtime health check |
| POST | `/api/v1/runtime/inference` | Run inference |
| GET | `/api/v1/runtime/inference` | List inference jobs |
| GET | `/api/v1/runtime/inference/{job_id}` | Get inference result |
| GET | `/api/v1/runtime/registry` | Model registry |
| GET | `/api/v1/runtime/registry/models` | List registered models |

### Inference Provenance

Every inference result includes full provenance:
- `model_id`, `model_name`, `model_version`
- `execution_device`, `gpu_name`, `framework`, `dtype`
- `prompt_hash`, `output_hash`
- `tokens_generated`, `generation_time_seconds`, `tokens_per_second`
- `evidence_class`: always `MODEL_INFERENCE`
- `limitations`: populated for incomplete/error/low-performance results

### Security

- Prompt validated against code execution patterns (import, exec, eval, subprocess)
- Model ID validated against injection characters
- Worker ID validated against injection
- All inference results include provenance for audit trail
- No arbitrary code execution. Only structured workloads.

## MatrAIx Integration

When MatrAIx runtime is connected to a GPU worker:
```
AURORA → PersonaSimulationProvider → ComputeManager → Colab/Lightning → MatrAIx → result
```

Evidence class remains `SIMULATED`. Never promoted to `REAL_OBSERVATION`.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AURORA_COMPUTE_WORKER_TOKEN` | (empty) | Worker authentication token |
| `AURORA_COLAB_WORKER_ENABLED` | `false` | Enable Colab provider |
| `AURORA_LIGHTNING_ENDPOINT` | (empty) | Lightning API endpoint |
| `AURORA_LIGHTNING_API_KEY` | (empty) | Lightning API key |
| `AURORA_LIGHTNING_WORKSPACE` | (empty) | Lightning workspace |
| `AURORA_LIGHTNING_PROJECT` | (empty) | Lightning project |

## Testing

263 tests covering:

### Compute Fabric (103 tests)
- Worker Protocol v2 schemas
- Enhanced provider status model
- Worker lifecycle (register, heartbeat, disconnect, reconnect)
- Provider registry
- Colab provider (config, register, heartbeat, timeout, GPU, health)
- Lightning provider (config, register, heartbeat, status, health)
- CPU fallback
- AUTO routing
- Explicit provider routing
- GPU capability discovery
- Job lifecycle (submit, progress, complete, fail)
- Job cancellation
- Benchmark execution
- Job dispatch to worker (pending queue, result reporting)
- Worker authentication (valid, invalid, protocol mismatch)
- Audit events
- Security (payload validation, no arbitrary exec, no secret leakage)
- Stale worker detection

### Model Runtime (74 tests)
- Schema validation (ModelConfig, RuntimeInfo, InferenceRequest, InferenceResult)
- Model registry (default models, lookup, VRAM estimation)
- Security (prompt validation, code exec prevention, model ID validation)
- Runtime manager (lifecycle, discovery, load/unload, inference, provenance)
- Runtime manager job dispatch (RUNTIME_LOAD, RUNTIME_UNLOAD, RUNTIME_INFER)
- Compute runtime provider (LLM interface bridge)
- REST API (health, runtimes, inference, registry)
- Worker runtime handler (discover, load, unload, infer, health)
- Worker job polling (pending jobs, result reporting)
- Edge cases (defaults, bounds, limitations)

## Live Tesla T4 Verification

### Prerequisites
- Google Colab GPU runtime (T4 recommended)
- Connected Colab worker (Cell 3 in notebook)
- Backend running with `AURORA_COLAB_WORKER_ENABLED=true`

### Verification Model
- **Model ID**: `smollm2-1.7b`
- **Model Name**: SmolLM2 1.7B Instruct
- **Framework**: transformers + PyTorch
- **Expected Device**: CUDA (GPU)
- **Expected VRAM**: ~2 GB

### Load Process
1. Worker polls for `RUNTIME_LOAD` job
2. Worker downloads model from HuggingFace
3. Worker loads model to GPU via `device_map="auto"`
4. Worker reports `LOADED` status with memory info

### Inference Process
1. RuntimeManager dispatches `RUNTIME_INFER` job
2. Worker polls and receives job
3. Worker tokenizes prompt on GPU
4. Worker runs `model.generate()` on Tesla T4
5. Worker decodes output tokens
6. Worker reports result with timing and hashes
7. RuntimeManager builds provenance

### Provenance
Every inference includes:
- `job_id`, `inference_id`, `worker_id`, `runtime_id`
- `model_id`, `model_name`, `model_version`
- `execution_device`, `gpu_name`, `framework`, `dtype`
- `prompt_hash`, `output_hash`
- `tokens_generated`, `generation_time_seconds`, `tokens_per_second`
- `evidence_class`: `MODEL_INFERENCE`
- `limitations`: populated for incomplete/error/low-performance results

### Runtime States
```
UNAVAILABLE → DISCOVERING → READY → LOADING → READY (model loaded)
                                        ↘ ERROR
                     READY → UNLOADING → READY (model unloaded)
```

### Failure Conditions
- Worker not connected → `WorkerNotFound`
- Model not in registry → `Model not in approved registry`
- Insufficient VRAM → `Insufficient VRAM`
- Model load timeout → `TimeoutError`
- Inference timeout → `InferenceStatus.TIMEOUT`
- CUDA OOM → `InferenceStatus.FAILED`

### Verification Levels
- **AUTOMATED VERIFIED**: Code and tests pass
- **LIVE GPU VERIFIED**: Connected Colab worker executed the workload
- **LIVE MODEL VERIFIED**: Actual model loaded on Tesla T4 and generated inference
