import React, { useEffect, useState } from 'react';
import { FileText } from 'lucide-react';
import { GlassPanel, ConfidenceIndicator, LoadingState, EmptyState, StatusBadge } from '../components/shell/primitives';
import { useInspector, InspectorSectionTitle, InspectorRow } from '../components/shell/InspectorSheet';
import { listReports } from '../services/reports';
import { useEventBus } from '../lib/eventBus';
import type { ReportRecord } from '../types/domain';

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<ReportRecord[] | null>(null);
  const { openInspector } = useInspector();
  const { emit } = useEventBus();

  useEffect(() => {
    emit('navigation', 'Reports opened', 'live');
    listReports().then(r => setReports(r.data));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openReport = (r: ReportRecord) => {
    openInspector({
      title: r.title,
      body: (
        <div>
          <StatusBadge origin="demo" />
          <InspectorSectionTitle>Executive summary</InspectorSectionTitle>
          <p style={{ fontSize: 13, color: 'var(--aur-ink-dim)', lineHeight: 1.6 }}>{r.executiveSummary}</p>
          <InspectorSectionTitle>Details</InspectorSectionTitle>
          <InspectorRow label="Author" value={r.author} />
          <InspectorRow label="Generated" value={new Date(r.generatedAt).toLocaleString()} />
          <InspectorRow label="Format" value={r.format.toUpperCase()} />
          <InspectorRow label="Findings" value={r.findingsCount} />
          <InspectorRow label="Confidence" value={<ConfidenceIndicator band={r.confidence} showLabel={false} />} />
        </div>
      ),
    });
  };

  return (
    <GlassPanel padding={0}>
      {reports === null && <LoadingState label="Loading reports…" />}
      {reports !== null && reports.length === 0 && <EmptyState message="No reports generated yet." />}
      {reports?.map(r => (
        <button
          key={r.id}
          onClick={() => openReport(r)}
          style={{ display: 'flex', alignItems: 'center', gap: 13, width: '100%', padding: '14px 18px', border: 'none', borderBottom: '1px solid var(--aur-border-soft)', background: 'none', color: 'inherit', textAlign: 'left', cursor: 'pointer' }}
        >
          <div style={{ width: 34, height: 34, borderRadius: 9, background: 'rgba(255,138,101,0.1)', border: '1px solid rgba(255,138,101,0.2)', color: 'var(--aur-accent-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <FileText size={15} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13.5, fontWeight: 500 }}>{r.title}</div>
            <div style={{ fontSize: 11.5, color: 'var(--aur-ink-faint)', marginTop: 2 }}>{r.author} · {new Date(r.generatedAt).toLocaleDateString()} · {r.findingsCount} findings</div>
          </div>
          <ConfidenceIndicator band={r.confidence} showLabel={false} />
        </button>
      ))}
    </GlassPanel>
  );
};
