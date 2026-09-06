import React, { useEffect, useState } from 'react';
import { GlassPanel, LoadingState, EmptyState } from '../components/shell/primitives';
import { listInvestigations, getInvestigationFindings, getInvestigationResult } from '../services/investigations';
import { useEventBus } from '../lib/eventBus';
import type { InvestigationSummary, InvestigationFinding } from '../services/investigations';

const STAGES = ['Question', 'Data', 'Evidence', 'Analysis', 'Conclusion'];

const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#9096A8', PLANNING: '#7C9EFF', MEMORY_RETRIEVAL: '#7C9EFF', GAP_ANALYSIS: '#7C9EFF',
  INVESTIGATING: '#FBBF24', ANALYZING: '#FBBF24', COMPARING: '#FBBF24', SUFFICIENCY_CHECK: '#FBBF24',
  VALIDATING: '#A78BFA', SYNTHESIZING: '#A78BFA', COMPLETE: '#34D399', PARTIAL: '#FBBF24',
  ABSTAINED: '#9096A8', FAILED: '#F87171', CANCELLED: '#9096A8',
};

export const IntelligencePage: React.FC = () => {
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [findings, setFindings] = useState<InvestigationFinding[]>([]);
  const [executiveSummary, setExecutiveSummary] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const { emit } = useEventBus();

  useEffect(() => {
    emit('navigation', 'Intelligence opened', 'live');
    listInvestigations({ limit: 50 })
      .then(r => {
        const invs = r.investigations || [];
        setInvestigations(invs);
        if (invs.length) setSelectedId(invs[0].investigation_id);
      })
      .catch(() => setInvestigations([]))
      .finally(() => setLoading(false));
  }, [emit]);

  useEffect(() => {
    if (!selectedId) return;
    getInvestigationFindings(selectedId)
      .then(r => setFindings(r.findings || []))
      .catch(() => setFindings([]));
    getInvestigationResult(selectedId)
      .then(r => setExecutiveSummary(r.result?.executive_summary || ''))
      .catch(() => setExecutiveSummary(''));
  }, [selectedId]);

  const selected = investigations.find(i => i.investigation_id === selectedId) ?? null;

  return (
    <div>
      <GlassPanel style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
          {STAGES.map((s, i) => (
            <React.Fragment key={s}>
              <span style={{ fontSize: 11, fontWeight: 600, color: i === 0 ? 'var(--aur-accent)' : 'var(--aur-ink-faint)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s}</span>
              {i < STAGES.length - 1 && <span style={{ color: 'var(--aur-ink-faint)' }}>→</span>}
            </React.Fragment>
          ))}
        </div>
        <select
          value={selectedId ?? ''}
          onChange={e => setSelectedId(e.target.value)}
          style={{ width: '100%', background: 'rgba(0,0,0,0.28)', border: '1px solid var(--aur-border-soft)', borderRadius: 9, padding: '10px 12px', color: 'var(--aur-ink)', fontSize: 13.5, outline: 'none' }}
        >
          {investigations.map(inv => (
            <option key={inv.investigation_id} value={inv.investigation_id}>
              {inv.query.slice(0, 80)}{inv.query.length > 80 ? '...' : ''}
            </option>
          ))}
        </select>
      </GlassPanel>

      {loading && <LoadingState label="Loading investigations…" />}

      {!loading && investigations.length === 0 && (
        <EmptyState message="No investigations yet" hint="Create one in Investigation Center" />
      )}

      {selected && (
        <>
          <GlassPanel style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Question</div>
            <p style={{ fontSize: 15, lineHeight: 1.5 }}>{selected.query}</p>
            <div style={{ display: 'flex', gap: 14, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, background: STATUS_COLORS[selected.status] || '#9096A8', color: '#000' }}>
                {selected.status}
              </span>
              <span style={{ fontSize: 11.5, color: 'var(--aur-ink-dim)' }}>
                {selected.domain} · {selected.evidence_count} evidence · {selected.findings_count} findings
              </span>
            </div>
          </GlassPanel>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <GlassPanel>
              <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Findings</h2>
              {findings.length === 0 && <EmptyState message="No findings yet" />}
              {findings.map(f => (
                <div key={f.finding_id} style={{ padding: '9px 2px', borderBottom: '1px solid var(--aur-border-soft)' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 500 }}>{f.statement}</div>
                  <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', marginTop: 2 }}>
                    {f.classification} · {(f.confidence * 100).toFixed(0)}% confidence
                  </div>
                </div>
              ))}
            </GlassPanel>

            <GlassPanel>
              <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Executive Summary</h2>
              {executiveSummary ? (
                <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--aur-ink)' }}>{executiveSummary}</p>
              ) : (
                <EmptyState message="No summary available" hint="Summary generated after investigation completes" />
              )}
            </GlassPanel>
          </div>
        </>
      )}
    </div>
  );
};
