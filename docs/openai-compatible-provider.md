# OpenAI-Compatible Remote Provider

AURORA CORE can connect to any OpenAI-compatible API without requiring a local GPU, Colab worker, Ollama, or NVIDIA NIM.

## Architecture

```
AURORA Frontend (Compute Page)
    ↓
AURORA Backend (API routes)
    ↓
OpenAICompatibleProvider (LLM provider)
    ↓
Configured Remote API (HTTPS)
    ↓
Remote Model
    ↓
Response → AURORA LLM-1 through LLM-5 systems
```

The remote server performs all inference. AURORA does NOT need a GPU for this provider.

## Configuration

### Environment Variables

```bash
# Provider selection
AURORA_LLM_PROVIDER=openai-compatible

# Provider-specific (preferred)
AURORA_OPENAI_COMPATIBLE_BASE_URL=https://example.com/v1
AURORA_OPENAI_COMPATIBLE_API_KEY=your-api-key
AURORA_OPENAI_COMPATIBLE_MODEL=model-name

# Or use generic env vars (fallback)
AURORA_LLM_API_KEY=your-api-key
AURORA_LLM_BASE_URL=https://example.com/v1
AURORA_LLM_MODEL=model-name
```

Provider-specific variables take precedence over generic ones.

### Frontend Configuration

The Compute page (`/compute`) includes an OPENAI-COMPATIBLE card where you can:

1. Enter a **Provider Name** (display only)
2. Enter the **Base URL** (e.g., `https://api.example.com/v1`)
3. Enter the **API Key** (password field, never stored in browser)
4. Enter the **Model** name
5. Click **Test Connection** to verify
6. Click **Save Configuration** to apply for the session

Configuration is session-scoped (stored in server memory only). The API key is never persisted to disk, never exposed in API responses, and never logged.

## Security

- API keys are server-side only
- Never exposed in `/health`, `/status`, or any GET endpoint
- Never stored in localStorage or browser memory
- Never logged or included in audit events
- Provenance records hostname only, never the full URL with credentials
- Base URL validation: HTTPS required for non-localhost hosts
- Credential-in-URL detection: rejects `https://user:pass@host/...`

## Supported API Contract

Standard OpenAI-compatible `/chat/completions` endpoint:

```json
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "model-name",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "max_tokens": 2048,
  "temperature": 0.7
}
```

The provider is conservative: it only includes `temperature` in the request if non-default, because some servers reject unsupported parameters.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/compute/providers/openai-compatible/test` | Test connection |
| POST | `/api/v1/compute/providers/openai-compatible/configure` | Save session config |
| GET | `/api/v1/compute/providers/openai-compatible/status` | Get provider status |
| POST | `/api/v1/compute/providers/openai-compatible/infer` | Run inference |

### Test Connection

```json
POST /api/v1/compute/providers/openai-compatible/test
{
  "base_url": "https://api.example.com/v1",
  "api_key": "your-key",
  "model": "model-name"
}

Response:
{
  "status": "CONNECTED",
  "provider": "openai-compatible",
  "base_url": "api.example.com",
  "model": "model-name",
  "latency_ms": 1234,
  "message": "Connection successful"
}
```

### Provider Status

```json
GET /api/v1/compute/providers/openai-compatible/status

Response:
{
  "provider": "openai-compatible",
  "status": "CONFIGURED",
  "base_url": "api.example.com",
  "model": "model-name",
  "execution": "REMOTE_API",
  "gpu_required": false
}
```

## Error Handling

Normalized error types returned to frontend:

| Status | Meaning |
|--------|---------|
| `CONNECTED` | Connection successful |
| `AUTHENTICATION_ERROR` | Invalid or missing API key |
| `MODEL_UNAVAILABLE` | Model not found |
| `UNREACHABLE` | Server unreachable |
| `TIMEOUT` | Request timed out |
| `RATE_LIMITED` | Too many requests (429) |
| `INVALID_REQUEST` | Bad request (400) |
| `PROVIDER_ERROR` | Other HTTP error |

## GPU Independence

This provider:

- Does NOT require Colab, CUDA, NVIDIA, or local GPU
- Does NOT require a Compute Worker
- Does NOT require Ollama
- Can be used while the Colab worker is disconnected
- Reports `gpu_required: false` in all status responses

## Provenance

Every successful inference records:

```json
{
  "provider": "openai-compatible",
  "model": "model-name",
  "base_url_hostname": "api.example.com",
  "prompt_hash": "sha256:16chars",
  "output_hash": "sha256:16chars",
  "latency_ms": 1234,
  "request_id": "chatcmpl-...",
  "runtime": "remote-api",
  "gpu_required": false
}
```

Never records: API key, Authorization header, full URL with credentials.

## Limitations

- API key must be re-entered each session (by design — no persistent secret storage)
- Model listing (`/v1/models`) may not be available on all servers (provider falls back to generate-based test)
- No streaming support in this milestone
- No organization/project parameter support
- Temperature is only sent if non-default (conservative approach)
