/**
 * Memory Center — Cognitive memory search, retrieve, and inspect.
 * Connected to real backend. NO_DEPLOYMENT_SIGNAL.
 */

import { useState, useEffect, useCallback } from 'react';
import { GlassPanel, LoadingState, EmptyState } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import { API_BASE } from '../services/config';

interface MemoryRecord {
  memory_id: string;
  memory_type: string;
  version: number;
  domain: string;
  title: string;
  content: string;
  source: string;
  provenance: string;
  created_at: number;
  observed_at: number | null;
  updated_at: number;
  status: string;
  confidence: number;
  evidence_refs: string[];
  entity_refs: string[];
  tags: string[];
}

interface SearchResult {
  memory: {
    memory_id: string;
    memory_type: string;
    title: string;
    domain: string;
    status: string;
    created_at: number;
  };
  score: number;
  match_reasons: string[];
}

interface MemoryStats {
  total: number;
  by_type: Record<string, number>;
  by_domain: Record<string, number>;
  by_status: Record<string, number>;
  index_size: number;
  relationship_count: number;
}

const MEMORY_TYPE_COLORS: Record<string, string> = {
  EPISODIC: '#7C9EFF',
  SEMANTIC: '#34D399',
  EVIDENCE: '#FBBF24',
  WORKING: '#A78BFA',
};

async function apiGet<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json();
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json();
}

export function MemoryCenter() {
  const {} = useEventBus();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selected, setSelected] = useState<MemoryRecord | null>(null);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const s = await apiGet<MemoryStats>('/api/v1/memory/stats');
      setStats(s);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<{ results: SearchResult[]; total: number }>(
        `/api/v1/memory/search?query=${encodeURIComponent(query)}&top_k=20`
      );
      setResults(data.results || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRetrieve = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiPost<{ records: { memory: MemoryRecord; score: number }[] }>(
        '/api/v1/memory/retrieve',
        { query, domain: 'general', top_k: 10 }
      );
      setResults(
        (data.records || []).map(r => ({
          memory: {
            memory_id: r.memory.memory_id,
            memory_type: r.memory.memory_type,
            title: r.memory.title,
            domain: r.memory.domain,
            status: r.memory.status,
            created_at: r.memory.created_at,
          },
          score: r.score,
          match_reasons: [],
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Retrieve failed');
    } finally {
      setLoading(false);
    }
  };

  const handleInspect = async (id: string) => {
    try {
      const record = await apiGet<MemoryRecord>(`/api/v1/memory/${id}`);
      setSelected(record);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  };

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
      <GlassPanel>
        <div style={{ padding: 16 }}>
          <h2 style={{ margin: '0 0 12px', fontSize: 18, color: 'var(--aur-ink)' }}>Memory Center</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search memories by content, title, or entity..."
              onKeyDown={e => { if (e.key === 'Enter') handleSearch(); }}
              style={{
                flex: 1, minWidth: 200, padding: '8px 12px',
                background: 'var(--aur-bg-elevated)', border: '1px solid var(--aur-border)',
                borderRadius: 8, color: 'var(--aur-ink)', fontSize: 14,
              }}
            />
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              style={{
                padding: '8px 16px', background: 'var(--aur-accent)', border: 'none',
                borderRadius: 8, color: '#fff', fontSize: 14, fontWeight: 600,
                cursor: loading ? 'wait' : 'pointer', opacity: loading || !query.trim() ? 0.5 : 1,
              }}
            >
              Search
            </button>
            <button
              onClick={handleRetrieve}
              disabled={loading || !query.trim()}
              style={{
                padding: '8px 16px', background: 'var(--aur-glass)', border: '1px solid var(--aur-border)',
                borderRadius: 8, color: 'var(--aur-ink)', fontSize: 14,
                cursor: loading ? 'wait' : 'pointer', opacity: loading || !query.trim() ? 0.5 : 1,
              }}
            >
              Retrieve for Reasoning
            </button>
          </div>
        </div>
      </GlassPanel>

      {stats && (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {[
            { label: 'Total', value: stats.total },
            { label: 'Relationships', value: stats.relationship_count },
            { label: 'Index Size', value: stats.index_size },
          ].map(s => (
            <GlassPanel key={s.label}>
              <div style={{ padding: '8px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--aur-accent)' }}>{s.value}</div>
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', textTransform: 'uppercase' }}>{s.label}</div>
              </div>
            </GlassPanel>
          ))}
          {Object.entries(stats.by_type).map(([type, count]) => (
            <GlassPanel key={type}>
              <div style={{ padding: '8px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: MEMORY_TYPE_COLORS[type] || 'var(--aur-ink)' }}>{count}</div>
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', textTransform: 'uppercase' }}>{type}</div>
              </div>
            </GlassPanel>
          ))}
        </div>
      )}

      {error && (
        <div style={{ color: 'var(--aur-negative)', fontSize: 13, padding: '0 4px' }}>{error}</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '380px 1fr' : '1fr', gap: 16, flex: 1, minHeight: 0 }}>
        <div style={{ overflow: 'auto' }}>
          {loading ? (
            <LoadingState label="Searching memory..." />
          ) : results.length === 0 ? (
            <EmptyState message="No memory records found" hint="Search or retrieve to find memories" />
          ) : (
            <GlassPanel>
              <div style={{ padding: '12px 16px' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--aur-accent)', textTransform: 'uppercase', marginBottom: 8 }}>
                  Results ({results.length})
                </div>
                {results.map(r => (
                  <div
                    key={r.memory.memory_id}
                    onClick={() => handleInspect(r.memory.memory_id)}
                    style={{
                      padding: '8px 12px', marginBottom: 6, borderRadius: 8, cursor: 'pointer',
                      background: selected?.memory_id === r.memory.memory_id ? 'var(--aur-glass-strong)' : 'transparent',
                      border: selected?.memory_id === r.memory.memory_id ? '1px solid var(--aur-accent)' : '1px solid transparent',
                      transition: 'all 150ms ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--aur-ink)' }}>{r.memory.title}</span>
                      <span style={{
                        padding: '1px 6px', borderRadius: 4, fontSize: 10, fontWeight: 600,
                        background: MEMORY_TYPE_COLORS[r.memory.memory_type] || '#9096A8', color: '#000',
                      }}>
                        {r.memory.memory_type}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4, fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                      <span>{r.memory.domain}</span>
                      <span>score: {(r.score * 100).toFixed(0)}%</span>
                      <span>{r.memory.status}</span>
                    </div>
                    {r.match_reasons.length > 0 && (
                      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--aur-ink-faint)' }}>
                        {r.match_reasons.join(' · ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </GlassPanel>
          )}
        </div>

        {selected && (
          <GlassPanel>
            <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 16, color: 'var(--aur-ink)' }}>Memory Detail</h3>
                <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: 'var(--aur-ink-dim)', cursor: 'pointer', fontSize: 18 }}>
                  &times;
                </button>
              </div>

              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                <span style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600,
                  background: MEMORY_TYPE_COLORS[selected.memory_type] || '#9096A8', color: '#000',
                }}>
                  {selected.memory_type}
                </span>
                <span style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>{selected.domain}</span>
                <span style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>v{selected.version}</span>
                <span style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
                  confidence: {(selected.confidence * 100).toFixed(0)}%
                </span>
              </div>

              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8, color: 'var(--aur-ink)' }}>{selected.title}</div>

              <div style={{
                fontSize: 13, lineHeight: 1.6, color: 'var(--aur-ink)', padding: 12,
                background: 'var(--aur-bg-elevated)', borderRadius: 8, marginBottom: 12,
                whiteSpace: 'pre-wrap',
              }}>
                {selected.content}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
                  <strong>Source:</strong> {selected.source}
                </div>
                <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
                  <strong>Status:</strong> {selected.status}
                </div>
                <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
                  <strong>Created:</strong> {new Date(selected.created_at * 1000).toLocaleString()}
                </div>
                <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
                  <strong>Updated:</strong> {new Date(selected.updated_at * 1000).toLocaleString()}
                </div>
              </div>

              {selected.provenance && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: 4 }}>Provenance</div>
                  <div style={{ fontSize: 12, color: 'var(--aur-ink)', padding: 8, background: 'var(--aur-bg-elevated)', borderRadius: 6 }}>
                    {selected.provenance}
                  </div>
                </div>
              )}

              {selected.tags.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: 4 }}>Tags</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {selected.tags.map(tag => (
                      <span key={tag} style={{ padding: '2px 6px', borderRadius: 4, fontSize: 11, background: 'var(--aur-glass)', color: 'var(--aur-ink-dim)' }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selected.evidence_refs.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: 4 }}>Evidence References</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {selected.evidence_refs.map(ref => (
                      <span key={ref} style={{ padding: '2px 6px', borderRadius: 4, fontSize: 11, background: 'var(--aur-glass)', color: 'var(--aur-accent)' }}>
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selected.entity_refs.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: 4 }}>Entity References</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {selected.entity_refs.map(ref => (
                      <span key={ref} style={{ padding: '2px 6px', borderRadius: 4, fontSize: 11, background: 'var(--aur-glass)', color: 'var(--aur-ink-dim)' }}>
                        {ref}
                      </span>
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

export default MemoryCenter;
