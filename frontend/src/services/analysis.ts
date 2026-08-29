/**
 * M25 Market Analysis Service.
 * Fetches structured analysis from the backend /market/{asset}/analysis endpoint.
 * Falls back to local computation if backend is unavailable.
 */

import type { OHLCBar } from '../types';
import { API_BASE } from './config';

// ============================================================
// Types
// ============================================================

export type TrendDirection = 'uptrend' | 'downtrend' | 'ranging' | 'transition';
export type TrendStrength = 'strong' | 'moderate' | 'weak';
export type MomentumState = 'bullish' | 'bearish' | 'neutral' | 'mixed' | 'overbought' | 'oversold';
export type VolatilityRegime = 'low' | 'normal' | 'high' | 'expanding' | 'contracting';
export type VolumeStateType = 'confirming' | 'weak' | 'mixed' | 'diverging' | 'unavailable';
export type StructureState = 'bullish' | 'bearish' | 'range' | 'transition' | 'mixed';
export type AlignmentState = 'aligned_bullish' | 'aligned_bearish' | 'mixed' | 'conflicting' | 'insufficient_data';
export type DataQualityLevel = 'good' | 'stale' | 'insufficient' | 'missing' | 'invalid';

export interface TrendContext {
  direction: TrendDirection;
  strength: TrendStrength;
  ema_aligned: boolean;
  adx_value: number | null;
  adx_trending: boolean;
  structure_confirms: boolean;
  evidence: string[];
  conflicts: string[];
}

export interface MomentumContext {
  state: MomentumState;
  rsi_value: number | null;
  rsi_zone: string;
  macd_positive: boolean;
  macd_histogram: number | null;
  stochastic_k: number | null;
  stochastic_d: number | null;
  cci_value: number | null;
  roc_value: number | null;
  williams_r_value: number | null;
  evidence: string[];
  conflicts: string[];
}

export interface VolatilityContextType {
  regime: VolatilityRegime;
  atr_value: number | null;
  atr_pct: number | null;
  bb_width: number | null;
  bb_position: string;
  evidence: string[];
}

export interface VolumeAnalysisContext {
  state: VolumeStateType;
  obv_trend: string;
  vwap_distance: number | null;
  mfi_value: number | null;
  mfi_zone: string;
  has_volume_data: boolean;
  evidence: string[];
}

export interface StructureAnalysisContext {
  state: StructureState;
  regime: string;
  swing_count: number;
  break_count: number;
  active_support_count: number;
  active_resistance_count: number;
  evidence: string[];
}

export interface LiquidityAnalysisContext {
  swept_count: number;
  unswept_count: number;
  nearest_liquidity: number | null;
  evidence: string[];
}

export interface TimeframeAnalysis {
  timeframe: string;
  trend: TrendDirection;
  structure: StructureState;
  regime: string;
  momentum: MomentumState;
}

export interface MultiTimeframeContextType {
  alignment: AlignmentState;
  timeframes: TimeframeAnalysis[];
  evidence: string[];
}

export interface ConflictItem {
  domain_a: string;
  state_a: string;
  domain_b: string;
  state_b: string;
  description: string;
}

export interface DataQualityContextType {
  quality: DataQualityLevel;
  candle_count: number;
  latest_timestamp: string | null;
  provider: string;
  stale: boolean;
  missing_fields: string[];
  timeframe: string;
  asset: string;
}

export type ConfluenceLevelType = 'strong_agreement' | 'moderate_agreement' | 'weak_agreement'
  | 'neutral' | 'mixed' | 'moderate_disagreement' | 'strong_disagreement' | 'insufficient_data';

export interface ConfluenceResult {
  level: ConfluenceLevelType;
  score: number;
  bullish_aligned: number;
  bearish_aligned: number;
  conflicting: number;
  missing: number;
  evidence_summary: string[];
}

export type ScenarioTypeVal = 'continuation' | 'reversal' | 'range' | 'breakout' | 'breakdown' | 'insufficient_evidence';

export interface ScenarioEvidence {
  domain: string;
  supports: boolean;
  description: string;
}

export interface Scenario {
  scenario_type: ScenarioTypeVal;
  name: string;
  supporting_evidence: ScenarioEvidence[];
  conflicting_evidence: ScenarioEvidence[];
  invalidating_conditions: string[];
  confidence: number;
  relevant_timeframe: string;
  explanation: string;
}

export interface ScenarioResult {
  scenarios: Scenario[];
  primary_scenario: Scenario;
  methodology_version: string;
}

export type ConflictSeverityType = 'low' | 'medium' | 'high' | 'critical';

export interface EnhancedConflict {
  conflict_type: string;
  severity: ConflictSeverityType;
  domain_a: string;
  state_a: string;
  domain_b: string;
  state_b: string;
  description: string;
  evidence: string[];
}

export interface DataProvenanceResult {
  provider: string;
  asset: string;
  timeframe: string;
  retrieved_at: string;
  data_timestamp: string | null;
  freshness: string;
  data_quality: string;
  is_demo: boolean;
  methodology_version: string;
}

export interface ResearchIntegrityResult {
  no_deployment_signal: boolean;
  no_predictions: boolean;
  no_trading_signals: boolean;
  deterministic: boolean;
  no_future_data: boolean;
  classification: string;
  disclaimer: string;
}

export interface ExplanationSection {
  heading: string;
  content: string;
  evidence: string[];
}

export interface MarketAnalysis {
  asset: string;
  timeframe: string;
  trend: TrendContext;
  momentum: MomentumContext;
  volatility: VolatilityContextType;
  volume: VolumeAnalysisContext;
  structure: StructureAnalysisContext;
  liquidity: LiquidityAnalysisContext;
  multi_timeframe: MultiTimeframeContextType;
  conflicts: EnhancedConflict[];
  data_quality: DataQualityContextType;
  explanation: ExplanationSection[];
  confluence: ConfluenceResult;
  scenarios: ScenarioResult;
  uncertainty: string[];
  methodology_version: string;
  provenance: DataProvenanceResult;
  research_integrity: ResearchIntegrityResult;
  provider: string;
  is_demo: boolean;
  research_conclusion: string;
}

// ============================================================
// API Fetch
// ============================================================

const _analysisCache = new Map<string, { data: MarketAnalysis; time: number }>();
const ANALYSIS_CACHE_TTL = 30_000;

export async function fetchMarketAnalysis(
  asset: string,
  timeframe: string = '1d',
  limit: number = 200,
): Promise<MarketAnalysis | null> {
  const cacheKey = `${asset}:${timeframe}:${limit}`;
  const cached = _analysisCache.get(cacheKey);
  if (cached && Date.now() - cached.time < ANALYSIS_CACHE_TTL) {
    return cached.data;
  }

  try {
    const resp = await fetch(
      `${API_BASE}/market/${asset}/analysis?timeframe=${timeframe}&limit=${limit}`,
      { signal: AbortSignal.timeout(20000) },
    );
    if (!resp.ok) return null;
    const data: MarketAnalysis = await resp.json();
    _analysisCache.set(cacheKey, { data, time: Date.now() });
    return data;
  } catch {
    return null;
  }
}

// ============================================================
// Local Fallback Analysis (when backend unavailable)
// ============================================================

export function computeLocalAnalysis(
  bars: OHLCBar[],
  asset: string,
  timeframe: string,
): MarketAnalysis | null {
  if (bars.length < 30) return null;

  const closes = bars.map(b => b.close);
  const highs = bars.map(b => b.high);
  const lows = bars.map(b => b.low);

  // Simple local trend via EMA
  const ema12 = computeLocalEMA(closes, 12);
  const ema26 = computeLocalEMA(closes, 26);
  const lastEma12 = ema12[ema12.length - 1];
  const lastEma26 = ema26[ema26.length - 1];
  const emaAligned = lastEma12 != null && lastEma26 != null && lastEma12 > lastEma26;

  const trendDir: TrendDirection = emaAligned ? 'uptrend' : 'downtrend';

  // RSI
  const rsiVals = computeLocalRSI(closes, 14);
  const lastRsi = rsiVals[rsiVals.length - 1] ?? null;

  // ATR
  const atrVals = computeLocalATR(highs, lows, closes, 14);
  const lastAtr = atrVals[atrVals.length - 1] ?? null;
  const lastClose = closes[closes.length - 1];
  const atrPct = lastAtr && lastClose ? lastAtr / lastClose : null;

  const trend: TrendContext = {
    direction: trendDir,
    strength: 'moderate',
    ema_aligned: emaAligned,
    adx_value: null,
    adx_trending: false,
    structure_confirms: false,
    evidence: [`EMA12 ${emaAligned ? '>' : '<'} EMA26`],
    conflicts: [],
  };

  const momentum: MomentumContext = {
    state: lastRsi != null ? (lastRsi > 60 ? 'bullish' : lastRsi < 40 ? 'bearish' : 'neutral') : 'neutral',
    rsi_value: lastRsi,
    rsi_zone: lastRsi != null ? (lastRsi > 70 ? 'overbought' : lastRsi < 30 ? 'oversold' : 'neutral') : 'neutral',
    macd_positive: emaAligned,
    macd_histogram: null,
    stochastic_k: null,
    stochastic_d: null,
    cci_value: null,
    roc_value: null,
    williams_r_value: null,
    evidence: lastRsi != null ? [`RSI(14) = ${lastRsi.toFixed(1)}`] : [],
    conflicts: [],
  };

  const vol: VolatilityContextType = {
    regime: atrPct != null ? (atrPct > 0.04 ? 'high' : atrPct < 0.01 ? 'low' : 'normal') : 'normal',
    atr_value: lastAtr,
    atr_pct: atrPct,
    bb_width: null,
    bb_position: 'unknown',
    evidence: lastAtr != null ? [`ATR = ${lastAtr.toFixed(2)}`] : [],
  };

  const volumeCtx: VolumeAnalysisContext = {
    state: 'unavailable',
    obv_trend: 'unknown',
    vwap_distance: null,
    mfi_value: null,
    mfi_zone: 'unknown',
    has_volume_data: false,
    evidence: ['Local analysis — volume not computed'],
  };

  const structureCtx: StructureAnalysisContext = {
    state: 'range',
    regime: 'ranging',
    swing_count: 0,
    break_count: 0,
    active_support_count: 0,
    active_resistance_count: 0,
    evidence: ['Local analysis — structure not computed'],
  };

  const liquidityCtx: LiquidityAnalysisContext = {
    swept_count: 0,
    unswept_count: 0,
    nearest_liquidity: null,
    evidence: [],
  };

  const mtf: MultiTimeframeContextType = {
    alignment: 'insufficient_data',
    timeframes: [],
    evidence: ['Local analysis — multi-timeframe not available'],
  };

  const dataQuality: DataQualityContextType = {
    quality: 'good',
    candle_count: bars.length,
    latest_timestamp: bars[bars.length - 1]?.time ?? null,
    provider: 'local',
    stale: false,
    missing_fields: [],
    timeframe,
    asset,
  };

  const explanation: ExplanationSection[] = [
    { heading: 'Trend', content: trend.direction.toUpperCase(), evidence: trend.evidence },
    { heading: 'Momentum', content: momentum.state.toUpperCase(), evidence: momentum.evidence },
    { heading: 'Volatility', content: vol.regime.toUpperCase(), evidence: vol.evidence },
    { heading: 'Data Quality', content: `LOCAL — ${bars.length} candles`, evidence: ['Computed locally'] },
  ];

  return {
    asset,
    timeframe,
    trend,
    momentum,
    volatility: vol,
    volume: volumeCtx,
    structure: structureCtx,
    liquidity: liquidityCtx,
    multi_timeframe: mtf,
    conflicts: [],
    data_quality: dataQuality,
    explanation,
    confluence: {
      level: 'insufficient_data', score: 0, bullish_aligned: 0,
      bearish_aligned: 0, conflicting: 0, missing: 0, evidence_summary: [],
    },
    scenarios: {
      scenarios: [{
        scenario_type: 'insufficient_evidence', name: 'Local Only',
        supporting_evidence: [], conflicting_evidence: [],
        invalidating_conditions: [], confidence: 0,
        relevant_timeframe: timeframe, explanation: 'Backend unavailable — local analysis only',
      }],
      primary_scenario: {
        scenario_type: 'insufficient_evidence', name: 'Local Only',
        supporting_evidence: [], conflicting_evidence: [],
        invalidating_conditions: [], confidence: 0,
        relevant_timeframe: timeframe, explanation: 'Backend unavailable — local analysis only',
      },
      methodology_version: 'm26.0',
    },
    uncertainty: ['Backend unavailable — local analysis only'],
    methodology_version: 'm26.0',
    provenance: {
      provider: 'local', asset, timeframe,
      retrieved_at: new Date().toISOString(), data_timestamp: null,
      freshness: 'unknown', data_quality: 'unknown', is_demo: true,
      methodology_version: 'm26.0',
    },
    research_integrity: {
      no_deployment_signal: true, no_predictions: true, no_trading_signals: true,
      deterministic: true, no_future_data: true, classification: 'ANALYTICAL_RESEARCH',
      disclaimer: 'Descriptive analytical research. No predictions. No trading signals.',
    },
    provider: 'local',
    is_demo: true,
    research_conclusion: 'NO_DEPLOYMENT_SIGNAL',
  };
}

// ============================================================
// Local indicator helpers
// ============================================================

function computeLocalEMA(values: number[], period: number): (number | null)[] {
  if (values.length < period) return values.map(() => null);
  const k = 2 / (period + 1);
  const result: (number | null)[] = new Array(period - 1).fill(null);
  let ema = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result.push(ema);
  for (let i = period; i < values.length; i++) {
    ema = values[i] * k + ema * (1 - k);
    result.push(ema);
  }
  return result;
}

function computeLocalRSI(closes: number[], period: number): (number | null)[] {
  if (closes.length < period + 1) return closes.map(() => null);
  const result: (number | null)[] = new Array(period).fill(null);
  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const change = closes[i] - closes[i - 1];
    avgGain += Math.max(change, 0);
    avgLoss += Math.max(-change, 0);
  }
  avgGain /= period;
  avgLoss /= period;
  result.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    avgGain = (avgGain * (period - 1) + Math.max(change, 0)) / period;
    avgLoss = (avgLoss * (period - 1) + Math.max(-change, 0)) / period;
    result.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  }
  return result;
}

function computeLocalATR(highs: number[], lows: number[], closes: number[], period: number): (number | null)[] {
  if (closes.length < 2) return closes.map(() => null);
  const tr: number[] = [highs[0] - lows[0]];
  for (let i = 1; i < closes.length; i++) {
    tr.push(Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1])));
  }
  const result: (number | null)[] = [];
  for (let i = 0; i < tr.length; i++) {
    if (i + 1 < period) { result.push(null); continue; }
    const start = i + 1 - period;
    result.push(tr.slice(start, i + 1).reduce((a, b) => a + b, 0) / period);
  }
  return result;
}
