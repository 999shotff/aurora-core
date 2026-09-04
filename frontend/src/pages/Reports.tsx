import React, { useState } from 'react';
import { API_BASE } from '../services/config';

interface ReportSection {
  title: string;
  content: string;
  status: 'available' | 'unavailable' | 'insufficient';
}

const Reports: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC-USD');
  const [generating, setGenerating] = useState(false);
  const [report, setReport] = useState<ReportSection[] | null>(null);

  const generateReport = async () => {
    setGenerating(true);
    setReport(null);
    try {
      const sections: ReportSection[] = [];

      const healthRes = await fetch(`${API_BASE}/health`);
      const health = await healthRes.json();
      sections.push({
        title: 'System Status',
        content: `Backend: ${health.status}. Version: ${health.version}. Uptime: ${Math.floor(health.uptime_seconds / 60)}m.`,
        status: 'available',
      });

      try {
        const quoteRes = await fetch(`${API_BASE}/market/${selectedSymbol}/quote`);
        if (quoteRes.ok) {
          const quote = await quoteRes.json();
          sections.push({
            title: 'Market Data',
            content: `${selectedSymbol}: $${quote.price.toFixed(2)} (${quote.changePct >= 0 ? '+' : ''}${quote.changePct.toFixed(2)}%). Volume: ${quote.volume?.toLocaleString() || 'N/A'}.`,
            status: 'available',
          });
        } else {
          sections.push({ title: 'Market Data', content: 'Quote unavailable.', status: 'unavailable' });
        }
      } catch {
        sections.push({ title: 'Market Data', content: 'Backend unavailable for quote.', status: 'unavailable' });
      }

      sections.push({
        title: 'Geo Evidence',
        content: 'GIBS provides RGB visualization only. Scientific spectral indices (NDVI/NDWI/NDBI/EVI) require NIR/SWIR bands. DATA_UNAVAILABLE for all spectral indices.',
        status: 'unavailable',
      });

      sections.push({
        title: 'Research Status',
        content: 'NO_DEPLOYMENT_SIGNAL preserved. No trading signals derived. All predictive research halted per M15 conclusion.',
        status: 'available',
      });

      sections.push({
        title: 'Limitations',
        content: 'This report is auto-generated from live system state. It does not contain financial advice, predictions, or trading recommendations. All analysis is deterministic.',
        status: 'available',
      });

      setReport(sections);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ color: '#e6edf3', fontSize: '20px', fontWeight: 600, marginBottom: '4px' }}>Reports</h1>
      <p style={{ color: '#8b949e', fontSize: '12px', marginBottom: '20px' }}>Generate system reports from live state</p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', alignItems: 'center' }}>
        <select value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)} style={selectStyle}>
          <option value="BTC-USD">BTC-USD</option>
          <option value="SPY">SPY</option>
          <option value="QQQ">QQQ</option>
          <option value="GOLD">GOLD</option>
        </select>
        <button onClick={generateReport} disabled={generating} style={btnStyle}>
          {generating ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {report && (
        <div style={{ background: 'rgba(13, 17, 23, 0.8)', border: '1px solid #21262d', borderRadius: '12px', padding: '20px' }}>
          <div style={{ borderBottom: '1px solid #21262d', paddingBottom: '12px', marginBottom: '16px' }}>
            <h2 style={{ color: '#e6edf3', fontSize: '16px', fontWeight: 600, margin: 0 }}>AURORA CORE Report</h2>
            <div style={{ color: '#8b949e', fontSize: '11px', marginTop: '4px' }}>
              Generated: {new Date().toISOString()} | Asset: {selectedSymbol}
            </div>
          </div>
          {report.map((section, i) => (
            <div key={i} style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <h3 style={{ color: '#c9d1d9', fontSize: '13px', fontWeight: 600, margin: 0 }}>{section.title}</h3>
                <StatusTag status={section.status} />
              </div>
              <div style={{ color: '#8b949e', fontSize: '12px', lineHeight: '1.6' }}>{section.content}</div>
            </div>
          ))}
          <div style={{ borderTop: '1px solid #21262d', paddingTop: '12px', marginTop: '16px' }}>
            <div style={{ color: '#8b949e', fontSize: '10px' }}>
              Disclaimer: This report is auto-generated from live system state. It does not constitute financial advice.
              All analysis is deterministic. NO_DEPLOYMENT_SIGNAL preserved.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatusTag: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, { bg: string; text: string }> = {
    available: { bg: 'rgba(63, 185, 80, 0.1)', text: '#3fb950' },
    unavailable: { bg: 'rgba(240, 136, 62, 0.1)', text: '#f0883e' },
    insufficient: { bg: 'rgba(227, 179, 65, 0.1)', text: '#e3b341' },
  };
  const c = colors[status] || colors.unavailable;
  return (
    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '9px', fontWeight: 700, background: c.bg, color: c.text, textTransform: 'uppercase' }}>
      {status}
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

export { Reports };
