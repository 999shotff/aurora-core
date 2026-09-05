import React from 'react';
import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import type { DataOrigin, ConfidenceBand } from '../types/domain';

/* ---------------------------------------------------------- GlassPanel */
export const GlassPanel: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  padding?: number | string;
  variant?: 'default' | 'strong';
}> = ({ children, style, className, padding = '20px 22px', variant = 'default' }) => (
  <section
    className={`aur-glass ${variant === 'strong' ? 'aur-glass--strong' : ''} aur-glass--md ${className ?? ''}`}
    style={{ padding, ...style }}
  >
    {children}
  </section>
);

/* ---------------------------------------------------------- StatusBadge (LIVE / DEMO / DERIVED / UNAVAILABLE) */
const ORIGIN_STYLE: Record<DataOrigin, { color: string; bg: string; border: string; label: string }> = {
  live: { color: '#34D399', bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.28)', label: 'LIVE' },
  demo: { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.28)', label: 'DEMO' },
  derived: { color: '#7C9EFF', bg: 'rgba(124,158,255,0.12)', border: 'rgba(124,158,255,0.28)', label: 'DERIVED' },
  unavailable: { color: '#9096A8', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.1)', label: 'UNAVAILABLE' },
};

export const StatusBadge: React.FC<{ origin: DataOrigin; small?: boolean }> = ({ origin, small }) => {
  const s = ORIGIN_STYLE[origin];
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        fontSize: small ? 9.5 : 11, fontWeight: 700, letterSpacing: '0.04em',
        color: s.color, background: s.bg, border: `1px solid ${s.border}`,
        padding: small ? '2px 6px' : '3px 9px', borderRadius: 6,
      }}
      title={origin === 'demo' ? 'Illustrative sample data — not a live source' : undefined}
    >
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor' }} />
      {s.label}
    </span>
  );
};

/* ---------------------------------------------------------- ConfidenceIndicator */
const CONFIDENCE_STYLE: Record<ConfidenceBand, { color: string; label: string; fill: number }> = {
  low: { color: '#F87171', label: 'Low confidence', fill: 0.3 },
  medium: { color: '#FBBF24', label: 'Medium confidence', fill: 0.62 },
  high: { color: '#34D399', label: 'High confidence', fill: 0.92 },
};

export const ConfidenceIndicator: React.FC<{ band: ConfidenceBand; showLabel?: boolean }> = ({ band, showLabel = true }) => {
  const s = CONFIDENCE_STYLE[band];
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: 46, height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
        <div style={{ width: `${s.fill * 100}%`, height: '100%', background: s.color, borderRadius: 3 }} />
      </div>
      {showLabel && <span style={{ fontSize: 11.5, color: 'var(--aur-ink-dim)' }}>{s.label}</span>}
    </div>
  );
};

/* ---------------------------------------------------------- MetricCard */
export const MetricCard: React.FC<{
  label: string;
  value: string;
  delta?: string;
  deltaPositive?: boolean;
  origin?: DataOrigin;
  icon?: React.ReactNode;
  onClick?: () => void;
}> = ({ label, value, delta, deltaPositive, origin, icon, onClick }) => (
  <button
    onClick={onClick}
    className={`aur-glass aur-glass--sm ${onClick ? 'aur-glass--interactive' : ''}`}
    style={{
      padding: '16px 18px', textAlign: 'left', color: 'inherit', cursor: onClick ? 'pointer' : 'default',
      width: '100%',
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
      <span style={{ fontSize: 12, color: 'var(--aur-ink-dim)', fontWeight: 500 }}>{label}</span>
      {icon ?? (origin && <StatusBadge origin={origin} small />)}
    </div>
    <div style={{ fontSize: 23, fontWeight: 600, fontFamily: 'var(--aur-font-display)', letterSpacing: '-0.01em' }}>{value}</div>
    {delta && (
      <div style={{ fontSize: 11.5, fontWeight: 500, marginTop: 6, color: deltaPositive ? 'var(--aur-positive)' : 'var(--aur-negative)' }}>
        {delta}
      </div>
    )}
  </button>
);

/* ---------------------------------------------------------- Loading / Error / Empty states */
export const LoadingState: React.FC<{ label?: string }> = ({ label = 'Loading…' }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '48px 20px', color: 'var(--aur-ink-dim)' }}>
    <Loader2 size={22} className="aur-spin" style={{ animation: 'aur-spin 0.9s linear infinite' }} />
    <span style={{ fontSize: 13 }}>{label}</span>
    <style>{`@keyframes aur-spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

export const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '48px 20px', textAlign: 'center' }}>
    <AlertTriangle size={22} color="#F87171" />
    <span style={{ fontSize: 13, color: 'var(--aur-ink)' }}>{message}</span>
    {onRetry && (
      <button
        onClick={onRetry}
        style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, background: 'var(--aur-glass-strong)', border: '1px solid var(--aur-border-soft)', color: 'var(--aur-ink)', fontSize: 12.5, fontWeight: 600, padding: '8px 16px', borderRadius: 9, cursor: 'pointer' }}
      >
        <RefreshCw size={13} /> Retry
      </button>
    )}
  </div>
);

export const EmptyState: React.FC<{ message: string; hint?: string }> = ({ message, hint }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '48px 20px', textAlign: 'center', color: 'var(--aur-ink-faint)' }}>
    <Inbox size={22} />
    <span style={{ fontSize: 13, color: 'var(--aur-ink-dim)' }}>{message}</span>
    {hint && <span style={{ fontSize: 11.5 }}>{hint}</span>}
  </div>
);
