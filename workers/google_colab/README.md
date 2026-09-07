# AURORA Colab GPU Worker

Connect a Google Colab GPU runtime to your AURORA CORE backend.

## Prerequisites

- A running AURORA CORE backend (production: `https://aurora-core-1-txvl.onrender.com`)
- `AURORA_COMPUTE_WORKER_TOKEN` set on the backend
- A Google account with Colab access

## Setup

### 1. Configure Backend Token

On your AURORA backend, set the worker token:

```bash
export AURORA_COMPUTE_WORKER_TOKEN="your-secret-token-here"
export AURORA_COLAB_WORKER_ENABLED=true
```

### 2. Open the Notebook

Open `AURORA_Colab_Worker.ipynb` in Google Colab:
- Go to https://colab.research.google.com
- File → Open notebook → Upload → select `AURORA_Colab_Worker.ipynb`

### 3. Start GPU Runtime

In Colab:
- Runtime → Change runtime type → Hardware accelerator → **GPU (T4)**

### 4. Run Cells

| Cell | Purpose |
|------|---------|
| Cell 1 | Configure backend URL and worker token (secure input) |
| Cell 2 | Detect GPU hardware from runtime |
| Cell 3 | Connect worker + start heartbeat + job polling |
| Cell 4 | Run GPU benchmark (real matrix multiplication) |
| Cell 5 | Load model (smollm2-1.7b) on Tesla T4 |
| Cell 6 | Run inference on loaded model |
| Cell 7 | Check runtime status via API |
| Cell 8 | Disconnect worker cleanly |

### 5. Verify Connection

After Cell 3, you should see:

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

### 6. Run GPU Benchmark

Cell 5 runs a real matrix multiplication benchmark:

- Executes on actual GPU hardware
- Reports actual GFLOPS
- Generates SHA-256 checksum from computation
- Never fabricated

### 7. Disconnect

Cell 8 gracefully shuts down the worker:
- Stops heartbeat loop
- Sends shutdown to backend
- Backend marks worker as DISCONNECTED

## Model Runtime

After connecting (Cell 3), the worker can load and run models:

### Load Model (Cell 5)
- Downloads model from HuggingFace
- Loads to GPU via `device_map="auto"`
- Reports load time and memory usage
- Model stays loaded for inference

### Run Inference (Cell 6)
- Tokenizes prompt on GPU
- Runs `model.generate()` on Tesla T4
- Reports output, timing, and hashes
- Provenance recorded for audit trail

### Approved Models
| Model | VRAM | Best For |
|-------|------|----------|
| `smollm2-1.7b` | 2 GB | Low-VRAM, fast inference |
| `phi-3.5-mini` | 4 GB | Strong reasoning, small size |
| `mistral-7b` | 7 GB | Strong reasoning per parameter |
| `qwen2.5-7b` | 7 GB | Multilingual, coding |
| `llama-3.1-8b` | 8 GB | General reasoning |

## Session Behavior

- Colab sessions are **temporary**
- When Colab disconnects, AURORA marks worker as DISCONNECTED after heartbeat timeout (~2 minutes)
- To reconnect: re-run Cell 3
- Heartbeats run every 30 seconds

## GPU Detection

GPU information comes only from real runtime:
- **PyTorch CUDA API** (preferred)
- **nvidia-smi** (fallback)

If no GPU detected:
- `GPU_STATUS = UNKNOWN`
- Worker still connects but without GPU capabilities
- You must set Runtime → Change runtime type → GPU

## Security

- Worker token entered via `getpass` (masked input, not stored)
- Token never printed in full
- Token never sent to frontend
- No Google credentials collected
- No arbitrary Python/shell execution accepted
- Only structured workloads supported

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AURORA_COMPUTE_WORKER_TOKEN` | Yes | Worker authentication token (set on backend) |
| `AURORA_COLAB_WORKER_ENABLED` | Yes | Must be `true` on backend |

## Troubleshooting

**"FAILED: No response from backend"**
- Check backend URL is correct
- Verify backend is running
- Check network connectivity

**"FAILED: Registration rejected — Invalid worker API token"**
- Token does not match `AURORA_COMPUTE_WORKER_TOKEN` on backend
- Re-enter token in Cell 1

**"No CUDA available"**
- Runtime is not set to GPU
- Go to Runtime → Change runtime type → GPU (T4)

**Heartbeat fails after some time**
- Colab session may have expired
- Re-run Cell 3 to reconnect

## Files

| File | Purpose |
|------|---------|
| `AURORA_Colab_Worker.ipynb` | Main Colab notebook |
| `worker.py` | Standalone worker client (for non-notebook usage) |
| `README.md` | This file |
