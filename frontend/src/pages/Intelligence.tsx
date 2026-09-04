import React, { useState } from 'react';
import { API_BASE } from '../services/config';

interface IntelligenceResult {
  step: string;
  status: 'complete' | 'pending' | 'unavailable';
  data: string;
}

const Intelligence: React.FC<{ symbol: string }> = ({ symbol }) => {
  const [results, setResults] = useState<IntelligenceResult[]>([]);
  const [loading, setLoading] = useState(false);

  const runAnalysis = async () => {
    setLoading(true);
    const items: IntelligenceResult[] = [];

    items.push({ step: 'REQUEST', status: 'complete', data: `Analysis requested for ${symbol}` });

    try {
      const res = await fetch(`${API_BASE}/market/${symbol}/analysis?timeframe=1D&limit=100`);
      if (res.ok) {
        const data = await res.json();
        items.push({ step: 'DATA', status: 'complete', data: `Received ${data.bars?.length || 0} bars from ${data.provider || 'unknown'}` });
        items.push({ step: 'ANALYSIS', status: 'complete', data: `Market regime: ${data.market_state?.regime || 'unknown'}. Volatility: ${data.market_state?.volatility_regime || 'unknown'}.` });
        items.push({ step: 'EVIDENCE', status: 'complete', data: `${data.evidence?.length || 0} evidence items collected. ${data.evidence?.filter((e: Record<string, unknown>) => e.polarity === 'bullish').length || 0} bullish, ${data.evidence?.filter((e: Record<string, unknown>) => e.polarity === 'bearish').length || 0} bearish.` });
        items.push({ step: 'SYNTHESIS', status: 'complete', data: `Confluence score: ${data.confluence?.score ?? 'N/A'}. ${data.confluence?.interpretation || 'No interpretation available.'}` });
        items.push({ step: 'RESULT', status: 'complete', data: `NO_DEPLOYMENT_SIGNAL. No trading recommendation derived.` });
      } else {
        items.push({ step: 'DATA', status: 'unavailable', data: 'API returned error' });
        items.push({ step: 'ANALYSIS', status: 'unavailable', data: 'Cannot analyze without data' });
      }
    } catch {
      items.push({ step: 'DATA', status: 'unavailable', data: 'Backend unavailable' });
      items.push({ step: 'ANALYSIS', status: 'unavailable', data: 'Cannot analyze without data' });
    }

    setResults(items);
    setLoading(false);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ color: '#e6edf3', fontSize: '20px', fontWeight: 600, marginBottom: '4px' }}>Intelligence</h1>
      <p style={{ color: '#8b949e', fontSize: '12px', marginBottom: '20px' }}>Request → Observation → Data → Analysis → Evidence → Synthesis → Result</p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', alignItems: 'center' }}>
        <span style={{ color: '#c9d1d9', fontSize: '12px' }}>Asset:</span>
        <span style={{ color: '#26a69a', fontSize: '13px', fontWeight: 600 }}>{symbol}</span>
        <button onClick={runAnalysis} disabled={loading} style={btnStyle}>
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>

      {results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {results.map((r, i) => (
            <React.Fragment key={i}>
              <div style={{
                background: r.status === 'complete' ? 'rgba(63, 185, 80, 0.05)' : 'rgba(240, 136, 62, 0.05)',
                border: `1px solid ${r.status === 'complete' ? 'rgba(63, 185, 80, 0.2)' : 'rgba(240, 136, 62, 0.2)'}`,
                borderRadius: '6px',
                padding: '10px 12px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: '#e6edf3', fontSize: '11px', fontWeight: 600, letterSpacing: '0.5px' }}>{r.step}</span>
                  <span style={{ color: r.status === 'complete' ? '#3fb950' : '#f0883e', fontSize: '9px', fontWeight: 700 }}>{r.status}</span>
                </div>
                <div style={{ color: '#8b949e', fontSize: '11px', marginTop: '4px' }}>{r.data}</div>
              </div>
              {i < results.length - 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '1px 0' }}>
                  <div style={{ width: '1px', height: '8px', background: '#21262d' }} />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(13, 17, 23, 0.8)', border: '1px solid #21262d', borderRadius: '8px' }}>
        <div style={{ color: '#8b949e', fontSize: '11px' }}>
          This intelligence workspace connects request → observation → data → analysis → evidence → synthesis → result.
          It does not simulate AI reasoning. It shows actual processing events and state.
          NO_DEPLOYMENT_SIGNAL preserved. No trading recommendations derived.
        </div>
      </div>
    </div>
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

export { Intelligence };
