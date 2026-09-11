/**
 * AURORA Terminal — Macro Workspace Panel.
 *
 * Fetches real macro data from FRED via backend data fabric.
 * Shows DATA_UNAVAILABLE when no provider connected.
 * Never fabricates macroeconomic values.
 */

import React, { useState, useEffect } from 'react';
import { GlassPanel } from '../shell/primitives';
import { Globe, TrendingUp, TrendingDown } from 'lucide-react';
import {
  getMacroStatus,
  getMacroSeries,
  type ProviderStatus,
  type MacroSeries,
} from '../../services/dataFabric';

const MACRO_SERIES: { id: string; label: string; category: string }[] = [
  { id: 'CPIAUCSL', label: 'US CPI', category: 'inflation' },
  { id: 'FEDFUNDS', label: 'Fed Funds Rate', category: 'interest-rates' },
  { id: 'DGS10', label: 'US 10Y Yield', category: 'yields' },
  { id: 'DGS2', label: 'US 2Y Yield', category: 'yields' },
  { id: 'UNRATE', label: 'Unemployment Rate', category: 'employment' },
  { id: 'DCOILWTICO', label: 'Crude Oil WTI', category: 'commodities' },
  { id: 'GOLDAMGBD228NLBM', label: 'Gold Price', category: 'commodities' },
  { id: 'A191RL1Q225SBEA', label: 'Real GDP Growth', category: 'gdp' },
];

function MacroValue({ series }: { series: MacroSeries | null; loading: boolean }) {
  if (loading) return <span style={{ color: 'var(--aur-ink-faint)' }}>...</span>;
  if (!series || series.latest_value === null) {
    return <span style={{ color: 'var(--aur-ink-faint)' }}>--</span>;
  }
  return (
    <span style={{ fontWeight: 600, color: 'var(--aur-ink)' }}>
      {series.latest_value.toFixed(2)}
      <span style={{ fontSize: 9, color: 'var(--aur-ink-dim)', marginLeft: 2 }}>{series.unit}</span>
    </span>
  );
}

export const MacroWorkspacePanel: React.FC = () => {
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [seriesData, setSeriesData] = useState<Record<string, MacroSeries | null>>({});
  const [loadingSeries, setLoadingSeries] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getMacroStatus().then(s => {
      setStatus(s);
      if (s.state === 'READY') {
        MACRO_SERIES.forEach(ms => {
          setLoadingSeries(prev => ({ ...prev, [ms.id]: true }));
          getMacroSeries(ms.id)
            .then(data => setSeriesData(prev => ({ ...prev, [ms.id]: data })))
            .catch(() => setSeriesData(prev => ({ ...prev, [ms.id]: null })))
            .finally(() => setLoadingSeries(prev => ({ ...prev, [ms.id]: false })));
        });
      }
    }).catch(() => {});
  }, []);

  const connected = status?.state === 'READY';

  return (
    <GlassPanel style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Globe size={14} color="var(--aur-accent)" />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--aur-ink-faint)', textTransform: 'uppercase' }}>
          Global / Macro
        </span>
        {status && (
          <span style={{
            marginLeft: 'auto', fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 4,
            background: connected ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.1)',
            color: connected ? 'var(--aur-positive)' : 'var(--aur-negative)',
          }}>
            {connected ? 'CONNECTED' : status.state}
          </span>
        )}
      </div>

      {!connected ? (
        <div style={{
          padding: '10px 14px', background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.2)', borderRadius: 8, marginBottom: 12,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-negative)' }}>
            MACRO DATA UNAVAILABLE
          </div>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
            {status?.detail || 'No macro provider connected'}
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
          {MACRO_SERIES.map(ms => {
            const data = seriesData[ms.id];
            const loading = loadingSeries[ms.id];
            return (
              <div key={ms.id} style={{
                padding: '10px 12px', background: 'var(--aur-bg-elevated)',
                borderRadius: 8, border: '1px solid var(--aur-border-soft)',
              }}>
                <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginBottom: 2 }}>{ms.label}</div>
                <MacroValue series={data} loading={loading} />
                {data?.latest_date && (
                  <div style={{ fontSize: 9, color: 'var(--aur-ink-faint)', marginTop: 2 }}>
                    {data.latest_date}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {connected && (
        <div style={{ marginTop: 8, fontSize: 9, color: 'var(--aur-ink-faint)' }}>
          Source: FRED (Federal Reserve Economic Data)
        </div>
      )}
    </GlassPanel>
  );
};

export default MacroWorkspacePanel;
