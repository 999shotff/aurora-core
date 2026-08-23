import React, { useMemo } from 'react';
import {
  MarketAnalysis,
  TrendContext,
  MomentumContext,
  VolatilityContextType,
  VolumeAnalysisContext,
  StructureAnalysisContext,
  LiquidityAnalysisContext,
  MultiTimeframeContextType,
  ConflictItem,
  DataQualityContextType,
  ExplanationSection,
  fetchMarketAnalysis,
  computeLocalAnalysis,
} from '../services/analysis';
import { OHLCBar } from '../types';

interface Props {
  asset: string;
  timeframe: string;
  bars: OHLCBar[];
  visible: boolean;
}

export const MarketContextPanel: React.FC<Props> = ({ asset, timeframe, bars, visible }) => {
  const [analysis, setAnalysis] = React.useState<MarketAnalysis | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchMarketAnalysis(asset, timeframe, 200).then(data => {
      if (cancelled) return;
      if (data) {
        setAnalysis(data);
      } else {
        // Fallback to local
        const local = computeLocalAnalysis(bars, asset, timeframe);
        setAnalysis(local);
      }
      setLoading(false);
    }).catch(() => {
      if (cancelled) return;
      const local = computeLocalAnalysis(bars, asset, timeframe);
      setAnalysis(local);
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [asset, timeframe, bars, visible]);

  if (!visible) return null;

  if (loading) {
    return (
      <div style={styles.container}>
        <Header title="Market Context" badge="LOADING" badgeColor="#8b949e" />
        <div style={styles.placeholder}>Analyzing market...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <Header title="Market Context" badge="ERROR" badgeColor="#f85149" />
        <div style={styles.placeholder}>{error}</div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div style={styles.container}>
        <Header title="Market Context" badge="NO DATA" badgeColor="#8b949e" />
        <div style={styles.placeholder}>Insufficient data for analysis</div>
      </div>
    );
  }

  const qualityColor = analysis.data_quality.quality === 'good' ? '#26a69a' :
    analysis.data_quality.quality === 'stale' ? '#d29922' : '#f85149';

  return (
    <div style={styles.container}>
      <Header
        title="Market Context"
        badge={analysis.provider === 'local' ? 'LOCAL' : analysis.is_demo ? 'DEMO' : 'LIVE'}
        badgeColor={analysis.provider === 'local' ? '#8b949e' : analysis.is_demo ? '#f0883e' : '#26a69a'}
      />

      <TrendSection data={analysis.trend} />
      <MomentumSection data={analysis.momentum} />
      <VolatilitySection data={analysis.volatility} />
      <VolumeSection data={analysis.volume} />
      <StructureSection data={analysis.structure} />
      <LiquiditySection data={analysis.liquidity} />
      <MultiTimeframeSection data={analysis.multi_timeframe} />
      <ConflictSection data={analysis.conflicts} />
      <DataQualitySection data={analysis.data_quality} qualityColor={qualityColor} />
      <ExplanationSectionComp data={analysis.explanation} />
    </div>
  );
};

// ============================================================
// Sub-components
// ============================================================

const Header: React.FC<{ title: string; badge: string; badgeColor: string }> = ({ title, badge, badgeColor }) => (
  <div style={styles.header}>
    <span style={styles.title}>{title}</span>
    <span style={{ ...styles.badge, background: badgeColor }}>{badge}</span>
  </div>
);

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={styles.section}>
    <div style={styles.sectionTitle}>{title}</div>
    {children}
  </div>
);

const Row: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div style={styles.row}>
    <span style={styles.rowLabel}>{label}</span>
    <span style={{ ...styles.rowValue, color: color ?? '#f0f6fc' }}>{value}</span>
  </div>
);

const EvidenceList: React.FC<{ evidence: string[] }> = ({ evidence }) => {
  if (evidence.length === 0) return null;
  return (
    <div style={styles.evidence}>
      {evidence.slice(0, 4).map((e, i) => (
        <div key={i} style={styles.evidenceItem}>- {e}</div>
      ))}
    </div>
  );
};

const TrendSection: React.FC<{ data: TrendContext }> = ({ data }) => {
  const color = data.direction === 'uptrend' ? '#3fb950' :
    data.direction === 'downtrend' ? '#f85149' :
    data.direction === 'transition' ? '#d29922' : '#8b949e';
  return (
    <Section title="TREND">
      <Row label="Direction" value={data.direction.toUpperCase()} color={color} />
      <Row label="Strength" value={data.strength.toUpperCase()} />
      <Row label="EMA Aligned" value={data.ema_aligned ? 'Yes' : 'No'} />
      {data.adx_value != null && <Row label="ADX" value={data.adx_value.toFixed(1)} />}
      <Row label="Structure Confirms" value={data.structure_confirms ? 'Yes' : 'No'} />
      <EvidenceList evidence={data.evidence} />
    </Section>
  );
};

const MomentumSection: React.FC<{ data: MomentumContext }> = ({ data }) => {
  const color = data.state === 'bullish' ? '#3fb950' :
    data.state === 'bearish' ? '#f85149' :
    data.state === 'overbought' ? '#d29922' :
    data.state === 'oversold' ? '#2196F3' : '#8b949e';
  return (
    <Section title="MOMENTUM">
      <Row label="State" value={data.state.toUpperCase()} color={color} />
      {data.rsi_value != null && <Row label="RSI (14)" value={data.rsi_value.toFixed(1)} />}
      <Row label="MACD" value={data.macd_positive ? 'Positive' : 'Negative'} />
      {data.stochastic_k != null && <Row label="Stoch %K" value={data.stochastic_k.toFixed(1)} />}
      {data.cci_value != null && <Row label="CCI" value={data.cci_value.toFixed(1)} />}
      {data.roc_value != null && <Row label="ROC" value={`${data.roc_value.toFixed(2)}%`} />}
      {data.williams_r_value != null && <Row label="Williams %R" value={data.williams_r_value.toFixed(1)} />}
      <EvidenceList evidence={data.evidence} />
    </Section>
  );
};

const VolatilitySection: React.FC<{ data: VolatilityContextType }> = ({ data }) => {
  const color = data.regime === 'high' ? '#f85149' :
    data.regime === 'low' ? '#3fb950' :
    data.regime === 'expanding' ? '#d29922' : '#8b949e';
  return (
    <Section title="VOLATILITY">
      <Row label="Regime" value={data.regime.toUpperCase()} color={color} />
      {data.atr_value != null && <Row label="ATR" value={data.atr_value.toFixed(2)} />}
      {data.atr_pct != null && <Row label="ATR %" value={`${(data.atr_pct * 100).toFixed(2)}%`} />}
      {data.bb_width != null && <Row label="BB Width" value={data.bb_width.toFixed(4)} />}
      <Row label="BB Position" value={data.bb_position} />
      <EvidenceList evidence={data.evidence} />
    </Section>
  );
};

const VolumeSection: React.FC<{ data: VolumeAnalysisContext }> = ({ data }) => {
  const color = data.state === 'confirming' ? '#3fb950' :
    data.state === 'diverging' ? '#f85149' :
    data.state === 'unavailable' ? '#8b949e' : '#d29922';
  return (
    <Section title="VOLUME">
      <Row label="State" value={data.state.toUpperCase()} color={color} />
      <Row label="OBV Trend" value={data.obv_trend} />
      {data.vwap_distance != null && <Row label="VWAP Dist" value={`${(data.vwap_distance * 100).toFixed(2)}%`} />}
      {data.mfi_value != null && <Row label="MFI" value={data.mfi_value.toFixed(1)} />}
      <EvidenceList evidence={data.evidence} />
    </Section>
  );
};

const StructureSection: React.FC<{ data: StructureAnalysisContext }> = ({ data }) => {
  const color = data.state === 'bullish' ? '#3fb950' :
    data.state === 'bearish' ? '#f85149' :
    data.state === 'transition' ? '#d29922' : '#8b949e';
  return (
    <Section title="STRUCTURE">
      <Row label="State" value={data.state.toUpperCase()} color={color} />
      <Row label="Regime" value={data.regime.toUpperCase()} />
      <Row label="Swings" value={String(data.swing_count)} />
      <Row label="Breaks" value={String(data.break_count)} />
      <Row label="Support" value={String(data.active_support_count)} />
      <Row label="Resistance" value={String(data.active_resistance_count)} />
      <EvidenceList evidence={data.evidence} />
    </Section>
  );
};

const LiquiditySection: React.FC<{ data: LiquidityAnalysisContext }> = ({ data }) => (
  <Section title="LIQUIDITY">
    <Row label="Swept" value={String(data.swept_count)} />
    <Row label="Unswept" value={String(data.unswept_count)} />
    {data.nearest_liquidity != null && <Row label="Nearest" value={data.nearest_liquidity.toFixed(2)} />}
    <EvidenceList evidence={data.evidence} />
  </Section>
);

const MultiTimeframeSection: React.FC<{ data: MultiTimeframeContextType }> = ({ data }) => {
  const color = data.alignment === 'aligned_bullish' ? '#3fb950' :
    data.alignment === 'aligned_bearish' ? '#f85149' :
    data.alignment === 'conflicting' ? '#d29922' : '#8b949e';
  return (
    <Section title="MULTI-TIMEFRAME">
      <Row label="Alignment" value={data.alignment.toUpperCase()} color={color} />
      {data.timeframes.map((tf, i) => (
        <Row key={i} label={tf.timeframe} value={`${tf.trend} / ${tf.momentum}`} />
      ))}
      <EvidenceList evidence={data.evidence} />
    </Section>
  );
};

const ConflictSection: React.FC<{ data: ConflictItem[] }> = ({ data }) => {
  if (data.length === 0) {
    return (
      <Section title="CONFLICTS">
        <Row label="Status" value="None detected" color="#3fb950" />
      </Section>
    );
  }
  return (
    <Section title="CONFLICTS">
      <Row label="Count" value={String(data.length)} color="#d29922" />
      {data.slice(0, 5).map((c, i) => (
        <div key={i} style={styles.conflictItem}>
          <span style={{ color: '#d29922' }}>{c.domain_a}</span>
          {' vs '}
          <span style={{ color: '#d29922' }}>{c.domain_b}</span>
          <div style={styles.conflictDesc}>{c.description}</div>
        </div>
      ))}
    </Section>
  );
};

const DataQualitySection: React.FC<{ data: DataQualityContextType; qualityColor: string }> = ({ data, qualityColor }) => (
  <Section title="DATA QUALITY">
    <Row label="Quality" value={data.quality.toUpperCase()} color={qualityColor} />
    <Row label="Candles" value={String(data.candle_count)} />
    <Row label="Provider" value={data.provider} />
    <Row label="Stale" value={data.stale ? 'Yes' : 'No'} />
    {data.missing_fields.length > 0 && <Row label="Missing" value={data.missing_fields.join(', ')} />}
  </Section>
);

const ExplanationSectionComp: React.FC<{ data: ExplanationSection[] }> = ({ data }) => (
  <Section title="EXPLANATION">
    {data.map((s, i) => (
      <div key={i} style={styles.explanationSection}>
        <div style={styles.explanationHeading}>{s.heading}: {s.content}</div>
        {s.evidence.length > 0 && (
          <div style={styles.evidence}>
            {s.evidence.slice(0, 3).map((e, j) => (
              <div key={j} style={styles.evidenceItem}>- {e}</div>
            ))}
          </div>
        )}
      </div>
    ))}
  </Section>
);

// ============================================================
// Styles
// ============================================================

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: 280,
    background: '#0d1117',
    borderLeft: '1px solid #21262d',
    overflowY: 'auto',
    flexShrink: 0,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid #21262d',
  },
  title: { fontSize: 13, fontWeight: 700, color: '#f0f6fc' },
  badge: { fontSize: 9, padding: '2px 8px', borderRadius: 4, fontWeight: 800, color: '#000' },
  placeholder: { padding: 20, color: '#8b949e', textAlign: 'center', fontSize: 12 },
  section: { padding: '8px 16px', borderBottom: '1px solid #161b22' },
  sectionTitle: { fontSize: 10, fontWeight: 700, color: '#8b949e', letterSpacing: 0.5, marginBottom: 4, textTransform: 'uppercase' },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '2px 0', fontSize: 11 },
  rowLabel: { color: '#8b949e' },
  rowValue: { fontFamily: 'monospace', fontWeight: 600 },
  evidence: { marginTop: 4, paddingLeft: 8 },
  evidenceItem: { fontSize: 10, color: '#8b949e', lineHeight: 1.4 },
  conflictItem: { padding: '4px 0', fontSize: 11, color: '#f0f6fc' },
  conflictDesc: { fontSize: 10, color: '#d29922', marginTop: 2 },
  explanationSection: { marginBottom: 6 },
  explanationHeading: { fontSize: 11, fontWeight: 600, color: '#f0f6fc' },
};
