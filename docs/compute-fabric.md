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

Future runtimes (not yet implemented):
- llama.cpp
- vLLM
- Transformers
- Ollama

Interface:
```python
class ModelRuntime:
    def load(model_id: str) -> None
    def unload() -> None
    def health() -> RuntimeStatus
    def capabilities() -> ComputeCapabilities
    def infer(input: dict) -> dict
```

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

103 tests covering:
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
- Model runtime contract
- Worker authentication (valid, invalid, protocol mismatch)
- Audit events
- Security (payload validation, no arbitrary exec, no secret leakage)
- Stale worker detection
