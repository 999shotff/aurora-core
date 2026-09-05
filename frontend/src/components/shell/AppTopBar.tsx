import React from 'react';
import { Menu, Wifi, WifiOff } from 'lucide-react';
import { SearchCommand } from './SearchCommand';

interface AppTopBarProps {
  title: string;
  subtitle?: string;
  onOpenMobileNav: () => void;
  connectionOk: boolean;
  right?: React.ReactNode;
}

export const AppTopBar: React.FC<AppTopBarProps> = ({ title, subtitle, onOpenMobileNav, connectionOk, right }) => (
  <div
    className="aur-glass aur-glass--md"
    style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap',
      padding: '12px 16px', marginBottom: 20,
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
      <button
        onClick={onOpenMobileNav}
        className="aur-hamburger-btn"
        aria-label="Open navigation"
        style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--aur-glass-strong)', border: '1px solid var(--aur-border-soft)', color: 'var(--aur-ink)', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}
      >
        <Menu size={17} />
      </button>
      <div style={{ minWidth: 0 }}>
        <h1 style={{ fontSize: 17, fontWeight: 600, letterSpacing: '-0.01em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 12, color: 'var(--aur-ink-dim)', marginTop: 1 }}>{subtitle}</p>}
      </div>
      <div title={connectionOk ? 'System connected' : 'System offline — showing last-known / demo state'} style={{ display: 'flex', alignItems: 'center', color: connectionOk ? 'var(--aur-positive)' : 'var(--aur-ink-faint)' }}>
        {connectionOk ? <Wifi size={15} /> : <WifiOff size={15} />}
      </div>
    </div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
      <SearchCommand />
      {right}
    </div>
  </div>
);
