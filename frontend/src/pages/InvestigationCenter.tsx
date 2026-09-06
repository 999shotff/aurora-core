/**
 * LLM-4: Investigation Center — bounded, auditable investigation workstation.
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { useState, useEffect, useCallback } from 'react';
import { useEventBus } from '../lib/eventBus';
import {
  GlassPanel,
  StatusBadge,
  LoadingState,
  ErrorState,
  EmptyState,
} from '../components/shell/primitives';
import {
  createInvestigation,
  listInvestigations,
  startInvestigation,
  cancelInvestigation,
  reopenInvestigation,
  getInvestigationEvents,
  getInvestigationResult,
  type InvestigationSummary,
  type InvestigationEvent,
  type InvestigationResultData,
} from '../services/investigations';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#9096A8',
  PLANNING: '#7C9EFF',
  MEMORY_RETRIEVAL: '#7C9EFF',
  GAP_ANALYSIS: '#7C9EFF',
  INVESTIGATING: '#FBBF24',
  ANALYZING: '#FBBF24',
  COMPARING: '#FBBF24',
  SUFFICIENCY_CHECK: '#FBBF24',
  VALIDATING: '#A78BFA',
  SYNTHESIZING: '#A78BFA',
  COMPLETE: '#34D399',
  PARTIAL: '#FBBF24',
  ABSTAINED: '#9096A8',
  FAILED: '#F87171',
  CANCELLED: '#9096A8',
};

const DOMAIN_ICONS: Record<string, string> = {
  market: '\u{1F4C8}',
  geo: '\u{1F30D}',
  research: '\u{1F52C}',
  general: '\u{1F50D}',
};

export function InvestigationCenter() {
  const { emit } = useEventBus();
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('general');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [result, setResult] = useState<InvestigationResultData | null>(null);
  const [starting, setStarting] = useState(false);

  const loadInvestigations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listInvestigations({ limit: 50 });
      setInvestigations(data.investigations || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInvestigations();
  }, [loadInvestigations]);

  useEffect(() => {
    if (!selectedId) return;
    const loadDetails = async () => {
      try {
        const [evData, resData] = await Promise.all([
          getInvestigationEvents(selectedId),
          getInvestigationResult(selectedId),
        ]);
        setEvents(evData.events || []);
        setResult(resData.result);
      } catch {
        // ignore
      }
    };
    loadDetails();
  }, [selectedId]);

  const handleCreate = async () => {
    if (!query.trim()) return;
    try {
      setStarting(true);
      const inv = await createInvestigation({ query, domain });
      emit({ kind: 'processing', label: `Investigation created: ${inv.investigation_id}` });
      await loadInvestigations();
      setSelectedId(inv.investigation_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create');
    } finally {
      setStarting(false);
    }
  };

  const handleStart = async (id: string) => {
    try {
      setStarting(true);
      await startInvestigation(id);
      emit({ kind: 'processing', label: `Investigation started: ${id}` });
      await loadInvestigations();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start');
    } finally {
      setStarting(false);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await cancelInvestigation(id);
      await loadInvestigations();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to cancel');
    }
  };

  const handleReopen = async (id: string) => {
    try {
      await reopenInvestigation(id);
      await loadInvestigations();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reopen');
    }
  };

  const active = investigations.filter((i) =>
    !['COMPLETE', 'PARTIAL', 'ABSTAINED', 'FAILED', 'CANCELLED'].includes(i.status),
  );
  const history = investigations.filter((i) =>
    ['COMPLETE', 'PARTIAL', 'ABSTAINED', 'FAILED', 'CANCELLED'].includes(i.status),
  );

  const selected = investigations.find((i) => i.investigation_id === selectedId);

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      <GlassPanel>
        <div style={{ padding: '16px' }}>
          <h2 style={{ margin: '0 0 12px', fontSize: '18px', color: 'var(--aur-ink)' }}>
            Investigation Center
          </h2>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe your investigation objective..."
              style={{
                flex: 1,
                minHeight: '48px',
                padding: '8px 12px',
                background: 'var(--aur-bg-elevated)',
                border: '1px solid var(--aur-border)',
                borderRadius: '8px',
                color: 'var(--aur-ink)',
                fontSize: '14px',
                resize: 'vertical',
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  handleCreate();
                }
              }}
            />
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              style={{
                padding: '8px 12px',
                background: 'var(--aur-bg-elevated)',
                border: '1px solid var(--aur-border)',
                borderRadius: '8px',
                color: 'var(--aur-ink)',
                fontSize: '14px',
              }}
            >
              <option value="general">General</option>
              <option value="market">Market</option>
              <option value="geo">Geo</option>
              <option value="research">Research</option>
            </select>
            <button
              onClick={handleCreate}
              disabled={starting || !query.trim()}
              style={{
                padding: '8px 20px',
                background: 'var(--aur-accent)',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                fontSize: '14px',
                fontWeight: 600,
                cursor: starting ? 'wait' : 'pointer',
                opacity: starting || !query.trim() ? 0.5 : 1,
              }}
            >
              {starting ? 'Starting...' : 'Investigate'}
            </button>
          </div>
        </div>
      </GlassPanel>

      {error && (
        <div style={{ color: 'var(--aur-negative)', fontSize: '13px', padding: '0 4px' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '320px 1fr' : '1fr', gap: '16px', flex: 1, minHeight: 0 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto' }}>
          {loading ? (
            <LoadingState label="Loading investigations..." />
          ) : (
            <>
              {active.length > 0 && (
                <GlassPanel>
                  <div style={{ padding: '12px 16px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--aur-accent)', textTransform: 'uppercase', marginBottom: '8px' }}>
                      Active ({active.length})
                    </div>
                    {active.map((inv) => (
                      <InvestigationCard
                        key={inv.investigation_id}
                        investigation={inv}
                        selected={selectedId === inv.investigation_id}
                        onSelect={() => setSelectedId(inv.investigation_id)}
                        onStart={handleStart}
                        onCancel={handleCancel}
                        onReopen={handleReopen}
                        starting={starting}
                      />
                    ))}
                  </div>
                </GlassPanel>
              )}

              {history.length > 0 && (
                <GlassPanel>
                  <div style={{ padding: '12px 16px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: '8px' }}>
                      History ({history.length})
                    </div>
                    {history.map((inv) => (
                      <InvestigationCard
                        key={inv.investigation_id}
                        investigation={inv}
                        selected={selectedId === inv.investigation_id}
                        onSelect={() => setSelectedId(inv.investigation_id)}
                        onStart={handleStart}
                        onCancel={handleCancel}
                        onReopen={handleReopen}
                        starting={starting}
                      />
                    ))}
                  </div>
                </GlassPanel>
              )}

              {investigations.length === 0 && (
                <EmptyState
                  message="No investigations yet"
                  hint="Describe an objective above and click Investigate"
                />
              )}
            </>
          )}
        </div>

        {selected && (
          <GlassPanel>
            <div style={{ padding: '16px', overflow: 'auto', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ margin: 0, fontSize: '16px', color: 'var(--aur-ink)' }}>
                  Investigation Detail
                </h3>
                <button
                  onClick={() => setSelectedId(null)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--aur-ink-dim)',
                    cursor: 'pointer',
                    fontSize: '18px',
                  }}
                >
                  &times;
                </button>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    background: STATUS_COLORS[selected.status] || '#9096A8',
                    color: '#000',
                  }}
                >
                  {selected.status}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--aur-ink-dim)' }}>
                  {DOMAIN_ICONS[selected.domain] || ''} {selected.domain}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--aur-ink-dim)' }}>
                  {selected.evidence_count} evidence &middot; {selected.findings_count} findings
                </span>
              </div>

              <div style={{ fontSize: '13px', color: 'var(--aur-ink)', marginBottom: '12px', padding: '8px', background: 'var(--aur-bg-elevated)', borderRadius: '6px' }}>
                {selected.query}
              </div>

              {selected.tools_used.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Tools Used
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {selected.tools_used.map((tool) => (
                      <span key={tool} style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '11px', background: 'var(--aur-glass)', color: 'var(--aur-ink-dim)' }}>
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {result && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Result
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--aur-ink)', padding: '8px', background: 'var(--aur-bg-elevated)', borderRadius: '6px' }}>
                    {result.executive_summary || 'No summary available'}
                  </div>
                  {result.findings.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      {result.findings.map((f) => (
                        <div key={f.finding_id} style={{ padding: '6px 8px', marginBottom: '4px', borderRadius: '4px', background: 'var(--aur-glass)', fontSize: '12px' }}>
                          <span style={{ color: 'var(--aur-ink)' }}>{f.statement}</span>
                          <span style={{ marginLeft: '8px', color: 'var(--aur-ink-dim)' }}>
                            ({f.classification}, {(f.confidence * 100).toFixed(0)}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  {result.uncertainties.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--aur-warning)' }}>
                      Uncertainties: {result.uncertainties.join('; ')}
                    </div>
                  )}
                </div>
              )}

              {events.length > 0 && (
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Audit Trail ({events.length} events)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {events.map((ev) => (
                      <div key={ev.event_id} style={{ display: 'flex', gap: '8px', fontSize: '11px', padding: '4px 8px', background: 'var(--aur-glass)', borderRadius: '4px' }}>
                        <span style={{ color: 'var(--aur-ink-faint)', minWidth: '80px' }}>
                          {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                        </span>
                        <span style={{ color: 'var(--aur-accent)', fontWeight: 600, minWidth: '100px' }}>
                          {ev.event_type}
                        </span>
                        <span style={{ color: 'var(--aur-ink-dim)' }}>{ev.summary}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </GlassPanel>
        )}
      </div>
    </div>
  );
}

function InvestigationCard({
  investigation,
  selected,
  onSelect,
  onStart,
  onCancel,
  onReopen,
  starting,
}: {
  investigation: InvestigationSummary;
  selected: boolean;
  onSelect: () => void;
  onStart: (id: string) => void;
  onCancel: (id: string) => void;
  onReopen: (id: string) => void;
  starting: boolean;
}) {
  const inv = investigation;
  const canStart = inv.status === 'DRAFT';
  const canCancel = !['COMPLETE', 'PARTIAL', 'ABSTAINED', 'FAILED', 'CANCELLED'].includes(inv.status);
  const canReopen = ['COMPLETE', 'PARTIAL', 'ABSTAINED', 'FAILED'].includes(inv.status);

  return (
    <div
      onClick={onSelect}
      style={{
        padding: '8px 12px',
        marginBottom: '6px',
        borderRadius: '8px',
        cursor: 'pointer',
        background: selected ? 'var(--aur-glass-strong)' : 'transparent',
        border: selected ? '1px solid var(--aur-accent)' : '1px solid transparent',
        transition: 'all 150ms ease',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '13px', color: 'var(--aur-ink)', fontWeight: 500 }}>
          {DOMAIN_ICONS[inv.domain] || ''} {inv.query.slice(0, 60)}{inv.query.length > 60 ? '...' : ''}
        </span>
        <span
          style={{
            padding: '1px 6px',
            borderRadius: '4px',
            fontSize: '10px',
            fontWeight: 600,
            background: STATUS_COLORS[inv.status] || '#9096A8',
            color: '#000',
          }}
        >
          {inv.status}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '4px', fontSize: '11px', color: 'var(--aur-ink-dim)' }}>
        <span>{inv.evidence_count} evidence</span>
        <span>{inv.findings_count} findings</span>
        <span>{new Date(inv.created_at * 1000).toLocaleDateString()}</span>
      </div>
      <div style={{ display: 'flex', gap: '4px', marginTop: '6px' }}>
        {canStart && (
          <button
            onClick={(e) => { e.stopPropagation(); onStart(inv.investigation_id); }}
            disabled={starting}
            style={{ padding: '2px 8px', fontSize: '11px', background: 'var(--aur-accent)', color: '#fff', border: 'none', borderRadius: '4px', cursor: starting ? 'wait' : 'pointer' }}
          >
            Start
          </button>
        )}
        {canCancel && (
          <button
            onClick={(e) => { e.stopPropagation(); onCancel(inv.investigation_id); }}
            style={{ padding: '2px 8px', fontSize: '11px', background: 'var(--aur-glass)', color: 'var(--aur-ink-dim)', border: '1px solid var(--aur-border)', borderRadius: '4px', cursor: 'pointer' }}
          >
            Cancel
          </button>
        )}
        {canReopen && (
          <button
            onClick={(e) => { e.stopPropagation(); onReopen(inv.investigation_id); }}
            style={{ padding: '2px 8px', fontSize: '11px', background: 'var(--aur-glass)', color: 'var(--aur-ink-dim)', border: '1px solid var(--aur-border)', borderRadius: '4px', cursor: 'pointer' }}
          >
            Reopen
          </button>
        )}
      </div>
    </div>
  );
}
