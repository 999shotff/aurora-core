import React from 'react';
import { INDICATOR_GROUPS } from '../services/data';
import type { IndicatorGroup, IndicatorDef } from '../services/data';
import { IndicatorParameterEditor } from './IndicatorParameterEditor';

interface Props {
  enabled: Set<string>;
  onToggle: (id: string) => void;
  indicatorParams: Record<string, Record<string, number>>;
  onParamUpdate: (indicatorId: string, paramId: string, value: number) => void;
  onParamReset: (indicatorId: string) => void;
  compact?: boolean;
}

export const IndicatorSelector: React.FC<Props> = ({ enabled, onToggle, indicatorParams, onParamUpdate, onParamReset, compact }) => {
  const groups: IndicatorGroup[] = ['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME', 'LEVELS'];

  if (compact) {
    return (
      <div className="indicator-compact">
        <div className="indicator-compact-header">
          <span className="indicator-compact-count">{enabled.size} active</span>
        </div>
        <div className="indicator-compact-groups">
          {groups.map(group => {
            const items = INDICATOR_GROUPS.filter(i => i.group === group);
            return (
              <div key={group} className="indicator-compact-group">
                <div className="indicator-compact-group-title">{group}</div>
                <div className="indicator-compact-items">
                  {items.map(item => (
                    <button
                      key={item.id}
                      className={`indicator-chip ${enabled.has(item.id) ? 'indicator-chip-on' : ''}`}
                      onClick={() => onToggle(item.id)}
                    >
                      <span className="indicator-chip-dot" />
                      {item.name}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        <IndicatorParameterEditor
          indicatorParams={indicatorParams}
          onUpdate={onParamUpdate}
          onReset={onParamReset}
        />
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Indicators</span>
        <span style={styles.count}>{enabled.size} active</span>
      </div>
      {groups.map(group => {
        const items = INDICATOR_GROUPS.filter(i => i.group === group);
        return (
          <div key={group} style={styles.group}>
            <div style={styles.groupTitle}>{group}</div>
            {items.map(item => (
              <IndicatorRow key={item.id} item={item} on={enabled.has(item.id)} onToggle={onToggle} />
            ))}
          </div>
        );
      })}
      <IndicatorParameterEditor
        indicatorParams={indicatorParams}
        onUpdate={onParamUpdate}
        onReset={onParamReset}
      />
    </div>
  );
};

const IndicatorRow: React.FC<{ item: IndicatorDef; on: boolean; onToggle: (id: string) => void }> = ({
  item, on, onToggle,
}) => (
  <button style={on ? styles.rowOn : styles.row} onClick={() => onToggle(item.id)}>
    <span style={styles.checkbox}>{on ? '\u25CF' : '\u25CB'}</span>
    <span style={styles.name}>{item.name}</span>
    <span style={styles.badge}>{item.overlay ? 'OVL' : 'PNL'}</span>
  </button>
);

const styles: Record<string, React.CSSProperties> = {
  container: { width: '100%', background: 'var(--aur-bg-base)', display: 'flex', flexDirection: 'column', overflow: 'auto', flexShrink: 0 },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', borderBottom: '1px solid var(--aur-border-soft)' },
  title: { fontSize: 12, fontWeight: 600, color: 'var(--aur-ink)' },
  count: { fontSize: 10, color: 'var(--aur-ink-dim)' },
  group: { padding: '4px 0', borderBottom: '1px solid var(--aur-border-soft)' },
  groupTitle: { fontSize: 9, fontWeight: 700, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', letterSpacing: 0.5, padding: '4px 12px' },
  row: { display: 'flex', alignItems: 'center', gap: 6, width: '100%', background: 'none', border: 'none', padding: '4px 12px', cursor: 'pointer', color: 'var(--aur-ink-dim)', fontSize: 11, textAlign: 'left', fontFamily: 'inherit', transition: 'background 0.1s' },
  rowOn: { display: 'flex', alignItems: 'center', gap: 6, width: '100%', background: 'rgba(124, 158, 255, 0.08)', border: 'none', padding: '4px 12px', cursor: 'pointer', color: 'var(--aur-accent)', fontSize: 11, textAlign: 'left', fontFamily: 'inherit', transition: 'background 0.1s' },
  checkbox: { width: 12, fontSize: 10 },
  name: { flex: 1 },
  badge: { fontSize: 8, color: 'var(--aur-ink-faint)', background: 'var(--aur-bg-elevated)', padding: '1px 4px', borderRadius: 3 },
};
