/**
 * Compute Fabric Page — provider-agnostic GPU/CPU orchestration control.
 *
 * Shows compute status, provider cards, mode selector, enable/disable.
 * Honest states: NO fake GPU data. If not connected, shows NOT CONNECTED.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { GlassPanel, LoadingState, EmptyState } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import {
  getComputeStatus,
  enableCompute,
  disableCompute,
  setComputeMode,
  type ComputeStatus,
  type ComputeProviderInfo,
  type ComputeMode,
} from '../services/compute';

const STATUS_COLORS: Record<string, string> = {
  READY: 'var(--aur-positive)',
  DISABLED: 'var(--aur-ink-dim)',
  NOT_CONFIGURED: 'var(--aur-ink-faint)',
  DISCONNECTED: 'var(--aur-warning)',
  DEGRADED: 'var(--aur-warning)',
  BUSY: 'var(--aur-accent-2)',
  ERROR: 'var(--aur-negative)',
  UNKNOWN: 'var(--aur-ink-dim)',
  STARTING: 'var(--aur-accent)',
  STOPPING: 'var(--aur-accent)',
  STOPPED: 'var(--aur-ink-dim)',
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || 'var(--aur-ink-dim)';
  const isOn = status === 'READY';
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: color, boxShadow: isOn ? `0 0 6px ${color}` : 'none',
    }} />
  );
}

function ProviderCard({ provider }: { provider: ComputeProviderInfo }) {
  const caps = provider.capabilities;
  return (
    <GlassPanel>
      <div style={{ padding: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <StatusDot status={provider.status} />
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--aur-ink)' }}>{provider.name}</span>
          </div>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
            background: STATUS_COLORS[provider.status] || 'var(--aur-ink-dim)',
            color: '#000', textTransform: 'uppercase',
          }}>
            {provider.status.replace('_', ' ')}
          </span>
        </div>

        {provider.status === 'NOT_CONFIGURED' && (
          <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', fontStyle: 'italic' }}>
            Not configured — add environment variables to enable
          </div>
        )}
        {provider.status === 'DISCONNECTED' && (
          <div style={{ fontSize: 11, color: 'var(--aur-warning)', fontStyle: 'italic' }}>
            No worker connected — start a worker to enable GPU compute
          </div>
        )}

        {caps.gpu_name && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 8 }}>
            <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
              GPU: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{caps.gpu_name}</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
              VRAM: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{caps.vram_gb} GB</span>
            </div>
            {caps.cuda_version && (
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                CUDA: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{caps.cuda_version}</span>
              </div>
            )}
            {caps.framework && (
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                Framework: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{caps.framework}</span>
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
          {caps.inference && <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'var(--aur-glass-strong)', color: 'var(--aur-accent)' }}>INFERENCE</span>}
          {caps.embeddings && <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'var(--aur-glass-strong)', color: 'var(--aur-accent)' }}>EMBEDDINGS</span>}
          {caps.vision && <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'var(--aur-glass-strong)', color: 'var(--aur-accent)' }}>VISION</span>}
          {caps.training && <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'var(--aur-glass-strong)', color: 'var(--aur-accent)' }}>TRAINING</span>}
        </div>

        {provider.worker_id && (
          <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 6 }}>
            Worker: {provider.worker_id}
          </div>
        )}
      </div>
    </GlassPanel>
  );
}

export const ComputePage: React.FC = () => {
  const { emit } = useEventBus();
  const [status, setStatus] = useState<ComputeStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getComputeStatus();
      setStatus(s);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch compute status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    emit('navigation', 'Compute opened', 'live');
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleToggle = useCallback(async () => {
    if (!status) return;
    setToggling(true);
    try {
      const newStatus = status.enabled ? await disableCompute() : await enableCompute();
      setStatus(newStatus);
      emit('compute', newStatus.enabled ? 'Compute enabled' : 'Compute disabled', 'live');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Toggle failed');
    } finally {
      setToggling(false);
    }
  }, [status]);

  const handleModeChange = useCallback(async (mode: ComputeMode) => {
    try {
      const newStatus = await setComputeMode(mode);
      setStatus(newStatus);
      emit('compute', `Mode: ${mode}`, 'live');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Mode change failed');
    }
  }, []);

  if (loading) return <LoadingState label="Loading compute fabric..." />;
  if (error && !status) return <EmptyState message={error} />;

  const modes: { value: ComputeMode; label: string }[] = [
    { value: 'AUTO', label: 'AUTO' },
    { value: 'CPU', label: 'CPU' },
    { value: 'LIGHTNING', label: 'Lightning AI' },
    { value: 'GOOGLE_COLAB', label: 'Google Colab' },
  ];

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'auto' }}>
      {error && (
        <div style={{ color: 'var(--aur-negative)', fontSize: 12, padding: '8px 12px', background: 'rgba(248,113,113,0.1)', borderRadius: 8 }}>
          {error}
        </div>
      )}

      {/* Hero: Compute status */}
      <GlassPanel variant="strong">
        <div style={{ padding: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: 'var(--aur-ink)' }}>Compute Fabric</h2>
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
                Provider-agnostic GPU/CPU orchestration
              </div>
            </div>
            <button
              onClick={handleToggle}
              disabled={toggling}
              style={{
                padding: '8px 20px', borderRadius: 8, border: 'none',
                background: status?.enabled ? 'var(--aur-negative)' : 'var(--aur-positive)',
                color: '#fff', fontSize: 13, fontWeight: 600, cursor: toggling ? 'wait' : 'pointer',
                opacity: toggling ? 0.6 : 1,
              }}
            >
              {toggling ? '...' : status?.enabled ? 'DISABLE GPU' : 'ENABLE GPU'}
            </button>
          </div>

          {/* Status grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            <div style={{ padding: '10px 14px', background: 'var(--aur-bg-elevated)', borderRadius: 8 }}>
              <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 4 }}>BACKEND</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <StatusDot status={status?.enabled ? 'READY' : 'DISABLED'} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{status?.enabled ? 'ONLINE' : 'OFFLINE'}</span>
              </div>
            </div>
            <div style={{ padding: '10px 14px', background: 'var(--aur-bg-elevated)', borderRadius: 8 }}>
              <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 4 }}>GPU</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <StatusDot status={status?.enabled ? 'READY' : 'DISABLED'} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{status?.enabled ? 'ON' : 'OFF'}</span>
              </div>
            </div>
            <div style={{ padding: '10px 14px', background: 'var(--aur-bg-elevated)', borderRadius: 8 }}>
              <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 4 }}>MODE</div>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{status?.mode || 'CPU'}</span>
            </div>
            <div style={{ padding: '10px 14px', background: 'var(--aur-bg-elevated)', borderRadius: 8 }}>
              <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 4 }}>ACTIVE</div>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{status?.active_provider || 'CPU'}</span>
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* Mode selector */}
      <GlassPanel>
        <div style={{ padding: 4 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
            Compute Mode
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {modes.map(m => (
              <button
                key={m.value}
                onClick={() => handleModeChange(m.value)}
                style={{
                  padding: '8px 16px', borderRadius: 8, border: '1px solid',
                  borderColor: status?.mode === m.value ? 'var(--aur-accent)' : 'var(--aur-border)',
                  background: status?.mode === m.value ? 'var(--aur-glass-strong)' : 'transparent',
                  color: status?.mode === m.value ? 'var(--aur-accent)' : 'var(--aur-ink-dim)',
                  fontSize: 12, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </GlassPanel>

      {/* Provider cards */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
          Providers
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
          {status?.providers.map(p => (
            <ProviderCard key={p.provider_id} provider={p} />
          ))}
        </div>
      </div>

      {/* Jobs summary */}
      <GlassPanel>
        <div style={{ padding: 4 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
            Jobs
          </div>
          <div style={{ display: 'flex', gap: 20 }}>
            <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
              Active: <span style={{ fontWeight: 600, color: 'var(--aur-ink)' }}>{status?.active_jobs ?? 0}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)' }}>
              Completed: <span style={{ fontWeight: 600, color: 'var(--aur-ink)' }}>{status?.total_jobs_completed ?? 0}</span>
            </div>
          </div>
        </div>
      </GlassPanel>
    </div>
  );
};

export default ComputePage;
