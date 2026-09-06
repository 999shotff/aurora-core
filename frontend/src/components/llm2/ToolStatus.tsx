import { useState, useEffect } from 'react';
import {
  listTools,
  getSafetyLog,
  type ToolInfo,
  type SafetyLogEntry,
} from '../../services/reasoning';

interface ToolStatusProps {
  refreshInterval?: number;
}

export function ToolStatus({ refreshInterval = 10000 }: ToolStatusProps) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [safetyLog, setSafetyLog] = useState<SafetyLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'registry' | 'log'>('registry');

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const [toolsData, logData] = await Promise.all([
          listTools(),
          getSafetyLog(),
        ]);
        if (mounted) {
          setTools(toolsData.tools);
          setSafetyLog(logData.log);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load tools');
          setLoading(false);
        }
      }
    };

    fetchData();
    const interval = setInterval(fetchData, refreshInterval);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [refreshInterval]);

  if (loading) {
    return (
      <div className="aur-panel" style={{ padding: '16px', textAlign: 'center' }}>
        <span style={{ color: 'var(--aur-text-secondary)', fontSize: '12px' }}>
          Loading tools...
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

  return (
    <div className="aur-panel" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '13px', color: 'var(--aur-text)' }}>
          TOOL STATUS
        </h3>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            onClick={() => setActiveTab('registry')}
            className={`aur-btn ${activeTab === 'registry' ? 'aur-btn--primary' : ''}`}
            style={{ fontSize: '10px', padding: '2px 8px' }}
          >
            REGISTRY ({tools.length})
          </button>
          <button
            onClick={() => setActiveTab('log')}
            className={`aur-btn ${activeTab === 'log' ? 'aur-btn--primary' : ''}`}
            style={{ fontSize: '10px', padding: '2px 8px' }}
          >
            SAFETY LOG ({safetyLog.length})
          </button>
        </div>
      </div>

      {activeTab === 'registry' && (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {tools.map((tool) => (
            <ToolCard key={tool.name} tool={tool} />
          ))}
        </div>
      )}

      {activeTab === 'log' && (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {safetyLog.length === 0 ? (
            <div style={{
              padding: '16px',
              textAlign: 'center',
              color: 'var(--aur-text-secondary)',
              fontSize: '11px',
            }}>
              No tool executions logged yet
            </div>
          ) : (
            safetyLog.map((entry, i) => (
              <SafetyLogCard key={i} entry={entry} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

function ToolCard({ tool }: { tool: ToolInfo }) {
  return (
    <div
      className="aur-glass"
      style={{
        padding: '8px 10px',
        marginBottom: '6px',
        borderLeft: `3px solid ${tool.deterministic ? '#64ff64' : '#ffc864'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontSize: '11px',
          fontFamily: 'var(--aur-font-mono)',
          color: 'var(--aur-text)',
        }}>
          {tool.name}
        </span>
        <div style={{ display: 'flex', gap: '4px' }}>
          {tool.deterministic && (
            <span style={{
              fontSize: '9px',
              padding: '1px 4px',
              borderRadius: '2px',
              background: 'rgba(100, 255, 100, 0.15)',
              color: '#64ff64',
            }}>
              DETERMINISTIC
            </span>
          )}
          <span style={{
            fontSize: '9px',
            padding: '1px 4px',
            borderRadius: '2px',
            background: 'var(--aur-surface)',
            color: 'var(--aur-text-secondary)',
          }}>
            {tool.timeout}s
          </span>
        </div>
      </div>

      <div style={{ fontSize: '10px', color: 'var(--aur-text-secondary)', marginTop: '4px' }}>
        {tool.description}
      </div>

      <div style={{ marginTop: '4px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {tool.permissions.map((perm) => (
          <span
            key={perm}
            style={{
              fontSize: '8px',
              padding: '1px 3px',
              borderRadius: '2px',
              background: isDeniedPermission(perm) ? 'rgba(255, 100, 100, 0.15)' : 'rgba(100, 200, 255, 0.15)',
              color: isDeniedPermission(perm) ? '#ff6464' : '#64c8ff',
            }}
          >
            {perm}
          </span>
        ))}
      </div>
    </div>
  );
}

function SafetyLogCard({ entry }: { entry: SafetyLogEntry }) {
  return (
    <div
      style={{
        padding: '6px 8px',
        marginBottom: '4px',
        background: 'var(--aur-surface)',
        borderRadius: '3px',
        fontSize: '10px',
        fontFamily: 'var(--aur-font-mono)',
        borderLeft: `3px solid ${entry.success ? '#64ff64' : '#ff6464'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--aur-text)' }}>{entry.tool_name}</span>
        <span style={{ color: entry.success ? '#64ff64' : '#ff6464' }}>
          {entry.success ? 'OK' : 'FAIL'}
        </span>
      </div>
      <div style={{ color: 'var(--aur-text-secondary)', marginTop: '2px' }}>
        {entry.execution_time_ms.toFixed(0)}ms | {entry.planning_context || 'direct'}
      </div>
      {entry.error && (
        <div style={{ color: '#ff6464', marginTop: '2px' }}>
          {entry.error}
        </div>
      )}
    </div>
  );
}

function isDeniedPermission(perm: string): boolean {
  return ['TRADE', 'MODIFY', 'DELETE', 'ARBITRARY_CODE', 'NETWORK_EXTERNAL', 'WRITE_RESEARCH'].includes(perm);
}
