import { useState, useEffect } from 'react';
import {
  getEvidenceGraph,
  type EvidenceGraphData,
  type EvidenceGraphNode,
  type EvidenceGraphEdge,
} from '../../services/reasoning';

interface EvidenceGraphViewProps {
  refreshInterval?: number;
}

export function EvidenceGraphView({ refreshInterval = 5000 }: EvidenceGraphViewProps) {
  const [graph, setGraph] = useState<EvidenceGraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    let interval: ReturnType<typeof setInterval>;

    const fetchGraph = async () => {
      try {
        const data = await getEvidenceGraph();
        if (mounted) {
          setGraph(data);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load graph');
          setLoading(false);
        }
      }
    };

    fetchGraph();
    interval = setInterval(fetchGraph, refreshInterval);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [refreshInterval]);

  if (loading) {
    return (
      <div className="aur-panel" style={{ padding: '16px', textAlign: 'center' }}>
        <span style={{ color: 'var(--aur-text-secondary)', fontSize: '12px' }}>
          Loading evidence graph...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="aur-panel" style={{ padding: '16px' }}>
        <div style={{ color: '#ff6464', fontSize: '12px' }}>
          Error: {error}
        </div>
      </div>
    );
  }

  if (!graph) {
    return (
      <div className="aur-panel" style={{ padding: '16px' }}>
        <span style={{ color: 'var(--aur-text-secondary)', fontSize: '12px' }}>
          No evidence graph available
        </span>
      </div>
    );
  }

  return (
    <div className="aur-panel" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '13px', color: 'var(--aur-text)' }}>
          EVIDENCE GRAPH
        </h3>
        <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--aur-text-secondary)' }}>
          <span>{graph.node_count} nodes</span>
          <span>{graph.edge_count} edges</span>
          {graph.contradiction_count > 0 && (
            <span style={{ color: '#ffc864' }}>
              {graph.contradiction_count} contradictions
            </span>
          )}
        </div>
      </div>

      {graph.nodes.length === 0 ? (
        <div style={{
          padding: '24px',
          textAlign: 'center',
          color: 'var(--aur-text-secondary)',
          fontSize: '12px',
        }}>
          No evidence nodes yet. Execute a reasoning query to populate the graph.
        </div>
      ) : (
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {graph.nodes.map((node) => (
            <EvidenceNodeCard key={node.evidence_id} node={node} edges={graph.edges} />
          ))}
        </div>
      )}

      {graph.edges.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '11px', color: 'var(--aur-text-secondary)', marginBottom: '4px' }}>
            RELATIONSHIPS
          </div>
          {graph.edges.map((edge, i) => (
            <div key={i} style={{
              padding: '4px 8px',
              marginBottom: '2px',
              background: 'var(--aur-surface)',
              borderRadius: '3px',
              fontSize: '10px',
              fontFamily: 'var(--aur-font-mono)',
            }}>
              <span style={{ color: getRelationshipColor(edge.relationship) }}>
                {edge.relationship}
              </span>
              {' '}
              <span style={{ color: 'var(--aur-text-secondary)' }}>
                {edge.source_id} → {edge.target_id}
              </span>
              {edge.description && (
                <span style={{ color: 'var(--aur-text-secondary)', marginLeft: '6px' }}>
                  ({edge.description})
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EvidenceNodeCard({
  node,
  edges,
}: {
  node: EvidenceGraphNode;
  edges: EvidenceGraphEdge[];
}) {
  const outgoing = edges.filter((e) => e.source_id === node.evidence_id);
  const incoming = edges.filter((e) => e.target_id === node.evidence_id);

  return (
    <div
      className="aur-glass"
      style={{
        padding: '8px 10px',
        marginBottom: '6px',
        borderLeft: `3px solid ${getEvidenceTypeColor(node.evidence_type)}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontSize: '11px',
          fontFamily: 'var(--aur-font-mono)',
          color: 'var(--aur-text)',
        }}>
          {node.evidence_id}
        </span>
        <span style={{
          fontSize: '9px',
          padding: '1px 4px',
          borderRadius: '2px',
          background: getEvidenceTypeColor(node.evidence_type) + '20',
          color: getEvidenceTypeColor(node.evidence_type),
        }}>
          {node.evidence_type.toUpperCase()}
        </span>
      </div>

      <div style={{ fontSize: '11px', color: 'var(--aur-text-secondary)', marginTop: '4px' }}>
        {node.tool_name}
      </div>

      {node.data_summary && (
        <div style={{ fontSize: '10px', color: 'var(--aur-text-secondary)', marginTop: '2px' }}>
          {node.data_summary}
        </div>
      )}

      {(outgoing.length > 0 || incoming.length > 0) && (
        <div style={{ marginTop: '4px', fontSize: '9px', color: 'var(--aur-text-secondary)' }}>
          {outgoing.length > 0 && (
            <span>→ {outgoing.length} outgoing </span>
          )}
          {incoming.length > 0 && (
            <span>← {incoming.length} incoming</span>
          )}
        </div>
      )}
    </div>
  );
}

function getEvidenceTypeColor(type: string): string {
  switch (type) {
    case 'observation': return '#64c8ff';
    case 'analysis': return '#a064ff';
    case 'inference': return '#ffc864';
    default: return '#888888';
  }
}

function getRelationshipColor(type: string): string {
  switch (type) {
    case 'SUPPORTS': return '#64ff64';
    case 'CONTRADICTS': return '#ff6464';
    case 'DERIVED_FROM': return '#64c8ff';
    default: return '#888888';
  }
}
