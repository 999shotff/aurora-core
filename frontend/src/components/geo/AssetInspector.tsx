import React from 'react';
import { InspectorSectionTitle, InspectorRow } from '../shell/InspectorSheet';
import { SourceBadge } from './SourceBadge';
import type { GeoAsset } from '../../types/geoAssets';

export const buildAssetInspectorBody = (asset: GeoAsset): React.ReactNode => (
  <div>
    <SourceBadge availability={asset.availability} />

    <InspectorSectionTitle>Identity</InspectorSectionTitle>
    <InspectorRow label="Asset ID" value={asset.assetId} />
    <InspectorRow label="Type" value={asset.assetType.replace('_', ' ')} />
    <InspectorRow label="Status" value={asset.status} />
    <InspectorRow label="Source" value={asset.source} />

    {(asset.location.latitude !== null || asset.location.longitude !== null) && (
      <>
        <InspectorSectionTitle>Position</InspectorSectionTitle>
        <InspectorRow label="Latitude" value={asset.location.latitude ?? '—'} />
        <InspectorRow label="Longitude" value={asset.location.longitude ?? '—'} />
      </>
    )}
    {asset.location.altitudeM !== null && <InspectorRow label="Altitude" value={`${asset.location.altitudeM} m`} />}
    {asset.location.depthM !== null && <InspectorRow label="Depth" value={`${asset.location.depthM} m`} />}

    <InspectorSectionTitle>Last observation</InspectorSectionTitle>
    <InspectorRow label="Timestamp" value={asset.lastObservationAt ? new Date(asset.lastObservationAt).toLocaleString() : 'No observation recorded'} />

    {asset.capabilities.length > 0 && (
      <>
        <InspectorSectionTitle>Capabilities</InspectorSectionTitle>
        <p style={{ fontSize: 12.5, color: 'var(--aur-ink-dim)' }}>{asset.capabilities.join(', ')}</p>
      </>
    )}

    {Object.keys(asset.metadata).length > 0 && (
      <>
        <InspectorSectionTitle>Metadata</InspectorSectionTitle>
        {Object.entries(asset.metadata).map(([k, v]) => <InspectorRow key={k} label={k} value={v} />)}
      </>
    )}

    {asset.evidenceRefs.length > 0 && (
      <>
        <InspectorSectionTitle>Evidence</InspectorSectionTitle>
        {asset.evidenceRefs.map(ref => <InspectorRow key={ref} label="Reference" value={ref} />)}
      </>
    )}

    {asset.limitations.length > 0 && (
      <>
        <InspectorSectionTitle>Limitations</InspectorSectionTitle>
        {asset.limitations.map((l, i) => (
          <p key={i} style={{ fontSize: 12, color: 'var(--aur-ink-faint)', marginBottom: 6, lineHeight: 1.5 }}>{l}</p>
        ))}
      </>
    )}
  </div>
);
