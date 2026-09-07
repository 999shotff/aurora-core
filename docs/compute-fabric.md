# Compute Fabric — Provider-Agnostic GPU/CPU Orchestration

**Status:** v0.1.0  
**Type:** Infrastructure layer  
**Depends On:** None (LLM-1 through LLM-5 work without GPU)

---

## What It Is

Provider-agnostic compute orchestration that routes workloads between:

1. **CPU** — always available, safe fallback
2. **Google Colab** — user-controlled GPU worker via authenticated protocol
3. **Lightning AI** — configured via environment variables

**It does NOT:**
- Make predictions
- Generate trading signals
- Execute arbitrary code
- Connect to brokers
- Fabricate GPU availability

---

## Architecture

```
                    AURORA CORE
                         |
                  ComputeManager
                         |
              +----------+----------+
              |          |          |
             CPU       Colab     Lightning
           Provider    Worker      Worker
              |          |          |
              +----------+----------+
                         |
                  Model / Job API
                         |
              LLM / ML / Vision tasks
```

---

## Providers

### CPU Provider

Always available. Safe fallback when GPU is OFF or unavailable.

- Status: `READY` when enabled
- Capabilities: inference, embeddings (no GPU)
- No external dependencies

### Google Colab Provider

User-controlled Colab worker connects via authenticated worker protocol.

**Status depends on real worker connection:**
- `NOT_CONFIGURED` — `AURORA_COLAB_WORKER_ENABLED` not set
- `DISCONNECTED` — no worker registered or heartbeat expired
- `READY` — worker connected and healthy

**Do NOT assume Colab is a permanent server.** Sessions expire.

### Lightning AI Provider

Configured via environment variables.

**Status depends on real configuration and worker:**
- `NOT_CONFIGURED` — missing `AURORA_LIGHTNING_ENDPOINT` or `AURORA_LIGHTNING_API_KEY`
- `DISCONNECTED` — no worker connected
- `READY` — worker connected and healthy

---

## Environment Variables

```bash
# Compute mode: AUTO, CPU, GOOGLE_COLAB, LIGHTNING
AURORA_COMPUTE_MODE=CPU

# Worker authentication token
AURORA_COMPUTE_WORKER_TOKEN=

# Google Colab
AURORA_COLAB_WORKER_ENABLED=false

# Lightning AI
AURORA_LIGHTNING_ENDPOINT=
AURORA_LIGHTNING_API_KEY=
AURORA_LIGHTNING_WORKSPACE=
AURORA_LIGHTNING_PROJECT=
```

---

## Worker Protocol

Workers register with AURORA and send periodic heartbeats.

### Registration

```
POST /api/v1/compute/workers/register

{
  "worker_id": "colab-gpu-1",
  "provider_id": "colab",
  "provider_type": "GOOGLE_COLAB",
  "capabilities": {
    "inference": true,
    "gpu_name": "T4",
    "vram_gb": 15.0,
    "cuda_version": "12.1",
    "framework": "pytorch"
  },
  "api_token": "your-secret-token"
}
```

### Heartbeat

```
POST /api/v1/compute/workers/{worker_id}/heartbeat

{
  "worker_id": "colab-gpu-1",
  "status": "READY",
  "capabilities": { ... },
  "api_token": "your-secret-token"
}
```

### Shutdown

```
POST /api/v1/compute/workers/{worker_id}/shutdown

{
  "worker_id": "colab-gpu-1",
  "reason": "session ending",
  "api_token": "your-secret-token"
}
```

---

## Compute Modes

| Mode | Behavior |
|------|----------|
| `AUTO` | Use GPU if available, fall back to CPU |
| `CPU` | Always use CPU |
| `GOOGLE_COLAB` | Require Colab, fail if unavailable |
| `LIGHTNING` | Require Lightning, fail if unavailable |

**AUTO mode** falls back to CPU safely.  
**Explicit modes** return error if provider unavailable — no silent switching.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/compute/health` | Health check |
| GET | `/api/v1/compute/status` | Full compute status |
| GET | `/api/v1/compute/providers` | All provider info |
| POST | `/api/v1/compute/enable` | Enable GPU compute |
| POST | `/api/v1/compute/disable` | Disable GPU compute |
| POST | `/api/v1/compute/mode` | Change compute mode |
| POST | `/api/v1/compute/jobs` | Submit a job |
| GET | `/api/v1/compute/jobs/{id}` | Get job status |
| POST | `/api/v1/compute/jobs/{id}/cancel` | Cancel a job |
| POST | `/api/v1/compute/workers/register` | Register worker |
| POST | `/api/v1/compute/workers/{id}/heartbeat` | Worker heartbeat |
| POST | `/api/v1/compute/workers/{id}/shutdown` | Worker shutdown |
| GET | `/api/v1/compute/audit` | Audit log |

---

## Frontend

Route: `/compute`

- Compute status dashboard
- Enable/disable GPU toggle
- Mode selector (AUTO/CPU/Lightning/Colab)
- Provider cards with honest status
- GPU info only shown when real worker connected
- Active jobs counter

---

## Security

- Worker authentication via `AURORA_COMPUTE_WORKER_TOKEN`
- API keys never exposed to frontend
- No arbitrary code execution
- No shell command execution
- No secret leakage
- Bounded retry/backoff
- Worker must authenticate on every request

---

## Routing Logic

```
AUTO:
  if GPU provider READY → use GPU
  else → use CPU

CPU:
  always CPU

GOOGLE_COLAB:
  if Colab READY → use Colab
  else → error

LIGHTNING:
  if Lightning READY → use Lightning
  else → error
```

---

## Failure Behavior

| Scenario | Result |
|----------|--------|
| GPU OFF | CPU only |
| Colab not configured | NOT_CONFIGURED |
| Colab worker disconnected | DISCONNECTED → CPU fallback (AUTO) |
| Lightning not configured | NOT_CONFIGURED |
| Lightning unavailable | DISCONNECTED → CPU fallback (AUTO) |
| Worker crashes | Heartbeat timeout → DISCONNECTED |
| Backend restart | Providers reset to initial state |
| Job timeout | Job marked TIMEOUT |

---

## LLM-1 → LLM-5 Integration

The LLM layer asks for capability/workload, not specific hardware:

```python
# "execute inference" — not "run on CUDA device 0"
ComputeJobRequest(workload_type=WorkloadType.INFERENCE)
```

The Compute Fabric decides where that workload goes.

---

## How to Connect a Colab Worker

1. Set `AURORA_COLAB_WORKER_ENABLED=true` on the backend
2. Set `AURORA_COMPUTE_WORKER_TOKEN=your-secret`
3. In a Colab notebook, run an AURORA worker service
4. Worker registers via `POST /api/v1/compute/workers/register`
5. Worker sends heartbeats every 60 seconds
6. Compute Fabric marks Colab as READY

---

## Known Limitations

- Colab sessions are not permanent
- Lightning requires real API key and endpoint
- No GPU provider connected by default
- Worker protocol is v1.0 — may evolve
- Job execution is currently stub (CPU completes immediately)

---

## NO_DEPLOYMENT_SIGNAL

This module routes computational workloads. It does NOT:
- Make predictions
- Generate trading signals
- Make trading decisions
- Connect to brokers or exchanges
- Use real money
