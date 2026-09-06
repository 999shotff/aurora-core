import { useState, useCallback } from 'react';
import { reasonWithTools, type ToolReasonResponse } from '../services/reasoning';

interface ReasoningPanelProps {
  domain?: string;
  onResult?: (result: ToolReasonResponse) => void;
}

export function ReasoningPanel({ domain = 'general', onResult }: ReasoningPanelProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ToolReasonResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await reasonWithTools({
        query: query.trim(),
        domain,
        goal: query.trim(),
      });
      setResult(response);
      onResult?.(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [query, domain, onResult]);

  return (
    <div className="aur-panel" style={{ padding: '16px' }}>
      <div style={{ marginBottom: '12px' }}>
        <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: 'var(--aur-text-secondary)' }}>
          REASONING QUERY
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about market data, geo observations, or research..."
          style={{
            width: '100%',
            minHeight: '80px',
            padding: '8px',
            background: 'var(--aur-surface)',
            border: '1px solid var(--aur-border)',
            borderRadius: '4px',
            color: 'var(--aur-text)',
            fontFamily: 'var(--aur-font-mono)',
            fontSize: '13px',
            resize: 'vertical',
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              handleSubmit();
            }
          }}
        />
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button
          onClick={handleSubmit}
          disabled={loading || !query.trim()}
          className="aur-btn aur-btn--primary"
          style={{ flex: 1 }}
        >
          {loading ? 'REASONING...' : 'EXECUTE REASONING'}
        </button>
        <span style={{ fontSize: '11px', color: 'var(--aur-text-secondary)', alignSelf: 'center' }}>
          ⌘+Enter
        </span>
      </div>

      {error && (
        <div style={{
          padding: '8px 12px',
          background: 'rgba(255, 100, 100, 0.1)',
          border: '1px solid rgba(255, 100, 100, 0.3)',
          borderRadius: '4px',
          color: '#ff6464',
          fontSize: '12px',
          marginBottom: '12px',
        }}>
          {error}
        </div>
      )}

      {result && (
        <div className="aur-glass" style={{ padding: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--aur-text-secondary)' }}>
              {result.request_id} | {result.provider}
            </span>
            <span style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: '3px',
              background: result.status === 'complete' ? 'rgba(100, 255, 100, 0.15)' : 'rgba(255, 200, 100, 0.15)',
              color: result.status === 'complete' ? '#64ff64' : '#ffc864',
            }}>
              {result.status.toUpperCase()}
            </span>
          </div>

          <h4 style={{ margin: '0 0 8px 0', fontSize: '13px', color: 'var(--aur-text)' }}>
            {result.summary}
          </h4>

          <div style={{ fontSize: '12px', lineHeight: '1.6', color: 'var(--aur-text-secondary)' }}>
            {result.answer}
          </div>

          {result.reasoning_points.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '11px', color: 'var(--aur-text-secondary)', marginBottom: '4px' }}>
                REASONING POINTS
              </div>
              {result.reasoning_points.map((rp, i) => (
                <div key={i} style={{
                  padding: '6px 8px',
                  marginBottom: '4px',
                  background: 'var(--aur-surface)',
                  borderRadius: '3px',
                  fontSize: '11px',
                }}>
                  <span style={{
                    display: 'inline-block',
                    padding: '1px 4px',
                    borderRadius: '2px',
                    marginRight: '6px',
                    background: rp.grounding === 'SUPPORTED_BY_EVIDENCE'
                      ? 'rgba(100, 255, 100, 0.15)'
                      : rp.grounding === 'INFERENCE'
                      ? 'rgba(100, 200, 255, 0.15)'
                      : 'rgba(255, 200, 100, 0.15)',
                    color: rp.grounding === 'SUPPORTED_BY_EVIDENCE'
                      ? '#64ff64'
                      : rp.grounding === 'INFERENCE'
                      ? '#64c8ff'
                      : '#ffc864',
                  }}>
                    {rp.grounding}
                  </span>
                  {rp.point}
                </div>
              ))}
            </div>
          )}

          {result.uncertainties.length > 0 && (
            <div style={{ marginTop: '8px', fontSize: '11px', color: '#ffc864' }}>
              UNCERTAINTIES: {result.uncertainties.join('; ')}
            </div>
          )}

          <div style={{
            marginTop: '12px',
            padding: '8px',
            background: 'var(--aur-surface)',
            borderRadius: '3px',
            fontSize: '10px',
            fontFamily: 'var(--aur-font-mono)',
            color: 'var(--aur-text-secondary)',
          }}>
            Tools: {result.tools_executed} | Evidence Nodes: {result.evidence_nodes} | Grounding: {(result.grounding_score * 100).toFixed(0)}%
          </div>
        </div>
      )}
    </div>
  );
}
