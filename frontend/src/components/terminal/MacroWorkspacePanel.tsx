/**
 * AURORA Terminal — Macro Workspace Panel.
 *
 * Architecture for Global/Macro data. Shows DATA_UNAVAILABLE when no provider connected.
 * Every real observation must have: source, timestamp, instrument, value, unit, frequency, provenance.
 *
 * NO_DEPLOYMENT_SIGNAL. No fabricated data.
 */

import React from 'react';
import { GlassPanel } from '../shell/primitives';
import { Globe } from 'lucide-react';

const MACRO_CATEGORIES = [
  { id: 'inflation', label: 'Inflation', series: ['CPI YoY', 'Core CPI', 'PCE'] },
  { id: 'interest-rates', label: 'Interest Rates', series: ['Fed Funds', '10Y Yield', '2Y Yield'] },
  { id: 'employment', label: 'Employment', series: ['NFP', 'Unemployment Rate', 'Wage Growth'] },
  { id: 'gdp', label: 'GDP', series: ['GDP QoQ', 'GDP YoY'] },
  { id: 'central-bank', label: 'Central Bank', series: ['ECB Rate', 'BOJ Rate', 'PBOC Rate'] },
  { id: 'currencies', label: 'Currencies', series: ['DXY', 'EUR/USD', 'USD/JPY'] },
  { id: 'commodities', label: 'Commodities', series: ['Gold', 'Crude Oil', 'Copper'] },
  { id: 'yields', label: 'Sovereign Yields', series: ['US 10Y', 'DE 10Y', 'JP 10Y'] },
];

export const MacroWorkspacePanel: React.FC = () => {
  return (
    <GlassPanel style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Globe size={14} color="var(--aur-accent)" />
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--aur-ink-faint)',
            textTransform: 'uppercase',
          }}
        >
          Global / Macro
        </span>
      </div>

      {/* Provider status */}
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
          MACRO DATA UNAVAILABLE
        </div>
        <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
          No macro data provider connected. Connect a provider to enable macro intelligence.
        </div>
      </div>

      {/* Category grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
        {MACRO_CATEGORIES.map(cat => (
          <div
            key={cat.id}
            style={{
              padding: '10px 12px',
              background: 'var(--aur-bg-elevated)',
              borderRadius: 8,
              border: '1px solid var(--aur-border-soft)',
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink)', marginBottom: 4 }}>
              {cat.label}
            </div>
            {cat.series.map(s => (
              <div
                key={s}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 10,
                  color: 'var(--aur-ink-dim)',
                  padding: '2px 0',
                }}
              >
                <span>{s}</span>
                <span style={{ color: 'var(--aur-ink-faint)' }}>--</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </GlassPanel>
  );
};

export default MacroWorkspacePanel;
