import React from 'react';
import { Check } from 'lucide-react';
import type { AssetCategorySummary, AssetType } from '../../types/geoAssets';
import { ASSET_TYPE_LABEL } from '../../types/geoAssets';

interface Props {
  summaries: AssetCategorySummary[];
  enabled: Set<AssetType>;
  onToggle: (type: AssetType) => void;
}

export const AssetLayerControl: React.FC<Props> = ({ summaries, enabled, onToggle }) => (
  <div style={{ background: 'var(--aur-glass)', border: '1px solid var(--aur-border-soft)', borderRadius: 'var(--aur-r-sm)', padding: '14px 16px' }}>
    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
      Observation layers
    </div>
    {summaries.map(s => {
      const isOn = enabled.has(s.assetType);
      return (
        <button
          key={s.assetType}
          onClick={() => onToggle(s.assetType)}
          style={{
            display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '8px 4px',
            background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left',
          }}
        >
          <span style={{
            width: 16, height: 16, borderRadius: 4, flexShrink: 0,
            border: `1.4px solid ${isOn ? 'var(--aur-accent)' : 'var(--aur-border)'}`,
            background: isOn ? 'var(--aur-accent)' : 'transparent',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {isOn && <Check size={11} color="#0A0B10" strokeWidth={3} />}
          </span>
          <span style={{ flex: 1, fontSize: 12.5, color: isOn ? 'var(--aur-ink)' : 'var(--aur-ink-dim)' }}>
            {ASSET_TYPE_LABEL[s.assetType]}
          </span>
          <span style={{ fontSize: 10.5, color: s.connected ? 'var(--aur-positive)' : 'var(--aur-ink-faint)', flexShrink: 0 }}>
            {s.connected ? `${s.assetCount}` : 'No data'}
          </span>
        </button>
      );
    })}
  </div>
);
