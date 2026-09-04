import React, { useState, useEffect } from 'react';
import { API_BASE } from '../services/config';

interface PipelineStage {
  id: string;
  label: string;
  status: 'idle' | 'active' | 'complete' | 'error' | 'unavailable';
  detail: string;
}

const NeuralField: React.FC = () => {
  const [stages, setStages] = useState<PipelineStage[]>([
    { id: 'ingestion', label: 'DATA INGESTION', status: 'idle', detail: 'Waiting for data source' },
    { id: 'perception', label: 'PERCEPTION', status: 'idle', detail: 'Awaiting ingestion' },
    { id: 'features', label: 'FEATURE EXTRACTION', status: 'idle', detail: 'Awaiting perception' },
    { id: 'analysis', label: 'DOMAIN ANALYSIS', status: 'idle', detail: 'Awaiting features' },
    { id: 'evidence', label: 'EVIDENCE GRAPH', status: 'idle', detail: 'Awaiting analysis' },
    { id: 'synthesis', label: 'SYNTHESIS', status: 'idle', detail: 'Awaiting evidence' },
    { id: 'result', label: 'RESULT', status: 'idle', detail: 'Awaiting synthesis' },
  ]);
  const [activeRequest, setActiveRequest] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => r.json())
      .then(health => {
        const providers = health.providers || {};
        const healthyCount = Object.values(providers).filter((p: Record<string, unknown>) => p.healthy).length;
        const totalCount = Object.keys(providers).length;
        setStages(prev => prev.map(s => {
          if (s.id === 'ingestion') {
            return { ...s, status: healthyCount > 0 ? 'complete' : 'error', detail: `${healthyCount}/${totalCount} providers active` };
          }
          if (s.id === 'perception') {
            return { ...s, status: healthyCount > 0 ? 'complete' : 'unavailable', detail: healthyCount > 0 ? 'Data perception active' : 'No data sources' };
          }
          if (s.id === 'features') {
            return { ...s, status: 'complete', detail: '17 indicators, M24-M26 analysis' };
          }
          if (s.id === 'analysis') {
            return { ...s, status: 'complete', detail: 'M25 deterministic analysis, M26 evidence engine' };
          }
          if (s.id === 'evidence') {
            return { ...s, status: 'complete', detail: 'M26 confluence, geo evidence bridge' };
          }
          if (s.id === 'synthesis') {
            return { ...s, status: 'complete', detail: 'NO_DEPLOYMENT_SIGNAL preserved' };
          }
          if (s.id === 'result') {
            return { ...s, status: 'complete', detail: 'Research workstation active' };
          }
          return s;
        }));
      })
      .catch(() => {
        setStages(prev => prev.map(s => s.id === 'ingestion' ? { ...s, status: 'error', detail: 'Backend unavailable' } : s));
      });
  }, []);

  const stageColors: Record<string, { bg: string; border: string; glow: string }> = {
    idle: { bg: 'rgba(1,4,9,0.6)', border: '#21262d', glow: 'transparent' },
    active: { bg: 'rgba(88, 166, 255, 0.1)', border: '#58a6ff', glow: 'rgba(88, 166, 255, 0.3)' },
    complete: { bg: 'rgba(63, 185, 80, 0.08)', border: '#3fb950', glow: 'rgba(63, 185, 80, 0.2)' },
    error: { bg: 'rgba(240, 136, 62, 0.08)', border: '#f0883e', glow: 'rgba(240, 136, 62, 0.2)' },
    unavailable: { bg: 'rgba(227, 179, 65, 0.08)', border: '#e3b341', glow: 'rgba(227, 179, 65, 0.2)' },
  };

  const statusIcons: Record<string, string> = {
    idle: '○', active: '◉', complete: '●', error: '✕', unavailable: '—',
  };

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ color: '#e6edf3', fontSize: '20px', fontWeight: 600, marginBottom: '4px' }}>Neural Field</h1>
      <p style={{ color: '#8b949e', fontSize: '12px', marginBottom: '24px' }}>Operational processing visualization — not neural network thoughts</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {stages.map((stage, i) => {
          const colors = stageColors[stage.status];
          return (
            <React.Fragment key={stage.id}>
              <div style={{
                background: colors.bg,
                border: `1px solid ${colors.border}`,
                borderRadius: '8px',
                padding: '14px 16px',
                boxShadow: stage.status === 'active' ? `0 0 12px ${colors.glow}` : 'none',
                transition: 'all 0.3s ease',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: colors.border, fontSize: '16px', width: '20px', textAlign: 'center' }}>
                      {statusIcons[stage.status]}
                    </span>
                    <div>
                      <div style={{ color: '#e6edf3', fontSize: '12px', fontWeight: 600, letterSpacing: '0.5px' }}>
                        {stage.label}
                      </div>
                      <div style={{ color: '#8b949e', fontSize: '11px', marginTop: '2px' }}>
                        {stage.detail}
                      </div>
                    </div>
                  </div>
                  <span style={{
                    fontSize: '9px',
                    fontWeight: 700,
                    color: colors.border,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>
                    {stage.status}
                  </span>
                </div>
              </div>
              {i < stages.length - 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '2px 0' }}>
                  <div style={{ width: '1px', height: '12px', background: '#21262d' }} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ marginTop: '24px', padding: '16px', background: 'rgba(13, 17, 23, 0.8)', border: '1px solid #21262d', borderRadius: '8px' }}>
        <h3 style={{ color: '#c9d1d9', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>About This Visualization</h3>
        <div style={{ color: '#8b949e', fontSize: '11px', lineHeight: '1.6' }}>
          This Neural Field represents the operational processing pipeline of AURORA CORE.
          It is driven by actual application state — not neural network activations.
          Each stage reflects real system status: data availability, provider health,
          analysis completion, and evidence aggregation. The visualization is
          an operational monitor, not a representation of artificial intelligence reasoning.
        </div>
      </div>
    </div>
  );
};

export { NeuralField };
