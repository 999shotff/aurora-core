import React from 'react';
import type { AnalysisMetrics, IndicatorSeries } from '../types';

interface Props {
  metrics: AnalysisMetrics | null;
  symbol: string;
  isDemo?: boolean;
  stale?: boolean;
  provider?: string;
  activeOverlays?: IndicatorSeries[];
}

export const AnalysisPanel: React.FC<Props> = ({ metrics, symbol, isDemo, stale, provider, activeOverlays = [] }) => {
  if (!metrics) {
    return (
      <div className="analysis-panel">
        <div className="analysis-panel-header">
          <span className="analysis-panel-title">Analysis</span>
          <span className="analysis-badge analysis-badge-loading">LOADING</span>
        </div>
        <div className="analysis-state">
          <div className="analysis-spinner" />
          <span>Computing indicators</span>
        </div>
      </div>
    );
  }

  const badgeClass = isDemo ? 'analysis-badge-demo' : stale ? 'analysis-badge-stale' : 'analysis-badge-live';
  const badgeText = isDemo ? 'DEMO' : stale ? 'STALE' : 'LIVE';
  const providerLabel = provider ?? 'unknown';

  const getOverlayValue = (name: string): number | null => {
    const series = activeOverlays.find(s => s.name === name);
    if (!series || series.points.length === 0) return null;
    return series.points[series.points.length - 1].value;
  };

  const hasOverlay = (name: string) => activeOverlays.some(s => s.name === name);

  return (
    <div className="analysis-panel">
      <div className="analysis-panel-header">
        <span className="analysis-panel-title">Analysis</span>
        <span className={`analysis-badge ${badgeClass}`}>{badgeText}</span>
      </div>

      <div className="analysis-section">
        <div className="analysis-section-title">Market Data</div>
        <ARow label="Symbol" value={symbol} />
        <ARow label="Provider" value={providerLabel} color={badgeClass === 'analysis-badge-live' ? 'var(--aur-positive)' : badgeClass === 'analysis-badge-stale' ? 'var(--aur-warning)' : 'var(--aur-accent-2)'} />
        <ARow label="Data Source" value={metrics.dataSource} color={badgeClass === 'analysis-badge-live' ? 'var(--aur-positive)' : 'var(--aur-accent-2)'} />
        <ARow label="Trend" value={metrics.trendState}
          color={metrics.trendState === 'Bullish' ? 'var(--aur-positive)' : metrics.trendState === 'Bearish' ? 'var(--aur-negative)' : 'var(--aur-ink-dim)'} />
        <ARow label="Volatility" value={metrics.volatilityState}
          color={metrics.volatilityState === 'High' ? 'var(--aur-negative)' : metrics.volatilityState === 'Low' ? 'var(--aur-positive)' : 'var(--aur-ink-dim)'} />
      </div>

      {hasOverlay('sma_20') && (
        <div className="analysis-section">
          <div className="analysis-section-title">SMA</div>
          <ARow label="SMA (20)" value={fmt(getOverlayValue('sma_20'))} color="var(--aur-accent)" />
          {hasOverlay('sma_50') && <ARow label="SMA (50)" value={fmt(getOverlayValue('sma_50'))} color="var(--aur-accent)" />}
        </div>
      )}

      {hasOverlay('ema_12') && (
        <div className="analysis-section">
          <div className="analysis-section-title">EMA</div>
          <ARow label="EMA (12)" value={fmt(getOverlayValue('ema_12'))} color="var(--aur-accent-2)" />
          {hasOverlay('ema_26') && <ARow label="EMA (26)" value={fmt(getOverlayValue('ema_26'))} color="var(--aur-accent-2)" />}
        </div>
      )}

      {hasOverlay('rsi_14') && (
        <div className="analysis-section">
          <div className="analysis-section-title">RSI</div>
          <ARow label="RSI (14)" value={fmt(getOverlayValue('rsi_14'))}
            color={(getOverlayValue('rsi_14') ?? 50) > 70 ? 'var(--aur-negative)' : (getOverlayValue('rsi_14') ?? 50) < 30 ? 'var(--aur-positive)' : 'var(--aur-ink)'} />
        </div>
      )}

      {hasOverlay('macd_line') && (
        <div className="analysis-section">
          <div className="analysis-section-title">MACD</div>
          <ARow label="MACD Line" value={fmt(getOverlayValue('macd_line'))} color="var(--aur-accent)" />
          <ARow label="Signal" value={fmt(getOverlayValue('macd_signal'))} color="var(--aur-accent-2)" />
          <ARow label="Histogram" value={fmt(getOverlayValue('macd_histogram'))}
            color={(getOverlayValue('macd_histogram') ?? 0) > 0 ? 'var(--aur-positive)' : 'var(--aur-negative)'} />
        </div>
      )}

      {hasOverlay('bb_upper') && (
        <div className="analysis-section">
          <div className="analysis-section-title">Bollinger Bands</div>
          <ARow label="Upper" value={fmt(getOverlayValue('bb_upper'))} color="var(--aur-stage-analysis)" />
          <ARow label="Middle" value={fmt(getOverlayValue('bb_middle'))} color="var(--aur-stage-analysis)" />
          <ARow label="Lower" value={fmt(getOverlayValue('bb_lower'))} color="var(--aur-stage-analysis)" />
        </div>
      )}

      {hasOverlay('stoch_k') && (
        <div className="analysis-section">
          <div className="analysis-section-title">Stochastic</div>
          <ARow label="%K" value={fmt(getOverlayValue('stoch_k'))} color="var(--aur-accent-2)" />
          <ARow label="%D" value={fmt(getOverlayValue('stoch_d'))} color="var(--aur-accent)" />
        </div>
      )}

      {hasOverlay('adx_line') && (
        <div className="analysis-section">
          <div className="analysis-section-title">ADX/DMI</div>
          <ARow label="ADX" value={fmt(getOverlayValue('adx_line'))} color="var(--aur-warning)" />
          <ARow label="+DI" value={fmt(getOverlayValue('adx_plus_di'))} color="var(--aur-positive)" />
          <ARow label="-DI" value={fmt(getOverlayValue('adx_minus_di'))} color="var(--aur-negative)" />
        </div>
      )}

      {hasOverlay('atr_14') && (
        <div className="analysis-section">
          <div className="analysis-section-title">ATR</div>
          <ARow label="ATR (14)" value={fmt(getOverlayValue('atr_14'))} color="var(--aur-accent-2)" />
        </div>
      )}

      {hasOverlay('cci_20') && (
        <div className="analysis-section">
          <div className="analysis-section-title">CCI</div>
          <ARow label="CCI (20)" value={fmt(getOverlayValue('cci_20'))} color="var(--aur-stage-analysis)" />
        </div>
      )}

      {hasOverlay('obv') && (
        <div className="analysis-section">
          <div className="analysis-section-title">OBV</div>
          <ARow label="OBV" value={fmtLarge(getOverlayValue('obv'))} color="var(--aur-accent)" />
        </div>
      )}

      {hasOverlay('mfi_14') && (
        <div className="analysis-section">
          <div className="analysis-section-title">MFI</div>
          <ARow label="MFI (14)" value={fmt(getOverlayValue('mfi_14'))} color="var(--aur-stage-analysis)" />
        </div>
      )}

      {hasOverlay('fib_0') && (
        <div className="analysis-section">
          <div className="analysis-section-title">Fibonacci</div>
          <ARow label="High" value={fmt(getOverlayValue('fib_0'))} color="var(--aur-stage-ingestion)" />
          <ARow label="Low" value={fmt(getOverlayValue('fib_100'))} color="var(--aur-positive)" />
          <ARow label="50.0%" value={fmt(getOverlayValue('fib_50'))} color="var(--aur-ink)" />
        </div>
      )}

      {!hasOverlay('sma_20') && !hasOverlay('ema_12') && !hasOverlay('rsi_14') && !hasOverlay('macd_line') && (
        <div className="analysis-section">
          <div className="analysis-section-title">Technical Indicators</div>
          <ARow label="RSI (14)" value={fmt(metrics.rsi)}
            color={metrics.rsi && metrics.rsi > 70 ? 'var(--aur-negative)' : metrics.rsi && metrics.rsi < 30 ? 'var(--aur-positive)' : 'var(--aur-ink)'} />
          <ARow label="MACD Line" value={fmt(metrics.macdLine)}
            color={metrics.macdHistogram && metrics.macdHistogram > 0 ? 'var(--aur-positive)' : 'var(--aur-negative)'} />
          <ARow label="MACD Signal" value={fmt(metrics.macdSignal)} />
          <ARow label="MACD Histogram" value={fmt(metrics.macdHistogram)}
            color={metrics.macdHistogram && metrics.macdHistogram > 0 ? 'var(--aur-positive)' : 'var(--aur-negative)'} />
          <ARow label="ATR (14)" value={fmt(metrics.atr)} />
        </div>
      )}

      <div className="analysis-section">
        <div className="analysis-section-title">Research Status</div>
        <div className="analysis-research-box">
          <div className="analysis-research-label">AURORA CORE Research Status</div>
          <div className="analysis-research-value">NO_DEPLOYMENT_SIGNAL</div>
          <div className="analysis-research-note">No profitable strategy detected. Analysis only.</div>
        </div>
      </div>
    </div>
  );
};

const ARow: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div className="analysis-row">
    <span className="analysis-row-label">{label}</span>
    <span className="analysis-row-value" style={{ color: color ?? 'var(--aur-ink)' }}>{value}</span>
  </div>
);

function fmt(v: number | null): string {
  return v !== null ? v.toFixed(v < 10 ? 4 : 2) : 'N/A';
}

function fmtLarge(v: number | null): string {
  if (v === null) return 'N/A';
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(2) + 'K';
  return v.toFixed(2);
}
