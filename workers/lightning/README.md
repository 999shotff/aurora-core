# AURORA Lightning AI Worker

Connect a Lightning AI GPU instance to AURORA CORE's Compute Fabric.

## How It Works

AURORA CORE orchestrates GPU compute through a **user-controlled worker**.
The worker runs on your Lightning AI instance and connects to your AURORA backend.

**AURORA does NOT:**
- Access your Lightning account
- Automate login
- Store your API credentials
- Manage your Lightning infrastructure

**AURORA DOES:**
- Connect to an already-running Lightning worker
- Authenticate via a shared worker token
- Execute structured GPU workloads
- Report real GPU capabilities

## Setup

### 1. Configure Your Backend

Set the worker token and Lightning credentials on your AURORA backend:

```bash
export AURORA_COMPUTE_WORKER_TOKEN="your-secret-token-here"
export AURORA_LIGHTNING_ENDPOINT="https://your-lightning-endpoint.com"
export AURORA_LIGHTNING_API_KEY="your-lightning-api-key"
export AURORA_LIGHTNING_ENABLED=true
```

### 2. Set Up Lightning Instance

Create a Lightning AI compute instance with GPU.

### 3. Install Worker

On your Lightning instance:

```bash
pip install requests torch
```

### 4. Configure Worker

Set environment variables on your Lightning instance:

```bash
export AURORA_BACKEND_URL="https://your-aurora-backend.onrender.com"
export AURORA_WORKER_TOKEN="your-secret-token-here"
```

### 5. Run Worker

```bash
python workers/lightning/worker.py
```

### 6. Verify

On your AURORA Terminal (/terminal), the compute status should show:

```
Lightning AI: READY
GPU: NVIDIA A100
VRAM: 81920 MB
```

## Session Lifecycle

- The worker maintains a persistent connection to AURORA
- When the Lightning instance stops, the worker disconnects
- AURORA marks the worker as DISCONNECTED after heartbeat timeout
- Restart the worker to reconnect

## Security

- The worker token is never sent to the frontend
- Authentication happens backend-side only
- No arbitrary code execution is accepted
- Only structured workloads (inference, embeddings, benchmark) are supported
