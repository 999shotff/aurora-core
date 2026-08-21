# Milestone 20: Production Deployment & Hosting

**Production engineering milestone. Research conclusions preserved.**

## Executive Summary

M20 prepares AURORA CORE for production deployment with CI/CD, Docker, Vercel config, production CORS, environment variable management, secret audit, and deployment documentation. The frontend build is blocked by Android /sdcard native binary restrictions but will work in CI on standard Linux.

## Production Architecture

```
Browser
   |
   v (HTTPS)
Frontend Hosting (Vercel)
   |
   v (HTTPS)
FastAPI Backend (Docker/Railway/Fly.io)
   |
   v
MarketDataProvider (Protocol)
   +-- DemoMarketDataProvider
   +-- RealMarketDataProvider (yfinance)
```

## Files Created

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | GitHub Actions CI/CD pipeline |
| `frontend/vercel.json` | Vercel deployment config |
| `Dockerfile` | Backend containerization |
| `.dockerignore` | Docker build exclusions |
| `requirements.txt` | Backend Python dependencies |
| `src/aurora/market/config.py` | Production config from env vars |
| `src/aurora/market/server.py` | Production server entry point |
| `.env.example` | Updated with all env vars |

## Files Modified

| File | Change |
|------|--------|
| `src/aurora/market/api.py` | Production CORS, version bump |
| `frontend/src/services/data.ts` | Stale data status, env var API URL |
| `frontend/src/App.tsx` | STALE/UNAVAILABLE states |
| `frontend/package.json` | Fixed build scripts for npx |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AURORA_DATA_MODE` | `demo` | Data provider mode |
| `AURORA_YAHOO_API_KEY` | (empty) | Yahoo Finance API key |
| `AURORA_HOST` | `0.0.0.0` | Server bind host |
| `AURORA_PORT` | `8000` | Server port |
| `AURORA_DEBUG` | `false` | Debug mode |
| `AURORA_LOG_LEVEL` | `info` | Log level |
| `AURORA_CORS_ORIGINS` | `https://aurora-core.vercel.app` | CORS origins |
| `AURORA_CACHE_TTL_SECONDS` | `60` | Cache TTL |
| `AURORA_CACHE_MAX_SIZE` | `256` | Cache max entries |
| `AURORA_RATE_LIMIT_RPM` | `60` | Rate limit RPM |
| `AURORA_RATE_LIMIT_BURST` | `10` | Rate limit burst |
| `AURORA_PROVIDER_TIMEOUT_SECONDS` | `10` | Provider timeout |
| `AURORA_PROVIDER_MAX_RETRIES` | `3` | Max retries |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Frontend API URL |

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`):

**Python tests job:**
- Python 3.12
- Install dependencies
- Ruff lint
- Mypy type check
- Pytest

**Frontend job:**
- Node.js 20
- npm ci
- TypeScript type check
- Vite build
- Upload artifact

Pipeline fails if: tests fail, typecheck fails, lint fails, build fails.

## Docker Configuration

```dockerfile
FROM python:3.12-slim
EXPOSE 8000
HEALTHCHECK: curl /health every 30s
CMD: python -m aurora.market.server
```

## Vercel Configuration

- Framework: Vite
- Build: `npm run build`
- Output: `dist/`
- SPA routing: all routes -> `/index.html`
- Asset caching: immutable for `/assets/*`

## Security Audit

| Check | Status |
|-------|--------|
| Secrets in source code | None found |
| .env in .gitignore | Yes |
| .env.example has placeholders only | Yes |
| API keys in frontend | None (VITE_API_URL only) |
| CORS configured | Yes (env-driven) |
| Debug mode default | false |
| Error responses | Structured, no stack traces |

## LIVE/DEMO/STALE/UNAVAILABLE States

| State | Display | Condition |
|-------|---------|-----------|
| DEMO | Orange badge | `is_demo=true` or no backend |
| LIVE | Green badge | `is_demo=false` AND `stale=false` |
| STALE | Yellow badge | `stale=true` (data > 5 minutes old) |
| UNAVAILABLE | Error state | Backend unreachable or provider error |

No silent fallback from LIVE to DEMO while displaying LIVE.

## Frontend Build Result

**TypeScript typecheck**: PASS (0 errors)

**Vite production build**: BLOCKED by Android /sdcard platform limitation
- Error: `Cannot find module "@esbuild/linux-arm64"` on /sdcard
- Root cause: /sdcard filesystem doesn't support native binary loading (dlopen)
- The `--ignore-scripts` flag used during npm install skipped esbuild binary download
- Even with binaries present, /sdcard has noexec-like restrictions
- **Resolution**: Build must be performed in CI (GitHub Actions) or standard Linux/Mac/Windows environment
- CI pipeline configured to handle this automatically

## Verification Results

| Check | Result |
|-------|--------|
| pytest | 1215/1215 passed |
| ruff | All clean |
| mypy | 0 errors (11 source files) |
| TypeScript | 0 errors |
| Secret audit | Clean |
| .gitignore | Correct |
| CORS | Configured |
| Health endpoint | Verified (M19) |
| Real data | Verified (M19) |
| CI/CD | Configured |
| Docker | Configured |
| Vercel | Configured |

## Deployment Instructions

### Frontend (Vercel)
1. Connect GitHub repo to Vercel
2. Set environment variable: `VITE_API_URL=https://your-backend.vercel.app`
3. Deploy will auto-trigger on push to main

### Backend (Railway/Fly.io/Docker)
1. Build: `docker build -t aurora-core .`
2. Set environment variables:
   - `AURORA_DATA_MODE=real`
   - `AURORA_CORS_ORIGINS=https://your-frontend.vercel.app`
3. Deploy: `docker run -p 8000:8000 aurora-core`

### Local Development
1. Backend: `AURORA_DATA_MODE=demo python -m aurora.market.server`
2. Frontend: `cd frontend && npm run dev`

## Known Limitations
1. Vite build requires standard Linux/Mac/Windows (Android /sdcard blocks native binaries)
2. yfinance free tier may rate-limit
3. No authentication (development mode)
4. No custom domain configured

## Research Integrity
- NO_DEPLOYMENT_SIGNAL preserved in all responses
- M1-M15 reports unaltered
- No profitability claims
- No trading functionality

## Hard Stop

Awaiting explicit approval for M21.
