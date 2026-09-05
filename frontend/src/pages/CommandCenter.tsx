import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowUpRight, Radar } from 'lucide-react';
import { GlassPanel, MetricCard, StatusBadge, ConfidenceIndicator, LoadingState } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import { listInvestigations } from '../services/investigations';
import { listEvidence } from '../services/evidence';
import type { Investigation, EvidenceItem, ProcessingEvent } from '../types/domain';

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const EVENT_KIND_LABEL: Record<ProcessingEvent['kind'], string> = {
  connection: 'Connection',
  data_fetch: 'Data',
  indicator_toggle: 'Indicator',
  structure_analysis: 'Structure',
  navigation: 'Navigation',
  evidence_indexed: 'Evidence',
  synthesis: 'Synthesis',
};

export const CommandCenter: React.FC = () => {
  const { events, emit } = useEventBus();
  const [investigations, setInvestigations] = useState<Investigation[] | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[] | null>(null);

  useEffect(() => {
    emit('navigation', 'Command Center opened', 'live');
    listInvestigations().then(r => setInvestigations(r.data)).catch(() => setInvestigations([]));
    listEvidence().then(r => setEvidence(r.data)).catch(() => setEvidence([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const active = investigations?.filter(i => i.status === 'active') ?? [];
  const recentEvidence = (evidence ?? []).slice().sort((a, b) => +new Date(b.timestamp) - +new Date(a.timestamp)).slice(0, 5);

  return (
    <div>
      {/* Hero: active session summary — real event-bus count, demo investigation set */}
      <section className="aur-glass aur-glass--strong aur-glass--radial aur-glass--lg" style={{
        position: 'relative', padding: '28px 28px 24px', marginBottom: 18, overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', inset: '-40%', background: 'radial-gradient(closest-side, rgba(124,158,255,0.28), transparent 70%), radial-gradient(closest-side, rgba(255,138,101,0.2), transparent 70%)', backgroundRepeat: 'no-repeat', backgroundSize: '60% 60%, 55% 55%', backgroundPosition: '15% 25%, 80% 70%', filter: 'blur(60px)', zIndex: 0, opacity: 0.7 }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <Radar size={16} color="var(--aur-accent)" />
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Active intelligence session</span>
            <StatusBadge origin="demo" small />
          </div>
          <div style={{ fontSize: 'clamp(24px, 3.4vw, 32px)', fontWeight: 600, fontFamily: 'var(--aur-font-display)', letterSpacing: '-0.01em', marginBottom: 6 }}>
            {active.length} active investigation{active.length === 1 ? '' : 's'} across market & geo domains
          </div>
          <p style={{ fontSize: 13, color: 'var(--aur-ink-dim)', maxWidth: 640 }}>
            Investigation and evidence records shown here are demo-adapter data — no investigation backend is wired up yet.
            System activity below reflects real application events from this session.
          </p>
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 14 }}>
        <MetricCard label="Active investigations" value={String(active.length)} origin="demo" />
        <MetricCard label="Evidence indexed" value={String(evidence?.length ?? 0)} origin="demo" />
        <MetricCard label="Session events" value={String(events.length)} origin="live" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 1fr', gap: 14 }}>
        {/* Real system activity feed */}
        <GlassPanel>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Activity size={15} color="var(--aur-accent)" />
            <h2 style={{ fontSize: 15, fontWeight: 600 }}>System activity</h2>
            <StatusBadge origin="live" small />
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--aur-ink-faint)', marginBottom: 10 }}>Real events emitted by the application this session.</p>
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {events.length === 0 && <LoadingState label="Waiting for activity…" />}
            {events.slice(0, 12).map(e => (
              <div key={e.id} style={{ display: 'flex', gap: 11, padding: '9px 2px', borderBottom: '1px solid var(--aur-border-soft)' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', marginTop: 6, flexShrink: 0, background: 'var(--aur-accent)' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5 }}>
                    <span style={{ fontWeight: 600 }}>{EVENT_KIND_LABEL[e.kind]}</span> — {e.label}
                  </div>
                  {e.detail && <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)' }}>{e.detail}</div>}
                </div>
                <span style={{ fontSize: 10.5, color: 'var(--aur-ink-faint)', flexShrink: 0 }}>{timeAgo(e.timestamp)}</span>
              </div>
            ))}
          </div>
        </GlassPanel>

        {/* Active investigations (demo) */}
        <GlassPanel>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600 }}>Active investigations</h2>
            <Link to="/research" style={{ fontSize: 11.5, color: 'var(--aur-accent)', display: 'flex', alignItems: 'center', gap: 3, textDecoration: 'none' }}>
              Open Research <ArrowUpRight size={12} />
            </Link>
          </div>
          {investigations === null && <LoadingState />}
          {active.map(inv => (
            <div key={inv.id} style={{ padding: '10px 2px', borderBottom: '1px solid var(--aur-border-soft)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{inv.title}</span>
                <span style={{ fontSize: 10.5, color: 'var(--aur-ink-faint)', flexShrink: 0 }}>{inv.domain}</span>
              </div>
              <div style={{ marginTop: 6 }}><ConfidenceIndicator band={inv.confidence} /></div>
            </div>
          ))}
        </GlassPanel>
      </div>

      <div style={{ marginTop: 14 }}>
        <GlassPanel>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>Recent evidence <StatusBadge origin="demo" small /></h2>
          {evidence === null && <LoadingState />}
          {recentEvidence.map(ev => (
            <div key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 2px', borderBottom: '1px solid var(--aur-border-soft)', gap: 10 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{ev.title}</div>
                <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', marginTop: 1 }}>{ev.source} · {ev.sourceType}</div>
              </div>
              <span style={{ fontSize: 10.5, color: 'var(--aur-ink-faint)', flexShrink: 0 }}>{timeAgo(ev.timestamp)}</span>
            </div>
          ))}
        </GlassPanel>
      </div>
    </div>
  );
};
