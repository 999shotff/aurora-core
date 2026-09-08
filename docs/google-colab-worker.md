# Google Colab GPU Worker — Setup Guide

Connect a real Google Colab GPU runtime to your AURORA CORE backend.

## Overview

AURORA CORE orchestrates GPU compute through **user-controlled workers**.
The worker runs inside your Colab notebook and connects to your AURORA backend.

```
Google Colab (GPU Runtime)
    ↓
AURORA Worker (Python client)
    ↓
HTTP → AURORA Backend (Render)
    ↓
Compute Fabric (GPU READY)
    ↓
GPU Benchmark / Workloads
```

## Prerequisites

1. **AURORA CORE backend** running (production: `https://aurora-core-1-txvl.onrender.com`)
2. **Worker token** configured on backend: `AURORA_COMPUTE_WORKER_TOKEN`
3. **Colab provider enabled** on backend: `AURORA_COLAB_WORKER_ENABLED=true`
4. **Google account** with Colab access

## Step 1: Configure Backend

On your AURORA backend (Render dashboard or SSH):

```bash
# Set worker authentication token
export AURORA_COMPUTE_WORKER_TOKEN="your-secret-token-here"

# Enable Colab provider
export AURORA_COLAB_WORKER_ENABLED=true
```

**Important:** The token must match exactly between backend and worker.

## Step 2: Open Colab Notebook

1. Go to https://colab.research.google.com
2. File → Open notebook
3. Upload → Select `workers/google_colab/AURORA_Colab_Worker.ipynb`

## Step 3: Start GPU Runtime

1. Runtime → Change runtime type
2. Hardware accelerator → **GPU (T4 recommended)**
3. Click Save

Verify GPU is available:
- Runtime → View runtime status
- Should show "GPU: Tesla T4" or similar

## Step 4: Configure Connection (Cell 1)

Cell 1 asks for:
- **Backend URL** (default: `https://aurora-core-1-txvl.onrender.com`)
- **Worker token** (entered securely via `getpass`, not stored)

The token is masked during input and never printed in full.

## Step 5: Detect GPU (Cell 2)

Cell 2 detects GPU from the actual runtime:
- Uses PyTorch CUDA API (preferred)
- Falls back to nvidia-smi
- Reports only real values (never fabricated)

Expected output:
```
GPU detected: Tesla T4
VRAM: 15360 MB (15.0 GB)
CUDA: 12.1
Compute capability: 7.5
Runtime: PyTorch 2.1.0
```

## Step 6: Connect Worker (Cell 3)

Cell 3 registers the worker with AURORA backend:

```
AURORA WORKER
==================================================
Protocol:    2.0
Worker:      colab-<hostname>-<timestamp>
Provider:    GOOGLE_COLAB
Connection:  CONNECTED
Auth:        SUCCESS
GPU:         Tesla T4
VRAM:        15360 MB (15.0 GB)
CUDA:        12.1
Heartbeat:   ACTIVE (every 30s)
==================================================
```

**What happens:**
1. Worker sends `REGISTER` to `/api/v1/compute/workers/register`
2. Backend validates token
3. Backend checks protocol version
4. Backend registers worker with GPU capabilities
5. Backend sends `REGISTER_ACK`
6. Provider status changes to READY

## Step 7: Start Heartbeat (Cell 4)

Cell 4 starts a background heartbeat loop:
- Sends `HEARTBEAT` every 30 seconds
- Reports current status (READY/BUSY)
- Updates GPU capabilities
- Backend responds with `HEARTBEAT_ACK`

The worker stays READY as long as heartbeats are received.

## Step 8: Run GPU Benchmark (Cell 5)

Cell 5 runs a **real** GPU benchmark:
- Matrix multiplication on actual GPU
- Configurable matrix size and iterations
- Reports actual GFLOPS
- Generates SHA-256 checksum

Expected output:
```
GPU BENCHMARK RESULT
==================================================
GPU:              Tesla T4
Matrix:           2048x2048
Iterations:       20
Execution time:   0.847s
GFLOPS:           40.32
Checksum:         a1b2c3d4e5f6g7h8
Status:           PASSED
==================================================
```

**Important:** The benchmark executes on real GPU hardware. GFLOPS values are legitimate.

## Step 9: Verify in Frontend

Open your AURORA frontend at `/compute`:

Expected display:
```
Google Colab
● READY

Worker:
colab-<hostname>-<timestamp>

GPU:
Model: Tesla T4
VRAM: 15.0 GB
CUDA: 12.1
Compute: 7.5
Runtime: PyTorch 2.1.0

Capabilities: INFERENCE EMBEDDINGS VISION TRAINING BENCHMARK
```

## Step 10: Disconnect (Cell 6)

Cell 6 gracefully shuts down:
1. Stops heartbeat loop
2. Sends `SHUTDOWN` to backend
3. Backend removes worker
4. Provider status changes to DISCONNECTED

## Disconnect / Reconnect Behavior

### When Colab stops:
1. Heartbeats stop
2. After ~120 seconds, provider detects stale worker
3. Provider status: `READY → DISCONNECTED`
4. Frontend shows: `DISCONNECTED`

### To reconnect:
1. Re-run Cell 3 (connect worker)
2. Re-run Cell 4 (start heartbeat)
3. Worker status: `DISCONNECTED → READY`

### Heartbeat timeout:
- Provider timeout: 120 seconds
- Manager timeout: 150 seconds
- Heartbeat interval: 30 seconds

## Security

### What AURORA does NOT do:
- Access your Google account
- Automate login
- Store your credentials
- Accept arbitrary Python execution
- Accept arbitrary shell commands
- Send credentials to frontend

### What AURORA DOES:
- Connects to an already-running Colab session
- Authenticates via shared worker token
- Executes only structured workloads
- Reports real GPU capabilities

### Token handling:
- Entered via `getpass` (masked)
- Never printed in full
- Never stored in notebook
- Never sent to frontend
- Validated server-side only

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/compute/workers/register` | POST | Register worker |
| `/api/v1/compute/workers/{id}/heartbeat` | POST | Periodic heartbeat |
| `/api/v1/compute/workers/{id}/shutdown` | POST | Graceful shutdown |
| `/api/v1/compute/status` | GET | Check provider status |

## Troubleshooting

### "FAILED: No response from backend"
- Backend URL may be incorrect
- Backend may be down
- Check network connectivity
- Verify backend health: `GET /api/v1/compute/health`

### "FAILED: Registration rejected — Invalid worker API token"
- Token does not match backend
- Re-enter token in Cell 1
- Verify backend has `AURORA_COMPUTE_WORKER_TOKEN` set

### "No CUDA available"
- Runtime not set to GPU
- Go to Runtime → Change runtime type → GPU
- Verify: Runtime → View runtime status

### Worker connects but shows UNKNOWN GPU
- GPU detection failed
- Check if PyTorch is installed
- Check if nvidia-smi is available
- Try installing PyTorch: `pip install torch`

### Heartbeat fails repeatedly
- Backend may have restarted
- Re-run Cell 3 to reconnect
- Check backend logs for errors

### Benchmark shows 0 GFLOPS
- GPU not available
- Check Runtime → View runtime status
- Ensure GPU is allocated

### Ollama model not found
- Model must be in approved whitelist: `qwen2.5:0.5b`
- Run Cell 6 to verify Ollama + approved model
- Check `AURORA_APPROVED_OLLAMA_MODELS` environment variable

### Ollama not reachable
- Run Cell 5 to install dependencies + Ollama
- Check if Ollama binary exists at `/usr/local/bin/ollama`
- Kill existing processes: `pkill -f ollama`
- Start fresh: `/usr/local/bin/ollama serve &amp;`

### Inference returns "runtime: ollama not available"
- Ollama runtime handler not connected
- Run Cell 3 (worker connection) + Cell 5 (Ollama install) + Cell 6 (Ollama verify)
- Check that `_ollama_runtime` is initialized in worker

### GPU/CPU status shows CPU_ONLY
- Ollama is running but not using GPU
- Check `nvidia-smi` output for Ollama processes
- Ensure Ollama was started after GPU was allocated
- Restart Ollama: `pkill -f ollama &amp;&amp; /usr/local/bin/ollama serve &amp;`

## Environment Variables

| Variable | Where | Required | Description |
|----------|-------|----------|-------------|
| `AURORA_COMPUTE_WORKER_TOKEN` | Backend | Yes | Worker authentication token |
| `AURORA_COLAB_WORKER_ENABLED` | Backend | Yes | Enable Colab provider (`true`/`false`) |

## Worker Protocol v2

| Message | Direction | Purpose |
|---------|-----------|---------|
| `REGISTER` | Worker → Backend | Register with capabilities |
| `REGISTER_ACK` | Backend → Worker | Accept/reject |
| `HEARTBEAT` | Worker → Backend | Liveness + state |
| `HEARTBEAT_ACK` | Backend → Worker | Ack + pending jobs |
| `SHUTDOWN` | Worker → Backend | Graceful shutdown |

## GPU Detection Priority

1. **PyTorch CUDA API** (preferred)
   - `torch.cuda.get_device_name(0)`
   - `torch.cuda.get_device_properties(0)`
   - `torch.version.cuda`
   - `torch.cuda.get_device_capability(0)`

2. **nvidia-smi** (fallback)
   - `nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap`

3. **UNKNOWN** (if both fail)
   - Worker still connects
   - No GPU capabilities reported

## Ollama Runtime

The worker supports running inference via Ollama (localhost:11434) in addition to Transformers.

### Architecture
```
AURORA → OllamaProvider → RuntimeManager → Compute Fabric → Colab Worker → Ollama → GPU → result
```

### Security Constraints
- Ollama runs on **localhost only** (127.0.0.1:11434)
- Ollama is **NOT exposed to public internet**
- Only **approved models** can be loaded (whitelist enforced)
- No arbitrary code execution
- No credential storage

### GPU/CPU Classification
Cell 7 verifies GPU vs CPU execution:
- **GPU_ACCELERATED**: Model running on GPU (confirmed via nvidia-smi/ollama ps)
- **CPU_ONLY**: Model running on CPU
- **GPU_AVAILABLE_BUT_NOT_USED**: GPU detected but Ollama not using it
- **RUNTIME_UNAVAILABLE**: Cannot determine

### Notebook Cells
1. Cell 1: Configure (backend URL, worker token)
2. Cell 2: Detect GPU
3. Cell 3: Connect worker + start heartbeat + job polling
4. Cell 4: Run GPU benchmark
5. Cell 5: Install dependencies + Ollama
6. Cell 6: Verify Ollama + approved model
7. Cell 7: Verify GPU execution + run live inference
8. Cell 8: Check runtime status (including GPU/CPU)
9. Cell 9: Disconnect cleanly
