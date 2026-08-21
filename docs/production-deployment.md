# AURORA CORE — Production Deployment Guide

**Version:** 0.2.0
**Status:** CONFIGURED — Not yet deployed

## Architecture

```
GitHub Repository (999shotff/aurora-core)
    |
    +--> Vercel (Frontend)
    |      React + TypeScript + Vite
    |      https://aurora-core.vercel.app
    |
    +--> Render (Backend)
           FastAPI + yfinance
           https://aurora-core-api.onrender.com
           /health endpoint
```

## 1. GitHub Setup

Repository: https://github.com/999shotff/aurora-core

Branch: `main`

CI/CD: `.github/workflows/ci.yml`

## 2. Backend Deployment (Render)

### Prerequisites
- Render account
- Docker support enabled

### Steps
1. Connect GitHub repo to Render
2. Create new Web Service
3. Select Docker runtime
4. Set environment variables (see below)
5. Deploy

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AURORA_DATA_MODE` | Yes | `demo` | `real` for live yfinance data |
| `AURORA_CORS_ORIGINS` | Yes | `https://aurora-core.vercel.app` | Comma-separated allowed origins |
| `AURORA_HOST` | No | `0.0.0.0` | Bind address |
| `AURORA_PORT` | No | `8000` | Bind port (Render sets this) |
| `AURORA_DEBUG` | No | `false` | Enable debug logging |
| `AURORA_LOG_LEVEL` | No | `info` | Logging level |
| `AURORA_CACHE_TTL_SECONDS` | No | `60` | Cache TTL |
| `AURORA_RATE_LIMIT_RPM` | No | `60` | Requests per minute |
| `AURORA_RATE_LIMIT_BURST` | No | `10` | Burst limit |
| `AURORA_WS_ENABLED` | No | `true` | Enable WebSocket |
| `AURORA_WS_MAX_CONNECTIONS` | No | `100` | Max WS connections |
| `AURORA_PROVIDER_TIMEOUT_SECONDS` | No | `10` | Provider timeout |
| `AURORA_PROVIDER_MAX_RETRIES` | No | `3` | Provider retries |

### Health Check
```
GET /health
```

## 3. Frontend Deployment (Vercel)

### Prerequisites
- Vercel account connected to GitHub

### Steps
1. Import repo in Vercel dashboard
2. Framework: Vite
3. Root directory: `frontend`
4. Build command: `npm run build`
5. Output directory: `dist`
6. Environment variables:
   - `VITE_API_URL` = `https://aurora-core-api.onrender.com`
7. Deploy

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | Yes (prod) | `http://127.0.0.1:8000` | Backend API URL |

## 4. CORS Configuration

Backend CORS is configured via `AURORA_CORS_ORIGINS` (comma-separated).

Default: `https://aurora-core.vercel.app`

For local development, add `http://localhost:5173`.

## 5. Data Modes

### DEMO mode (`AURORA_DATA_MODE=demo`)
- Generated mock OHLCV data
- No external network calls
- `is_demo: true` in all responses
- Badge: DEMO (orange)

### REAL mode (`AURORA_DATA_MODE=real`)
- Live market data from yfinance
- 6 target assets: BTC-USD, ETH-USD, SPY, QQQ, GOLD, SILVER
- 10 total assets in registry
- Rate limited (60 RPM)
- `is_demo: false` in all responses
- Badge: LIVE (green) or STALE (yellow)

## 6. Health Check

The `/health` endpoint exposes:
- Application status (healthy/degraded)
- Provider status
- Data mode (demo/real)
- Stale status
- Research conclusion: NO_DEPLOYMENT_SIGNAL
- Uptime
- Provider health details

No secrets are exposed.

## 7. Troubleshooting

### Frontend shows DEMO instead of LIVE
- Check `VITE_API_URL` is set correctly in Vercel
- Check backend `AURORA_DATA_MODE=real`
- Check backend is running and `/health` returns `is_demo: false`

### CORS errors
- Ensure `AURORA_CORS_ORIGINS` includes your Vercel domain
- Check for trailing commas or spaces

### Backend won't start
- Check Render logs
- Verify Dockerfile builds correctly
- Check environment variables

### Stale data
- yfinance may have delays
- Check `provider_health.seconds_since_last_success` in `/health`
- Stale threshold: 300 seconds (5 minutes)

## 8. Rollback

### Backend
- Render supports automatic rollback to previous deployment
- Or redeploy with `AURORA_DATA_MODE=demo` to disable live data

### Frontend
- Vercel supports automatic rollback to previous deployment
- Or set `VITE_API_URL` back to development URL

## 9. Security Notes

- No secrets in source code
- `.env` excluded via `.gitignore`
- CORS restricted to configured origins
- Debug disabled by default
- No authentication (documented limitation)
- Rate limiting enabled (60 RPM)
- Provider failures return structured errors (no stack traces)

## 10. Research Integrity

**NO_DEPLOYMENT_SIGNAL** is preserved in all responses.

The UI may display:
- Research status
- Historical analysis
- Indicators
- Market data
- Charts
- Research methodology

The UI must NOT transform research outputs into:
- BUY/SELL signals
- Guaranteed predictions
- Profit claims
- Automated trading instructions

M1-M15 research reports are unaltered.

## 11. Known Limitations

1. **No authentication**: API is open (development mode)
2. **yfinance rate limits**: Free tier may throttle
3. **WebSocket polling**: Provider-backed polling, not true push
4. **No custom domain**: Using hosting provider's domain
5. **No database**: State is ephemeral
6. **No live trading**: Market analysis/visualization only

## 12. Commands

### Backend
```bash
# Local development
AURORA_DATA_MODE=real python -m aurora.market.server

# Docker
docker build -t aurora-core .
docker run -p 8000:8000 -e AURORA_DATA_MODE=real aurora-core

# Health check
curl http://localhost:8000/health
```

### Frontend
```bash
# Local development
cd frontend && npm run dev

# Production build
cd frontend && npm run build

# Type check
cd frontend && npm run typecheck
```
