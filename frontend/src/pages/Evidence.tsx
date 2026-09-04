import React, { useState, useCallback } from 'react';
import { API_BASE } from '../services/config';

interface EvidenceRecord {
  id: string;
  domain: string;
  classification: string;
  polarity: string;
  strength: string;
  value: string;
  description: string;
  source: string;
  timestamp: string;
}

const Evidence: React.FC = () => {
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState<string>('all');

  const loadEvidence = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/health`);
      const health = await res.json();
      const providers = health.providers || {};
      const items: EvidenceRecord[] = [];
      Object.entries(providers).forEach(([name, info]: [string, Record<string, unknown>]) => {
        items.push({
          id: `provider_${name}`,
          domain: 'data_provider',
          classification: 'INFRASTRUCTURE',
          polarity: 'NEUTRAL',
          strength: (info.healthy as boolean) ? 'MODERATE' : 'ABSENT',
          value: `${name}: ${(info.healthy as boolean) ? 'HEALTHY' : 'DOWN'}`,
          description: `Data provider ${name} status. ${(info.consecutive_failures as number) || 0} consecutive failures.`,
          source: name,
          timestamp: (info.last_success as string) || new Date().toISOString(),
        });
      });
      items.push({
        id: 'integrity_no_deploy',
        domain: 'integrity',
        classification: 'CONSTRAINT',
        polarity: 'NEUTRAL',
        strength: 'STRONG',
        value: 'NO_DEPLOYMENT_SIGNAL',
        description: 'Research conclusion: NO_DEPLOYMENT_SIGNAL is immutable. No trading signals derived.',
        source: 'aurora_core',
        timestamp: new Date().toISOString(),
      });
      setEvidence(items);
    } catch {
      setEvidence([{
        id: 'error',
        domain: 'system',
        classification: 'ERROR',
        polarity: 'UNAVAILABLE',
        strength: 'ABSENT',
        value: 'BACKEND UNAVAILABLE',
        description: 'Cannot load evidence. Backend is unreachable.',
        source: 'aurora_core',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  }, []);

  const filtered = selectedDomain === 'all' ? evidence : evidence.filter(e => e.domain === selectedDomain);
  const domains = [...new Set(evidence.map(e => e.domain))];

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ color: '#e6edf3', fontSize: '20px', fontWeight: 600, marginBottom: '4px' }}>Evidence</h1>
      <p style={{ color: '#8b949e', fontSize: '12px', marginBottom: '20px' }}>Provenance-tracked observations and system evidence</p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <button onClick={loadEvidence} disabled={loading} style={btnStyle}>
          {loading ? 'Loading...' : 'Load Evidence'}
        </button>
        <select value={selectedDomain} onChange={e => setSelectedDomain(e.target.value)} style={selectStyle}>
          <option value="all">All Domains</option>
          {domains.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filtered.map(item => (
          <div key={item.id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <span style={{ color: '#26a69a', fontSize: '12px', fontWeight: 600 }}>{item.value}</span>
                <StrengthBadge strength={item.strength} />
              </div>
              <span style={{ color: '#8b949e', fontSize: '10px' }}>{new Date(item.timestamp).toLocaleString()}</span>
            </div>
            <div style={{ color: '#c9d1d9', fontSize: '12px', marginBottom: '6px' }}>{item.description}</div>
            <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: '#8b949e' }}>
              <span>Domain: {item.domain}</span>
              <span>Source: {item.source}</span>
              <span>Classification: {item.classification}</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && !loading && (
          <div style={{ color: '#8b949e', fontSize: '12px', padding: '40px', textAlign: 'center' }}>
            No evidence loaded. Click "Load Evidence" to query system state.
          </div>
        )}
      </div>
    </div>
  );
};

const StrengthBadge: React.FC<{ strength: string }> = ({ strength }) => {
  const colors: Record<string, { bg: string; border: string; text: string }> = {
    STRONG: { bg: 'rgba(63, 185, 80, 0.1)', border: 'rgba(63, 185, 80, 0.3)', text: '#3fb950' },
    MODERATE: { bg: 'rgba(88, 166, 255, 0.1)', border: 'rgba(88, 166, 255, 0.3)', text: '#58a6ff' },
    WEAK: { bg: 'rgba(227, 179, 65, 0.1)', border: 'rgba(227, 179, 65, 0.3)', text: '#e3b341' },
    ABSENT: { bg: 'rgba(240, 136, 62, 0.1)', border: 'rgba(240, 136, 62, 0.3)', text: '#f0883e' },
  };
  const c = colors[strength] || colors.ABSENT;
  return (
    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '9px', fontWeight: 700, background: c.bg, border: `1px solid ${c.border}`, color: c.text }}>
      {strength}
    </span>
  );
};

const btnStyle: React.CSSProperties = {
  background: '#21262d',
  border: '1px solid #30363d',
  borderRadius: '6px',
  padding: '6px 12px',
  color: '#c9d1d9',
  fontSize: '12px',
  cursor: 'pointer',
};

const selectStyle: React.CSSProperties = {
  background: '#0d1117',
  border: '1px solid #30363d',
  borderRadius: '6px',
  padding: '6px 12px',
  color: '#c9d1d9',
  fontSize: '12px',
};

const cardStyle: React.CSSProperties = {
  background: 'rgba(13, 17, 23, 0.8)',
  border: '1px solid #21262d',
  borderRadius: '8px',
  padding: '12px',
};

export { Evidence };
