import React, { useMemo } from 'react';
import { OHLCBar } from '../types';
import { analyzeStructure, MarketRegime, SwingPoint, StructureBreak, SRLevel } from '../services/structure';

interface Props {
  bars: OHLCBar[];
  enabled: boolean;
}

export const MarketStructurePanel: React.FC<Props> = ({ bars, enabled }) => {
  const result = useMemo(() => {
    if (!enabled || bars.length < 7) return null;
    try {
      const highs = bars.map((b) => b.high);
      const lows = bars.map((b) => b.low);
      const closes = bars.map((b) => b.close);
      return analyzeStructure(highs, lows, closes);
    } catch {
      return null;
    }
  }, [bars, enabled]);

  if (!enabled) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <span style={styles.title}>Market Structure</span>
          <span style={{ ...styles.badge, background: '#8b949e' }}>OFF</span>
        </div>
        <div style={{ padding: 20, color: '#8b949e', textAlign: 'center' }}>
          Structure analysis disabled
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>
          <span style={styles.title}>Market Structure</span>
          <span style={{ ...styles.badge, background: '#8b949e' }}>LOADING</span>
        </div>
        <div style={{ padding: 20, color: '#8b949e', textAlign: 'center' }}>Analyzing...</div>
      </div>
    );
  }

  const { swings, breaks, supportResistance, liquidity, regime } = result;

  const swingHighs = swings.filter((s) => s.swing_type === 'high');
  const swingLows = swings.filter((s) => s.swing_type === 'low');
  const bosBreaks = breaks.filter((b) => b.break_type === 'bos_bull' || b.break_type === 'bos_bear');
  const chochBreaks = breaks.filter((b) => b.break_type === 'choch_bull' || b.break_type === 'choch_bear');
  const sweptLevels = liquidity.filter((l) => l.swept);
  const unsweptLevels = liquidity.filter((l) => !l.swept);

  const topSR = [...supportResistance]
    .sort((a, b) => b.touches - a.touches)
    .slice(0, 3);

  const lastSwings = swings.slice(-3);
  const lastBreaks = breaks.slice(-3);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Market Structure</span>
        <span style={{ ...styles.badge, background: '#26a69a' }}>LIVE</span>
      </div>

      <Section title="Market Regime">
        <Row
          label="Current"
          value={regime.toUpperCase()}
          color={regimeColor(regime)}
        />
      </Section>

      <Section title="Swing Points">
        <Row label="Swing Highs" value={String(swingHighs.length)} />
        <Row label="Swing Lows" value={String(swingLows.length)} />
        {lastSwings.map((sw, i) => (
          <Row
            key={i}
            label={sw.swing_type === 'high' ? 'High' : 'Low'}
            value={fmtPrice(sw.price)}
            color={sw.swing_type === 'high' ? '#f0883e' : '#2196F3'}
          />
        ))}
        {lastSwings.length === 0 && (
          <div style={{ color: '#8b949e', fontSize: 11, padding: '4px 0' }}>No swings detected</div>
        )}
      </Section>

      <Section title="Structure Breaks">
        <Row label="BOS" value={String(bosBreaks.length)} color="#d29922" />
        <Row label="CHOCH" value={String(chochBreaks.length)} color="#f85149" />
        {lastBreaks.map((brk, i) => (
          <Row
            key={i}
            label={breakTypeLabel(brk)}
            value={fmtPrice(brk.reference_price)}
            color={breakTypeColor(brk.break_type)}
          />
        ))}
        {lastBreaks.length === 0 && (
          <div style={{ color: '#8b949e', fontSize: 11, padding: '4px 0' }}>No breaks detected</div>
        )}
      </Section>

      <Section title="Support / Resistance">
        {topSR.map((sr, i) => (
          <Row
            key={i}
            label={`${sr.type === 'support' ? 'S' : 'R'} (${sr.touches})`}
            value={fmtPrice(sr.level)}
            color={sr.type === 'support' ? '#3fb950' : '#f85149'}
          />
        ))}
        {topSR.length === 0 && (
          <div style={{ color: '#8b949e', fontSize: 11, padding: '4px 0' }}>No levels detected</div>
        )}
      </Section>

      <Section title="Liquidity">
        <Row label="Swept" value={String(sweptLevels.length)} color="#f0883e" />
        <Row label="Un-swept" value={String(unsweptLevels.length)} color="#8b949e" />
      </Section>
    </div>
  );
};

function regimeColor(regime: MarketRegime): string {
  switch (regime) {
    case 'uptrend': return '#3fb950';
    case 'downtrend': return '#f85149';
    case 'ranging': return '#8b949e';
    default: return '#f0f6fc';
  }
}

function breakTypeLabel(brk: StructureBreak): string {
  switch (brk.break_type) {
    case 'bos_bull': return 'BOS ↑';
    case 'bos_bear': return 'BOS ↓';
    case 'choch_bull': return 'CHoCH ↑';
    case 'choch_bear': return 'CHoCH ↓';
    default: return brk.break_type;
  }
}

function breakTypeColor(type: string): string {
  if (type.includes('bull')) return '#3fb950';
  if (type.includes('bear')) return '#f85149';
  return '#f0f6fc';
}

function fmtPrice(v: number): string {
  return v < 10 ? v.toFixed(4) : v.toFixed(2);
}

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

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: 280,
    minWidth: 240,
    background: '#0d1117',
    borderLeft: '1px solid #21262d',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderBottom: '1px solid #21262d',
  },
  title: { fontSize: 13, fontWeight: 600, color: '#f0f6fc' },
  badge: { fontSize: 9, color: '#000', padding: '2px 6px', borderRadius: 4, fontWeight: 700 },
  section: { padding: '10px 12px', borderBottom: '1px solid #161b22' },
  sectionTitle: { fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0' },
  label: { fontSize: 12, color: '#8b949e' },
  value: { fontSize: 12, fontWeight: 600, fontFamily: 'monospace' },
};
