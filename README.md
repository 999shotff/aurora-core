# AURORA CORE

AI-first research and market-reasoning system.

## Current milestone: M26 — Evidence Confluence and Scenario Analysis

Production market-reasoning visualization system. React+TypeScript frontend on Vercel,
FastAPI backend on Render. **NO_DEPLOYMENT_SIGNAL** — this is an analytical research tool,
not a trading system.

### Architecture

- **Frontend** (Vercel): React + TypeScript + lightweight-charts
- **Backend** (Render): FastAPI + yfinance provider
- **Analysis Engine**: Pure Python deterministic analysis — indicators, market structure,
  evidence aggregation, confluence scoring, scenario generation

### Key Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Provider health, staleness, uptime |
| `GET /market/{asset}/ohlc` | OHLCV bars with validation and provenance |
| `GET /market/{asset}/analysis` | Full deterministic analysis (M26) |

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
