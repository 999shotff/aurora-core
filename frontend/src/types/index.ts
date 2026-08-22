export type Timeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1D' | '1W';

export type AssetCategory = 'crypto' | 'commodity' | 'equity_index' | 'forex' | 'etf';

export interface Asset {
  symbol: string;
  name: string;
  category: AssetCategory;
  exchange: string;
  tickerYahoo: string;
  defaultTimeframe: Timeframe;
  description: string;
  decimals: number;
}

export interface OHLCBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string;
  value: number;
}

export interface IndicatorSeries {
  name: string;
  parameters: Record<string, number | string>;
  points: IndicatorPoint[];
}

export interface ChartData {
  bars: OHLCBar[];
  overlays: IndicatorSeries[];
  panels: IndicatorSeries[];
}

export interface WatchlistItem {
  symbol: string;
  name: string;
  lastPrice: number | null;
  change: number | null;
  changePct: number | null;
  volume: number | null;
}

export interface IndicatorParamDef {
  id: string;
  label: string;
  type: 'number';
  default: number;
  min: number;
  max: number;
  step: number;
}

export type IndicatorOutputType = 'line' | 'histogram' | 'area';
export type IndicatorDisplayType = 'overlay' | 'oscillator';

export interface AnalysisMetrics {
  rsi: number | null;
  macdLine: number | null;
  macdSignal: number | null;
  macdHistogram: number | null;
  atr: number | null;
  sma20: number | null;
  ema12: number | null;
  bbUpper: number | null;
  bbMiddle: number | null;
  bbLower: number | null;
  trendState: string;
  volatilityState: string;
  dataSource: string;
}

export const TIMEFRAMES: Timeframe[] = ['1m', '5m', '15m', '30m', '1h', '4h', '1D', '1W'];

export const ASSETS: Asset[] = [
  { symbol: 'BTC-USD', name: 'Bitcoin', category: 'crypto', exchange: 'NASDAQ', tickerYahoo: 'BTC-USD', defaultTimeframe: '1D', description: 'Bitcoin vs US Dollar', decimals: 2 },
  { symbol: 'ETH-USD', name: 'Ethereum', category: 'crypto', exchange: 'NASDAQ', tickerYahoo: 'ETH-USD', defaultTimeframe: '1D', description: 'Ethereum vs US Dollar', decimals: 2 },
  { symbol: 'GOLD', name: 'Gold', category: 'commodity', exchange: 'COMEX', tickerYahoo: 'GC=F', defaultTimeframe: '1D', description: 'Gold Futures', decimals: 2 },
  { symbol: 'SILVER', name: 'Silver', category: 'commodity', exchange: 'COMEX', tickerYahoo: 'SI=F', defaultTimeframe: '1D', description: 'Silver Futures', decimals: 3 },
  { symbol: 'SPY', name: 'S&P 500 ETF', category: 'etf', exchange: 'NYSE', tickerYahoo: 'SPY', defaultTimeframe: '1D', description: 'SPDR S&P 500 ETF Trust', decimals: 2 },
  { symbol: 'QQQ', name: 'Nasdaq 100 ETF', category: 'etf', exchange: 'NASDAQ', tickerYahoo: 'QQQ', defaultTimeframe: '1D', description: 'Invesco QQQ Trust', decimals: 2 },
  { symbol: 'NIFTY', name: 'Nifty 50', category: 'equity_index', exchange: 'NSE', tickerYahoo: '^NSEI', defaultTimeframe: '1D', description: 'NSE Nifty 50 Index', decimals: 2 },
  { symbol: 'NASDAQ', name: 'NASDAQ Composite', category: 'equity_index', exchange: 'NASDAQ', tickerYahoo: '^IXIC', defaultTimeframe: '1D', description: 'NASDAQ Composite Index', decimals: 2 },
  { symbol: 'EURUSD', name: 'Euro/US Dollar', category: 'forex', exchange: 'FOREX', tickerYahoo: 'EURUSD=X', defaultTimeframe: '1D', description: 'EUR/USD Exchange Rate', decimals: 5 },
  { symbol: 'USDJPY', name: 'US Dollar/Japanese Yen', category: 'forex', exchange: 'FOREX', tickerYahoo: 'JPY=X', defaultTimeframe: '1D', description: 'USD/JPY Exchange Rate', decimals: 3 },
];
