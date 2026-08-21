import React from 'react';
import { AnalysisMetrics } from '../types';

interface Props {
  metrics: AnalysisMetrics | null;
  symbol: string;
  isDemo?: boolean;
  stale?: boolean;
  provider?: string;
}

export const AnalysisPanel: React.FC<Props> = ({ metrics, symbol, isDemo, stale, provider }) => {
  if (!metrics) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <span style={styles.title}>Analysis</span>
          <span style={{ ...styles.badge, background: '#8b949e' }}>LOADING</span>
        </div>
        <div style={{ padding: 20, color: '#8b949e', textAlign: 'center' }}>Loading...</div>
      </div>
    );
  }

  const badgeColor = isDemo ? '#f0883e' : stale ? '#d29922' : '#26a69a';
  const badgeText = isDemo ? 'DEMO' : stale ? 'STALE' : 'LIVE';
  const providerLabel = provider ?? 'unknown';

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Analysis</span>
        <span style={{ ...styles.badge, background: badgeColor }}>{badgeText}</span>
      </div>

      <Section title="Market Data">
        <Row label="Symbol" value={symbol} />
        <Row label="Provider" value={providerLabel} color={badgeColor} />
        <Row label="Data Source" value={metrics.dataSource} color={badgeColor} />
        <Row label="Trend" value={metrics.trendState}
          color={metrics.trendState === 'Bullish' ? '#3fb950' : metrics.trendState === 'Bearish' ? '#f85149' : '#8b949e'} />
        <Row label="Volatility" value={metrics.volatilityState}
          color={metrics.volatilityState === 'High' ? '#f85149' : metrics.volatilityState === 'Low' ? '#3fb950' : '#8b949e'} />
      </Section>

      <Section title="Technical Indicators">
        <Row label="RSI (14)" value={fmt(metrics.rsi)}
          color={metrics.rsi && metrics.rsi > 70 ? '#f85149' : metrics.rsi && metrics.rsi < 30 ? '#3fb950' : '#f0f6fc'} />
        <Row label="MACD Line" value={fmt(metrics.macdLine)}
          color={metrics.macdHistogram && metrics.macdHistogram > 0 ? '#3fb950' : '#f85149'} />
        <Row label="MACD Signal" value={fmt(metrics.macdSignal)} />
        <Row label="MACD Histogram" value={fmt(metrics.macdHistogram)}
          color={metrics.macdHistogram && metrics.macdHistogram > 0 ? '#3fb950' : '#f85149'} />
        <Row label="ATR (14)" value={fmt(metrics.atr)} />
      </Section>

      <Section title="Moving Averages">
        <Row label="SMA 20" value={fmt(metrics.sma20)} color="#2196F3" />
        <Row label="EMA 12" value={fmt(metrics.ema12)} color="#FF9800" />
      </Section>

      <Section title="Bollinger Bands">
        <Row label="Upper" value={fmt(metrics.bbUpper)} color="#9C27B0" />
        <Row label="Middle" value={fmt(metrics.bbMiddle)} color="#9C27B0" />
        <Row label="Lower" value={fmt(metrics.bbLower)} color="#9C27B0" />
      </Section>

      <Section title="Research Status">
        <div style={styles.researchBox}>
          <div style={styles.researchLabel}>AURORA CORE Research Status</div>
          <div style={styles.researchValue}>NO_DEPLOYMENT_SIGNAL</div>
          <div style={styles.researchNote}>No profitable strategy detected. Analysis only.</div>
        </div>
      </Section>
    </div>
  );
};

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={styles.section}>
    <div style={styles.sectionTitle}>{title}</div>
    {children}
  </div>
);

const Row: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div style={styles.row}>
    <span style={styles.label}>{label}</span>
    <span style={{ ...styles.value, color: color ?? '#f0f6fc' }}>{value}</span>
  </div>
);

function fmt(v: number | null): string {
  return v !== null ? v.toFixed(v < 10 ? 4 : 2) : '—';
}

const styles: Record<string, React.CSSProperties> = {
  container: { width: 280, minWidth: 240, background: '#0d1117', borderLeft: '1px solid #21262d', display: 'flex', flexDirection: 'column', overflow: 'auto' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid #21262d' },
  title: { fontSize: 13, fontWeight: 600, color: '#f0f6fc' },
  badge: { fontSize: 9, color: '#000', padding: '2px 6px', borderRadius: 4, fontWeight: 700 },
  section: { padding: '10px 12px', borderBottom: '1px solid #161b22' },
  sectionTitle: { fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0' },
  label: { fontSize: 12, color: '#8b949e' },
  value: { fontSize: 12, fontWeight: 600, fontFamily: 'monospace' },
  researchBox: { background: '#161b22', borderRadius: 6, padding: 10, border: '1px solid #f0883e33' },
  researchLabel: { fontSize: 11, color: '#f0883e', fontWeight: 700, marginBottom: 4 },
  researchValue: { fontSize: 13, color: '#f0883e', fontWeight: 900, fontFamily: 'monospace', marginBottom: 4 },
  researchNote: { fontSize: 10, color: '#8b949e', fontStyle: 'italic' },
};
