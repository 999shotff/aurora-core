import React, { useEffect, useState } from 'react';
import { Search, Satellite, TrendingUp, FileText, Calculator, StickyNote } from 'lucide-react';
import { GlassPanel, StatusBadge, ConfidenceIndicator, LoadingState, EmptyState } from '../components/shell/primitives';
import { useInspector, InspectorSectionTitle, InspectorRow } from '../components/shell/InspectorSheet';
import { listEvidence } from '../services/evidence';
import { useEventBus } from '../lib/eventBus';
import type { EvidenceItem, EvidenceSourceType } from '../types/domain';

const SOURCE_ICON: Record<EvidenceSourceType, React.ReactNode> = {
  satellite: <Satellite size={15} />,
  'market-data': <TrendingUp size={15} />,
  document: <FileText size={15} />,
  'derived-metric': <Calculator size={15} />,
  note: <StickyNote size={15} />,
};

const STATUS_STYLE: Record<EvidenceItem['status'], { color: string; label: string }> = {
  unverified: { color: 'var(--aur-ink-faint)', label: 'Unverified' },
  corroborated: { color: 'var(--aur-positive)', label: 'Corroborated' },
  contested: { color: 'var(--aur-negative)', label: 'Contested' },
};

export const EvidencePage: React.FC = () => {
  const [items, setItems] = useState<EvidenceItem[] | null>(null);
  const [query, setQuery] = useState('');
  const { openInspector } = useInspector();
  const { emit } = useEventBus();

  useEffect(() => {
    emit('navigation', 'Evidence opened', 'live');
    listEvidence().then(r => setItems(r.data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = (items ?? []).filter(e =>
    !query.trim() || e.title.toLowerCase().includes(query.toLowerCase()) || e.description.toLowerCase().includes(query.toLowerCase())
  );

  const openDetail = (ev: EvidenceItem) => {
    emit('evidence_indexed', `Evidence inspected: ${ev.title}`, 'demo');
    openInspector({
      title: ev.title,
      body: (
        <div>
          <StatusBadge origin="demo" />
          <InspectorSectionTitle>Summary</InspectorSectionTitle>
          <p style={{ fontSize: 13, color: 'var(--aur-ink-dim)', lineHeight: 1.6 }}>{ev.description}</p>
          <InspectorSectionTitle>Provenance</InspectorSectionTitle>
          <InspectorRow label="Source" value={ev.source} />
          <InspectorRow label="Source type" value={ev.sourceType} />
          <InspectorRow label="Timestamp" value={new Date(ev.timestamp).toLocaleString()} />
          <InspectorRow label="Status" value={<span style={{ color: STATUS_STYLE[ev.status].color }}>{STATUS_STYLE[ev.status].label}</span>} />
          <InspectorRow label="Confidence" value={<ConfidenceIndicator band={ev.confidence} showLabel={false} />} />
          {Object.keys(ev.metadata).length > 0 && (
            <>
              <InspectorSectionTitle>Metadata</InspectorSectionTitle>
              {Object.entries(ev.metadata).map(([k, v]) => <InspectorRow key={k} label={k} value={v} />)}
            </>
          )}
        </div>
      ),
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--aur-border-soft)', borderRadius: 10, padding: '9px 14px', marginBottom: 16 }}>
        <Search size={14} color="var(--aur-ink-faint)" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search evidence by title or description…"
          style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--aur-ink)', fontSize: 13 }}
        />
      </div>

      <GlassPanel padding={0}>
        {items === null && <LoadingState label="Loading evidence…" />}
        {items !== null && filtered.length === 0 && <EmptyState message="No evidence matches your search." />}
        {filtered.map(ev => (
          <button
            key={ev.id}
            onClick={() => openDetail(ev)}
            style={{ display: 'flex', alignItems: 'center', gap: 13, width: '100%', padding: '14px 18px', border: 'none', borderBottom: '1px solid var(--aur-border-soft)', background: 'none', color: 'inherit', textAlign: 'left', cursor: 'pointer' }}
          >
            <div style={{ width: 34, height: 34, borderRadius: 9, background: 'rgba(124,158,255,0.1)', border: '1px solid rgba(124,158,255,0.2)', color: 'var(--aur-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              {SOURCE_ICON[ev.sourceType]}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13.5, fontWeight: 500 }}>{ev.title}</div>
              <div style={{ fontSize: 11.5, color: 'var(--aur-ink-faint)', marginTop: 2 }}>{ev.source} · {new Date(ev.timestamp).toLocaleDateString()}</div>
            </div>
            <span style={{ fontSize: 11, fontWeight: 600, color: STATUS_STYLE[ev.status].color, flexShrink: 0 }}>{STATUS_STYLE[ev.status].label}</span>
          </button>
        ))}
      </GlassPanel>
    </div>
  );
};
