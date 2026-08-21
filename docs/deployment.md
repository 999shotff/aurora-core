# AURORA CORE — Deployment Guide

**Version:** 0.2.0
**Status:** NOT DEPLOYED — Configuration ready

## Architecture

```
GitHub Repository
    ↓
    ├── CI/CD (GitHub Actions)
    │   ├── Python tests, ruff, mypy
    │   ├── TypeScript typecheck
    │   └── Vite production build → artifact
    │
    ├── Frontend (Vercel)
    │   ├── Connects to GitHub repo
    │   ├── Auto-deploys on push to main
    │   └── Needs: VITE_API_URL environment variable
    │
    └── Backend (Render)
        ├── Docker build from Dockerfile
        ├── Runs FastAPI + uvicorn
        └── Needs: AURORA_DATA_MODE, AURORA_CORS_ORIGINS
```

## Deployment Steps

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "AURORA CORE v0.2.0"
git remote add origin https://github.com/YOUR_USERNAME/aurora-core.git
git push -u origin main
```

**NOT YET DONE** — requires GitHub credentials.

### Step 2: Deploy Frontend (Vercel)

1. Go to https://vercel.com/new
2. Import GitHub repo
3. Framework: Vite
4. Root directory: `frontend`
5. Environment variables:
   - `VITE_API_URL` = `https://your-backend.onrender.com`
6. Deploy

**NOT YET DONE** — requires Vercel account.

### Step 3: Deploy Backend (Render)

1. Go to https://render.com
2. Create new Web Service
3. Connect GitHub repo
4. Runtime: Docker
5. Dockerfile path: `./Dockerfile`
6. Environment variables:
   - `AURORA_DATA_MODE` = `real`
   - `AURORA_CORS_ORIGINS` = `https://your-frontend.vercel.app`
   - `AURORA_DEBUG` = `false`
7. Health check path: `/health`
8. Deploy

**NOT YET DONE** — requires Render account.

## Environment Variables

### Backend (Render)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AURORA_DATA_MODE` | Yes | `demo` | `real` for live data, `demo` for mock |
| `AURORA_CORS_ORIGINS` | Yes | `https://aurora-core.vercel.app` | Comma-separated allowed origins |
| `AURORA_HOST` | No | `0.0.0.0` | Bind address |
| `AURORA_PORT` | No | `8000` | Bind port |
| `AURORA_DEBUG` | No | `false` | Enable debug logging |
| `AURORA_LOG_LEVEL` | No | `info` | Logging level |
| `AURORA_YAHOO_API_KEY` | No | (empty) | Yahoo Finance API key (optional) |
| `AURORA_CACHE_TTL_SECONDS` | No | `60` | Cache TTL |
| `AURORA_CACHE_MAX_SIZE` | No | `256` | Max cache entries |
| `AURORA_RATE_LIMIT_RPM` | No | `60` | Requests per minute |
| `AURORA_RATE_LIMIT_BURST` | No | `10` | Burst limit |
| `AURORA_WS_ENABLED` | No | `true` | Enable WebSocket |
| `AURORA_WS_MAX_CONNECTIONS` | No | `100` | Max WS connections |
| `AURORA_WS_PING_INTERVAL` | No | `30` | WS ping interval (seconds) |
| `AURORA_PROVIDER_TIMEOUT_SECONDS` | No | `10` | Provider timeout |
| `AURORA_PROVIDER_MAX_RETRIES` | No | `3` | Provider retries |

### Frontend (Vercel)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes (prod) | `http://127.0.0.1:8000` | Backend URL |

## Health Endpoint

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "is_demo": false,
  "research_conclusion": "NO_DEPLOYMENT_SIGNAL",
  "services": [
    {"service": "market-data-api", "status": "operational", "version": "0.1.0"},
    {"service": "market-data-provider", "status": "operational", "version": "yfinance"},
    {"service": "chart-engine", "status": "operational", "version": "0.1.0"}
  ],
  "provider_health": {
    "healthy": true,
    "stale": false,
    "success_count": 5,
    "failure_count": 0,
    "consecutive_failures": 0
  }
}
```

## CORS

CORS origins are configured via `AURORA_CORS_ORIGINS` (comma-separated).

Default: `https://aurora-core.vercel.app`

For local development, add `http://localhost:5173`.

## Data Modes

### DEMO mode (`AURORA_DATA_MODE=demo`)
- Returns generated mock OHLCV data
- No external network calls
- `is_demo: true` in all responses
- Badge: DEMO (orange)

### REAL mode (`AURORA_DATA_MODE=real`)
- Fetches live market data from yfinance
- Supports 6 target assets: BTC-USD, ETH-USD, SPY, QQQ, GOLD, SILVER
- 10 total assets in registry
- Rate limited (60 RPM, burst 10)
- `is_demo: false` in all responses
- Badge: LIVE (green) or STALE (yellow) based on health

## Known Limitations

1. **No authentication**: API is open (development mode)
2. **yfinance rate limits**: Free tier may throttle. Rate limiter handles gracefully.
3. **WebSocket polling**: Provider-backed polling, not true push streaming.
4. **No custom domain**: Using hosting provider's generated domain.
5. **No database**: State is ephemeral (in-memory cache).
6. **No live trading**: This is a market analysis/visualization tool only.

## Security

- No secrets in source code (verified)
- `.env` in `.gitignore` (verified)
- CORS restricted to configured origins (verified)
- Debug disabled by default (verified)
- No API keys committed (verified)

## Research Integrity

- NO_DEPLOYMENT_SIGNAL preserved in all responses
- M1-M15 research reports unaltered
- No profitability claims
- No trading functionality
- No buy/sell execution
