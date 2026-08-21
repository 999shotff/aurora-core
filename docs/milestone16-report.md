# Milestone 16: Product Architecture & TradingView Integration

**Product engineering phase. Research conclusions preserved.**

## Executive Summary

M16 builds the foundation of the AURORA CORE trading analysis platform with TradingView-style market visualization. This is a **product engineering milestone**, not a research milestone. The scientific conclusion from M1-15 (**NO_DEPLOYMENT_SIGNAL**) is preserved and immutable.

## What Was Built

### 1. Product Architecture

```
src/aurora/product/
├── __init__.py          # Product layer entry point
├── api/                 # Typed API contracts (dataclasses)
│   └── __init__.py      # OHLC, indicators, metadata, watchlist, chart, analysis, health schemas
├── assets/              # Asset registry
│   └── __init__.py      # 10 configurable assets (BTC, ETH, Gold, Silver, SPY, QQQ, NIFTY, NASDAQ, EURUSD, USDJPY)
├── charts/              # Chart data service with indicators
│   └── __init__.py      # SMA, EMA, RSI, MACD, Bollinger, ATR calculations + mock data generator
├── config/              # Application configuration
│   └── __init__.py      # Server, data, chart, WebSocket config
├── services/            # Service layer
│   └── __init__.py      # Market metadata, chart, health services
├── types/               # Shared type definitions
│   └── __init__.py      # Timeframe, chart theme, indicator/overlay/panel types
└── websocket/           # WebSocket abstraction
    └── __init__.py      # Protocol, mock WebSocket for testing
```

### 2. TradingView Integration Layer

- **Data contracts**: OHLCBar, IndicatorSeries, ChartConfiguration, ChartOverlay, ChartPanel
- **Indicator engine**: SMA, EMA, RSI, MACD, Bollinger Bands, ATR — all pure Python
- **Chart builder**: Assembles OHLCV data + overlays + panels into TradingView-compatible response
- **Mock data**: Geometric Brownian motion generator for development (deterministic with seed)
- **WebSocket abstraction**: Protocol-based handler for future real-time streaming

### 3. Asset Registry

| Symbol | Name | Category | Exchange | Yahoo Ticker |
|--------|------|----------|----------|-------------|
| BTC-USD | Bitcoin | crypto | NASDAQ | BTC-USD |
| ETH-USD | Ethereum | crypto | NASDAQ | ETH-USD |
| GOLD | Gold | commodity | COMEX | GC=F |
| SILVER | Silver | commodity | COMEX | SI=F |
| SPY | S&P 500 ETF | etf | NYSE | SPY |
| QQQ | Nasdaq 100 ETF | etf | NASDAQ | QQQ |
| NIFTY | Nifty 50 | equity_index | NSE | ^NSEI |
| NASDAQ | NASDAQ Composite | equity_index | NASDAQ | ^IXIC |
| EURUSD | Euro/US Dollar | forex | FOREX | EURUSD=X |
| USDJPY | US Dollar/Japanese Yen | forex | FOREX | JPY=X |

### 4. API Contracts

All schemas are frozen dataclasses — no external dependencies:

- **OHLC**: OHLCBar, OHLCResponse
- **Indicators**: IndicatorPoint, IndicatorSeries, IndicatorRequest, IndicatorResponse
- **Metadata**: MarketMetadata, MarketMetadataResponse
- **Watchlist**: WatchlistItem, Watchlist, WatchlistResponse
- **Chart**: ChartOverlay, ChartPanel, ChartConfiguration, ChartResponse
- **Analysis**: AnalysisRequest, AnalysisResult, AnalysisResponse
- **Health**: HealthStatus, HealthResponse

### 5. Technical Indicators

| Indicator | Parameters | Output |
|-----------|-----------|--------|
| SMA | period | Moving average line |
| EMA | period | Exponential moving average |
| RSI | period (default 14) | 0-100 oscillator |
| MACD | fast=12, slow=26, signal=9 | Line, signal, histogram |
| Bollinger | period=20, num_std=2.0 | Upper, middle, lower bands |
| ATR | period (default 14) | Average true range |

### 6. Configuration

```python
AuroraConfig(
    server=ServerConfig(host="127.0.0.1", port=8000, debug=True),
    data=DataConfig(provider="yfinance", cache_enabled=True),
    chart=ChartConfig(default_theme="dark", responsive=True),
    websocket=WebSocketConfig(enabled=True),
    research_conclusion="NO_DEPLOYMENT_SIGNAL",  # Preserved
    version="0.1.0",
)
```

## Research Integrity

- All M1-15 files untouched
- `NO_DEPLOYMENT_SIGNAL` preserved in config and health endpoint
- No prediction claims in any product module
- Clear separation: `src/aurora/models/` (research) vs `src/aurora/product/` (product)
- All data responses include disclaimer: "Research only. No predictions or recommendations."

## Test Results

- **M16 tests**: 58 pass
- **Full test suite**: 1139 pass, 0 fail
- **Ruff**: All M16 files clean

## What Was NOT Built

- No live trading
- No broker integration
- No buy/sell recommendations
- No prediction models
- No deployment
- No hosting
- No TradingView JavaScript (requires Node.js/frontend framework — documented as architecture)

## Future Work (M17+)

If approved:
- Frontend: TradingView Lightweight Charts integration (requires Node.js + React/Vue)
- Backend API: FastAPI/Flask serving the typed contracts
- WebSocket: Real-time streaming for live charts
- Dashboard: Dark glassmorphism UI with pages (Home, Market Terminal, Asset Explorer, Strategy Lab, Research Reports, Settings)
