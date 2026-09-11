/**
 * Unified Analysis — API client.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { API_BASE } from './config';

export type EvidenceClass = 'OBSERVED' | 'DERIVED' | 'STATISTICAL' | 'SIMULATED' | 'HYPOTHESIS' | 'UNAVAILABLE';
export type DirectionalBias = 'UP' | 'DOWN' | 'NEUTRAL' | 'MIXED' | 'INSUFFICIENT_DATA';
export type AssessmentStrength = 'LOW' | 'MODERATE' | 'HIGH';

// ============================================================
// Market Analysis Types (M25/M26 backend response)
// ============================================================

export type TrendDirection = 'uptrend' | 'downtrend' | 'sideways' | 'transition' | 'insufficient_data';
export type TrendStrength = 'strong' | 'moderate' | 'weak' | 'absent';
export type MomentumState = 'bullish' | 'bearish' | 'neutral' | 'overbought' | 'oversold' | 'divergence' | 'insufficient_data';
export type VolatilityRegime = 'high' | 'low' | 'normal' | 'expanding' | 'contracting' | 'insufficient_data';
export type VolumeState = 'confirming' | 'diverging' | 'climax' | 'dry' | 'unavailable' | 'insufficient_data';
export type StructureContextState = 'bullish' | 'bearish' | 'neutral' | 'transition' | 'insufficient_data';
export type MarketRegime = 'trending_up' | 'trending_down' | 'ranging' | 'volatile' | 'insufficient_data';
export type AlignmentState = 'aligned_bullish' | 'aligned_bearish' | 'conflicting' | 'mixed' | 'insufficient_data';
export type DataQuality = 'good' | 'stale' | 'poor' | 'insufficient';
export type ConfluenceLevel = 'strong_agreement' | 'moderate_agreement' | 'weak_agreement' | 'neutral' | 'mixed' | 'moderate_disagreement' | 'strong_disagreement' | 'insufficient_data';
export type ConflictSeverity = 'low' | 'medium' | 'high' | 'critical';
export type ScenarioType = 'continuation' | 'reversal' | 'range' | 'breakout' | 'breakdown' | 'insufficient_evidence';

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
  state: VolumeState;
  obv_trend: string;
  vwap_distance: number | null;
  mfi_value: number | null;
  mfi_zone: string;
  has_volume_data: boolean;
  evidence: string[];
}

export interface StructureAnalysisContext {
  state: StructureContextState;
  regime: MarketRegime;
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
  structure: StructureContextState;
  regime: MarketRegime;
  momentum: MomentumState;
}

export interface MultiTimeframeContextType {
  alignment: AlignmentState;
  timeframes: TimeframeAnalysis[];
  evidence: string[];
}

export interface EnhancedConflict {
  conflict_type: string;
  severity: ConflictSeverity;
  domain_a: string;
  state_a: string;
  domain_b: string;
  state_b: string;
  description: string;
  evidence: string[];
}

export interface DataQualityContextType {
  quality: DataQuality;
  candle_count: number;
  latest_timestamp: string | null;
  provider: string;
  stale: boolean;
  missing_fields: string[];
  invalid_candles_removed: number;
  timeframe: string;
  asset: string;
}

export interface ExplanationSection {
  heading: string;
  content: string;
  evidence: string[];
}

export interface ConfluenceResult {
  level: ConfluenceLevel;
  score: number;
  bullish_aligned: number;
  bearish_aligned: number;
  conflicting: number;
  missing: number;
  evidence_summary: string[];
}

export interface ScenarioResult {
  scenarios: Array<{
    scenario_type: ScenarioType;
    name: string;
    supporting_evidence: Array<{ domain: string; supports: boolean; description: string }>;
    conflicting_evidence: Array<{ domain: string; supports: boolean; description: string }>;
    invalidating_conditions: string[];
    confidence: number;
    relevant_timeframe: string;
    explanation: string;
  }>;
  primary_scenario: {
    scenario_type: ScenarioType;
    name: string;
    explanation: string;
    confidence: number;
  };
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

export interface DataProvenance {
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

export interface MarketAnalysis {
  asset: string;
  timeframe: string;
  timestamp: string;
  data_quality: DataQualityContextType;
  market_regime: string;
  trend: TrendContext;
  momentum: MomentumContext;
  volatility: VolatilityContextType;
  volume: VolumeAnalysisContext;
  structure: StructureAnalysisContext;
  liquidity: LiquidityAnalysisContext;
  multi_timeframe: MultiTimeframeContextType;
  confluence: ConfluenceResult;
  scenarios: ScenarioResult;
  conflicts: EnhancedConflict[];
  evidence: {
    items: Array<{
      domain: string;
      classification: string;
      polarity: string;
      strength: string;
      value: string;
      description: string;
      source_indicator: string;
    }>;
    bullish_count: number;
    bearish_count: number;
    neutral_count: number;
    unavailable_count: number;
    total_evidence: number;
    bullish_pct: number;
    bearish_pct: number;
  };
  uncertainty: string[];
  methodology_version: string;
  provenance: DataProvenance;
  research_integrity: ResearchIntegrityResult;
  provider?: string;
  is_demo?: boolean;
}

// ============================================================
// Market Analysis API
// ============================================================

export async function fetchMarketAnalysis(
  asset: string,
  timeframe: string,
  limit: number = 200,
): Promise<MarketAnalysis | null> {
  try {
    const resp = await fetch(
      `${API_BASE}/market/${encodeURIComponent(asset)}/analysis?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`,
    );
    if (!resp.ok) return null;
    return resp.json();
  } catch {
    return null;
  }
}

// ============================================================
// Local Analysis Fallback
// ============================================================

function ema(closes: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [closes[0]];
  for (let i = 1; i < closes.length; i++) {
    result.push(closes[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}

function sma(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) { result.push(null); continue; }
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += values[j];
    result.push(sum / period);
  }
  return result;
}

function rsi(closes: number[], period: number = 14): number | null {
  if (closes.length < period + 1) return null;
  let gains = 0, losses = 0;
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gains += diff; else losses -= diff;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) { avgGain = (avgGain * (period - 1) + diff) / period; avgLoss = (avgLoss * (period - 1)) / period; }
    else { avgGain = (avgGain * (period - 1)) / period; avgLoss = (avgLoss * (period - 1) - diff) / period; }
  }
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

function atr(highs: number[], lows: number[], closes: number[], period: number = 14): number | null {
  if (highs.length < period + 1) return null;
  const trs: number[] = [];
  for (let i = 1; i < highs.length; i++) {
    trs.push(Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1])));
  }
  let sum = 0;
  for (let i = 0; i < period; i++) sum += trs[i];
  let val = sum / period;
  for (let i = period; i < trs.length; i++) {
    val = (val * (period - 1) + trs[i]) / period;
  }
  return val;
}

function detectSwings(highs: number[], lows: number[]): { highs: number[]; lows: number[] } {
  const swingHighs: number[] = [];
  const swingLows: number[] = [];
  for (let i = 2; i < highs.length - 2; i++) {
    if (highs[i] > highs[i - 1] && highs[i] > highs[i - 2] && highs[i] > highs[i + 1] && highs[i] > highs[i + 2]) {
      swingHighs.push(i);
    }
    if (lows[i] < lows[i - 1] && lows[i] < lows[i - 2] && lows[i] < lows[i + 1] && lows[i] < lows[i + 2]) {
      swingLows.push(i);
    }
  }
  return { highs: swingHighs, lows: swingLows };
}

function computeBollinger(closes: number[], period: number = 20): { upper: number; middle: number; lower: number; width: number; position: string } | null {
  if (closes.length < period) return null;
  const recent = closes.slice(-period);
  const mean = recent.reduce((a, b) => a + b, 0) / period;
  const variance = recent.reduce((a, b) => a + (b - mean) ** 2, 0) / period;
  const std = Math.sqrt(variance);
  const upper = mean + 2 * std;
  const lower = mean - 2 * std;
  const width = upper - lower;
  const last = closes[closes.length - 1];
  let position = 'middle';
  if (last > upper) position = 'above_upper';
  else if (last > mean) position = 'upper_middle';
  else if (last > lower) position = 'lower_middle';
  else position = 'below_lower';
  return { upper, middle: mean, lower, width, position };
}

export function computeLocalAnalysis(
  bars: import('../types').OHLCBar[],
  asset: string,
  timeframe: string,
): MarketAnalysis {
  const closes = bars.map(b => b.close);
  const highs = bars.map(b => b.high);
  const lows = bars.map(b => b.low);
  const last = bars[bars.length - 1];
  const first = bars[0];

  const ema12 = ema(closes, 12);
  const ema26 = ema(closes, 26);
  const ema50 = ema(closes, 50);
  const sma200 = sma(closes, 200);
  const rsiValue = rsi(closes);
  const atrValue = atr(highs, lows, closes);
  const bb = computeBollinger(closes);
  const swings = detectSwings(highs, lows);

  const priceChange = first.close > 0 ? (last.close - first.close) / first.close : 0;
  const emaAligned = ema12[ema12.length - 1] > ema26[ema26.length - 1];
  const trendDir: TrendDirection = priceChange > 0.02 ? 'uptrend' : priceChange < -0.02 ? 'downtrend' : 'sideways';
  const trendStrength: TrendStrength = Math.abs(priceChange) > 0.1 ? 'strong' : Math.abs(priceChange) > 0.04 ? 'moderate' : 'weak';

  let momentumState: MomentumState = 'neutral';
  if (rsiValue != null) {
    if (rsiValue > 70) momentumState = 'overbought';
    else if (rsiValue < 30) momentumState = 'oversold';
    else if (rsiValue > 55) momentumState = 'bullish';
    else if (rsiValue < 45) momentumState = 'bearish';
  }

  let volRegime: VolatilityRegime = 'normal';
  if (atrValue != null && last.close > 0) {
    const atrPct = atrValue / last.close;
    if (atrPct > 0.04) volRegime = 'high';
    else if (atrPct < 0.015) volRegime = 'low';
  }

  const activeSupport = swings.lows.length;
  const activeResistance = swings.highs.length;

  const now = new Date().toISOString();
  return {
    asset,
    timeframe,
    timestamp: now,
    data_quality: {
      quality: bars.length >= 50 ? 'good' : bars.length >= 20 ? 'stale' : 'poor',
      candle_count: bars.length,
      latest_timestamp: last.time ?? null,
      provider: 'local',
      stale: false,
      missing_fields: [],
      invalid_candles_removed: 0,
      timeframe,
      asset,
    },
    market_regime: volRegime === 'high' ? 'volatile' : trendDir === 'uptrend' ? 'trending_up' : trendDir === 'downtrend' ? 'trending_down' : 'ranging',
    trend: {
      direction: trendDir,
      strength: trendStrength,
      ema_aligned: emaAligned,
      adx_value: null,
      adx_trending: false,
      structure_confirms: trendDir === 'uptrend' ? emaAligned : true,
      evidence: [`Price change ${(priceChange * 100).toFixed(1)}% over ${bars.length} bars`],
      conflicts: [],
    },
    momentum: {
      state: momentumState,
      rsi_value: rsiValue,
      rsi_zone: rsiValue != null ? (rsiValue > 70 ? 'overbought' : rsiValue < 30 ? 'oversold' : 'neutral') : 'unknown',
      macd_positive: emaAligned,
      macd_histogram: null,
      stochastic_k: null,
      stochastic_d: null,
      cci_value: null,
      roc_value: null,
      williams_r_value: null,
      evidence: rsiValue != null ? [`RSI(14) = ${rsiValue.toFixed(1)}`] : ['Insufficient data for RSI'],
      conflicts: [],
    },
    volatility: {
      regime: volRegime,
      atr_value: atrValue,
      atr_pct: atrValue != null && last.close > 0 ? atrValue / last.close : null,
      bb_width: bb?.width ?? null,
      bb_position: bb?.position ?? 'unknown',
      evidence: atrValue != null ? [`ATR(14) = ${atrValue.toFixed(2)}`] : ['Insufficient data for ATR'],
    },
    volume: {
      state: 'unavailable',
      obv_trend: 'unknown',
      vwap_distance: null,
      mfi_value: null,
      mfi_zone: 'unknown',
      has_volume_data: false,
      evidence: ['No volume data available in local computation'],
    },
    structure: {
      state: trendDir === 'uptrend' ? 'bullish' : trendDir === 'downtrend' ? 'bearish' : 'neutral',
      regime: volRegime === 'high' ? 'volatile' : trendDir === 'uptrend' ? 'trending_up' : trendDir === 'downtrend' ? 'trending_down' : 'ranging',
      swing_count: swings.highs.length + swings.lows.length,
      break_count: 0,
      active_support_count: activeSupport,
      active_resistance_count: activeResistance,
      evidence: [`Detected ${swings.lows.length} swing lows, ${swings.highs.length} swing highs`],
    },
    liquidity: {
      swept_count: 0,
      unswept_count: swings.lows.length,
      nearest_liquidity: swings.lows.length > 0 ? lows[swings.lows[swings.lows.length - 1]] ?? null : null,
      evidence: ['Liquidity analysis limited in local mode'],
    },
    multi_timeframe: {
      alignment: 'insufficient_data',
      timeframes: [],
      evidence: ['Multi-timeframe analysis requires backend data'],
    },
    confluence: {
      level: 'insufficient_data',
      score: 0,
      bullish_aligned: 0,
      bearish_aligned: 0,
      conflicting: 0,
      missing: 0,
      evidence_summary: ['Confluence scoring requires full backend analysis'],
    },
    scenarios: {
      scenarios: [
        {
          scenario_type: 'continuation' as ScenarioType,
          name: 'Continuation',
          supporting_evidence: [],
          conflicting_evidence: [],
          invalidating_conditions: [],
          confidence: 0.3,
          relevant_timeframe: timeframe,
          explanation: 'Basic scenario — local analysis limited',
        },
      ],
      primary_scenario: {
        scenario_type: 'continuation' as ScenarioType,
        name: 'Continuation',
        explanation: 'Default scenario — local analysis limited',
        confidence: 0.3,
      },
      methodology_version: 'local.0',
    },
    conflicts: [],
    evidence: {
      items: [],
      bullish_count: 0,
      bearish_count: 0,
      neutral_count: 0,
      unavailable_count: 0,
      total_evidence: 0,
      bullish_pct: 0,
      bearish_pct: 0,
    },
    uncertainty: ['Local analysis — limited indicators, no multi-timeframe, no volume data'],
    methodology_version: 'local.0',
    provenance: {
      provider: 'local',
      asset,
      timeframe,
      retrieved_at: now,
      data_timestamp: last.time ?? null,
      freshness: 'local',
      data_quality: bars.length >= 50 ? 'good' : 'stale',
      is_demo: false,
      methodology_version: 'local.0',
    },
    research_integrity: {
      no_deployment_signal: true,
      no_predictions: true,
      no_trading_signals: true,
      deterministic: true,
      no_future_data: true,
      classification: 'NO_DEPLOYMENT_SIGNAL',
      disclaimer: 'This is local analysis for research purposes only. No trading signals.',
    },
    provider: 'local',
    is_demo: false,
  };
}

// ============================================================
// Unified Analysis API
// ============================================================

export interface UnifiedAssessment {
  assessment_id: string;
  question: string;
  assessment: string;
  directional_bias: DirectionalBias;
  strength: AssessmentStrength;
  confidence: string;
  evidence_summary: string;
  total_inputs: number;
  observed_count: number;
  derived_count: number;
  simulated_count: number;
  hypothesis_count: number;
  evidence_agreement_ratio: string;
  supporting_factors: string[];
  contradicting_factors: string[];
  behavioral_factors: string[];
  cycle_hypotheses: string[];
  regime: string;
  uncertainty: string[];
  limitations: string[];
  source_inputs: string[];
  provenance: Array<{
    source_id: string;
    source_type: string;
    evidence_class: EvidenceClass;
    methodology: string;
  }>;
  asset: string | null;
  timeframe: string | null;
  domain: string;
  timestamp: number;
  computation_time_ms: number;
}

export interface UnifiedAnalysisRequest {
  question: string;
  asset?: string;
  timeframe?: string;
  domain?: string;
  market_context?: Record<string, unknown>;
  indicator_data?: Record<string, unknown>;
  structure_data?: Record<string, unknown>;
  run_persona?: boolean;
  run_cycles?: boolean;
}

export async function runUnifiedAnalysis(req: UnifiedAnalysisRequest): Promise<UnifiedAssessment> {
  const resp = await fetch(`${API_BASE}/api/v1/analysis/unified`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!resp.ok) throw new Error(`Analysis failed: ${resp.status}`);
  return resp.json();
}

export async function getAssessment(id: string): Promise<UnifiedAssessment> {
  const resp = await fetch(`${API_BASE}/api/v1/analysis/unified/${id}`);
  if (!resp.ok) throw new Error(`Assessment not found: ${resp.status}`);
  return resp.json();
}

export async function getAnalysisHealth(): Promise<{ status: string; service: string }> {
  const resp = await fetch(`${API_BASE}/api/v1/analysis/unified/health`);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}
