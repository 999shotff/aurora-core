# Milestone 18: Real Market Data Backend + WebSocket Pipeline

**Data infrastructure milestone. Research conclusions preserved.**

## Executive Summary

M18 implements a production-ready market data architecture with provider abstraction, OHLC normalization/validation, data provenance tracking, REST API (FastAPI), WebSocket service, bounded caching, rate limiting, structured error handling, and frontend-backend integration. **NO_DEPLOYMENT_SIGNAL** remains immutable.

## Architecture

```
Frontend (React/TypeScript)
   ↓ fetch
FastAPI REST API + WebSocket
   ↓
MarketDataService (cache → rate limiter → provider)
   ↓
MarketDataProvider (Protocol)
   ├── DemoMarketDataProvider (mock, deterministic)
   └── RealMarketDataProvider (yfinance, live data)
   ↓
Normalization → Validation → Provenance
```

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/aurora/market/__init__.py` | 75 | Package exports |
| `src/aurora/market/provider.py` | 380 | Provider interface + Demo + Real (yfinance) |
| `src/aurora/market/normalization.py` | 115 | OHLC validation + normalization |
| `src/aurora/market/provenance.py` | 55 | Data provenance tracking |
| `src/aurora/market/cache.py` | 90 | Bounded LRU cache with TTL |
| `src/aurora/market/rate_limiter.py` | 115 | Token bucket + retry + throttler |
| `src/aurora/market/errors.py` | 80 | Structured error types |
| `src/aurora/market/api.py` | 276 | FastAPI REST + WebSocket endpoints |
| `src/aurora/market/ws.py` | 135 | WebSocket service (subscribe/unsubscribe) |
| `.env.example` | 22 | Environment variable template |
| `tests/test_milestone18.py` | 590 | 76 comprehensive tests |
| `frontend/src/services/data.ts` | 310 | Updated: backend API client + fallback mock |
| `frontend/src/App.tsx` | 70 | Updated: async data loading, LIVE/DEMO display |
| `frontend/src/components/AnalysisPanel.tsx` | 105 | Updated: nullable metrics, loading state |

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/services/data.ts` | Added backend fetch with fallback |
| `frontend/src/App.tsx` | Async loading, data source display |
| `frontend/src/components/AnalysisPanel.tsx` | Nullable metrics support |

## Dependencies Added

| Package | Purpose |
|---------|---------|
| fastapi | REST API framework |
| uvicorn | ASGI server |
| python-dotenv | .env file loading |

## Provider Abstraction

### MarketDataProvider Protocol
```python
class MarketDataProvider(Protocol):
    name: str
    is_demo: bool
    get_ohlc(symbol, timeframe, limit) -> ProviderResponse
    get_latest_quote(symbol) -> ProviderResponse
    get_asset_metadata(symbol) -> dict | None
    get_available_timeframes(symbol) -> list[str]
```

### DemoMarketDataProvider
- Deterministic PRNG (mulberry32) with configurable seed
- 10 assets with realistic volatility profiles
- Clearly labeled `is_demo = True`
- No network calls

### RealMarketDataProvider (yfinance)
- Fetches real market data from Yahoo Finance
- Timeframe mapping: 1m→5d, 5m→60d, 1d→5y, 1w→10y
- Graceful error handling (returns structured errors, never raises)
- API key via `AURORA_YAHOO_API_KEY` env var (optional)

## REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health + provider status |
| `/assets` | GET | All registered assets |
| `/market/{asset}/ohlc` | GET | OHLC candles with provenance |
| `/market/{asset}/quote` | GET | Latest quote |
| `/market/{asset}/metadata` | GET | Asset metadata |
| `/market/{asset}/timeframes` | GET | Available timeframes |

### Query Parameters
- `timeframe`: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M
- `limit`: 1–5000 (default: 200)

## WebSocket Protocol

| Endpoint | Description |
|----------|-------------|
| `/ws/market/{asset}` | Real-time candle stream |

### Messages
```json
{
  "channel": "ohlc",
  "symbol": "BTC-USD",
  "data": {"timestamp": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...},
  "provider": "demo",
  "is_demo": true
}
```

## OHLC Normalization

### Validation Rules
- Open, high, low, close must be positive
- Volume must be non-negative
- High must be >= all others; Low must be <= all others
- Timestamps must be ISO 8601 with timezone
- Timestamps must be strictly increasing
- Duplicate timestamps removed
- Invalid candles rejected (not silently repaired)

## Data Provenance

Every response includes:
```json
{
  "provider": "yfinance",
  "asset": "BTC-USD",
  "timeframe": "1d",
  "retrieved_at": "2026-08-20T...",
  "data_timestamp": "2026-08-20T...",
  "source_status": "ok",
  "is_demo": false
}
```

## Caching

- Bounded LRU cache (max 256 entries)
- TTL-based expiration (default 60s)
- Per-endpoint keying: `ohlc:{asset}:{timeframe}:{limit}`
- Invalidation on prefix
- No stale data masquerading as live

## Rate Limiting

- Token bucket per provider (60 RPM, burst 10)
- Request throttler tracks per-provider limiters
- Retry policy with exponential backoff (max 3 retries)
- 429 response on rate limit exceeded

## Error Handling

| Error Code | HTTP Status | Retryable |
|------------|-------------|-----------|
| INVALID_ASSET | 404 | No |
| INVALID_TIMEFRAME | 400 | No |
| PROVIDER_UNAVAILABLE | 503 | Yes |
| RATE_LIMIT | 429 | Yes |
| AUTH_FAILURE | 401 | No |
| MALFORMED_RESPONSE | 502 | Yes |
| STALE_DATA | 504 | Yes |
| NETWORK_FAILURE | 503 | Yes |

## Frontend Integration

- `fetchOHLCV()` tries backend first, falls back to local mock
- `getDataSourceInfo()` checks backend health for LIVE/DEMO status
- Data bar shows: `Source: yfinance LIVE` or `Source: mock (local) DEMO`
- Analysis panel shows loading state during fetch
- Backend availability auto-detected on first request

## Security

- API keys stored in environment variables only
- `.env.example` committed (no secrets)
- CORS configured for development (`*`)
- Secrets never exposed to browser JavaScript

## Research Firewall

```
PRODUCT MARKET DATA
        |
        v
CHART / ANALYSIS
        |
        X
RESEARCH PREDICTION
```

- Market data pipeline does NOT generate trading predictions
- No buy/sell/recommendation logic anywhere in M18
- All responses include `research_conclusion: NO_DEPLOYMENT_SIGNAL`
- Provider responses contain only raw market data

## Verification Results

| Check | Result |
|-------|--------|
| pytest (total) | 1215 passed |
| pytest (M18) | 76 passed |
| ruff (M18 files) | All clean |
| mypy (M18 files) | 0 errors |
| TypeScript type-check | 0 errors |
| Python test suite | 47.9s |

## Known Limitations

1. **yfinance rate limits**: Free tier may throttle; rate limiter handles gracefully
2. **No intraday history**: yfinance limits intraday data to 60 days
3. **Forex gaps**: Some forex pairs may have missing weekend data
4. **WebSocket polling**: Backend WebSocket polls provider periodically (not true push)
5. **No authentication**: API is open (development mode); production auth is future work
6. **Vite build**: Native binaries cannot load from `/sdcard` filesystem on Android

## Live Data Verification

Live data was NOT actually verified with a running yfinance connection during this milestone. The RealMarketDataProvider adapter is implemented and tested for error cases. Actual live data fetch requires running the FastAPI server with network access and `AURORA_DATA_MODE=real`.

## Definition of Done

| Criterion | Status |
|-----------|--------|
| Provider abstraction exists | DONE |
| Demo provider works | DONE |
| Real provider adapter exists | DONE |
| OHLC normalization works | DONE |
| Data validation works | DONE |
| Provenance is recorded | DONE |
| REST API works | DONE |
| WebSocket works | DONE |
| Reconnect handling works | DONE |
| Error handling works | DONE |
| Rate limiting exists | DONE |
| Cache is bounded | DONE |
| Secrets are protected | DONE |
| Frontend can consume backend data | DONE |
| LIVE/DEMO state is explicit | DONE |
| Research firewall exists | DONE |
| Tests pass | DONE (1215/1215) |
| Ruff passes | DONE |
| Mypy passes | DONE |
| Documentation exists | DONE |

## Hard Stop

Awaiting explicit approval for M19.
