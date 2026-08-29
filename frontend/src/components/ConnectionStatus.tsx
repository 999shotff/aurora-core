import React from 'react';
import type { ConnectionState } from '../services/stream';

interface Props {
  state: ConnectionState;
  provider?: string;
  isDemo?: boolean;
}

const STATE_CONFIG: Record<ConnectionState, { label: string; color: string; bg: string }> = {
  live: { label: 'LIVE', color: '#000', bg: '#26a69a' },
  connecting: { label: 'CONNECTING', color: '#000', bg: '#d29922' },
  reconnecting: { label: 'RECONNECTING', color: '#000', bg: '#d29922' },
  fallback: { label: 'REST FALLBACK', color: '#000', bg: '#f0883e' },
  offline: { label: 'OFFLINE', color: '#fff', bg: '#f85149' },
};

export const ConnectionStatus: React.FC<Props> = ({ state, provider, isDemo }) => {
  const config = STATE_CONFIG[state] ?? STATE_CONFIG.offline;
  return (
    <div style={styles.container}>
      <div style={{ ...styles.dot, background: config.bg }} />
      <span style={{ ...styles.badge, background: config.bg, color: config.color }}>
        {config.label}
      </span>
      {provider && state === 'live' && (
        <span style={styles.provider}>
          {provider}{isDemo ? ' (demo)' : ''}
        </span>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '0 8px',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    flexShrink: 0,
  },
  badge: {
    fontSize: 9,
    fontWeight: 800,
    padding: '2px 6px',
    borderRadius: 3,
    letterSpacing: 0.3,
  },
  provider: {
    fontSize: 9,
    color: '#8b949e',
    fontFamily: 'monospace',
  },
};
