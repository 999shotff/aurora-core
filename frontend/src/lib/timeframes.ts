/**
 * M28 — Canonical Timeframe Engine.
 * Single source of truth for all timeframe definitions.
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

export type TimeframeId = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1D' | '1W';

export interface TimeframeDef {
  id: TimeframeId;
  label: string;
  durationMs: number;
  isIntraday: boolean;
  aggregationSource: TimeframeId | null;
  aggregationIntervalMinutes: number;
  yfinanceInterval: string;
  yfinancePeriod: string;
  minDataBars: number;
}

const MINUTE = 60_000;
const HOUR = 3_600_000;
const DAY = 86_400_000;
const WEEK = 604_800_000;

export const TIMEFRAME_DEFS: Record<TimeframeId, TimeframeDef> = {
  '1m': {
    id: '1m', label: '1m', durationMs: MINUTE, isIntraday: true,
    aggregationSource: null, aggregationIntervalMinutes: 1,
    yfinanceInterval: '1m', yfinancePeriod: '5d',
    minDataBars: 30,
  },
  '5m': {
    id: '5m', label: '5m', durationMs: 5 * MINUTE, isIntraday: true,
    aggregationSource: null, aggregationIntervalMinutes: 5,
    yfinanceInterval: '5m', yfinancePeriod: '60d',
    minDataBars: 30,
  },
  '15m': {
    id: '15m', label: '15m', durationMs: 15 * MINUTE, isIntraday: true,
    aggregationSource: null, aggregationIntervalMinutes: 15,
    yfinanceInterval: '15m', yfinancePeriod: '60d',
    minDataBars: 30,
  },
  '30m': {
    id: '30m', label: '30m', durationMs: 30 * MINUTE, isIntraday: true,
    aggregationSource: null, aggregationIntervalMinutes: 30,
    yfinanceInterval: '30m', yfinancePeriod: '60d',
    minDataBars: 30,
  },
  '1h': {
    id: '1h', label: '1h', durationMs: HOUR, isIntraday: true,
    aggregationSource: null, aggregationIntervalMinutes: 60,
    yfinanceInterval: '1h', yfinancePeriod: '730d',
    minDataBars: 30,
  },
  '4h': {
    id: '4h', label: '4h', durationMs: 4 * HOUR, isIntraday: true,
    aggregationSource: '1h', aggregationIntervalMinutes: 240,
    yfinanceInterval: '1h', yfinancePeriod: '730d',
    minDataBars: 30,
  },
  '1D': {
    id: '1D', label: '1D', durationMs: DAY, isIntraday: false,
    aggregationSource: null, aggregationIntervalMinutes: 1440,
    yfinanceInterval: '1d', yfinancePeriod: '5y',
    minDataBars: 30,
  },
  '1W': {
    id: '1W', label: '1W', durationMs: WEEK, isIntraday: false,
    aggregationSource: null, aggregationIntervalMinutes: 10080,
    yfinanceInterval: '1wk', yfinancePeriod: '10y',
    minDataBars: 12,
  },
};

export const TIMEFRAME_IDS: TimeframeId[] = ['1m', '5m', '15m', '30m', '1h', '4h', '1D', '1W'];

export function getTimeframeDef(id: string): TimeframeDef | undefined {
  return TIMEFRAME_DEFS[id as TimeframeId];
}

export function isIntradayTimeframe(id: string): boolean {
  return getTimeframeDef(id)?.isIntraday ?? false;
}

export function getTimeframeDurationMs(id: string): number {
  return getTimeframeDef(id)?.durationMs ?? DAY;
}

export function isAggregatedTimeframe(id: string): boolean {
  return getTimeframeDef(id)?.aggregationSource !== null;
}

export function getAggregationSource(id: string): TimeframeId | null {
  return getTimeframeDef(id)?.aggregationSource ?? null;
}
