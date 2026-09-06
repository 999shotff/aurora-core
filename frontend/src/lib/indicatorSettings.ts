/**
 * Indicator Control Center — Settings Store
 *
 * Manages indicator configuration with localStorage persistence.
 * Propagates changes to Market Observatory via shared state.
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { INDICATOR_GROUPS, type IndicatorDef } from '../services/data';

const STORAGE_KEY = 'aurora.indicator-settings.v1';
const SCHEMA_VERSION = 1;

export interface IndicatorSetting {
  id: string;
  enabled: boolean;
  params: Record<string, number>;
}

export interface IndicatorSettingsState {
  version: number;
  indicators: IndicatorSetting[];
  lastCalculated: number | null;
}

export interface IndicatorValue {
  seriesName: string;
  label: string;
  value: number | null;
  formatted: string;
}

export interface IndicatorFullState {
  id: string;
  name: string;
  group: 'TREND' | 'MOMENTUM' | 'VOLATILITY' | 'VOLUME' | 'LEVELS';
  enabled: boolean;
  overlay: boolean;
  minDataLength: number;
  params: Record<string, number>;
  paramDefs: IndicatorDef['params'];
  values: IndicatorValue[];
  subSeries: string[];
  status: 'ok' | 'insufficient_data' | 'unavailable';
}

function getDefaultSettings(): IndicatorSetting[] {
  return INDICATOR_GROUPS.map(def => ({
    id: def.id,
    enabled: ['sma', 'ema', 'rsi', 'macd', 'bb', 'atr'].includes(def.id),
    params: Object.fromEntries(def.params.map(p => [p.id, p.default])),
  }));
}

function getDefaults(): IndicatorSettingsState {
  return {
    version: SCHEMA_VERSION,
    indicators: getDefaultSettings(),
    lastCalculated: null,
  };
}

export function loadIndicatorSettings(): IndicatorSettingsState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return getDefaults();
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return getDefaults();
    if (parsed.version !== SCHEMA_VERSION) {
      localStorage.removeItem(STORAGE_KEY);
      return getDefaults();
    }
    if (!Array.isArray(parsed.indicators)) return getDefaults();
    const defaults = getDefaults();
    const merged = defaults.indicators.map(defaultInd => {
      const stored = parsed.indicators.find((s: IndicatorSetting) => s.id === defaultInd.id);
      if (!stored) return defaultInd;
      return {
        id: defaultInd.id,
        enabled: typeof stored.enabled === 'boolean' ? stored.enabled : defaultInd.enabled,
        params: { ...defaultInd.params, ...stored.params },
      };
    });
    return {
      version: SCHEMA_VERSION,
      indicators: merged,
      lastCalculated: typeof parsed.lastCalculated === 'number' ? parsed.lastCalculated : null,
    };
  } catch {
    return getDefaults();
  }
}

export function saveIndicatorSettings(state: IndicatorSettingsState): boolean {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function resetIndicatorSettings(): IndicatorSettingsState {
  const defaults = getDefaults();
  saveIndicatorSettings(defaults);
  return defaults;
}

export function getEnabledSet(settings: IndicatorSettingsState): Set<string> {
  return new Set(settings.indicators.filter(i => i.enabled).map(i => i.id));
}

export function getParamsRecord(settings: IndicatorSettingsState): Record<string, Record<string, number>> {
  const result: Record<string, Record<string, number>> = {};
  for (const ind of settings.indicators) {
    if (Object.keys(ind.params).length > 0) {
      result[ind.id] = { ...ind.params };
    }
  }
  return result;
}

export function validateIndicatorParams(
  indicatorId: string,
  params: Record<string, number>
): { valid: boolean; errors: string[] } {
  const def = INDICATOR_GROUPS.find(d => d.id === indicatorId);
  if (!def) return { valid: false, errors: [`Unknown indicator: ${indicatorId}`] };

  const errors: string[] = [];

  for (const paramDef of def.params) {
    const value = params[paramDef.id];
    if (value === undefined) continue;
    if (typeof value !== 'number' || isNaN(value) || !isFinite(value)) {
      errors.push(`${paramDef.label}: must be a valid number`);
      continue;
    }
    if (value < paramDef.min) errors.push(`${paramDef.label}: must be >= ${paramDef.min}`);
    if (value > paramDef.max) errors.push(`${paramDef.label}: must be <= ${paramDef.max}`);
    if (paramDef.step >= 1 && value !== Math.round(value)) {
      errors.push(`${paramDef.label}: must be an integer`);
    }
  }

  if (indicatorId === 'macd') {
    const fast = params.fast ?? 12;
    const slow = params.slow ?? 26;
    if (fast >= slow) errors.push('Fast must be less than Slow');
  }

  if (indicatorId === 'ichimoku') {
    const tenkan = params.tenkan ?? 9;
    const kijun = params.kijun ?? 26;
    const senkouB = params.senkouB ?? 52;
    if (tenkan >= kijun) errors.push('Tenkan must be less than Kijun');
    if (kijun >= senkouB) errors.push('Kijun must be less than Senkou B');
  }

  return { valid: errors.length === 0, errors };
}

export function extractLatestValues(
  series: Array<{ name: string; points: Array<{ time: string; value: number }> }>,
  indicatorId: string,
  subSeries: string[]
): IndicatorValue[] {
  const values: IndicatorValue[] = [];

  for (const seriesName of subSeries) {
    const s = series.find(sr => sr.name === seriesName);
    if (!s || s.points.length === 0) {
      values.push({
        seriesName,
        label: seriesName.replace(/_/g, ' ').toUpperCase(),
        value: null,
        formatted: '—',
      });
      continue;
    }
    const lastPoint = s.points[s.points.length - 1];
    values.push({
      seriesName,
      label: seriesName.replace(/_/g, ' ').toUpperCase(),
      value: lastPoint.value,
      formatted: formatIndicatorValue(indicatorId, seriesName, lastPoint.value),
    });
  }

  return values;
}

function formatIndicatorValue(indicatorId: string, seriesName: string, value: number): string {
  if (indicatorId === 'rsi' || indicatorId === 'williamsr' || indicatorId === 'stochastic') {
    return value.toFixed(2);
  }
  if (indicatorId === 'macd') {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (indicatorId === 'obv') {
    return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  if (indicatorId === 'cci' || indicatorId === 'roc' || indicatorId === 'mfi') {
    return value.toFixed(2);
  }
  if (indicatorId === 'atr') {
    return value.toFixed(2);
  }
  if (indicatorId === 'adx') {
    return value.toFixed(2);
  }
  if (indicatorId === 'fib') {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (indicatorId === 'pivot') {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (seriesName.includes('bb_') || seriesName.includes('ema_') || seriesName.includes('sma_') || seriesName.includes('ichimoku_')) {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
