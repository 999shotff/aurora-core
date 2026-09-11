/**
 * AURORA Terminal — Provider Status Panel.
 *
 * Compact global system status area showing all provider states.
 * Uses real backend status. Never displays READY unless actually READY.
 */

import React, { useState, useEffect } from 'react';
import { getTerminalStatus, type ProviderStatus } from '../../services/terminal';
import { GlassPanel } from '../shell/primitives';

const STATUS_COLORS: Record<string, { color: string; bg: string; border: string }> = {
  ready: { color: '#34D399', bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.28)' },
  degraded: { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.28)' },
  offline: { color: '#9096A8', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)' },
  unavailable: { color: '#F87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.2)' },
};

function ProviderRow({ provider }: { provider: ProviderStatus }) {
  const s = STATUS_COLORS[provider.status] || STATUS_COLORS.unavailable;
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 0',
        borderBottom: '1px solid var(--aur-border-soft)',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: s.color,
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.06em',
          color: 'var(--aur-ink-dim)',
          minWidth: 56,
        }}
      >
        {provider.category}
      </span>
      <span style={{ fontSize: 11, color: 'var(--aur-ink)', flex: 1 }}>{provider.name}</span>
      <span
        style={{
          fontSize: 9,
          fontWeight: 600,
          padding: '2px 6px',
          borderRadius: 4,
          background: s.bg,
          border: `1px solid ${s.border}`,
          color: s.color,
        }}
      >
        {provider.detail}
      </span>
    </div>
  );
}

export const ProviderStatusPanel: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const data = await getTerminalStatus();
        if (mounted) {
          setProviders(data.providers);
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <GlassPanel style={{ padding: compact ? '10px 14px' : '14px 18px' }}>
        <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>Loading status...</div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel style={{ padding: compact ? '10px 14px' : '14px 18px' }}>
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.08em',
          color: 'var(--aur-ink-faint)',
          textTransform: 'uppercase',
          marginBottom: 8,
        }}
      >
        System Status
      </div>
      {providers.map(p => (
        <ProviderRow key={p.category} provider={p} />
      ))}
    </GlassPanel>
  );
};

export default ProviderStatusPanel;
