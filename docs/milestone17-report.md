# Milestone 17: Trading Terminal Frontend + TradingView Lightweight Charts

**Product visualization milestone. Research conclusions preserved.**

## Executive Summary

M17 implements a browser-based AURORA CORE trading terminal frontend using React, TypeScript, and TradingView Lightweight Charts. The terminal renders candlestick charts with volume, 6 technical indicators, a watchlist, asset selector, timeframe selector, and analysis panel. **NO_DEPLOYMENT_SIGNAL** remains immutable.

## Architecture

```
frontend/
├── src/
│   ├── types/index.ts          # TypeScript types aligned with M16 API contracts
│   ├── services/data.ts        # Mock data generator + indicator calculations
│   ├── components/
│   │   ├── PriceChart.tsx      # TradingView LWC candlestick chart with overlays
│   │   ├── TopBar.tsx          # Logo, asset selector, timeframe selector, status
│   │   ├── Watchlist.tsx       # Asset watchlist with prices/changes
│   │   └── AnalysisPanel.tsx   # Technical indicators, research status
│   ├── App.tsx                 # Main terminal layout
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles (dark theme)
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.x | UI framework |
| react-dom | 18.x | DOM rendering |
| lightweight-charts | 4.2.x | TradingView charting |
| typescript | 5.5.x | Type checking |
| vite | 5.4.x | Build tool |
| @vitejs/plugin-react | 4.x | React support |

## Frontend Stack

- **TypeScript** — full type safety aligned with M16 contracts
- **React 18** — functional components with hooks
- **TradingView Lightweight Charts** — candlestick, line, histogram series
- **Vite 5** — fast dev server and build
- **CSS-in-JS** — inline styles for zero-dependency styling

## Implementation Details

### PriceChart Component
- TradingView `createChart` with dark theme
- Candlestick series with green/red coloring
- Volume histogram (80% opacity, bottom 20%)
- Dynamic overlay series (SMA, EMA, Bollinger)
- Responsive resizing via `ResizeObserver`
- Crosshair enabled (Mode 0 = Normal)

### Indicator Calculations (services/data.ts)
All indicators are pure TypeScript, no external dependencies:

| Indicator | Implementation |
|-----------|---------------|
| SMA | Simple moving average window |
| EMA | Exponential with 2/(period+1) multiplier |
| RSI | Wilder's smoothing, 0-100 range |
| MACD | 12/26/9 with line, signal, histogram |
| Bollinger | 20-period SMA ± 2σ |
| ATR | True range smoothed with SMA |

### Asset Selector
- Dropdown with all 10 M16 registry assets
- Changing asset regenerates chart data
- Category-colored symbols in watchlist

### Timeframe Selector
- Buttons: 1m, 5m, 15m, 30m, 1h, 4h, 1D, 1W
- Active state highlighted
- Switching regenerates chart data

### Watchlist
- All 10 assets displayed
- Symbol, name, last price, change, change %
- Click to switch active asset
- Category color coding
- "DEMO" badge clearly visible

### Analysis Panel
- **Market Data**: Symbol, source (DEMO), trend, volatility
- **Technical Indicators**: RSI, MACD (line/signal/histogram), ATR
- **Moving Averages**: SMA 20, EMA 12
- **Bollinger Bands**: Upper, middle, lower
- **Research Status**: "NO_DEPLOYMENT_SIGNAL" prominently displayed

### Research Integrity
- "DEMO" badge in watchlist header
- "DEMO DATA" label in chart status bar
- "DEMO" badge in analysis panel
- "Data Source: DEMO" in metrics
- Research Status section with NO_DEPLOYMENT_SIGNAL
- No buy/sell/recommendation/prediction anywhere

### Mock Data
- Deterministic PRNG (mulberry32) with configurable seed
- Geometric Brownian motion for price paths
- Different volatility per asset class
- Different start prices per asset

## Data Architecture

```
UI Components
    ↓
Market Data Service (services/data.ts)
    ↓
Mock Data Generator (deterministic)
    ↓
Indicator Calculator (pure TypeScript)
    ↓
TradingView LWC (rendering)
```

Future: Replace mock generator with API/WebSocket to M16 backend.

## Known Limitations

1. **Vite build**: Native binaries (rollup, esbuild) cannot load from `/sdcard` filesystem on Android. Build requires copying to internal storage (`/data/...`) or running on a standard filesystem. TypeScript type-checking passes on `/sdcard`.
2. **Mock data only**: All chart data is generated deterministically. No live market data.
3. **No real-time streaming**: WebSocket client abstraction exists in M16 but not connected in frontend.
4. **No persistent state**: Watchlist and settings reset on page reload.
5. **No mobile optimization**: Layout is desktop-first; mobile layout future work.

## Verification Results

- **TypeScript type-check**: PASS (0 errors)
- **Python test suite**: 1139 pass, 0 fail
- **Ruff (new files)**: All clean
- **Ruff (pre-existing)**: 28 warnings in earlier phase files (not M16/M17)
- **Vite build**: BLOCKED by /sdcard native binary restriction (not a code issue)

## Definition of Done

| Criterion | Status |
|-----------|--------|
| Frontend runs | TypeScript compiles; Vite blocked by filesystem |
| Trading terminal renders | Code complete; needs non-/sdcard filesystem |
| Candlestick chart works | PriceChart.tsx implements TradingView LWC |
| Volume works | Histogram series with volume data |
| Asset selector works | Dropdown with 10 M16 assets |
| Timeframe selector works | 8 timeframe buttons |
| SMA works | computeSMA + overlay series |
| EMA works | computeEMA + overlay series |
| RSI works | computeRSI + analysis panel |
| MACD works | computeMACD + analysis panel |
| Bollinger Bands works | computeBollinger + analysis panel |
| ATR works | computeATR + analysis panel |
| Watchlist works | 10 assets with prices/changes |
| Mock/live distinction is explicit | DEMO badges, labels, data source |
| Research status is visible | NO_DEPLOYMENT_SIGNAL in panel |
| API architecture is clean | Type-aligned with M16 contracts |
| Tests pass | 1139 Python tests pass |
| Type checking passes | TypeScript 0 errors |
| Lint passes | All new files clean |
| Documentation written | This report |

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/types/index.ts` | 75 | TypeScript types + asset registry |
| `frontend/src/services/data.ts` | 230 | Mock data + indicator calculations |
| `frontend/src/components/PriceChart.tsx` | 85 | TradingView LWC chart |
| `frontend/src/components/TopBar.tsx` | 65 | Navigation bar |
| `frontend/src/components/Watchlist.tsx` | 80 | Asset watchlist |
| `frontend/src/components/AnalysisPanel.tsx` | 95 | Analysis + research status |
| `frontend/src/App.tsx` | 55 | Main terminal layout |
| `frontend/src/main.tsx` | 10 | Entry point |
| `frontend/src/index.css` | 30 | Global dark theme |
| `frontend/package.json` | 20 | Dependencies |
| `frontend/tsconfig.json` | (from template) | TypeScript config |
| `frontend/vite.config.ts` | (from template) | Vite config |

## Hard Stop

Awaiting explicit approval for M18.
