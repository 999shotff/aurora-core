import React from 'react';
import type { AssetAvailability } from '../../types/geoAssets';

const STYLE: Record<AssetAvailability, { color: string; bg: string; border: string }> = {
  LIVE: { color: '#34D399', bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.28)' },
  DERIVED: { color: '#7C9EFF', bg: 'rgba(124,158,255,0.12)', border: 'rgba(124,158,255,0.28)' },
  REGISTERED: { color: '#A78BFA', bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.28)' },
  DEMO: { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.28)' },
  STALE: { color: '#FF8A65', bg: 'rgba(255,138,101,0.12)', border: 'rgba(255,138,101,0.28)' },
  UNAVAILABLE: { color: '#9096A8', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)' },
};

export const SourceBadge: React.FC<{ availability: AssetAvailability; small?: boolean }> = ({ availability, small }) => {
  const s = STYLE[availability];
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        fontSize: small ? 9.5 : 11, fontWeight: 700, letterSpacing: '0.04em',
        color: s.color, background: s.bg, border: `1px solid ${s.border}`,
        padding: small ? '2px 6px' : '3px 9px', borderRadius: 6, whiteSpace: 'nowrap',
      }}
    >
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor', flexShrink: 0 }} />
      {availability}
    </span>
  );
};
