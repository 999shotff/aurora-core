import type { OHLCBar, IndicatorSeries, Asset, Timeframe, AnalysisMetrics, IndicatorParamDef, IndicatorDisplayType } from '../types';
import { API_BASE } from './config';

export { API_BASE } from './config';

interface BackendOHLCResponse {
  symbol: string;
  timeframe: string;
  bars: { timestamp: string; open: number; high: number; low: number; close: number; volume: number }[];
  count: number;
  rejected_count: number;
  validation_errors: string[];
  provenance: {
    provider: string;
    asset: string;
    timeframe: string;
    retrieved_at: string;
    data_timestamp: string;
    source_status: string;
    is_demo: boolean;
  };
}

interface BackendQuoteResponse {
  symbol: string;
  last_price: number;
  timestamp: string;
  provider: string;
  is_demo: boolean;
  source_status: string;
}

interface BackendHealthResponse {
  status: string;
  services: { service: string; status: string; version: string }[];
  research_conclusion: string;
}

let _backendAvailable: boolean | null = null;
let _backendCheckTime = 0;
const BACKEND_CACHE_TTL = 30_000; // 30 seconds

async function checkBackend(): Promise<boolean> {
  const now = Date.now();
  if (_backendAvailable !== null && now - _backendCheckTime < BACKEND_CACHE_TTL) {
    return _backendAvailable;
  }
  try {
    const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    _backendAvailable = resp.ok;
  } catch {
    _backendAvailable = false;
  }
  _backendCheckTime = now;
  return _backendAvailable;
}

export function invalidateBackendCache(): void {
  _backendAvailable = null;
  _backendCheckTime = 0;
}

export async function fetchOHLCFromBackend(
  symbol: string,
  timeframe: Timeframe,
  limit: number = 200,
  signal?: AbortSignal
): Promise<{ bars: OHLCBar[]; isDemo: boolean; provider: string; stale: boolean } | null> {
  const available = await checkBackend();
  if (!available) return null;
  try {
    const tf = timeframe.toLowerCase();
    const resp = await fetch(`${API_BASE}/market/${symbol}/ohlc?timeframe=${tf}&limit=${limit}`, {
      signal: signal ?? AbortSignal.timeout(15000),
    });
    if (!resp.ok) return null;
    const data: BackendOHLCResponse = await resp.json();
    if (!data.bars || data.bars.length === 0) return null;
    const isIntraday = tf !== '1d' && tf !== '1w';
    const mapped = data.bars
      .filter(b => b.timestamp && isFinite(b.open) && isFinite(b.high) && isFinite(b.low) && isFinite(b.close) && isFinite(b.volume))
      .map(b => ({
        time: isIntraday ? b.timestamp.replace('Z', '').replace(/\.\d+$/, '') : b.timestamp.split('T')[0],
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
        volume: b.volume,
      }));
    const bars = sanitizeBars(mapped);
    if (bars.length === 0) return null;
    return {
      bars,
      isDemo: data.provenance?.is_demo ?? true,
      provider: data.provenance?.provider ?? 'unknown',
      stale: data.provenance?.source_status === 'stale',
    };
  } catch {
    return null;
  }
}

export async function fetchQuoteFromBackend(symbol: string): Promise<BackendQuoteResponse | null> {
  const available = await checkBackend();
  if (!available) return null;
  try {
    const resp = await fetch(`${API_BASE}/market/${symbol}/quote`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

export async function getBackendHealth(): Promise<BackendHealthResponse | null> {
  const available = await checkBackend();
  if (!available) return null;
  try {
    const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

export async function getDataSourceInfo(): Promise<{ isDemo: boolean; provider: string }> {
  const health = await getBackendHealth();
  if (health) {
    const providerSvc = health.services.find(s => s.service === 'market-data-provider');
    return {
      isDemo: providerSvc ? providerSvc.version === 'demo' : true,
      provider: providerSvc?.version ?? 'unknown',
    };
  }
  return { isDemo: true, provider: 'mock (no backend)' };
}

export function generateMockOHLCV(
  symbol: string,
  _timeframe: Timeframe,
  nBars: number = 200,
  seed: number = 42
): OHLCBar[] {
  let price = getStartPrice(symbol);
  const volatility = getVolatility(symbol);
  const bars: OHLCBar[] = [];
  const rng = mulberry32(seed);
  const startDate = new Date('2024-01-01');

  for (let i = 0; i < nBars; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    const ret = gaussianRandom(rng) * volatility + 0.0002;
    price *= 1 + ret;
    const high = price * (1 + Math.abs(gaussianRandom(rng) * volatility * 0.5));
    const low = price * (1 - Math.abs(gaussianRandom(rng) * volatility * 0.5));
    const open = price * (1 + gaussianRandom(rng) * volatility * 0.2);
    const vol = 1_000_000 + rng() * 49_000_000;

    bars.push({
      time: date.toISOString().split('T')[0],
      open: round(open, 2),
      high: round(Math.max(high, open, price), 2),
      low: round(Math.min(low, open, price), 2),
      close: round(price, 2),
      volume: round(vol, 0),
    });
  }
  return bars;
}

export async function fetchOHLCV(
  symbol: string,
  timeframe: Timeframe,
  nBars: number = 200,
  signal?: AbortSignal
): Promise<{ bars: OHLCBar[]; isDemo: boolean; provider: string; stale: boolean; empty: boolean }> {
  if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  const backendData = await fetchOHLCFromBackend(symbol, timeframe, nBars, signal);
  if (backendData) {
    return { ...backendData, empty: false };
  }
  const available = await checkBackend();
  if (available) {
    return { bars: [], isDemo: true, provider: 'unknown', stale: false, empty: true };
  }
  throw new Error('BACKEND UNAVAILABLE');
}

function getStartPrice(symbol: string): number {
  const prices: Record<string, number> = {
    'BTC-USD': 42000, 'ETH-USD': 2200, 'GOLD': 2000, 'SILVER': 24,
    'SPY': 470, 'QQQ': 400, 'NIFTY': 21000, 'NASDAQ': 16000,
    'EURUSD': 1.1, 'USDJPY': 148,
  };
  return prices[symbol] ?? 100;
}

function getVolatility(symbol: string): number {
  if (symbol.includes('BTC') || symbol.includes('ETH')) return 0.03;
  if (symbol.includes('GOLD') || symbol.includes('SILVER')) return 0.01;
  if (symbol.includes('EUR') || symbol.includes('JPY')) return 0.005;
  return 0.015;
}

function mulberry32(a: number) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function gaussianRandom(rng: () => number): number {
  const u1 = rng();
  const u2 = rng();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

function round(val: number, decimals: number): number {
  return Math.round(val * 10 ** decimals) / 10 ** decimals;
}

export function sanitizeBars(rawBars: { time: string; open: number; high: number; low: number; close: number; volume: number }[]): OHLCBar[] {
  const byTime = new Map<string, { time: string; open: number; high: number; low: number; close: number; volume: number }>();
  for (const b of rawBars) {
    if (!b.time || !isFinite(b.open) || !isFinite(b.high) || !isFinite(b.low) || !isFinite(b.close) || !isFinite(b.volume)) continue;
    const maxOC = Math.max(b.open, b.close);
    const minOC = Math.min(b.open, b.close);
    const high = Math.max(b.high, maxOC);
    const low = Math.min(b.low, minOC);
    const sanitized = { ...b, high, low };
    const existing = byTime.get(b.time);
    if (!existing || b.high > existing.high || b.low < existing.low) {
      byTime.set(b.time, sanitized);
    }
  }
  const sorted = Array.from(byTime.values()).sort((a, b) => {
    if (/^\d{4}-\d{2}-\d{2}$/.test(a.time)) return a.time.localeCompare(b.time);
    return new Date(a.time).getTime() - new Date(b.time).getTime();
  });
  return sorted.map(b => ({
    time: b.time,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
    volume: b.volume,
  }));
}

function validateArray(arr: number[], name: string): void {
  if (!Array.isArray(arr)) throw new Error(`${name} must be an array`);
}

function validatePeriod(period: number, name: string): number {
  const p = Math.floor(period);
  if (!isFinite(p) || p < 1) throw new Error(`${name} must be >= 1`);
  return p;
}

export function computeSMA(values: number[], period: number): (number | null)[] {
  validateArray(values, 'values');
  const p = validatePeriod(period, 'period');
  if (values.length === 0) return [];
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i < p - 1) { result.push(null); continue; }
    const slice = values.slice(i - p + 1, i + 1);
    const valid = slice.filter(v => isFinite(v));
    if (valid.length < p) { result.push(null); continue; }
    result.push(round(valid.reduce((a, b) => a + b, 0) / p, 6));
  }
  return result;
}

export function computeEMA(values: number[], period: number): (number | null)[] {
  validateArray(values, 'values');
  const p = validatePeriod(period, 'period');
  if (values.length === 0) return [];
  if (values.length < p) return new Array(values.length).fill(null);
  const result: (number | null)[] = new Array(p - 1).fill(null);
  const k = 2 / (p + 1);
  let ema = values.slice(0, p).reduce((a, b) => a + b, 0) / p;
  result.push(round(ema, 6));
  for (let i = p; i < values.length; i++) {
    const v = values[i];
    if (!isFinite(v)) { result.push(null); continue; }
    ema = v * k + ema * (1 - k);
    result.push(round(ema, 6));
  }
  return result;
}

export function computeRSI(closes: number[], period: number = 14): (number | null)[] {
  validateArray(closes, 'closes');
  const p = validatePeriod(period, 'period');
  if (closes.length < p + 1) return closes.map(() => null);
  const result: (number | null)[] = new Array(p).fill(null);
  const gains: number[] = [];
  const losses: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    gains.push(isFinite(change) ? Math.max(change, 0) : 0);
    losses.push(isFinite(change) ? Math.max(-change, 0) : 0);
  }
  let avgGain = gains.slice(0, p).reduce((a, b) => a + b, 0) / p;
  let avgLoss = losses.slice(0, p).reduce((a, b) => a + b, 0) / p;
  result.push(avgLoss === 0 ? 100 : round(100 - 100 / (1 + avgGain / avgLoss), 2));
  for (let i = p; i < gains.length; i++) {
    avgGain = (avgGain * (p - 1) + gains[i]) / p;
    avgLoss = (avgLoss * (p - 1) + losses[i]) / p;
    result.push(avgLoss === 0 ? 100 : round(100 - 100 / (1 + avgGain / avgLoss), 2));
  }
  return result;
}

export function computeMACD(closes: number[], fast = 12, slow = 26, signal = 9): { macdLine: (number | null)[]; signalLine: (number | null)[]; histogram: (number | null)[] } {
  validateArray(closes, 'closes');
  const f = validatePeriod(fast, 'fast');
  const s = validatePeriod(slow, 'slow');
  if (closes.length === 0) return { macdLine: [], signalLine: [], histogram: [] };
  const emaFast = computeEMA(closes, f);
  const emaSlow = computeEMA(closes, s);
  const macdLine: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (emaFast[i] !== null && emaSlow[i] !== null) {
      macdLine.push(round((emaFast[i] as number) - (emaSlow[i] as number), 6));
    } else {
      macdLine.push(null);
    }
  }
  const validMacd = macdLine.filter((v): v is number => v !== null);
  const signalRaw = computeEMA(validMacd, signal);
  const signalLine: (number | null)[] = [];
  let j = 0;
  for (const v of macdLine) {
    if (v === null) { signalLine.push(null); }
    else { signalLine.push(j < signalRaw.length ? signalRaw[j] : null); j++; }
  }
  const histogram: (number | null)[] = [];
  for (let i = 0; i < macdLine.length; i++) {
    if (macdLine[i] !== null && signalLine[i] !== null) {
      histogram.push(round((macdLine[i] as number) - (signalLine[i] as number), 6));
    } else {
      histogram.push(null);
    }
  }
  return { macdLine, signalLine, histogram };
}

export function computeBollinger(closes: number[], period = 20, numStd = 2): { upper: (number | null)[]; middle: (number | null)[]; lower: (number | null)[] } {
  validateArray(closes, 'closes');
  const p = validatePeriod(period, 'period');
  const middle = computeSMA(closes, p);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (middle[i] === null) { upper.push(null); lower.push(null); continue; }
    const window = closes.slice(i - p + 1, i + 1);
    const std = Math.sqrt(window.reduce((s, x) => s + (x - (middle[i] as number)) ** 2, 0) / p);
    upper.push(round((middle[i] as number) + numStd * std, 6));
    lower.push(round((middle[i] as number) - numStd * std, 6));
  }
  return { upper, middle, lower };
}

export function computeATR(highs: number[], lows: number[], closes: number[], period = 14): (number | null)[] {
  validateArray(highs, 'highs');
  validateArray(lows, 'lows');
  validateArray(closes, 'closes');
  const p = validatePeriod(period, 'period');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  if (closes.length < 2) return closes.map(() => null);
  const trValues: number[] = [highs[0] - lows[0]];
  for (let i = 1; i < closes.length; i++) {
    trValues.push(Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1])));
  }
  return computeSMA(trValues, p);
}

function computeRollingMax(values: number[], window: number): (number | null)[] {
  validateArray(values, 'values');
  const w = validatePeriod(window, 'window');
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < w) { result.push(null); continue; }
    const slice = values.slice(i + 1 - w, i + 1).filter(v => isFinite(v));
    result.push(slice.length > 0 ? Math.max(...slice) : null);
  }
  return result;
}

function computeRollingMin(values: number[], window: number): (number | null)[] {
  validateArray(values, 'values');
  const w = validatePeriod(window, 'window');
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < w) { result.push(null); continue; }
    const slice = values.slice(i + 1 - w, i + 1).filter(v => isFinite(v));
    result.push(slice.length > 0 ? Math.min(...slice) : null);
  }
  return result;
}

export function computeStochastic(
  highs: number[], lows: number[], closes: number[],
  kPeriod = 14, dPeriod = 3, smoothK = 3
): { k: (number | null)[]; d: (number | null)[] } {
  validateArray(highs, 'highs'); validateArray(lows, 'lows'); validateArray(closes, 'closes');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  const n = closes.length;
  const kp = validatePeriod(kPeriod, 'kPeriod');
  const dp = validatePeriod(dPeriod, 'dPeriod');
  const sk = validatePeriod(smoothK, 'smoothK');
  if (n === 0) return { k: [], d: [] };
  const kRaw: (number | null)[] = [];
  for (let i = 0; i < n; i++) {
    if (i + 1 < kp) { kRaw.push(null); continue; }
    const start = i + 1 - kp;
    const hh = Math.max(...highs.slice(start, i + 1));
    const ll = Math.min(...lows.slice(start, i + 1));
    kRaw.push(hh === ll ? 50 : (closes[i] - ll) / (hh - ll) * 100);
  }
  const kValid = kRaw.filter((v): v is number => v !== null);
  const kSmoothedRaw = computeSMA(kValid, sk);
  const kSmoothed: (number | null)[] = [];
  let ki = 0;
  for (const v of kRaw) {
    if (v === null) { kSmoothed.push(null); } else {
      kSmoothed.push(ki < kSmoothedRaw.length ? kSmoothedRaw[ki] : null); ki++;
    }
  }
  const kValidSmoothed = kSmoothed.filter((v): v is number => v !== null);
  const dRaw = computeSMA(kValidSmoothed, dp);
  const d: (number | null)[] = [];
  let di = 0;
  for (const v of kSmoothed) {
    if (v === null) { d.push(null); } else {
      d.push(di < dRaw.length ? dRaw[di] : null); di++;
    }
  }
  return { k: kSmoothed, d };
}

export function computeAdxDmi(
  highs: number[], lows: number[], closes: number[], period = 14
): { plusDi: (number | null)[]; minusDi: (number | null)[]; adx: (number | null)[] } {
  validateArray(highs, 'highs'); validateArray(lows, 'lows'); validateArray(closes, 'closes');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  const p = validatePeriod(period, 'period');
  const n = closes.length;
  if (n < 2) {
    return { plusDi: Array(n).fill(null), minusDi: Array(n).fill(null), adx: Array(n).fill(null) };
  }
  const trList: number[] = [highs[0] - lows[0]];
  const plusDm: number[] = [0];
  const minusDm: number[] = [0];
  for (let i = 1; i < n; i++) {
    trList.push(Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1])));
    const up = highs[i] - highs[i - 1];
    const down = lows[i - 1] - lows[i];
    plusDm.push(up > down && up > 0 ? up : 0);
    minusDm.push(down > up && down > 0 ? down : 0);
  }
  const atrVals = computeEMA(trList, p);
  const plusDmEma = computeEMA(plusDm, p);
  const minusDmEma = computeEMA(minusDm, p);
  const plusDi: (number | null)[] = [];
  const minusDi: (number | null)[] = [];
  const dxList: (number | null)[] = [];
  for (let i = 0; i < n; i++) {
    const a = atrVals[i]; const pdm = plusDmEma[i]; const mdm = minusDmEma[i];
    if (a === null || a === 0 || pdm === null || mdm === null) {
      plusDi.push(null); minusDi.push(null); dxList.push(null);
    } else {
      const pdi = 100 * pdm / a; const mdi = 100 * mdm / a;
      plusDi.push(pdi); minusDi.push(mdi);
      const denom = pdi + mdi;
      dxList.push(denom === 0 ? 0 : 100 * Math.abs(pdi - mdi) / denom);
    }
  }
  const dxValid = dxList.filter((v): v is number => v !== null);
  const adxRaw = computeEMA(dxValid, p);
  const adx: (number | null)[] = [];
  let ai = 0;
  for (const v of dxList) {
    if (v === null) { adx.push(null); } else {
      adx.push(ai < adxRaw.length ? adxRaw[ai] : null); ai++;
    }
  }
  return { plusDi, minusDi, adx };
}

export function computeCCI(
  highs: number[], lows: number[], closes: number[], period = 20
): (number | null)[] {
  validateArray(highs, 'highs'); validateArray(lows, 'lows'); validateArray(closes, 'closes');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  const p = validatePeriod(period, 'period');
  const n = closes.length;
  const tp = highs.map((h, i) => (h + lows[i] + closes[i]) / 3);
  const tpSma = computeSMA(tp, p);
  const result: (number | null)[] = [];
  for (let i = 0; i < n; i++) {
    if (tpSma[i] === null) { result.push(null); continue; }
    const start = i + 1 - p;
    const segment = tp.slice(start, i + 1);
    const meanDev = segment.reduce((s, x) => s + Math.abs(x - tpSma[i]!), 0) / p;
    result.push(meanDev === 0 ? 0 : (tp[i] - tpSma[i]!) / (0.015 * meanDev));
  }
  return result;
}

export function computeROC(values: number[], period = 12): (number | null)[] {
  validateArray(values, 'values');
  const p = validatePeriod(period, 'period');
  return values.map((v, i) =>
    i < p || values[i - p] === 0 || !isFinite(v) ? null : (v - values[i - p]) / values[i - p] * 100
  );
}

export function computeWilliamsR(
  highs: number[], lows: number[], closes: number[], period = 14
): (number | null)[] {
  validateArray(highs, 'highs'); validateArray(lows, 'lows'); validateArray(closes, 'closes');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  const p = validatePeriod(period, 'period');
  const n = closes.length;
  const result: (number | null)[] = [];
  for (let i = 0; i < n; i++) {
    if (i + 1 < p) { result.push(null); continue; }
    const start = i + 1 - p;
    const hh = Math.max(...highs.slice(start, i + 1));
    const ll = Math.min(...lows.slice(start, i + 1));
    result.push(hh === ll ? -50 : (hh - closes[i]) / (hh - ll) * -100);
  }
  return result;
}

export function computeOBV(closes: number[], volumes: number[]): number[] {
  validateArray(closes, 'closes');
  validateArray(volumes, 'volumes');
  if (closes.length !== volumes.length) throw new Error('Array length mismatch');
  if (closes.length === 0) return [];
  const result = [0];
  for (let i = 1; i < closes.length; i++) {
    const prev = result[result.length - 1];
    if (closes[i] > closes[i - 1]) result.push(prev + volumes[i]);
    else if (closes[i] < closes[i - 1]) result.push(prev - volumes[i]);
    else result.push(prev);
  }
  return result;
}

export function computeVWAP(
  highs: number[], lows: number[], closes: number[], volumes: number[]
): (number | null)[] {
  validateArray(highs, 'highs'); validateArray(lows, 'lows');
  validateArray(closes, 'closes'); validateArray(volumes, 'volumes');
  if (highs.length !== lows.length || highs.length !== closes.length || highs.length !== volumes.length)
    throw new Error('Array length mismatch');
  const n = closes.length;
  const result: (number | null)[] = [];
  let cumTpVol = 0, cumVol = 0;
  for (let i = 0; i < n; i++) {
    const tp = (highs[i] + lows[i] + closes[i]) / 3;
    cumTpVol += tp * volumes[i];
    cumVol += volumes[i];
    result.push(cumVol === 0 ? null : cumTpVol / cumVol);
  }
  return result;
}

export function computeMFI(
  highs: number[], lows: number[], closes: number[], volumes: number[], period = 14
): (number | null)[] {
  validateArray(highs, 'highs'); validateArray(lows, 'lows');
  validateArray(closes, 'closes'); validateArray(volumes, 'volumes');
  if (highs.length !== lows.length || highs.length !== closes.length || highs.length !== volumes.length)
    throw new Error('Array length mismatch');
  const p = validatePeriod(period, 'period');
  const n = closes.length;
  const tp = highs.map((h, i) => (h + lows[i] + closes[i]) / 3);
  const mf = tp.map((t, i) => t * volumes[i]);
  const result: (number | null)[] = [];
  for (let i = 0; i < n; i++) {
    if (i < p) { result.push(null); continue; }
    const start = i + 1 - p;
    let posMf = 0, negMf = 0;
    for (let j = start + 1; j <= i; j++) {
      if (tp[j] > tp[j - 1]) posMf += mf[j];
      else if (tp[j] < tp[j - 1]) negMf += mf[j];
    }
    result.push(negMf === 0 ? 100 : 100 - 100 / (1 + posMf / negMf));
  }
  return result;
}

export function computeIchimoku(
  highs: number[], lows: number[], closes: number[],
  tenkanP = 9, kijunP = 26, senkouBP = 52
): {
  tenkanSen: (number | null)[]; kijunSen: (number | null)[];
  senkouA: (number | null)[]; senkouB: (number | null)[]; chikou: (number | null)[];
} {
  validateArray(highs, 'highs'); validateArray(lows, 'lows'); validateArray(closes, 'closes');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  const tp = validatePeriod(tenkanP, 'tenkanP');
  const kp = validatePeriod(kijunP, 'kijunP');
  const sbp = validatePeriod(senkouBP, 'senkouBP');
  const tenkanMax = computeRollingMax(highs, tp);
  const tenkanMin = computeRollingMin(lows, tp);
  const tenkanSen = tenkanMax.map((mx, i) =>
    mx !== null && tenkanMin[i] !== null ? (mx + tenkanMin[i]) / 2 : null
  );
  const kijunMax = computeRollingMax(highs, kp);
  const kijunMin = computeRollingMin(lows, kp);
  const kijunSen = kijunMax.map((mx, i) =>
    mx !== null && kijunMin[i] !== null ? (mx + kijunMin[i]) / 2 : null
  );
  const senkouA = tenkanSen.map((t, i) =>
    t !== null && kijunSen[i] !== null ? (t + kijunSen[i]!) / 2 : null
  );
  const senkouBMax = computeRollingMax(highs, sbp);
  const senkouBMin = computeRollingMin(lows, sbp);
  const senkouB = senkouBMax.map((mx, i) =>
    mx !== null && senkouBMin[i] !== null ? (mx + senkouBMin[i]) / 2 : null
  );
  const chikou: (number | null)[] = new Array(closes.length).fill(null);
  for (let i = 0; i < closes.length; i++) {
    const target = i - kp;
    if (target >= 0) chikou[target] = closes[i];
  }
  return { tenkanSen, kijunSen, senkouA, senkouB, chikou };
}

export function computePivotPoints(
  highs: number[], lows: number[], closes: number[]
): { pivot: (number | null)[]; r1: (number | null)[]; r2: (number | null)[]; r3: (number | null)[];
  s1: (number | null)[]; s2: (number | null)[]; s3: (number | null)[] } {
  validateArray(highs, 'highs'); validateArray(lows, 'lows'); validateArray(closes, 'closes');
  if (highs.length !== lows.length || highs.length !== closes.length) throw new Error('Array length mismatch');
  const n = closes.length;
  const pivot: (number | null)[] = [null];
  const r1: (number | null)[] = [null]; const r2: (number | null)[] = [null];
  const r3: (number | null)[] = [null]; const s1: (number | null)[] = [null];
  const s2: (number | null)[] = [null]; const s3: (number | null)[] = [null];
  for (let i = 1; i < n; i++) {
    const h = highs[i - 1]; const l = lows[i - 1]; const c = closes[i - 1];
    const p = (h + l + c) / 3;
    pivot.push(p); r1.push(2 * p - l); r2.push(p + (h - l));
    r3.push(h + 2 * (p - l)); s1.push(2 * p - h);
    s2.push(p - (h - l)); s3.push(l - 2 * (h - p));
  }
  return { pivot, r1, r2, r3, s1, s2, s3 };
}

export function computeFibonacci(
  high: number, low: number, levels?: number[]
): Record<number, number> {
  if (!levels) levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
  if (high < low) [high, low] = [low, high];
  const diff = high - low;
  const result: Record<number, number> = {};
  for (const level of levels) {
    result[level] = high - diff * level;
  }
  return result;
}

export function computeAllIndicators(
  bars: OHLCBar[],
  enabled?: Set<string>,
  params?: Record<string, Record<string, number>>
): IndicatorSeries[] {
  const closes = bars.map(b => b.close);
  const highs = bars.map(b => b.high);
  const lows = bars.map(b => b.low);
  const volumes = bars.map(b => b.volume);
  const times = bars.map(b => b.time);
  const series: IndicatorSeries[] = [];
  const on = (id: string) => !enabled || enabled.has(id);
  const p = (id: string) => params?.[id] ?? {};

  const addSeries = (name: string, values: (number | null)[], seriesParams: Record<string, number | string> = {}) => {
    series.push({
      name,
      parameters: seriesParams,
      points: values.map((v, i) => v !== null ? { time: times[i], value: v } : null).filter((pt): pt is { time: string; value: number } => pt !== null),
    });
  };

  if (on('sma')) {
    const period = p('sma').period ?? 20;
    addSeries('sma_20', computeSMA(closes, period), { period });
    addSeries('sma_50', computeSMA(closes, 50), { period: 50 });
  }
  if (on('ema')) {
    const period = p('ema').period ?? 12;
    addSeries('ema_12', computeEMA(closes, period), { period });
    addSeries('ema_26', computeEMA(closes, 26), { period: 26 });
  }
  if (on('adx')) {
    const period = p('adx').period ?? 14;
    const adx = computeAdxDmi(highs, lows, closes, period);
    addSeries('adx_plus_di', adx.plusDi, { period });
    addSeries('adx_minus_di', adx.minusDi, { period });
    addSeries('adx_line', adx.adx, { period });
  }
  if (on('ichimoku')) {
    const tenkan = p('ichimoku').tenkan ?? 9;
    const kijun = p('ichimoku').kijun ?? 26;
    const senkouB = p('ichimoku').senkouB ?? 52;
    const ich = computeIchimoku(highs, lows, closes, tenkan, kijun, senkouB);
    addSeries('ichimoku_tenkan', ich.tenkanSen, { tenkan, kijun, senkouB });
    addSeries('ichimoku_kijun', ich.kijunSen);
    addSeries('ichimoku_senkou_a', ich.senkouA);
    addSeries('ichimoku_senkou_b', ich.senkouB);
  }
  if (on('rsi')) {
    const period = p('rsi').period ?? 14;
    addSeries('rsi_14', computeRSI(closes, period), { period });
  }
  if (on('macd')) {
    const fast = p('macd').fast ?? 12;
    const slow = p('macd').slow ?? 26;
    const signal = p('macd').signal ?? 9;
    const macd = computeMACD(closes, fast, slow, signal);
    addSeries('macd_line', macd.macdLine, { fast, slow, signal });
    addSeries('macd_signal', macd.signalLine);
    addSeries('macd_histogram', macd.histogram);
  }
  if (on('stochastic')) {
    const kPeriod = p('stochastic').kPeriod ?? 14;
    const dPeriod = p('stochastic').dPeriod ?? 3;
    const smoothK = p('stochastic').smoothK ?? 3;
    const stoch = computeStochastic(highs, lows, closes, kPeriod, dPeriod, smoothK);
    addSeries('stoch_k', stoch.k, { kPeriod, dPeriod, smoothK });
    addSeries('stoch_d', stoch.d);
  }
  if (on('cci')) {
    const period = p('cci').period ?? 20;
    addSeries('cci_20', computeCCI(highs, lows, closes, period), { period });
  }
  if (on('roc')) {
    const period = p('roc').period ?? 12;
    addSeries('roc_12', computeROC(closes, period), { period });
  }
  if (on('williamsr')) {
    const period = p('williamsr').period ?? 14;
    addSeries('williamsr_14', computeWilliamsR(highs, lows, closes, period), { period });
  }
  if (on('bb')) {
    const period = p('bb').period ?? 20;
    const stdDev = p('bb').stdDev ?? 2;
    const bb = computeBollinger(closes, period, stdDev);
    addSeries('bb_upper', bb.upper, { period, stdDev });
    addSeries('bb_middle', bb.middle);
    addSeries('bb_lower', bb.lower);
  }
  if (on('atr')) {
    const period = p('atr').period ?? 14;
    addSeries('atr_14', computeATR(highs, lows, closes, period), { period });
  }
  if (on('obv')) {
    addSeries('obv', computeOBV(closes, volumes));
  }
  if (on('vwap')) {
    addSeries('vwap', computeVWAP(highs, lows, closes, volumes));
  }
  if (on('mfi')) {
    const period = p('mfi').period ?? 14;
    addSeries('mfi_14', computeMFI(highs, lows, closes, volumes, period), { period });
  }
  if (on('pivot')) {
    const piv = computePivotPoints(highs, lows, closes);
    addSeries('pivot_pp', piv.pivot);
    addSeries('pivot_r1', piv.r1);
    addSeries('pivot_r2', piv.r2);
    addSeries('pivot_r3', piv.r3);
    addSeries('pivot_s1', piv.s1);
    addSeries('pivot_s2', piv.s2);
    addSeries('pivot_s3', piv.s3);
  }
  if (on('fib')) {
    const fibLevels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
    const levelNames = ['0', '23.6', '38.2', '50', '61.8', '78.6', '100'];
    const fibHigh = Math.max(...highs);
    const fibLow = Math.min(...lows);
    const fibValues = computeFibonacci(fibHigh, fibLow, fibLevels);
    const fibPoint = { time: times[times.length - 1], value: fibHigh };
    for (let i = 0; i < fibLevels.length; i++) {
      const level = fibLevels[i];
      const label = levelNames[i];
      const price = fibValues[level];
      series.push({
        name: `fib_${label}`,
        parameters: { level, price, high: fibHigh, low: fibLow },
        points: [{ time: fibPoint.time, value: price }],
      });
    }
  }

  return series;
}

export type IndicatorGroup = 'TREND' | 'MOMENTUM' | 'VOLATILITY' | 'VOLUME' | 'LEVELS';

export interface IndicatorDef {
  id: string;
  name: string;
  group: IndicatorGroup;
  overlay: boolean;
  displayType: IndicatorDisplayType;
  minDataLength: number;
  params: IndicatorParamDef[];
  subSeries: string[];
}

export type { IndicatorParamDef };

export interface IndicatorConfig {
  id: string;
  name: string;
  group: string;
  overlay: boolean;
  displayType: 'overlay' | 'oscillator';
  params: IndicatorParamDef[];
  subSeries: string[];
}

export const INDICATOR_GROUPS: IndicatorDef[] = [
  { id: 'sma', name: 'SMA', group: 'TREND', overlay: true, displayType: 'overlay', minDataLength: 20,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 20, min: 2, max: 200, step: 1 }],
    subSeries: ['sma_20', 'sma_50'] },
  { id: 'ema', name: 'EMA', group: 'TREND', overlay: true, displayType: 'overlay', minDataLength: 26,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 12, min: 2, max: 200, step: 1 }],
    subSeries: ['ema_12', 'ema_26'] },
  { id: 'adx', name: 'ADX/DMI', group: 'TREND', overlay: false, displayType: 'oscillator', minDataLength: 28,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['adx_plus_di', 'adx_minus_di', 'adx_line'] },
  { id: 'ichimoku', name: 'Ichimoku', group: 'TREND', overlay: true, displayType: 'overlay', minDataLength: 52,
    params: [
      { id: 'tenkan', label: 'Tenkan', type: 'number', default: 9, min: 2, max: 100, step: 1 },
      { id: 'kijun', label: 'Kijun', type: 'number', default: 26, min: 2, max: 200, step: 1 },
      { id: 'senkouB', label: 'Senkou B', type: 'number', default: 52, min: 2, max: 200, step: 1 },
    ],
    subSeries: ['ichimoku_tenkan', 'ichimoku_kijun', 'ichimoku_senkou_a', 'ichimoku_senkou_b'] },
  { id: 'rsi', name: 'RSI', group: 'MOMENTUM', overlay: false, displayType: 'oscillator', minDataLength: 15,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['rsi_14'] },
  { id: 'macd', name: 'MACD', group: 'MOMENTUM', overlay: false, displayType: 'oscillator', minDataLength: 35,
    params: [
      { id: 'fast', label: 'Fast', type: 'number', default: 12, min: 2, max: 100, step: 1 },
      { id: 'slow', label: 'Slow', type: 'number', default: 26, min: 2, max: 200, step: 1 },
      { id: 'signal', label: 'Signal', type: 'number', default: 9, min: 2, max: 100, step: 1 },
    ],
    subSeries: ['macd_line', 'macd_signal', 'macd_histogram'] },
  { id: 'stochastic', name: 'Stochastic', group: 'MOMENTUM', overlay: false, displayType: 'oscillator', minDataLength: 17,
    params: [
      { id: 'kPeriod', label: '%K', type: 'number', default: 14, min: 2, max: 100, step: 1 },
      { id: 'dPeriod', label: '%D', type: 'number', default: 3, min: 2, max: 50, step: 1 },
      { id: 'smoothK', label: 'Smooth', type: 'number', default: 3, min: 1, max: 50, step: 1 },
    ],
    subSeries: ['stoch_k', 'stoch_d'] },
  { id: 'cci', name: 'CCI', group: 'MOMENTUM', overlay: false, displayType: 'oscillator', minDataLength: 20,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 20, min: 2, max: 100, step: 1 }],
    subSeries: ['cci_20'] },
  { id: 'roc', name: 'ROC', group: 'MOMENTUM', overlay: false, displayType: 'oscillator', minDataLength: 13,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 12, min: 1, max: 100, step: 1 }],
    subSeries: ['roc_12'] },
  { id: 'williamsr', name: 'Williams %R', group: 'MOMENTUM', overlay: false, displayType: 'oscillator', minDataLength: 14,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['williamsr_14'] },
  { id: 'bb', name: 'Bollinger', group: 'VOLATILITY', overlay: true, displayType: 'overlay', minDataLength: 20,
    params: [
      { id: 'period', label: 'Period', type: 'number', default: 20, min: 2, max: 200, step: 1 },
      { id: 'stdDev', label: 'Std Dev', type: 'number', default: 2, min: 0.5, max: 5, step: 0.5 },
    ],
    subSeries: ['bb_upper', 'bb_middle', 'bb_lower'] },
  { id: 'atr', name: 'ATR', group: 'VOLATILITY', overlay: false, displayType: 'oscillator', minDataLength: 14,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 1, max: 100, step: 1 }],
    subSeries: ['atr_14'] },
  { id: 'obv', name: 'OBV', group: 'VOLUME', overlay: false, displayType: 'oscillator', minDataLength: 2,
    params: [],
    subSeries: ['obv'] },
  { id: 'vwap', name: 'VWAP', group: 'VOLUME', overlay: true, displayType: 'overlay', minDataLength: 1,
    params: [],
    subSeries: ['vwap'] },
  { id: 'mfi', name: 'MFI', group: 'VOLUME', overlay: false, displayType: 'oscillator', minDataLength: 15,
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['mfi_14'] },
  { id: 'pivot', name: 'Pivot Points', group: 'LEVELS', overlay: true, displayType: 'overlay', minDataLength: 2,
    params: [],
    subSeries: ['pivot_pp', 'pivot_r1', 'pivot_r2', 'pivot_r3', 'pivot_s1', 'pivot_s2', 'pivot_s3'] },
  { id: 'fib', name: 'Fibonacci', group: 'LEVELS', overlay: true, displayType: 'overlay', minDataLength: 2,
    params: [],
    subSeries: ['fib_0', 'fib_23.6', 'fib_38.2', 'fib_50', 'fib_61.8', 'fib_78.6', 'fib_100'] },
];

export const INDICATOR_CONFIGS: IndicatorConfig[] = [
  {
    id: 'sma', name: 'SMA', group: 'TREND', overlay: true, displayType: 'overlay',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 20, min: 5, max: 200, step: 1 }],
    subSeries: ['sma_20', 'sma_50'],
  },
  {
    id: 'ema', name: 'EMA', group: 'TREND', overlay: true, displayType: 'overlay',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 12, min: 5, max: 200, step: 1 }],
    subSeries: ['ema_12', 'ema_26'],
  },
  {
    id: 'rsi', name: 'RSI', group: 'MOMENTUM', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['rsi_14'],
  },
  {
    id: 'macd', name: 'MACD', group: 'MOMENTUM', overlay: false, displayType: 'oscillator',
    params: [
      { id: 'fast', label: 'Fast', type: 'number', default: 12, min: 2, max: 50, step: 1 },
      { id: 'slow', label: 'Slow', type: 'number', default: 26, min: 5, max: 100, step: 1 },
      { id: 'signal', label: 'Signal', type: 'number', default: 9, min: 2, max: 50, step: 1 },
    ],
    subSeries: ['macd_line', 'macd_signal', 'macd_histogram'],
  },
  {
    id: 'bb', name: 'Bollinger', group: 'VOLATILITY', overlay: true, displayType: 'overlay',
    params: [
      { id: 'period', label: 'Period', type: 'number', default: 20, min: 5, max: 100, step: 1 },
      { id: 'stdDev', label: 'Std Dev', type: 'number', default: 2.0, min: 0.5, max: 5.0, step: 0.1 },
    ],
    subSeries: ['bb_upper', 'bb_middle', 'bb_lower'],
  },
  {
    id: 'atr', name: 'ATR', group: 'VOLATILITY', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['atr_14'],
  },
  {
    id: 'stochastic', name: 'Stochastic', group: 'MOMENTUM', overlay: false, displayType: 'oscillator',
    params: [
      { id: 'kPeriod', label: '%K', type: 'number', default: 14, min: 2, max: 50, step: 1 },
      { id: 'dPeriod', label: '%D', type: 'number', default: 3, min: 2, max: 20, step: 1 },
      { id: 'smoothK', label: 'Smooth', type: 'number', default: 3, min: 1, max: 10, step: 1 },
    ],
    subSeries: ['stoch_k', 'stoch_d'],
  },
  {
    id: 'cci', name: 'CCI', group: 'MOMENTUM', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 20, min: 5, max: 100, step: 1 }],
    subSeries: ['cci_20'],
  },
  {
    id: 'roc', name: 'ROC', group: 'MOMENTUM', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 12, min: 2, max: 50, step: 1 }],
    subSeries: ['roc_12'],
  },
  {
    id: 'williamsr', name: 'Williams %R', group: 'MOMENTUM', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 100, step: 1 }],
    subSeries: ['williamsr_14'],
  },
  {
    id: 'adx', name: 'ADX/DMI', group: 'TREND', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 5, max: 50, step: 1 }],
    subSeries: ['adx_plus_di', 'adx_minus_di', 'adx_line'],
  },
  {
    id: 'obv', name: 'OBV', group: 'VOLUME', overlay: false, displayType: 'oscillator',
    params: [],
    subSeries: ['obv'],
  },
  {
    id: 'vwap', name: 'VWAP', group: 'VOLUME', overlay: true, displayType: 'overlay',
    params: [],
    subSeries: ['vwap'],
  },
  {
    id: 'mfi', name: 'MFI', group: 'VOLUME', overlay: false, displayType: 'oscillator',
    params: [{ id: 'period', label: 'Period', type: 'number', default: 14, min: 2, max: 50, step: 1 }],
    subSeries: ['mfi_14'],
  },
  {
    id: 'ichimoku', name: 'Ichimoku', group: 'TREND', overlay: true, displayType: 'overlay',
    params: [
      { id: 'tenkan', label: 'Tenkan', type: 'number', default: 9, min: 5, max: 50, step: 1 },
      { id: 'kijun', label: 'Kijun', type: 'number', default: 10, min: 10, max: 100, step: 1 },
      { id: 'senkouB', label: 'Senkou B', type: 'number', default: 52, min: 20, max: 200, step: 1 },
    ],
    subSeries: ['ichimoku_tenkan', 'ichimoku_kijun', 'ichimoku_senkou_a', 'ichimoku_senkou_b'],
  },
  {
    id: 'pivot', name: 'Pivot Points', group: 'LEVELS', overlay: true, displayType: 'overlay',
    params: [],
    subSeries: ['pivot_pp', 'pivot_r1', 'pivot_r2', 'pivot_r3', 'pivot_s1', 'pivot_s2', 'pivot_s3'],
  },
  {
    id: 'fib', name: 'Fibonacci', group: 'LEVELS', overlay: true, displayType: 'overlay',
    params: [],
    subSeries: ['fib_0', 'fib_23.6', 'fib_38.2', 'fib_50', 'fib_61.8', 'fib_78.6', 'fib_100'],
  },
];

export function getAnalysisMetrics(bars: OHLCBar[]): AnalysisMetrics {
  const closes = bars.map(b => b.close);
  const highs = bars.map(b => b.high);
  const lows = bars.map(b => b.low);
  const last = closes[closes.length - 1];

  const rsi = computeRSI(closes, 14);
  const macd = computeMACD(closes);
  const atr = computeATR(highs, lows, closes, 14);
  const sma20 = computeSMA(closes, 20);
  const ema12 = computeEMA(closes, 12);
  const bb = computeBollinger(closes);

  const lastRsi = rsi.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastMacdLine = macd.macdLine.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastMacdSignal = macd.signalLine.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastMacdHist = macd.histogram.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastAtr = atr.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastSma20 = sma20.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastEma12 = ema12.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastBbUpper = bb.upper.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastBbMiddle = bb.middle.filter((v): v is number => v !== null).slice(-1)[0] ?? null;
  const lastBbLower = bb.lower.filter((v): v is number => v !== null).slice(-1)[0] ?? null;

  let trendState = 'Neutral';
  if (lastSma20 && last > lastSma20) trendState = 'Bullish';
  else if (lastSma20 && last < lastSma20) trendState = 'Bearish';

  let volatilityState = 'Normal';
  if (lastAtr && lastSma20) {
    const atrPct = lastAtr / lastSma20;
    if (atrPct > 0.03) volatilityState = 'High';
    else if (atrPct < 0.01) volatilityState = 'Low';
  }

  return {
    rsi: lastRsi, macdLine: lastMacdLine, macdSignal: lastMacdSignal, macdHistogram: lastMacdHist,
    atr: lastAtr, sma20: lastSma20, ema12: lastEma12,
    bbUpper: lastBbUpper, bbMiddle: lastBbMiddle, bbLower: lastBbLower,
    trendState, volatilityState, dataSource: 'DEMO',
  };
}

export function getAssetForSymbol(symbol: string): Asset | undefined {
  return ASSETS_IMPORT.find(a => a.symbol === symbol);
}

export function getFibonacciValues(
  bars: OHLCBar[]
): { high: number; low: number; levels: Record<number, number> } | null {
  if (bars.length < 2) return null;
  const high = Math.max(...bars.map(b => b.high));
  const low = Math.min(...bars.map(b => b.low));
  if (high === low) return null;
  return { high, low, levels: computeFibonacci(high, low) };
}

const ASSETS_IMPORT = [
  { symbol: 'BTC-USD', name: 'Bitcoin', category: 'crypto' as const, exchange: 'NASDAQ', tickerYahoo: 'BTC-USD', defaultTimeframe: '1D' as const, description: 'Bitcoin vs US Dollar', decimals: 2 },
  { symbol: 'ETH-USD', name: 'Ethereum', category: 'crypto' as const, exchange: 'NASDAQ', tickerYahoo: 'ETH-USD', defaultTimeframe: '1D' as const, description: 'Ethereum vs US Dollar', decimals: 2 },
  { symbol: 'GOLD', name: 'Gold', category: 'commodity' as const, exchange: 'COMEX', tickerYahoo: 'GC=F', defaultTimeframe: '1D' as const, description: 'Gold Futures', decimals: 2 },
  { symbol: 'SILVER', name: 'Silver', category: 'commodity' as const, exchange: 'COMEX', tickerYahoo: 'SI=F', defaultTimeframe: '1D' as const, description: 'Silver Futures', decimals: 3 },
  { symbol: 'SPY', name: 'S&P 500 ETF', category: 'etf' as const, exchange: 'NYSE', tickerYahoo: 'SPY', defaultTimeframe: '1D' as const, description: 'SPDR S&P 500 ETF Trust', decimals: 2 },
  { symbol: 'QQQ', name: 'Nasdaq 100 ETF', category: 'etf' as const, exchange: 'NASDAQ', tickerYahoo: 'QQQ', defaultTimeframe: '1D' as const, description: 'Invesco QQQ Trust', decimals: 2 },
  { symbol: 'NIFTY', name: 'Nifty 50', category: 'equity_index' as const, exchange: 'NSE', tickerYahoo: '^NSEI', defaultTimeframe: '1D' as const, description: 'NSE Nifty 50 Index', decimals: 2 },
  { symbol: 'NASDAQ', name: 'NASDAQ Composite', category: 'equity_index' as const, exchange: 'NASDAQ', tickerYahoo: '^IXIC', defaultTimeframe: '1D' as const, description: 'NASDAQ Composite Index', decimals: 2 },
  { symbol: 'EURUSD', name: 'Euro/US Dollar', category: 'forex' as const, exchange: 'FOREX', tickerYahoo: 'EURUSD=X', defaultTimeframe: '1D' as const, description: 'EUR/USD Exchange Rate', decimals: 5 },
  { symbol: 'USDJPY', name: 'US Dollar/Japanese Yen', category: 'forex' as const, exchange: 'FOREX', tickerYahoo: 'JPY=X', defaultTimeframe: '1D' as const, description: 'USD/JPY Exchange Rate', decimals: 3 },
];
