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
- Accept arbitrary code execution

**AURORA DOES:**
- Connect to an already-running Lightning worker
- Authenticate via a shared worker token
- Execute structured GPU workloads
- Report real GPU capabilities
- Load and run approved HuggingFace models via source_model_id resolution

## Setup

### 1. Configure Your Backend

Set the worker token on your AURORA backend:

```bash
export AURORA_COMPUTE_WORKER_TOKEN="your-secret-token-here"
```

### 2. Set Up Lightning Instance

Create a Lightning AI compute instance with GPU.

### 3. Install Worker

On your Lightning instance:

```bash
pip install requests torch transformers
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
GPU: <actual GPU name>
VRAM: <actual VRAM> MB
Runtime: READY
```

## Model Runtime

The worker supports loading and running approved HuggingFace models.

### Approved Models

| model_id | source_model_id |
|----------|----------------|
| `qwen2.5-0.5b-instruct` | `Qwen/Qwen2.5-0.5B-Instruct` |
| `smollm2-1.7b` | `HuggingFaceTB/SmolLM2-1.7B-Instruct` |
| `phi-3.5-mini` | `microsoft/Phi-3.5-mini-instruct` |
| `mistral-7b` | `mistralai/Mistral-7B-Instruct-v0.3` |
| `qwen2.5-7b` | `Qwen/Qwen2.5-7B-Instruct` |
| `llama-3.1-8b` | `meta-llama/Llama-3.1-8B-Instruct` (requires auth) |

### Source Model ID Resolution

The worker resolves AURORA internal `model_id` to the official HuggingFace `source_model_id` before calling `from_pretrained()`. Only approved source_model_id values are permitted.

### Security

- Only registered models may be loaded
- Arbitrary HuggingFace repository IDs are rejected
- Arbitrary URLs are rejected
- The worker token is never exposed to the frontend
- No arbitrary code execution is accepted

## Session Lifecycle

- The worker maintains a persistent connection to AURORA
- When the Lightning instance stops, the worker disconnects
- AURORA marks the worker as DISCONNECTED after heartbeat timeout
- Restart the worker to reconnect

## Worker Protocol v2

The worker implements:
- Registration with capabilities
- Periodic heartbeat with GPU status
- Job polling for dispatched workloads
- Runtime operations: discover, load, unload, infer, health
- Benchmark execution (real GPU matrix multiply)
