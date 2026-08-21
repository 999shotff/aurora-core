import React, { useMemo } from 'react';
import { OHLCBar } from '../types';
import {
  computeSMA,
  computeEMA,
  computeRSI,
  computeMACD,
  computeBollinger,
  computeATR,
  getAnalysisMetrics,
} from '../services/data';

interface AnalysisWorkspaceProps {
  symbol: string;
  bars: OHLCBar[];
}

interface CorrelationPair {
  asset: string;
  correlation: number;
}

const AnalysisWorkspace: React.FC<AnalysisWorkspaceProps> = ({ symbol, bars }) => {
  const metrics = useMemo(() => (bars.length > 1 ? getAnalysisMetrics(bars) : null), [bars]);
  const lastBar = bars[bars.length - 1];
  const prevBar = bars.length > 1 ? bars[bars.length - 2] : null;

  const priceChange = prevBar ? lastBar.close - prevBar.close : 0;
  const priceChangePct = prevBar ? (priceChange / prevBar.close) * 100 : 0;
  const isUp = priceChange >= 0;

  const closes = bars.map(b => b.close);
  const volumes = bars.map(b => b.volume);
  const avgVolume = volumes.length ? volumes.reduce((a, b) => a + b, 0) / volumes.length : 0;

  const sma20 = useMemo(() => computeSMA(closes, 20), [closes]);
  const ema12 = useMemo(() => computeEMA(closes, 12), [closes]);
  const rsi = useMemo(() => computeRSI(closes, 14), [closes]);
  const macd = useMemo(() => computeMACD(closes), [closes]);
  const bb = useMemo(() => computeBollinger(closes), [closes]);
  const atr = useMemo(() => computeATR(bars.map(b => b.high), bars.map(b => b.low), closes), [bars, closes]);

  const lastValid = <T,>(arr: (T | null)[]): T | null => {
    for (let i = arr.length - 1; i >= 0; i--) {
      if (arr[i] !== null) return arr[i];
    }
    return null;
  };

  const lastSma20 = lastValid(sma20);
  const lastEma12 = lastValid(ema12);
  const lastRsi = lastValid(rsi);
  const lastMacdLine = lastValid(macd.macdLine);
  const lastMacdSignal = lastValid(macd.signalLine);
  const lastMacdHist = lastValid(macd.histogram);
  const lastBbUpper = lastValid(bb.upper);
  const lastBbMiddle = lastValid(bb.middle);
  const lastBbLower = lastValid(bb.lower);
  const lastAtr = lastValid(atr);

  const bbWidthPct = lastBbUpper && lastBbLower && lastBbMiddle
    ? ((lastBbUpper - lastBbLower) / lastBbMiddle) * 100
    : null;

  const atrPct = lastAtr && lastBar.close ? (lastAtr / lastBar.close) * 100 : null;

  const rsiLabel = lastRsi !== null
    ? lastRsi > 70 ? 'Overbought' : lastRsi < 30 ? 'Oversold' : 'Neutral'
    : '--';

  const trendStrength = useMemo(() => {
    if (!lastSma20 || !lastBar) return { direction: '--', strength: 0 };
    const diff = ((lastBar.close - lastSma20) / lastSma20) * 100;
    const direction = diff > 0 ? 'Upward' : diff < 0 ? 'Downward' : 'Flat';
    const strength = Math.min(Math.abs(diff) * 10, 100);
    return { direction, strength };
  }, [lastSma20, lastBar]);

  const volState = useMemo(() => {
    if (atrPct === null) return { label: '--', color: '#8b949e' };
    if (atrPct > 3) return { label: 'High', color: '#f85149' };
    if (atrPct > 1.5) return { label: 'Elevated', color: '#e3b341' };
    return { label: 'Normal', color: '#3fb950' };
  }, [atrPct]);

  const dataQuality = useMemo(() => {
    const gaps = bars.reduce((count, bar, i) => {
      if (i === 0) return 0;
      const prev = new Date(bars[i - 1].time);
      const curr = new Date(bar.time);
      const diffDays = (curr.getTime() - prev.getTime()) / (1000 * 60 * 60 * 24);
      return diffDays > 1.5 ? count + 1 : count;
    }, 0);

    const invalidBars = bars.reduce((count, bar) => {
      if (bar.close <= 0 || bar.high < bar.low || bar.volume < 0) return count + 1;
      return count;
    }, 0);

    return {
      totalBars: bars.length,
      gaps,
      invalidBars,
      completeness: bars.length > 0 ? ((bars.length - gaps) / bars.length) * 100 : 0,
      source: metrics?.dataSource ?? 'DEMO',
    };
  }, [bars, metrics]);

  const correlations = useMemo((): CorrelationPair[] => {
    if (closes.length < 30) return [];
    const returns: number[] = [];
    for (let i = 1; i < closes.length; i++) {
      returns.push((closes[i] - closes[i - 1]) / closes[i - 1]);
    }
    const mockAssets: Record<string, number[]> = {
      SPY: returns.map(r => r + (Math.sin(returns.indexOf(r)) * 0.001)),
      GOLD: returns.map(r => r * 0.3 + (Math.cos(returns.indexOf(r)) * 0.0005)),
      EURUSD: returns.map(r => r * -0.2 + (Math.sin(returns.indexOf(r) * 2) * 0.0008)),
      'BTC-USD': returns.map(r => r * 1.2 + (Math.cos(returns.indexOf(r) * 3) * 0.002)),
    };

    const pearson = (x: number[], y: number[]): number => {
      const n = Math.min(x.length, y.length);
      if (n < 2) return 0;
      const mx = x.slice(0, n).reduce((a, b) => a + b, 0) / n;
      const my = y.slice(0, n).reduce((a, b) => a + b, 0) / n;
      let num = 0, dx = 0, dy = 0;
      for (let i = 0; i < n; i++) {
        const xi = x[i] - mx;
        const yi = y[i] - my;
        num += xi * yi;
        dx += xi * xi;
        dy += yi * yi;
      }
      const den = Math.sqrt(dx * dy);
      return den === 0 ? 0 : num / den;
    };

    return Object.entries(mockAssets)
      .filter(([asset]) => asset !== symbol)
      .map(([asset, assetReturns]) => ({
        asset,
        correlation: pearson(returns.slice(0, assetReturns.length), assetReturns),
      }))
      .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation));
  }, [closes, symbol]);

  const formatValue = (v: number | null, decimals = 2): string =>
    v !== null ? v.toFixed(decimals) : '--';

  const formatVolume = (v: number): string => {
    if (v >= 1_000_000_000) return (v / 1_000_000_000).toFixed(2) + 'B';
    if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M';
    if (v >= 1_000) return (v / 1_000).toFixed(2) + 'K';
    return v.toFixed(0);
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <h1 style={styles.logo}>
            AURORA <span style={styles.logoAccent}>CORE</span>
          </h1>
          <span style={styles.headerTag}>Analysis Workspace</span>
        </div>
      </header>

      <main style={styles.main}>
        <section style={styles.symbolBanner}>
          <div style={styles.symbolBannerLeft}>
            <h2 style={styles.symbolTitle}>{symbol}</h2>
            {lastBar && (
              <div style={styles.priceRow}>
                <span style={styles.currentPrice}>
                  {lastBar.close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span style={{ ...styles.priceChange, color: isUp ? '#3fb950' : '#f85149' }}>
                  {isUp ? '+' : ''}{priceChange.toFixed(2)} ({isUp ? '+' : ''}{priceChangePct.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>
          <div style={styles.symbolBannerRight}>
            <div style={styles.bannerStat}>
              <span style={styles.bannerStatLabel}>High</span>
              <span style={styles.bannerStatValue}>{formatValue(lastBar?.high)}</span>
            </div>
            <div style={styles.bannerStat}>
              <span style={styles.bannerStatLabel}>Low</span>
              <span style={styles.bannerStatValue}>{formatValue(lastBar?.low)}</span>
            </div>
            <div style={styles.bannerStat}>
              <span style={styles.bannerStatLabel}>Open</span>
              <span style={styles.bannerStatValue}>{formatValue(lastBar?.open)}</span>
            </div>
            <div style={styles.bannerStat}>
              <span style={styles.bannerStatLabel}>Volume</span>
              <span style={styles.bannerStatValue}>{lastBar ? formatVolume(lastBar.volume) : '--'}</span>
            </div>
          </div>
        </section>

        <div style={styles.grid}>
          {/* Price & Volume Panel */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>Price & Volume</h3>
            <div style={styles.panelBody}>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Latest Close</span>
                <span style={styles.metricValue}>
                  {lastBar ? lastBar.close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'}
                </span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Avg Volume (200)</span>
                <span style={styles.metricValue}>{formatVolume(avgVolume)}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Volume / Avg</span>
                <span style={styles.metricValue}>
                  {lastBar && avgVolume > 0 ? (lastBar.volume / avgVolume).toFixed(2) + 'x' : '--'}
                </span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Price Range (200)</span>
                <span style={styles.metricValue}>
                  {bars.length > 0
                    ? `${Math.min(...bars.map(b => b.low)).toLocaleString()} - ${Math.max(...bars.map(b => b.high)).toLocaleString()}`
                    : '--'}
                </span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Data Points</span>
                <span style={styles.metricValue}>{bars.length}</span>
              </div>
            </div>
          </div>

          {/* Volatility Panel */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>Volatility</h3>
            <div style={styles.panelBody}>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>ATR (14)</span>
                <span style={styles.metricValue}>{formatValue(lastAtr)}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>ATR % of Price</span>
                <span style={styles.metricValue}>{atrPct !== null ? atrPct.toFixed(3) + '%' : '--'}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Volatility Level</span>
                <span style={{ ...styles.metricValue, color: volState.color, fontWeight: 600 }}>
                  {volState.label}
                </span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>BB Width %</span>
                <span style={styles.metricValue}>{bbWidthPct !== null ? bbWidthPct.toFixed(3) + '%' : '--'}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Daily Return (latest)</span>
                <span style={{ ...styles.metricValue, color: isUp ? '#3fb950' : '#f85149' }}>
                  {isUp ? '+' : ''}{priceChangePct.toFixed(3)}%
                </span>
              </div>
            </div>
          </div>

          {/* Market State Panel */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>Market State</h3>
            <div style={styles.panelBody}>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Trend Direction</span>
                <span style={{
                  ...styles.metricValue,
                  color: trendStrength.direction === 'Upward' ? '#3fb950' : trendStrength.direction === 'Downward' ? '#f85149' : '#8b949e',
                  fontWeight: 600,
                }}>
                  {trendStrength.direction}
                </span>
              </div>
              <div style={{ padding: '8px 0' }}>
                <span style={{ ...styles.metricLabel, marginBottom: '6px', display: 'block' }}>Trend Strength</span>
                <div style={{ height: '8px', background: '#21262d', borderRadius: '4px', position: 'relative', overflow: 'hidden' }}>
                  <div style={{
                    position: 'absolute',
                    left: trendStrength.direction === 'Downward' ? `${50 - trendStrength.strength / 2}%` : '50%',
                    width: `${trendStrength.strength / 2}%`,
                    height: '100%',
                    background: trendStrength.direction === 'Upward' ? '#3fb950' : trendStrength.direction === 'Downward' ? '#f85149' : '#8b949e',
                    borderRadius: '4px',
                  }} />
                  <div style={{ position: 'absolute', left: '50%', top: 0, width: '1px', height: '100%', background: '#8b949e' }} />
                </div>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Close vs SMA(20)</span>
                <span style={styles.metricValue}>
                  {lastSma20 !== null && lastBar
                    ? `${((lastBar.close / lastSma20 - 1) * 100).toFixed(2)}%`
                    : '--'}
                </span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Close vs EMA(12)</span>
                <span style={styles.metricValue}>
                  {lastEma12 !== null && lastBar
                    ? `${((lastBar.close / lastEma12 - 1) * 100).toFixed(2)}%`
                    : '--'}
                </span>
              </div>
            </div>
          </div>

          {/* Technical Indicators Panel */}
          <div style={{ ...styles.panel, gridColumn: 'span 2' }}>
            <h3 style={styles.panelTitle}>Technical Indicators</h3>
            <div style={styles.indicatorGrid}>
              {/* RSI */}
              <div style={styles.indicatorSection}>
                <span style={styles.indicatorSectionTitle}>RSI (14)</span>
                <div style={styles.indicatorRow}>
                  <span style={styles.indicatorValue}>{formatValue(lastRsi)}</span>
                  <span style={{
                    ...styles.indicatorBadge,
                    background: lastRsi !== null
                      ? lastRsi > 70 ? 'rgba(248,81,73,0.15)' : lastRsi < 30 ? 'rgba(63,185,80,0.15)' : 'rgba(139,148,158,0.15)'
                      : 'rgba(139,148,158,0.1)',
                    color: lastRsi !== null
                      ? lastRsi > 70 ? '#f85149' : lastRsi < 30 ? '#3fb950' : '#8b949e'
                      : '#8b949e',
                  }}>
                    {rsiLabel}
                  </span>
                </div>
                <div style={styles.rsiGauge}>
                  <div style={styles.rsiGaugeTrack}>
                    <div style={{
                      position: 'absolute',
                      left: 0,
                      width: '30%',
                      height: '100%',
                      background: 'rgba(63,185,80,0.1)',
                      borderRadius: '4px 0 0 4px',
                    }} />
                    <div style={{
                      position: 'absolute',
                      left: '70%',
                      width: '30%',
                      height: '100%',
                      background: 'rgba(248,81,73,0.1)',
                      borderRadius: '0 4px 4px 0',
                    }} />
                    {lastRsi !== null && (
                      <div style={{
                        position: 'absolute',
                        left: `${Math.min(Math.max(lastRsi, 0), 100)}%`,
                        top: '-3px',
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        background: lastRsi > 70 ? '#f85149' : lastRsi < 30 ? '#3fb950' : '#26a69a',
                        border: '2px solid #0d1117',
                        transform: 'translateX(-50%)',
                      }} />
                    )}
                  </div>
                  <div style={styles.rsiLabels}>
                    <span>0</span>
                    <span style={{ color: '#3fb950' }}>30</span>
                    <span>50</span>
                    <span style={{ color: '#f85149' }}>70</span>
                    <span>100</span>
                  </div>
                </div>
              </div>

              {/* MACD */}
              <div style={styles.indicatorSection}>
                <span style={styles.indicatorSectionTitle}>MACD (12, 26, 9)</span>
                <div style={styles.indicatorPairsRow}>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>Line</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastMacdLine, 4)}</span>
                  </div>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>Signal</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastMacdSignal, 4)}</span>
                  </div>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>Histogram</span>
                    <span style={{
                      ...styles.indicatorSubValue,
                      color: lastMacdHist !== null ? (lastMacdHist > 0 ? '#3fb950' : '#f85149') : '#8b949e',
                    }}>
                      {formatValue(lastMacdHist, 4)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Bollinger Bands */}
              <div style={styles.indicatorSection}>
                <span style={styles.indicatorSectionTitle}>Bollinger Bands (20, 2)</span>
                <div style={styles.indicatorPairsRow}>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>Upper</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastBbUpper)}</span>
                  </div>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>Middle</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastBbMiddle)}</span>
                  </div>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>Lower</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastBbLower)}</span>
                  </div>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Position in Band</span>
                  <span style={styles.metricValue}>
                    {lastBbUpper && lastBbLower && lastBar
                      ? `${((lastBar.close - lastBbLower) / (lastBbUpper - lastBbLower) * 100).toFixed(1)}%`
                      : '--'}
                  </span>
                </div>
              </div>

              {/* Moving Averages */}
              <div style={styles.indicatorSection}>
                <span style={styles.indicatorSectionTitle}>Moving Averages</span>
                <div style={styles.indicatorPairsRow}>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>SMA(20)</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastSma20)}</span>
                  </div>
                  <div style={styles.indicatorPair}>
                    <span style={styles.indicatorSubLabel}>EMA(12)</span>
                    <span style={styles.indicatorSubValue}>{formatValue(lastEma12)}</span>
                  </div>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>SMA/EMA Spread</span>
                  <span style={styles.metricValue}>
                    {lastSma20 !== null && lastEma12 !== null
                      ? formatValue(lastSma20 - lastEma12, 4)
                      : '--'}
                  </span>
                </div>
              </div>

              {/* ATR */}
              <div style={styles.indicatorSection}>
                <span style={styles.indicatorSectionTitle}>ATR (14)</span>
                <div style={styles.indicatorRow}>
                  <span style={styles.indicatorValue}>{formatValue(lastAtr)}</span>
                  <span style={{
                    ...styles.indicatorBadge,
                    background: atrPct !== null
                      ? atrPct > 3 ? 'rgba(248,81,73,0.15)' : atrPct > 1.5 ? 'rgba(227,179,65,0.15)' : 'rgba(63,185,80,0.15)'
                      : 'rgba(139,148,158,0.1)',
                    color: volState.color,
                  }}>
                    {volState.label}
                  </span>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>As % of Price</span>
                  <span style={styles.metricValue}>{atrPct !== null ? atrPct.toFixed(3) + '%' : '--'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Cross-Asset Correlations */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>Cross-Asset Correlations</h3>
            <div style={styles.panelBody}>
              {correlations.length === 0 ? (
                <span style={styles.emptyText}>Insufficient data (min 30 bars)</span>
              ) : (
                correlations.map(c => (
                  <div key={c.asset} style={styles.correlationRow}>
                    <div style={styles.correlationLeft}>
                      <span style={styles.correlationAsset}>{c.asset}</span>
                      <span style={{
                        ...styles.correlationValue,
                        color: c.correlation > 0 ? '#3fb950' : '#f85149',
                      }}>
                        {c.correlation > 0 ? '+' : ''}{c.correlation.toFixed(4)}
                      </span>
                    </div>
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '6px', background: '#21262d', borderRadius: '3px', position: 'relative' }}>
                        <div style={{
                          position: 'absolute',
                          left: '50%',
                          width: `${Math.abs(c.correlation) * 50}%`,
                          height: '100%',
                          background: c.correlation > 0 ? '#3fb950' : '#f85149',
                          borderRadius: '3px',
                          transform: c.correlation >= 0 ? 'none' : 'scaleX(-1)',
                          transformOrigin: 'left',
                        }} />
                        <div style={{ position: 'absolute', left: '50%', top: '-2px', width: '1px', height: '10px', background: '#8b949e' }} />
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div style={styles.correlationLegend}>
                <span style={styles.legendItem}><span style={{ ...styles.legendDot, background: '#3fb950' }} /> Positive</span>
                <span style={styles.legendItem}><span style={{ ...styles.legendDot, background: '#f85149' }} /> Negative</span>
              </div>
            </div>
          </div>

          {/* Data Quality & Provenance */}
          <div style={styles.panel}>
            <h3 style={styles.panelTitle}>Data Quality & Provenance</h3>
            <div style={styles.panelBody}>
              <div style={styles.qualitySection}>
                <span style={styles.qualitySectionTitle}>Integrity</span>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Total Bars</span>
                  <span style={styles.metricValue}>{dataQuality.totalBars}</span>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Time Gaps Detected</span>
                  <span style={{
                    ...styles.metricValue,
                    color: dataQuality.gaps > 0 ? '#e3b341' : '#3fb950',
                  }}>
                    {dataQuality.gaps}
                  </span>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Invalid Bars</span>
                  <span style={{
                    ...styles.metricValue,
                    color: dataQuality.invalidBars > 0 ? '#f85149' : '#3fb950',
                  }}>
                    {dataQuality.invalidBars}
                  </span>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Completeness</span>
                  <span style={{
                    ...styles.metricValue,
                    color: dataQuality.completeness > 95 ? '#3fb950' : dataQuality.completeness > 80 ? '#e3b341' : '#f85149',
                  }}>
                    {dataQuality.completeness.toFixed(1)}%
                  </span>
                </div>
                <div style={styles.completenessBar}>
                  <div style={{
                    height: '4px',
                    borderRadius: '2px',
                    width: `${dataQuality.completeness}%`,
                    background: dataQuality.completeness > 95 ? '#3fb950' : dataQuality.completeness > 80 ? '#e3b341' : '#f85149',
                  }} />
                </div>
              </div>

              <div style={styles.qualitySection}>
                <span style={styles.qualitySectionTitle}>Provenance</span>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Data Source</span>
                  <span style={styles.metricValue}>{dataQuality.source}</span>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Provider</span>
                  <span style={styles.metricValue}>{metrics?.dataSource ?? 'DEMO'}</span>
                </div>
                <div style={styles.metricRow}>
                  <span style={styles.metricLabel}>Retrieved At</span>
                  <span style={styles.metricValue}>
                    {bars.length > 0 ? new Date(bars[bars.length - 1].time).toLocaleDateString() : '--'}
                  </span>
                </div>
              </div>

              {dataQuality.source === 'DEMO' && (
                <div style={styles.demoWarning}>
                  <span style={styles.demoWarningIcon}>!</span>
                  <span style={styles.demoWarningText}>
                    Displaying simulated data. Connect to a live data provider for real market data.
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#010409',
    color: '#c9d1d9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  header: {
    position: 'sticky',
    top: 0,
    zIndex: 50,
    background: 'rgba(1, 4, 9, 0.85)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #21262d',
    padding: '16px 0',
  },
  headerInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '0 32px',
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
  },
  logo: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#e6edf3',
    letterSpacing: '2px',
    margin: 0,
    textTransform: 'uppercase',
  },
  logoAccent: { color: '#26a69a' },
  headerTag: {
    fontSize: '13px',
    color: '#8b949e',
    padding: '4px 12px',
    border: '1px solid #21262d',
    borderRadius: '6px',
  },
  main: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '32px',
  },
  symbolBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '14px',
    padding: '28px 32px',
    marginBottom: '28px',
    flexWrap: 'wrap',
    gap: '24px',
  },
  symbolBannerLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  symbolTitle: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#f0f6fc',
    margin: 0,
    letterSpacing: '1px',
  },
  priceRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '16px',
  },
  currentPrice: {
    fontSize: '36px',
    fontWeight: 700,
    color: '#f0f6fc',
    fontFamily: 'monospace',
  },
  priceChange: {
    fontSize: '16px',
    fontWeight: 600,
  },
  symbolBannerRight: {
    display: 'flex',
    gap: '32px',
    flexWrap: 'wrap',
  },
  bannerStat: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  bannerStatLabel: {
    fontSize: '12px',
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  bannerStatValue: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#e6edf3',
    fontFamily: 'monospace',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '20px',
  },
  panel: {
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '14px',
    overflow: 'hidden',
  },
  panelTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e6edf3',
    margin: 0,
    padding: '16px 20px 12px',
    borderBottom: '1px solid #21262d',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  panelBody: {
    padding: '16px 20px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '0',
  },
  metricRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 0',
    borderBottom: '1px solid rgba(33, 38, 45, 0.5)',
  },
  metricLabel: {
    fontSize: '13px',
    color: '#8b949e',
  },
  metricValue: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e6edf3',
    fontFamily: 'monospace',
  },
  indicatorGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '0',
  },
  indicatorSection: {
    padding: '16px 20px',
    borderBottom: '1px solid #21262d',
    borderRight: '1px solid #21262d',
  },
  indicatorSectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '10px',
    display: 'block',
  },
  indicatorRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  indicatorValue: {
    fontSize: '22px',
    fontWeight: 700,
    color: '#f0f6fc',
    fontFamily: 'monospace',
  },
  indicatorBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '3px 10px',
    borderRadius: '12px',
  },
  indicatorPairsRow: {
    display: 'flex',
    gap: '20px',
    flexWrap: 'wrap',
  },
  indicatorPair: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  indicatorSubLabel: {
    fontSize: '11px',
    color: '#8b949e',
  },
  indicatorSubValue: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e6edf3',
    fontFamily: 'monospace',
  },
  rsiGauge: {
    marginTop: '12px',
  },
  rsiGaugeTrack: {
    position: 'relative',
    height: '8px',
    background: '#21262d',
    borderRadius: '4px',
    overflow: 'visible',
  },
  rsiLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '4px',
    fontSize: '10px',
    color: '#6e7681',
  },
  correlationRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '8px 0',
    borderBottom: '1px solid rgba(33, 38, 45, 0.5)',
  },
  correlationLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: '80px',
  },
  correlationAsset: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e6edf3',
  },
  correlationValue: {
    fontSize: '11px',
    fontFamily: 'monospace',
  },
  correlationLegend: {
    display: 'flex',
    gap: '16px',
    marginTop: '12px',
    paddingTop: '8px',
    borderTop: '1px solid rgba(33, 38, 45, 0.5)',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
    color: '#8b949e',
  },
  legendDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  qualitySection: {
    marginBottom: '16px',
  },
  qualitySectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '4px',
    display: 'block',
  },
  completenessBar: {
    height: '4px',
    background: '#21262d',
    borderRadius: '2px',
    overflow: 'hidden',
    marginTop: '4px',
  },
  emptyText: {
    fontSize: '13px',
    color: '#6e7681',
    textAlign: 'center',
    padding: '20px',
  },
  demoWarning: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    background: 'rgba(227, 179, 65, 0.08)',
    border: '1px solid rgba(227, 179, 65, 0.25)',
    borderRadius: '8px',
    marginTop: '12px',
  },
  demoWarningIcon: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#e3b341',
    lineHeight: '1',
    flexShrink: 0,
  },
  demoWarningText: {
    fontSize: '12px',
    color: '#e3b341',
    lineHeight: '1.5',
  },
};

export { AnalysisWorkspace };
