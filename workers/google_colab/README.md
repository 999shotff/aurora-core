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
| Cell 3 | Connect worker to AURORA backend |
| Cell 4 | Start heartbeat loop (worker stays READY) |
| Cell 5 | Run GPU benchmark (real matrix multiplication) |
| Cell 6 | Disconnect worker cleanly |

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

Cell 6 gracefully shuts down the worker:
- Stops heartbeat loop
- Sends shutdown to backend
- Backend marks worker as DISCONNECTED

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
