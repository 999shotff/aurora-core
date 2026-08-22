import React from 'react';
import { INDICATOR_GROUPS, IndicatorGroup, IndicatorDef } from '../services/data';

interface Props {
  enabled: Set<string>;
  onToggle: (id: string) => void;
}

export const IndicatorSelector: React.FC<Props> = ({ enabled, onToggle }) => {
  const groups: IndicatorGroup[] = ['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME', 'LEVELS'];

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
  container: { width: 180, background: '#0d1117', borderLeft: '1px solid #21262d', display: 'flex', flexDirection: 'column', overflow: 'auto', flexShrink: 0 },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderBottom: '1px solid #21262d' },
  title: { fontSize: 12, fontWeight: 600, color: '#f0f6fc' },
  count: { fontSize: 10, color: '#8b949e' },
  group: { padding: '4px 0', borderBottom: '1px solid #161b22' },
  groupTitle: { fontSize: 9, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5, padding: '4px 10px' },
  row: { display: 'flex', alignItems: 'center', gap: 6, width: '100%', background: 'none', border: 'none', padding: '4px 10px', cursor: 'pointer', color: '#8b949e', fontSize: 11, textAlign: 'left' },
  rowOn: { display: 'flex', alignItems: 'center', gap: 6, width: '100%', background: 'rgba(38,166,154,0.08)', border: 'none', padding: '4px 10px', cursor: 'pointer', color: '#26a69a', fontSize: 11, textAlign: 'left' },
  checkbox: { width: 12, fontSize: 10 },
  name: { flex: 1 },
  badge: { fontSize: 8, color: '#484f58', background: '#161b22', padding: '1px 4px', borderRadius: 3 },
};
