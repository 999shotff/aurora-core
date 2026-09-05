import React from 'react';
import { GlassPanel, ConfidenceIndicator, EmptyState } from '../shell/primitives';
import { SourceBadge } from './SourceBadge';
import type { GeoAssetObservation } from '../../types/geoAssets';
import { ASSET_TYPE_LABEL } from '../../types/geoAssets';
import type { ConfidenceBand } from '../../types/domain';

function confidenceToBand(c: number): ConfidenceBand {
  return c >= 0.75 ? 'high' : c >= 0.4 ? 'medium' : 'low';
}

interface Props {
  observations: GeoAssetObservation[];
  title?: string;
}

export const GeoEvidencePanel: React.FC<Props> = ({ observations, title = 'Geo evidence' }) => (
  <GlassPanel>
    <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>{title}</h2>
    {observations.length === 0 && (
      <EmptyState message="No multi-source evidence available yet." hint="Only connected sources produce evidence — nothing is fabricated." />
    )}
    {observations.map(o => (
      <div key={o.observationId} style={{ padding: '10px 2px', borderBottom: '1px solid var(--aur-border-soft)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          <span style={{ fontSize: 12.5, fontWeight: 500 }}>{ASSET_TYPE_LABEL[o.assetType]} observation</span>
          <SourceBadge availability={o.availability} small />
        </div>
        <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', margin: '3px 0 6px' }}>{o.source} · {new Date(o.timestamp).toLocaleString()}</div>
        <ConfidenceIndicator band={confidenceToBand(o.confidence)} showLabel={false} />
      </div>
    ))}
  </GlassPanel>
);
