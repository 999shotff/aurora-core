# Indicator Control Center

## Status: COMPLETE

## Architecture Overview

The Indicator Control Center is a standalone configuration and inspection feature that controls the Market Observatory's indicator behavior behind the scenes. It does NOT redesign the Market Observatory — it provides a separate page for configuring indicators.

### Core Principles

1. **Configuration layer only** — Market Observatory UI remains unchanged
2. **Shared state** — Changes propagate to Market Observatory via localStorage persistence
3. **Deterministic computation** — Uses existing `computeAllIndicators()` from `data.ts`
4. **No duplicate algorithms** — All indicator logic lives in `services/data.ts`

## Files Created

### Backend (Tests)
- `tests/test_indicator_settings.py` — 33 tests for settings store

### Frontend
- `frontend/src/lib/indicatorSettings.ts` — Settings store with localStorage persistence
- `frontend/src/pages/IndicatorsPage.tsx` — Main Indicators page component

## Files Modified

### Routing
- `frontend/src/App.tsx` — Added `/indicators` route
- `frontend/src/components/shell/AppShell.tsx` — Added title for `/indicators`
- `frontend/src/components/shell/AuroraSidebar.tsx` — Added INDICATORS to navigation

## Indicator Settings Architecture

### Storage Key
`aurora.indicator-settings.v1`

### Schema
```typescript
interface IndicatorSettingsState {
  version: number;  // SCHEMA_VERSION = 1
  indicators: IndicatorSetting[];
  lastCalculated: number | null;
}

interface IndicatorSetting {
  id: string;
  enabled: boolean;
  params: Record<string, number>;
}
```

### Default Enabled Indicators
- SMA (20)
- EMA (12)
- RSI (14)
- MACD (12, 26, 9)
- Bollinger (20, 2)
- ATR (14)

## Supported Parameters

### TREND Group (4 indicators)

| Indicator | Parameters | Defaults |
|-----------|-----------|----------|
| SMA | period | 20 |
| EMA | period | 12 |
| ADX/DMI | period | 14 |
| Ichimoku | tenkan, kijun, senkouB | 9, 26, 52 |

### MOMENTUM Group (6 indicators)

| Indicator | Parameters | Defaults |
|-----------|-----------|----------|
| RSI | period | 14 |
| MACD | fast, slow, signal | 12, 26, 9 |
| Stochastic | kPeriod, dPeriod, smoothK | 14, 3, 3 |
| CCI | period | 20 |
| ROC | period | 12 |
| Williams %R | period | 14 |

### VOLATILITY Group (2 indicators)

| Indicator | Parameters | Defaults |
|-----------|-----------|----------|
| Bollinger | period, stdDev | 20, 2 |
| ATR | period | 14 |

### VOLUME Group (3 indicators)

| Indicator | Parameters | Defaults |
|-----------|-----------|----------|
| OBV | (none) | — |
| VWAP | (none) | — |
| MFI | period | 14 |

### LEVELS Group (2 indicators)

| Indicator | Parameters | Defaults |
|-----------|-----------|----------|
| Pivot Points | (none) | — |
| Fibonacci | (none) | — |

## Parameter Validation

### Period Constraints
- All periods must be > 0
- Must be integers when step >= 1

### MACD Constraints
- `fast < slow`
- `signal > 0`

### Ichimoku Constraints
- `tenkan < kijun`
- `kijun < senkouB`

### Bollinger Constraints
- `stdDev` range: 0.5–5.0

## Persistence Mechanism

- **Storage**: localStorage
- **Key**: `aurora.indicator-settings.v1`
- **Debounce**: 300ms
- **Validation**: On load, invalid data falls back to defaults
- **Separate from Market Observatory**: Uses different storage key

## Data Flow

```
IndicatorsPage
  ↓ (user changes settings)
IndicatorSettingsState
  ↓ (debounced save)
localStorage
  ↓ (loaded on page load)
Market Observatory
  ↓ (reads enabled/params)
computeAllIndicators()
  ↓ (recomputes)
Chart/Panel values update
```

## Reset Behavior

### Reset All
1. Confirmation (via button click)
2. Restore all default parameters
3. Restore default enabled indicators
4. Persist defaults
5. Recompute indicators

### Reset Single
1. Restore only that indicator's parameters
2. Keep enabled state unchanged

## Data States

| State | Condition | Display |
|-------|-----------|---------|
| OK | Enough bars + valid params | Raw values |
| INSUFFICIENT_DATA | `bars.length < minDataLength` | Warning message |
| UNAVAILABLE | No data or invalid params | Error message |

## Raw Value Display

Each indicator shows its latest computed values:

- **SMA/EMA**: Single value
- **RSI/CCI/ROC/Williams %R**: Single value
- **MACD**: Line, Signal, Histogram
- **Bollinger**: Upper, Middle, Lower
- **Stochastic**: %K, %D
- **ADX/DMI**: ADX, +DI, -DI
- **Ichimoku**: Tenkan, Kijun, Senkou A, Senkou B
- **Pivot**: PP, R1, R2, R3, S1, S2, S3
- **Fibonacci**: 0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0

## Market Observatory Integration

- **No visual changes** to Market Observatory
- **No new settings panel** in Market Observatory
- **Only behavior change**: Indicator results may differ when user changes settings in Indicators page
- **Shared computation**: Both pages use `computeAllIndicators()` from `data.ts`

## Testing

33 tests covering:
- Settings defaults
- Serialization/deserialization
- Invalid persisted settings
- Parameter validation (period, MACD, Ichimoku)
- Enable/disable
- Reset behavior
- Latest value extraction
- Data states
- Parameter propagation
- Market Observatory integration
- No duplicate implementations

## Build Verification

- TypeScript: ✅ `npm run typecheck` passes
- Python lint: ✅ `ruff check` passes
- Python tests: ✅ 163 tests passing (49 LLM-1 + 81 LLM-2 + 33 indicators)
