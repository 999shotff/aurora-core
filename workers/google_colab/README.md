# AURORA Colab GPU Worker

Connect a Google Colab GPU runtime to AURORA CORE's Compute Fabric.

## How It Works

AURORA CORE orchestrates GPU compute through a **user-controlled worker**.
The worker runs inside your Colab notebook and connects to your AURORA backend.

**AURORA does NOT:**
- Access your Google account
- Automate login
- Store your credentials
- Bypass Colab restrictions

**AURORA DOES:**
- Connect to an already-running Colab GPU session
- Authenticate via a shared worker token
- Execute structured GPU workloads
- Report real GPU capabilities

## Setup

### 1. Configure Your Backend

Set the worker token on your AURORA backend:

```bash
export AURORA_COMPUTE_WORKER_TOKEN="your-secret-token-here"
export AURORA_COLAB_WORKER_ENABLED=true
```

### 2. Open the Worker Notebook

Open `aurora_colab_worker.ipynb` in Google Colab.

### 3. Configure the Worker

In the notebook's first cell, set:

```python
AURORA_BACKEND_URL = "https://your-aurora-backend.onrender.com"
AURORA_WORKER_TOKEN = "your-secret-token-here"  # Must match backend
```

### 4. Start GPU Runtime

In Colab: Runtime → Change runtime type → GPU (T4, V100, or A100).

### 5. Run All Cells

The worker will:
1. Detect your GPU
2. Connect to AURORA backend
3. Authenticate with the worker token
4. Report capabilities
5. Start accepting jobs

### 6. Verify

On your AURORA Terminal (/terminal), the compute status should show:

```
Google Colab: READY
GPU: Tesla T4
VRAM: 15360 MB
```

## Session Limitations

- Colab sessions are **temporary**
- When Colab disconnects, AURORA marks the worker as DISCONNECTED
- You must re-run the notebook to reconnect
- GPU VRAM is reported from the actual runtime

## Security

- The worker token is never sent to the frontend
- Authentication happens backend-side only
- No arbitrary code execution is accepted
- Only structured workloads (inference, embeddings, benchmark) are supported
