# M25 — Intelligent Market Analysis Engine

## Status: COMPLETE

## Architecture

```
OHLCV Data
  ↓
Deterministic Indicators (M23)
  ↓
Market Structure (M24)
  ↓
Market Context Engine (M25)
  ↓
Structured JSON Analysis
  ↓
Optional LLM Abstraction
  ↓
Natural Language Explanation
```

## Implemented Components

### 1. Market Context Engine (`src/aurora/features/market_context.py`)

The core deterministic analysis module. Produces a `MarketContext` dataclass containing all analytical dimensions.

**Entry point:** `analyze_market(bars, asset, timeframe, provider, stale, bars_by_tf)`

### 2. Trend Analysis

- EMA alignment (EMA12 vs EMA26)
- ADX trend strength
- Market structure regime integration (HH/HL/LH/LL patterns)
- Composite direction: UPTREND / DOWNTREND / RANGING / TRANSITION
- Strength: STRONG / MODERATE / WEAK

### 3. Momentum Analysis

- RSI(14) with zone classification (overbought/elevated/neutral/depressed/oversold)
- MACD line, signal, histogram
- Stochastic %K / %D
- CCI(20)
- ROC(12)
- Williams %R(14)
- Composite state: BULLISH / BEARISH / NEUTRAL / MIXED / OVERBOUGHT / OVERSOLD

### 4. Volatility Analysis

- ATR(14) with percentage of price
- Bollinger Bands width and position
- Expansion/contraction detection
- Regime: LOW / NORMAL / HIGH / EXPANDING / CONTRACTING

### 5. Volume Analysis

- OBV trend (rising/falling/flat)
- VWAP distance from price
- MFI(14) with zone classification
- Confirmation/divergence detection
- State: CONFIRMING / WEAK / MIXED / DIVERGING / UNAVAILABLE

### 6. Structure Integration

- Reuses M24 engine directly
- Swing point classification
- BOS/CHOCH break detection
- Active support/resistance levels
- State: BULLISH / BEARISH / RANGE / TRANSITION / MIXED

### 7. Liquidity Context

- Swept/unswept level counts
- Nearest liquidity level
- No predictive claims about future liquidity events

### 8. Multi-Timeframe Analysis

- Analyzes 1h, 4h, 1d timeframes (best effort)
- Trend/structure/regime/momentum per timeframe
- Alignment: ALIGNED_BULLISH / ALIGNED_BEARISH / MIXED / CONFLICTING / INSUFFICIENT_DATA

### 9. Conflict Detection

Detects contradictions between domains:
- Trend vs Momentum
- Trend vs Structure
- Momentum vs Structure
- Volatility vs Trend
- Volume divergence
- Multi-timeframe conflicts
- Momentum extremes vs structure

### 10. Data Quality

- Quality levels: GOOD / STALE / INSUFFICIENT / MISSING / INVALID
- Candle count, latest timestamp, provider
- Missing fields tracking

### 11. Explainable Analysis

Structured explanation sections with evidence lists. Each section contains heading, content, and supporting evidence.

### 12. AI/LLM Abstraction (`src/aurora/ai/__init__.py`)

- Abstract `LLMProvider` interface
- `StubLLMProvider` (default — no API key required)
- `format_analysis_for_llm()` — structured prompt from MarketContext
- `generate_natural_language_explanation()` — LLM or deterministic fallback
- No hardcoded providers. API keys remain backend-only.

### 13. Analysis API (`/market/{asset}/analysis`)

- FastAPI endpoint accepting asset, timeframe, limit
- Fetches primary + multi-timeframe data
- Returns full MarketContext as JSON
- Includes `research_conclusion: NO_DEPLOYMENT_SIGNAL`

### 14. Frontend Analysis Panel

- `MarketContextPanel.tsx` — toggleable panel showing all analysis dimensions
- Fetches from backend `/analysis` endpoint
- Falls back to local computation when backend unavailable
- Sections: Trend, Momentum, Volatility, Volume, Structure, Liquidity, Multi-Timeframe, Conflicts, Data Quality, Explanation

### 15. Live Synchronization

- Reuses M24.2 polling infrastructure (60s interval)
- AbortController for stale request cancellation
- Analysis re-fetches on asset/timeframe change
- Local fallback ensures UI always has data

### 16. Research Integrity

- All analysis is deterministic — same input produces same output
- No future-data leakage: indicator(T) depends only on data at or before T
- Leakage tests verify that adding future bars doesn't alter past analysis
- Chronological processing maintained throughout

## Test Coverage

53 new tests in `tests/test_m25_market_context.py`:
- Helper functions (6)
- Trend analysis (5)
- Momentum analysis (7)
- Volatility analysis (5)
- Volume analysis (4)
- Structure integration (3)
- Liquidity context (2)
- Multi-timeframe (3)
- Conflict detection (2)
- Data quality (4)
- Explanation (1)
- Full market analysis (8)
- Leakage prevention (3)

**Total: 1511 tests passing**

## Files Created/Modified

### New Files
- `src/aurora/features/market_context.py` — Core analysis engine
- `src/aurora/ai/__init__.py` — AI abstraction layer
- `frontend/src/services/analysis.ts` — TS analysis service + types
- `frontend/src/components/MarketContextPanel.tsx` — Frontend panel
- `tests/test_m25_market_context.py` — Test suite
- `docs/milestone25-report.md` — This document

### Modified Files
- `src/aurora/market/api.py` — Added `/market/{asset}/analysis` endpoint
- `frontend/src/App.tsx` — Integrated MarketContextPanel with toggle

## Limitations

- Multi-timeframe analysis is best-effort; missing timeframes don't block analysis
- LLM abstraction is stub-only; no real LLM provider is configured
- Local fallback has limited indicators (EMA, RSI, ATR only)
- Oscillator chart panes still deferred (needs lightweight-charts v5 upgrade)

## Research Integrity

NO_DEPLOYMENT_SIGNAL preserved. All analysis is descriptive and historical. No predictions, no trading signals, no buy/sell recommendations.
