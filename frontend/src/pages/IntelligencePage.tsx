import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { GlassPanel, StatusBadge, ConfidenceIndicator, LoadingState, EmptyState } from '../components/shell/primitives';
import { listInvestigations } from '../services/investigations';
import { listEvidence } from '../services/evidence';
import { useEventBus } from '../lib/eventBus';
import type { Investigation, EvidenceItem, Claim } from '../types/domain';

// Demo claims — no claim/hypothesis backend exists yet; kept local since only
// this page consumes them. Clearly DEMO via StatusBadge, same as elsewhere.
const DEMO_CLAIMS: Claim[] = [
  { id: 'cl_01', investigationId: 'inv_01', text: 'Realized volatility has compressed relative to the pre-halving baseline.', supportingEvidenceIds: ['ev_03'], contradictingEvidenceIds: ['ev_04'], confidence: 'medium' },
  { id: 'cl_02', investigationId: 'inv_02', text: 'Vegetation index decline in AOI-7 is concentrated in the northern third of the region.', supportingEvidenceIds: ['ev_01', 'ev_02'], contradictingEvidenceIds: [], confidence: 'high' },
];

const STAGES = ['Question', 'Data', 'Evidence', 'Analysis', 'Conclusion'];

export const IntelligencePage: React.FC = () => {
  const [investigations, setInvestigations] = useState<Investigation[] | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { emit } = useEventBus();

  useEffect(() => {
    emit('navigation', 'Intelligence opened', 'live');
    listInvestigations().then(r => { setInvestigations(r.data); if (r.data.length) setSelectedId(r.data[0].id); });
    listEvidence().then(r => setEvidence(r.data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = investigations?.find(i => i.id === selectedId) ?? null;
  const relatedEvidence = useMemo(() => (evidence ?? []).filter(e => e.investigationId === selectedId), [evidence, selectedId]);
  const relatedClaims = useMemo(() => DEMO_CLAIMS.filter(c => c.investigationId === selectedId), [selectedId]);

  return (
    <div>
      <GlassPanel style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
          {STAGES.map((s, i) => (
            <React.Fragment key={s}>
              <span style={{ fontSize: 11, fontWeight: 600, color: i === 0 ? 'var(--aur-accent)' : 'var(--aur-ink-faint)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s}</span>
              {i < STAGES.length - 1 && <ArrowRight size={12} color="var(--aur-ink-faint)" />}
            </React.Fragment>
          ))}
        </div>
        <select
          value={selectedId ?? ''}
          onChange={e => setSelectedId(e.target.value)}
          style={{ width: '100%', background: 'rgba(0,0,0,0.28)', border: '1px solid var(--aur-border-soft)', borderRadius: 9, padding: '10px 12px', color: 'var(--aur-ink)', fontSize: 13.5, outline: 'none' }}
        >
          {investigations?.map(inv => <option key={inv.id} value={inv.id}>{inv.title}</option>)}
        </select>
      </GlassPanel>

      {investigations === null && <LoadingState label="Loading investigations…" />}

      {selected && (
        <>
          <GlassPanel style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Question</div>
            <p style={{ fontSize: 15, lineHeight: 1.5 }}>{selected.question}</p>
            <div style={{ display: 'flex', gap: 14, marginTop: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <StatusBadge origin="demo" small />
              <ConfidenceIndicator band={selected.confidence} />
              <span style={{ fontSize: 11.5, color: 'var(--aur-ink-faint)' }}>{selected.evidenceCount} evidence items linked · updated {new Date(selected.updatedAt).toLocaleDateString()}</span>
            </div>
          </GlassPanel>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <GlassPanel>
              <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Supporting evidence</h2>
              {relatedEvidence.length === 0 && <EmptyState message="No linked evidence for this investigation." />}
              {relatedEvidence.map(ev => (
                <div key={ev.id} style={{ padding: '9px 2px', borderBottom: '1px solid var(--aur-border-soft)' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 500 }}>{ev.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', marginTop: 2 }}>{ev.source}</div>
                </div>
              ))}
            </GlassPanel>

            <GlassPanel>
              <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Claims &amp; conclusions</h2>
              {relatedClaims.length === 0 && <EmptyState message="No claims synthesized yet for this investigation." />}
              {relatedClaims.map(cl => (
                <div key={cl.id} style={{ padding: '10px 2px', borderBottom: '1px solid var(--aur-border-soft)' }}>
                  <p style={{ fontSize: 12.5, lineHeight: 1.5 }}>{cl.text}</p>
                  <div style={{ display: 'flex', gap: 10, marginTop: 6, alignItems: 'center' }}>
                    <ConfidenceIndicator band={cl.confidence} showLabel={false} />
                    <span style={{ fontSize: 10.5, color: 'var(--aur-positive)' }}>{cl.supportingEvidenceIds.length} supporting</span>
                    {cl.contradictingEvidenceIds.length > 0 && <span style={{ fontSize: 10.5, color: 'var(--aur-negative)' }}>{cl.contradictingEvidenceIds.length} conflicting</span>}
                  </div>
                </div>
              ))}
            </GlassPanel>
          </div>
        </>
      )}
    </div>
  );
};
