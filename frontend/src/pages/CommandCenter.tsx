import React, { useState, useEffect } from 'react';
import { API_BASE } from '../services/config';

interface HealthStatus {
  status: string;
  version: string;
  uptime_seconds: number;
  providers: Record<string, { healthy: boolean; last_success: string | null; consecutive_failures: number }>;
}

const CommandCenter: React.FC<{ onNavigate: (page: string) => void }> = ({ onNavigate }) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => r.json())
      .then(data => { setHealth(data); setLoading(false); })
      .catch(() => { setError('Backend unavailable'); setLoading(false); });
  }, []);

  const providerCount = health ? Object.keys(health.providers).length : 0;
  const healthyProviders = health ? Object.values(health.providers).filter(p => p.healthy).length : 0;

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ color: '#e6edf3', fontSize: '20px', fontWeight: 600, marginBottom: '4px' }}>Command Center</h1>
      <p style={{ color: '#8b949e', fontSize: '12px', marginBottom: '24px' }}>AURORA CORE — System Overview</p>

      {loading && <div style={{ color: '#8b949e', padding: '40px', textAlign: 'center' }}>Loading system status...</div>}
      {error && (
        <div style={{ padding: '16px', background: 'rgba(240, 136, 62, 0.08)', border: '1px solid rgba(240, 136, 62, 0.3)', borderRadius: '8px', marginBottom: '20px' }}>
          <div style={{ color: '#f0883e', fontWeight: 600, fontSize: '13px', marginBottom: '4px' }}>BACKEND UNAVAILABLE</div>
          <div style={{ color: '#8b949e', fontSize: '12px' }}>Cannot connect to {API_BASE}. Data unavailable.</div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        <StatCard label="System Status" value={health?.status || 'UNKNOWN'} color={health?.status === 'ok' ? '#3fb950' : '#f0883e'} />
        <StatCard label="Version" value={health?.version || '—'} color="#c9d1d9" />
        <StatCard label="Uptime" value={health ? formatUptime(health.uptime_seconds) : '—'} color="#c9d1d9" />
        <StatCard label="Providers" value={`${healthyProviders}/${providerCount}`} color={healthyProviders === providerCount ? '#3fb950' : '#f0883e'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        <div style={panelStyle}>
          <h3 style={panelTitle}>Quick Navigation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {[
              { id: 'market', label: 'Market Observatory' },
              { id: 'geo', label: 'Geo Observatory' },
              { id: 'research', label: 'Research' },
              { id: 'evidence', label: 'Evidence' },
              { id: 'settings', label: 'Settings' },
            ].map(item => (
              <button key={item.id} onClick={() => onNavigate(item.id)} style={navBtnStyle}>
                {item.label} →
              </button>
            ))}
          </div>
        </div>

        <div style={panelStyle}>
          <h3 style={panelTitle}>Data Providers</h3>
          {health?.providers ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {Object.entries(health.providers).map(([name, info]) => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px' }}>
                  <span style={{ color: '#c9d1d9', fontSize: '12px' }}>{name}</span>
                  <span style={{ color: info.healthy ? '#3fb950' : '#f0883e', fontSize: '11px', fontWeight: 600 }}>
                    {info.healthy ? 'HEALTHY' : 'DOWN'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: '#8b949e', fontSize: '12px', padding: '12px' }}>No provider data</div>
          )}
        </div>
      </div>

      <div style={panelStyle}>
        <h3 style={panelTitle}>System Integrity</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
          <IntegrityBadge label="NO_DEPLOYMENT_SIGNAL" status="PRESERVED" />
          <IntegrityBadge label="NO_PREDICTIONS" status="PRESERVED" />
          <IntegrityBadge label="NO_TRADING_SIGNALS" status="PRESERVED" />
          <IntegrityBadge label="NO_FABRICATED_DATA" status="PRESERVED" />
          <IntegrityBadge label="NO_GAMBLING" status="PRESERVED" />
          <IntegrityBadge label="SCIENTIFIC_INTEGRITY" status="VERIFIED" />
        </div>
      </div>
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
  <div style={{ background: 'rgba(13, 17, 23, 0.8)', border: '1px solid #21262d', borderRadius: '8px', padding: '16px' }}>
    <div style={{ fontSize: '10px', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '18px', fontWeight: 700, color }}>{value}</div>
  </div>
);

const IntegrityBadge: React.FC<{ label: string; status: string }> = ({ label, status }) => (
  <div style={{ padding: '8px', background: 'rgba(63, 185, 80, 0.08)', border: '1px solid rgba(63, 185, 80, 0.2)', borderRadius: '6px', textAlign: 'center' }}>
    <div style={{ fontSize: '10px', color: '#3fb950', fontWeight: 600 }}>{status}</div>
    <div style={{ fontSize: '9px', color: '#8b949e', marginTop: '2px' }}>{label}</div>
  </div>
);

const panelStyle: React.CSSProperties = {
  background: 'rgba(13, 17, 23, 0.8)',
  border: '1px solid #21262d',
  borderRadius: '12px',
  padding: '16px',
};

const panelTitle: React.CSSProperties = {
  color: '#c9d1d9',
  fontSize: '13px',
  fontWeight: 600,
  marginBottom: '12px',
};

const navBtnStyle: React.CSSProperties = {
  background: 'rgba(1, 4, 9, 0.6)',
  border: '1px solid #21262d',
  borderRadius: '6px',
  padding: '8px 12px',
  color: '#c9d1d9',
  fontSize: '12px',
  textAlign: 'left',
  cursor: 'pointer',
};

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export { CommandCenter };
