import { OHLCBar, IndicatorSeries, Asset, Timeframe, AnalysisMetrics } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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

async function checkBackend(): Promise<boolean> {
  if (_backendAvailable !== null) return _backendAvailable;
  try {
    const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    _backendAvailable = resp.ok;
  } catch {
    _backendAvailable = false;
  }
  return _backendAvailable;
}

export async function fetchOHLCFromBackend(
  symbol: string,
  timeframe: Timeframe,
  limit: number = 200
): Promise<{ bars: OHLCBar[]; isDemo: boolean; provider: string; stale: boolean } | null> {
  const available = await checkBackend();
  if (!available) return null;
  try {
    const tf = timeframe.toLowerCase();
    const resp = await fetch(`${API_BASE}/market/${symbol}/ohlc?timeframe=${tf}&limit=${limit}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!resp.ok) return null;
    const data: BackendOHLCResponse = await resp.json();
    return {
      bars: data.bars.map(b => ({
        time: b.timestamp.split('T')[0],
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
        volume: b.volume,
      })),
      isDemo: data.provenance?.is_demo ?? true,
      provider: data.provenance?.provider ?? 'unknown',
      stale: (data.provenance as Record<string, unknown>)?.stale === true,
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
  timeframe: Timeframe,
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
  nBars: number = 200
): Promise<{ bars: OHLCBar[]; isDemo: boolean; provider: string; stale: boolean }> {
  const backendData = await fetchOHLCFromBackend(symbol, timeframe, nBars);
  if (backendData) {
    return backendData;
  }
  return {
    bars: generateMockOHLCV(symbol, timeframe, nBars),
    isDemo: true,
    provider: 'mock (local)',
    stale: false,
  };
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

export function computeSMA(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) { result.push(null); continue; }
    const slice = values.slice(i - period + 1, i + 1);
    result.push(round(slice.reduce((a, b) => a + b, 0) / period, 6));
  }
  return result;
}

export function computeEMA(values: number[], period: number): (number | null)[] {
  if (!values.length) return [];
  const result: (number | null)[] = new Array(period - 1).fill(null);
  const k = 2 / (period + 1);
  let ema = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result.push(round(ema, 6));
  for (let i = period; i < values.length; i++) {
    ema = values[i] * k + ema * (1 - k);
    result.push(round(ema, 6));
  }
  return result;
}

export function computeRSI(closes: number[], period: number = 14): (number | null)[] {
  if (closes.length < period + 1) return closes.map(() => null);
  const result: (number | null)[] = new Array(period).fill(null);
  const gains: number[] = [];
  const losses: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    gains.push(Math.max(change, 0));
    losses.push(Math.max(-change, 0));
  }
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result.push(avgLoss === 0 ? 100 : round(100 - 100 / (1 + avgGain / avgLoss), 2));
  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    result.push(avgLoss === 0 ? 100 : round(100 - 100 / (1 + avgGain / avgLoss), 2));
  }
  return result;
}

export function computeMACD(closes: number[], fast = 12, slow = 26, signal = 9) {
  const emaFast = computeEMA(closes, fast);
  const emaSlow = computeEMA(closes, slow);
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

export function computeBollinger(closes: number[], period = 20, numStd = 2) {
  const middle = computeSMA(closes, period);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (middle[i] === null) { upper.push(null); lower.push(null); continue; }
    const window = closes.slice(i - period + 1, i + 1);
    const std = Math.sqrt(window.reduce((s, x) => s + (x - (middle[i] as number)) ** 2, 0) / period);
    upper.push(round((middle[i] as number) + numStd * std, 6));
    lower.push(round((middle[i] as number) - numStd * std, 6));
  }
  return { upper, middle, lower };
}

export function computeATR(highs: number[], lows: number[], closes: number[], period = 14): (number | null)[] {
  if (closes.length < 2) return closes.map(() => null);
  const trValues: number[] = [highs[0] - lows[0]];
  for (let i = 1; i < closes.length; i++) {
    trValues.push(Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1])));
  }
  return computeSMA(trValues, period);
}

export function computeAllIndicators(bars: OHLCBar[]): IndicatorSeries[] {
  const closes = bars.map(b => b.close);
  const highs = bars.map(b => b.high);
  const lows = bars.map(b => b.low);
  const times = bars.map(b => b.time);
  const series: IndicatorSeries[] = [];

  const addSeries = (name: string, values: (number | null)[]) => {
    series.push({
      name,
      parameters: {},
      points: values.map((v, i) => v !== null ? { time: times[i], value: v } : null).filter((p): p is { time: string; value: number } => p !== null),
    });
  };

  addSeries('sma_20', computeSMA(closes, 20));
  addSeries('ema_12', computeEMA(closes, 12));
  addSeries('rsi_14', computeRSI(closes, 14));
  addSeries('atr_14', computeATR(highs, lows, closes, 14));

  const macd = computeMACD(closes);
  addSeries('macd_line', macd.macdLine);
  addSeries('macd_signal', macd.signalLine);
  addSeries('macd_histogram', macd.histogram);

  const bb = computeBollinger(closes);
  addSeries('bb_upper', bb.upper);
  addSeries('bb_middle', bb.middle);
  addSeries('bb_lower', bb.lower);

  return series;
}

export function getAnalysisMetrics(bars: OHLCBar[]): AnalysisMetrics {
  const closes = bars.map(b => b.close);
  const highs = bars.map(b => b.high);
  const lows = bars.map(b => b.low);
  const last = closes[closes.length - 1];
  const prev = closes[closes.length - 2] ?? last;

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
