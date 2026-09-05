import React, { useState, useCallback } from 'react';
import { API_BASE } from '../services/config';

type DatasetSymbol = 'BTC-USD' | 'SPY' | 'QQQ';
type Timeframe = 'daily' | '4h' | '1h' | '15m';
type Side = 'long' | 'short' | 'flat';

interface BacktestParams {
  symbol: DatasetSymbol;
  timeframe: Timeframe;
  startEquity: number;
  positionSize: number;
  costRate: number;
  slippageBps: number;
  strategyParams: Record<string, number>;
}

interface MetricsSummary {
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  net_pnl: number;
  total_costs: number;
  expectancy: number;
  kelly_fraction: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown_duration: number;
}

interface RiskSummary {
  max_drawdown: number;
  value_at_risk_95: number;
  conditional_var_95: number;
  volatility_annualized: number;
  tail_ratio: number;
  ulcer_index: number;
  pain_index: number;
}

interface BacktestResult {
  initial_equity: number;
  final_equity: number;
  net_return: number;
  total_trades: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_cost: number;
  net_pnl: number;
  metrics: MetricsSummary;
  risk: RiskSummary;
  equity_curve: number[];
  timestamps: string[];
  positions: Array<{
    entry_time: string;
    exit_time: string | null;
    side: string;
    pnl: number;
    pnl_pct: number;
    holding_periods: number;
  }>;
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#010409',
    color: '#c9d1d9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    lineHeight: 1.6,
  },
  container: { maxWidth: '1400px', margin: '0 auto', padding: '0 24px' },
  header: {
    position: 'sticky', top: 0, zIndex: 50,
    background: 'rgba(1, 4, 9, 0.85)', backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #21262d', padding: '16px 0',
  },
  headerInner: {
    maxWidth: '1400px', margin: '0 auto', padding: '0 24px',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  logo: { fontSize: '20px', fontWeight: 700, color: '#e6edf3', letterSpacing: '2px', textTransform: 'uppercase' as const },
  logoAccent: { color: '#26a69a' },
  headerTag: { fontSize: '13px', color: '#8b949e', padding: '4px 12px', border: '1px solid #21262d', borderRadius: '6px' },
  main: { padding: '32px 0', display: 'grid', gridTemplateColumns: '380px 1fr', gap: '24px' },
  panel: { background: 'rgba(13, 17, 23, 0.6)', border: '1px solid #21262d', borderRadius: '14px', padding: '24px' },
  panelTitle: { fontSize: '16px', fontWeight: 600, color: '#e6edf3', marginBottom: '20px' },
  field: { marginBottom: '16px' },
  label: { fontSize: '12px', fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '6px', display: 'block' },
  select: {
    width: '100%', padding: '10px 12px', borderRadius: '8px',
    border: '1px solid #30363d', background: '#0d1117', color: '#c9d1d9',
    fontSize: '14px', outline: 'none',
  },
  input: {
    width: '100%', padding: '10px 12px', borderRadius: '8px',
    border: '1px solid #30363d', background: '#0d1117', color: '#c9d1d9',
    fontSize: '14px', outline: 'none', boxSizing: 'border-box' as const,
  },
  button: {
    width: '100%', padding: '12px', borderRadius: '8px', border: 'none',
    background: '#238636', color: '#fff', fontSize: '14px', fontWeight: 600,
    cursor: 'pointer', marginTop: '8px',
  },
  buttonDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' },
  metricCard: { background: 'rgba(1, 4, 9, 0.6)', border: '1px solid #21262d', borderRadius: '10px', padding: '16px' },
  metricValue: { fontSize: '20px', fontWeight: 700, color: '#26a69a', marginBottom: '2px' },
  metricValueRed: { fontSize: '20px', fontWeight: 700, color: '#f85149', marginBottom: '2px' },
  metricLabel: { fontSize: '11px', color: '#8b949e' },
  sectionTitle: { fontSize: '14px', fontWeight: 600, color: '#e6edf3', marginBottom: '12px' },
  tableContainer: { overflowX: 'auto', marginTop: '12px' },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '12px' },
  th: { textAlign: 'left' as const, padding: '8px 10px', borderBottom: '1px solid #21262d', color: '#8b949e', fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' as const },
  td: { padding: '6px 10px', borderBottom: '1px solid rgba(33, 38, 45, 0.5)', color: '#c9d1d9' },
  slider: { width: '100%', accentColor: '#26a69a' },
  tabBar: { display: 'flex', gap: '8px', marginBottom: '20px' },
  tab: { padding: '8px 16px', borderRadius: '8px', border: '1px solid #21262d', background: 'transparent', color: '#8b949e', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  tabActive: { background: 'rgba(38, 166, 154, 0.15)', color: '#26a69a', border: '1px solid rgba(38, 166, 154, 0.4)' },
  placeholder: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', border: '2px dashed #21262d', borderRadius: '12px', color: '#484f58', fontSize: '14px' },
  backLink: { fontSize: '13px', color: '#58a6ff', textDecoration: 'none', cursor: 'pointer', marginBottom: '16px', display: 'inline-block' },
  paramRow: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' },
  paramLabel: { fontSize: '12px', color: '#8b949e', minWidth: '100px' },
  paramValue: { fontSize: '12px', color: '#c9d1d9', minWidth: '50px', textAlign: 'right' as const },
};

const DEFAULT_PARAMS: BacktestParams = {
  symbol: 'BTC-USD',
  timeframe: 'daily',
  startEquity: 100000,
  positionSize: 1.0,
  costRate: 0.001,
  slippageBps: 5,
  strategyParams: { rsi_period: 14, rsi_overbought: 70, rsi_oversold: 30 },
};

function fmt(v: number, d = 2): string {
  return v.toFixed(d);
}
function fmtPct(v: number): string {
  return (v * 100).toFixed(2) + '%';
}
function fmtUsd(v: number): string {
  return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function MetricCard({ label, value, red }: { label: string; value: string; red?: boolean }) {
  return (
    <div style={styles.metricCard}>
      <div style={red ? styles.metricValueRed : styles.metricValue}>{value}</div>
      <div style={styles.metricLabel}>{label}</div>
    </div>
  );
}

function EquityCurve({ curve, timestamps }: { curve: number[]; timestamps: string[] }) {
  if (curve.length < 2) return null;
  const min = Math.min(...curve);
  const max = Math.max(...curve);
  const range = max - min || 1;
  const w = 800;
  const h = 200;
  const points = curve.map((v, i) => {
    const x = (i / (curve.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(' ');
  return (
    <div style={{ marginTop: '12px' }}>
      <div style={{ ...styles.sectionTitle, marginBottom: '8px' }}>Equity Curve</div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: '200px', background: '#0d1117', borderRadius: '8px' }}>
        <polyline points={points} fill="none" stroke="#26a69a" strokeWidth="2" />
        {curve.length > 0 && (
          <>
            <text x="4" y="16" fill="#8b949e" fontSize="11">{fmtUsd(curve[0])}</text>
            <text x={w - 4} y="16" fill="#26a69a" fontSize="11" textAnchor="end">{fmtUsd(curve[curve.length - 1])}</text>
          </>
        )}
      </svg>
    </div>
  );
}

const ResearchWorkspace: React.FC = () => {
  const [params, setParams] = useState<BacktestParams>(DEFAULT_PARAMS);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'metrics' | 'trades' | 'risk'>('metrics');

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/api/v1/research/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: params.symbol,
          timeframe: params.timeframe,
          initial_equity: params.startEquity,
          position_size: params.positionSize,
          commission_rate: params.costRate,
          slippage_bps: params.slippageBps,
          strategy: 'rsi_reversal',
          strategy_params: params.strategyParams,
        }),
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }
      const data: BacktestResult = await resp.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [params]);

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <span style={styles.logo}>AURORA <span style={styles.logoAccent}>CORE</span></span>
          <span style={styles.headerTag}>Research Workspace</span>
        </div>
      </header>

      <main style={styles.container}>
        <a style={styles.backLink} href="/">← Back to Dashboard</a>

        <div style={styles.main}>
          <div>
            <div style={styles.panel}>
              <div style={styles.panelTitle}>Configuration</div>

              <div style={styles.field}>
                <label style={styles.label}>Symbol</label>
                <select
                  style={styles.select}
                  value={params.symbol}
                  onChange={(e) => setParams({ ...params, symbol: e.target.value as DatasetSymbol })}
                >
                  <option value="BTC-USD">BTC-USD</option>
                  <option value="SPY">SPY</option>
                  <option value="QQQ">QQQ</option>
                </select>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Timeframe</label>
                <select
                  style={styles.select}
                  value={params.timeframe}
                  onChange={(e) => setParams({ ...params, timeframe: e.target.value as Timeframe })}
                >
                  <option value="daily">Daily</option>
                  <option value="4h">4 Hour</option>
                  <option value="1h">1 Hour</option>
                  <option value="15m">15 Minute</option>
                </select>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Initial Equity</label>
                <input
                  style={styles.input}
                  type="number"
                  value={params.startEquity}
                  onChange={(e) => setParams({ ...params, startEquity: Number(e.target.value) })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Position Size ({fmtPct(params.positionSize)})</label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.1"
                  value={params.positionSize}
                  onChange={(e) => setParams({ ...params, positionSize: Number(e.target.value) })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Commission Rate ({fmtPct(params.costRate)})</label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="0.01"
                  step="0.0001"
                  value={params.costRate}
                  onChange={(e) => setParams({ ...params, costRate: Number(e.target.value) })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Slippage ({params.slippageBps} bps)</label>
                <input
                  style={styles.slider}
                  type="range"
                  min="0"
                  max="50"
                  step="1"
                  value={params.slippageBps}
                  onChange={(e) => setParams({ ...params, slippageBps: Number(e.target.value) })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>RSI Period</label>
                <input
                  style={styles.input}
                  type="number"
                  value={params.strategyParams.rsi_period}
                  onChange={(e) => setParams({
                    ...params,
                    strategyParams: { ...params.strategyParams, rsi_period: Number(e.target.value) },
                  })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>RSI Overbought</label>
                <input
                  style={styles.input}
                  type="number"
                  value={params.strategyParams.rsi_overbought}
                  onChange={(e) => setParams({
                    ...params,
                    strategyParams: { ...params.strategyParams, rsi_overbought: Number(e.target.value) },
                  })}
                />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>RSI Oversold</label>
                <input
                  style={styles.input}
                  type="number"
                  value={params.strategyParams.rsi_oversold}
                  onChange={(e) => setParams({
                    ...params,
                    strategyParams: { ...params.strategyParams, rsi_oversold: Number(e.target.value) },
                  })}
                />
              </div>

              <button
                style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
                onClick={runBacktest}
                disabled={loading}
              >
                {loading ? 'Running...' : 'Run Backtest'}
              </button>

              {error && (
                <div style={{ color: '#f85149', fontSize: '13px', marginTop: '12px' }}>{error}</div>
              )}
            </div>
          </div>

          <div>
            {!result && !loading && (
              <div style={styles.placeholder}>Configure parameters and run a backtest</div>
            )}

            {loading && (
              <div style={styles.placeholder}>Running backtest...</div>
            )}

            {result && (
              <>
                <div style={styles.metricGrid}>
                  <MetricCard label="Net Return" value={fmtPct(result.net_return)} red={result.net_return < 0} />
                  <MetricCard label="Sharpe Ratio" value={fmt(result.sharpe_ratio)} red={result.sharpe_ratio < 0} />
                  <MetricCard label="Max Drawdown" value={fmtPct(result.max_drawdown)} red />
                  <MetricCard label="Total Trades" value={String(result.total_trades)} />
                  <MetricCard label="Win Rate" value={fmtPct(result.win_rate)} />
                  <MetricCard label="Net P&L" value={fmtUsd(result.net_pnl)} red={result.net_pnl < 0} />
                </div>

                <div style={styles.panel}>
                  <div style={styles.tabBar}>
                    <button
                      style={{ ...styles.tab, ...(activeTab === 'metrics' ? styles.tabActive : {}) }}
                      onClick={() => setActiveTab('metrics')}
                    >Performance</button>
                    <button
                      style={{ ...styles.tab, ...(activeTab === 'trades' ? styles.tabActive : {}) }}
                      onClick={() => setActiveTab('trades')}
                    >Trades ({result.positions.length})</button>
                    <button
                      style={{ ...styles.tab, ...(activeTab === 'risk' ? styles.tabActive : {}) }}
                      onClick={() => setActiveTab('risk')}
                    >Risk</button>
                  </div>

                  {activeTab === 'metrics' && result.metrics && (
                    <div style={styles.metricGrid}>
                      <MetricCard label="Annualized Return" value={fmtPct(result.metrics.annualized_return)} red={result.metrics.annualized_return < 0} />
                      <MetricCard label="Sortino Ratio" value={fmt(result.metrics.sortino_ratio)} />
                      <MetricCard label="Calmar Ratio" value={fmt(result.metrics.calmar_ratio)} />
                      <MetricCard label="Profit Factor" value={fmt(result.metrics.profit_factor)} />
                      <MetricCard label="Avg Win" value={fmtUsd(result.metrics.avg_win)} />
                      <MetricCard label="Avg Loss" value={fmtUsd(result.metrics.avg_loss)} red />
                      <MetricCard label="Expectancy" value={fmtUsd(result.metrics.expectancy)} />
                      <MetricCard label="Kelly %" value={fmtPct(result.metrics.kelly_fraction)} />
                      <MetricCard label="Total Costs" value={fmtUsd(result.metrics.total_costs)} />
                      <MetricCard label="Gross Profit" value={fmtUsd(result.metrics.gross_profit)} />
                      <MetricCard label="Gross Loss" value={fmtUsd(result.metrics.gross_loss)} red />
                      <MetricCard label="Avg Holding" value={fmt(result.metrics.avg_holding_periods, 0) + ' bars'} />
                    </div>
                  )}

                  {activeTab === 'trades' && (
                    <div style={styles.tableContainer}>
                      <table style={styles.table}>
                        <thead>
                          <tr>
                            <th style={styles.th}>Entry</th>
                            <th style={styles.th}>Exit</th>
                            <th style={styles.th}>Side</th>
                            <th style={styles.th}>P&L</th>
                            <th style={styles.th}>P&L %</th>
                            <th style={styles.th}>Bars</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.positions.map((t, i) => (
                            <tr key={i}>
                              <td style={styles.td}>{new Date(t.entry_time).toLocaleString()}</td>
                              <td style={styles.td}>{t.exit_time ? new Date(t.exit_time).toLocaleString() : 'OPEN'}</td>
                              <td style={{ ...styles.td, color: t.side === 'long' ? '#3fb950' : '#f85149' }}>{t.side}</td>
                              <td style={{ ...styles.td, color: t.pnl >= 0 ? '#3fb950' : '#f85149' }}>{fmtUsd(t.pnl)}</td>
                              <td style={{ ...styles.td, color: t.pnl_pct >= 0 ? '#3fb950' : '#f85149' }}>{fmtPct(t.pnl_pct)}</td>
                              <td style={styles.td}>{t.holding_periods}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {activeTab === 'risk' && result.risk && (
                    <div style={styles.metricGrid}>
                      <MetricCard label="Max Drawdown" value={fmtPct(result.risk.max_drawdown)} red />
                      <MetricCard label="VaR 95%" value={fmtPct(result.risk.value_at_risk_95)} red />
                      <MetricCard label="CVaR 95%" value={fmtPct(result.risk.conditional_var_95)} red />
                      <MetricCard label="Volatility (Ann.)" value={fmtPct(result.risk.volatility_annualized)} />
                      <MetricCard label="Tail Ratio" value={fmt(result.risk.tail_ratio)} />
                      <MetricCard label="Ulcer Index" value={fmt(result.risk.ulcer_index, 4)} />
                      <MetricCard label="Pain Index" value={fmt(result.risk.pain_index, 4)} />
                    </div>
                  )}
                </div>

                {result.equity_curve && result.equity_curve.length > 1 && (
                  <div style={{ ...styles.panel, marginTop: '16px' }}>
                    <EquityCurve curve={result.equity_curve} timestamps={result.timestamps} />
                  </div>
                )}

                <div style={{ ...styles.panel, marginTop: '16px' }}>
                  <h3 style={{ color: '#c9d1d9', fontSize: '14px', marginBottom: '12px' }}>GEO EVIDENCE</h3>
                  <div style={{ padding: '12px', background: 'rgba(240, 136, 62, 0.08)', borderRadius: '8px', fontSize: '12px', color: '#f0883e', marginBottom: '12px' }}>
                    ⚠ Geo evidence requires valid spectral bands (NIR/SWIR). GIBS provides RGB visualization imagery only. No valid geo observations available.
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                    <div style={{ padding: '8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#8b949e' }}>Provider</div>
                      <div style={{ fontSize: '12px', color: '#c9d1d9' }}>nasa_gibs</div>
                    </div>
                    <div style={{ padding: '8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#8b949e' }}>Status</div>
                      <div style={{ fontSize: '12px', color: '#f0883e' }}>DATA_UNAVAILABLE</div>
                    </div>
                    <div style={{ padding: '8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#8b949e' }}>Reason</div>
                      <div style={{ fontSize: '12px', color: '#c9d1d9' }}>RGB visualization only, no NIR/SWIR</div>
                    </div>
                    <div style={{ padding: '8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px' }}>
                      <div style={{ fontSize: '10px', color: '#8b949e' }}>Classification</div>
                      <div style={{ fontSize: '12px', color: '#c9d1d9' }}>OBSERVATION</div>
                    </div>
                  </div>
                  <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px', fontSize: '11px', color: '#8b949e' }}>
                    <strong>M26 Integration:</strong> Geo evidence is evidence, not a trading recommendation.
                    NO_DEPLOYMENT_SIGNAL preserved. NO_PREDICTIONS. NO_TRADING_SIGNALS.
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export { ResearchWorkspace };
