# AURORA CORE

AI-first research and market-reasoning system.

## Current milestone: M30.2 — Production Integration & Verification

Production market-reasoning visualization system. React+TypeScript frontend on Vercel,
FastAPI backend on Render. **NO_DEPLOYMENT_SIGNAL** — this is an analytical research tool,
not a trading system.

### Architecture

- **Frontend** (Vercel): React + TypeScript + lightweight-charts
- **Backend** (Render): FastAPI + yfinance provider
- **Analysis Engine**: Pure Python deterministic analysis — indicators, market structure,
  evidence aggregation, confluence scoring, scenario generation
- **Geo Module** (M30/30.1/30.2): Sentinel-2/1, NASA GIBS, SkyFi providers; raster processing; spectral indices; change detection; 3D globe

### Feature Status

| Feature | Status | Real Data Verified | Notes |
|---|---|---|---|
| Sentinel Provider | IMPLEMENTED | VERIFIED | Live OData API calls, URL encoding fixed |
| NASA GIBS Provider | IMPLEMENTED | VERIFIED | Tile URLs constructed correctly, no API key needed |
| SkyFi Provider | IMPLEMENTED | VERIFIED | Graceful NOT_CONFIGURED without API key |
| Raster Engine | IMPLEMENTED | TEST FIXTURES | numpy-based; real satellite pixel download deferred |
| NDVI | IMPLEMENTED | TEST FIXTURES | Per-pixel computation on real arrays |
| NDWI | IMPLEMENTED | TEST FIXTURES | Per-pixel computation on real arrays |
| NDBI | IMPLEMENTED | TEST FIXTURES | Per-pixel computation on real arrays |
| EVI | IMPLEMENTED | TEST FIXTURES | Per-pixel computation on real arrays |
| Time Series | IMPLEMENTED | TEST FIXTURES | Full engine; disconnected from API pipeline |
| Change Detection | IMPLEMENTED | TEST FIXTURES | Pixel-level diff; API uses scalar path |
| GeoEvidence Bridge | IMPLEMENTED | VERIFIED | Type-compatible with M26 evidence system |
| 2D Map | PARTIAL | NOT VERIFIED | Google Static Maps without API key |
| 3D Globe | PARTIAL | NOT VERIFIED | Decorative Three.js sphere; no Earth data |
| Research Backtest | IMPLEMENTED | TEST FIXTURES | Deterministic engine with RSI strategy |
| Production Build | DEFERRED | NOT VERIFIED | ARM64/musl prevents local Rollup |

### Key Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Provider health, staleness, uptime |
| `GET /market/{asset}/ohlc` | OHLCV bars with validation and provenance |
| `GET /market/{asset}/analysis` | Full deterministic analysis (M26) |
| `POST /api/v1/geo/health` | Geo providers health |
| `GET /api/v1/geo/providers` | Available geo providers and capabilities |
| `GET /api/v1/geo/datasets` | Available datasets and indices |
| `POST /api/v1/geo/search` | Search for available imagery scenes |
| `POST /api/v1/geo/observations` | Get full observation with raster data |
| `POST /api/v1/geo/change-detection` | Detect change between two scenes |
| `POST /api/v1/research/backtest` | Run deterministic backtest |

### Analysis Domains (M26)

- **Trend**: EMA alignment, ADX, structure confirmation
- **Momentum**: RSI, MACD, Stochastic, CCI, ROC, Williams %R
- **Volatility**: ATR regime, Bollinger Bands
- **Volume**: OBV, VWAP, MFI confirmation
- **Structure**: Swing points, BOS/CHOCH, S/R levels, regime
- **Liquidity**: Swept/unswept levels
- **Multi-Timeframe**: Cross-TF alignment
- **Confluence**: Weighted evidence scoring across all domains
- **Scenarios**: Continuation, reversal, range, breakout, breakdown
- **Conflicts**: Cross-domain divergence detection with severity
- **Geo Analysis** (M30.1): NDVI/NDWI/NDBI/EVI spectral indices, pixel change detection, time series analysis
- **Backtesting** (M29): Deterministic backtest engine with RSI reversal strategy
- **Research Integrity**: No-deployment-signal, no-predictions, deterministic

### Principles

1. Research claims are hypotheses until validated.
2. No look-ahead leakage.
3. No fake live data.
4. Numerical calculations belong in deterministic code, not the LLM.
5. A model may abstain when evidence is insufficient.
6. New models are challengers until they beat the champion on predefined tests.
7. OpenMythos/Kimi/other architectures are research references, not assumed solutions.

### Running

```bash
# Backend
cd src && python -m uvicorn aurora.market.api:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend && npm run dev

# Tests
python -m pytest tests/ -x
```
