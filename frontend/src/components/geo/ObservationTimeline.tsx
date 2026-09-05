import React, { useEffect, useState } from 'react';
import { SourceBadge } from './SourceBadge';
import { EmptyState } from '../shell/primitives';
import type { GeoAssetObservation } from '../../types/geoAssets';
import { ASSET_TYPE_LABEL } from '../../types/geoAssets';

interface Props {
  observations: GeoAssetObservation[];
}

export const ObservationTimeline: React.FC<Props> = ({ observations }) => {
  // "now" is a ticking state value, not a live Date.now() call during render —
  // keeps this component pure while still excluding future-dated entries.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(id);
  }, []);

  // Sort strictly by real timestamp value — never by a formatted display string,
  // and never show anything with a timestamp in the future.
  const sorted = observations
    .filter(o => new Date(o.timestamp).getTime() <= now)
    .slice()
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  if (sorted.length === 0) {
    return <EmptyState message="No observations recorded yet." hint="Observations appear here once a connected source reports one." />;
  }

  return (
    <div style={{ position: 'relative', paddingLeft: 18 }}>
      <div style={{ position: 'absolute', left: 5, top: 4, bottom: 4, width: 1, background: 'var(--aur-border-soft)' }} />
      {sorted.map(o => (
        <div key={o.observationId} style={{ position: 'relative', marginBottom: 16 }}>
          <span style={{ position: 'absolute', left: -18, top: 3, width: 9, height: 9, borderRadius: '50%', background: 'var(--aur-accent)', border: '2px solid var(--aur-bg-base)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12.5, fontWeight: 500 }}>{ASSET_TYPE_LABEL[o.assetType]} — {o.observationType}</span>
            <SourceBadge availability={o.availability} small />
          </div>
          <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', marginTop: 2 }}>
            {o.source} · {new Date(o.timestamp).toLocaleString()}
            {o.value !== null && ` · ${o.value}${o.unit ? ' ' + o.unit : ''}`}
          </div>
        </div>
      ))}
    </div>
  );
};
