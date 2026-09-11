/**
 * AURORA Terminal — Risk & Portfolio Panel.
 *
 * Architecture only. Shows DATA_UNAVAILABLE when no portfolio data connected.
 * Allows future integration of: positions, exposure, correlation, volatility, drawdown,
 * scenario analysis, stress testing, concentration, cross-asset exposure.
 *
 * NO_DEPLOYMENT_SIGNAL. No fabricated positions. No trade execution.
 */

import React from 'react';
import { GlassPanel } from '../shell/primitives';
import { Shield } from 'lucide-react';

const RISK_CATEGORIES = [
  { id: 'exposure', label: 'Position Exposure', status: 'DATA_UNAVAILABLE' },
  { id: 'correlation', label: 'Cross-Asset Correlation', status: 'DATA_UNAVAILABLE' },
  { id: 'volatility', label: 'Volatility Surface', status: 'DATA_UNAVAILABLE' },
  { id: 'drawdown', label: 'Drawdown Analysis', status: 'DATA_UNAVAILABLE' },
  { id: 'stress', label: 'Stress Testing', status: 'DATA_UNAVAILABLE' },
  { id: 'concentration', label: 'Concentration Risk', status: 'DATA_UNAVAILABLE' },
];

export const RiskPortfolioPanel: React.FC = () => {
  return (
    <GlassPanel style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Shield size={14} color="var(--aur-accent)" />
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--aur-ink-faint)',
            textTransform: 'uppercase',
          }}
        >
          Risk & Portfolio
        </span>
      </div>

      <div
        style={{
          padding: '10px 14px',
          background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.2)',
          borderRadius: 8,
          marginBottom: 12,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-negative)' }}>
          PORTFOLIO DATA UNAVAILABLE
        </div>
        <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
          No portfolio or position data connected. Connect a data source to enable risk analytics.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
        {RISK_CATEGORIES.map(cat => (
          <div
            key={cat.id}
            style={{
              padding: '10px 12px',
              background: 'var(--aur-bg-elevated)',
              borderRadius: 8,
              border: '1px solid var(--aur-border-soft)',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink)', marginBottom: 4 }}>
              {cat.label}
            </div>
            <div style={{ fontSize: 9, color: 'var(--aur-ink-faint)' }}>{cat.status}</div>
          </div>
        ))}
      </div>
    </GlassPanel>
  );
};

export default RiskPortfolioPanel;
