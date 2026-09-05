import React, { useMemo } from 'react';
import type { OHLCBar } from '../types';
import { analyzeStructure } from '../services/structure';
import type { MarketRegime, StructureBreak } from '../services/structure';

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
      <div className="structure-panel">
        <div className="structure-panel-header">
          <span className="structure-panel-title">Market Structure</span>
          <span className="structure-badge structure-badge-off">OFF</span>
        </div>
        <div className="structure-state">
          <span>Structure analysis is not enabled.</span>
          <span className="structure-state-desc">
            Enable STRUCTURE in the chart controls above to visualize swing points,
            break of structure (BOS), change of character (CHoCH), and support/resistance levels.
          </span>
        </div>
      </div>
    );
  }

  if (bars.length < 7) {
    return (
      <div className="structure-panel">
        <div className="structure-panel-header">
          <span className="structure-panel-title">Market Structure</span>
          <span className="structure-badge structure-badge-off">UNAVAILABLE</span>
        </div>
        <div className="structure-state">
          <span>Insufficient data for structure analysis</span>
          <span className="structure-state-desc">At least 7 bars required for swing point detection.</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="structure-panel">
        <div className="structure-panel-header">
          <span className="structure-panel-title">Market Structure</span>
          <span className="structure-badge structure-badge-loading">ANALYZING</span>
        </div>
        <div className="structure-state">
          <span>Analyzing market structure</span>
        </div>
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
    <div className="structure-panel">
      <div className="structure-panel-header">
        <span className="structure-panel-title">Market Structure</span>
        <span className="structure-badge structure-badge-live">ACTIVE</span>
      </div>

      <div className="structure-section">
        <div className="structure-section-title">Market Regime</div>
        <SRow label="Current" value={regime.toUpperCase()} color={regimeColor(regime)} />
      </div>

      <div className="structure-section">
        <div className="structure-section-title">Swing Points</div>
        <SRow label="Swing Highs" value={String(swingHighs.length)} />
        <SRow label="Swing Lows" value={String(swingLows.length)} />
        {lastSwings.map((sw, i) => (
          <SRow
            key={i}
            label={sw.swing_type === 'high' ? 'High' : 'Low'}
            value={fmtPrice(sw.price)}
            color={sw.swing_type === 'high' ? 'var(--aur-accent-2)' : 'var(--aur-accent)'}
          />
        ))}
        {lastSwings.length === 0 && (
          <div style={{ color: 'var(--aur-ink-faint)', fontSize: 11, padding: '4px 0' }}>No swings detected</div>
        )}
      </div>

      <div className="structure-section">
        <div className="structure-section-title">Structure Breaks</div>
        <SRow label="BOS" value={String(bosBreaks.length)} color="var(--aur-warning)" />
        <SRow label="CHOCH" value={String(chochBreaks.length)} color="var(--aur-negative)" />
        {lastBreaks.map((brk, i) => (
          <SRow
            key={i}
            label={breakTypeLabel(brk)}
            value={fmtPrice(brk.reference_price)}
            color={breakTypeColor(brk.break_type)}
          />
        ))}
        {lastBreaks.length === 0 && (
          <div style={{ color: 'var(--aur-ink-faint)', fontSize: 11, padding: '4px 0' }}>No breaks detected</div>
        )}
      </div>

      <div className="structure-section">
        <div className="structure-section-title">Support / Resistance</div>
        {topSR.map((sr, i) => (
          <SRow
            key={i}
            label={`${sr.level_type === 'support' ? 'S' : 'R'} (${sr.touches})`}
            value={fmtPrice(sr.level)}
            color={sr.level_type === 'support' ? 'var(--aur-positive)' : 'var(--aur-negative)'}
          />
        ))}
        {topSR.length === 0 && (
          <div style={{ color: 'var(--aur-ink-faint)', fontSize: 11, padding: '4px 0' }}>No levels detected</div>
        )}
      </div>

      <div className="structure-section">
        <div className="structure-section-title">Liquidity</div>
        <SRow label="Swept" value={String(sweptLevels.length)} color="var(--aur-accent-2)" />
        <SRow label="Un-swept" value={String(unsweptLevels.length)} color="var(--aur-ink-dim)" />
      </div>
    </div>
  );
};

function regimeColor(regime: MarketRegime): string {
  switch (regime) {
    case 'uptrend': return 'var(--aur-positive)';
    case 'downtrend': return 'var(--aur-negative)';
    case 'ranging': return 'var(--aur-ink-dim)';
    default: return 'var(--aur-ink)';
  }
}

function breakTypeLabel(brk: StructureBreak): string {
  switch (brk.break_type) {
    case 'bos_bull': return 'BOS \u2191';
    case 'bos_bear': return 'BOS \u2193';
    case 'choch_bull': return 'CHoCH \u2191';
    case 'choch_bear': return 'CHoCH \u2193';
    default: return brk.break_type;
  }
}

function breakTypeColor(type: string): string {
  if (type.includes('bull')) return 'var(--aur-positive)';
  if (type.includes('bear')) return 'var(--aur-negative)';
  return 'var(--aur-ink)';
}

function fmtPrice(v: number): string {
  return v < 10 ? v.toFixed(4) : v.toFixed(2);
}

const SRow: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
  <div className="structure-row">
    <span className="structure-row-label">{label}</span>
    <span className="structure-row-value" style={{ color: color ?? 'var(--aur-ink)' }}>{value}</span>
  </div>
);
