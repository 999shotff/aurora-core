/**
 * Compute Fabric Page — provider-agnostic GPU/CPU orchestration control.
 *
 * Shows compute status, provider cards, GPU info, worker status, benchmark.
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
  getRuntimeHealth,
  listRuntimes,
  type ComputeStatus,
  type ComputeProviderInfo,
  type ComputeMode,
  type RuntimeInfo,
  type RuntimeHealth,
} from '../services/compute';

const STATUS_COLORS: Record<string, string> = {
  READY: 'var(--aur-positive)',
  DISABLED: 'var(--aur-ink-dim)',
  NOT_CONFIGURED: 'var(--aur-ink-faint)',
  CONFIGURED: 'var(--aur-accent)',
  CONNECTING: 'var(--aur-accent)',
  AUTHENTICATING: 'var(--aur-accent)',
  HEALTH_CHECK: 'var(--aur-accent)',
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
  const gpu = caps.gpu;
  const workerStatus = provider.worker_status || 'OFFLINE';

  return (
    <GlassPanel>
      <div style={{ padding: 14 }}>
        {/* Header */}
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

        {/* Status messages */}
        {provider.status === 'NOT_CONFIGURED' && (
          <div style={{ fontSize: 11, color: 'var(--aur-ink-faint)', fontStyle: 'italic', marginBottom: 6 }}>
            Not configured — add environment variables to enable
          </div>
        )}
        {provider.status === 'DISCONNECTED' && (
          <div style={{ fontSize: 11, color: 'var(--aur-warning)', fontStyle: 'italic', marginBottom: 6 }}>
            No worker connected — start a worker to enable GPU compute
          </div>
        )}

        {/* Worker info */}
        {provider.worker_id && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, marginBottom: 6 }}>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)' }}>
              Worker: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{provider.worker_id.slice(0, 16)}...</span>
            </div>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)' }}>
              Status: <span style={{ color: STATUS_COLORS[workerStatus] || 'var(--aur-ink)', fontWeight: 500 }}>{workerStatus}</span>
            </div>
          </div>
        )}

        {/* GPU info — only from real runtime */}
        {gpu && gpu.name !== 'UNKNOWN' && (
          <div style={{
            padding: '8px 10px', background: 'var(--aur-bg-elevated)', borderRadius: 6,
            border: '1px solid var(--aur-border)', marginBottom: 6,
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              GPU
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                Model: <span style={{ color: 'var(--aur-ink)', fontWeight: 600 }}>{gpu.name}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                VRAM: <span style={{ color: 'var(--aur-ink)', fontWeight: 600 }}>{(gpu.vram_mb / 1024).toFixed(1)} GB</span>
              </div>
              {gpu.cuda_version && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  CUDA: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{gpu.cuda_version}</span>
                </div>
              )}
              {gpu.compute_capability && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  Compute: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{gpu.compute_capability}</span>
                </div>
              )}
              {gpu.driver_version && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  Driver: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{gpu.driver_version}</span>
                </div>
              )}
              {gpu.runtime_info && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  Runtime: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{gpu.runtime_info}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Capabilities */}
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {caps.inference && <Tag label="INFERENCE" />}
          {caps.embeddings && <Tag label="EMBEDDINGS" />}
          {caps.vision && <Tag label="VISION" />}
          {caps.training && <Tag label="TRAINING" />}
          {caps.benchmark && <Tag label="BENCHMARK" />}
          {caps.runtime && <Tag label="RUNTIME" />}
        </div>
      </div>
    </GlassPanel>
  );
}

function RuntimeCard({ runtime }: { runtime: RuntimeInfo }) {
  const statusColor = runtime.status === 'READY' ? 'var(--aur-positive)' :
                       runtime.status === 'ERROR' ? 'var(--aur-negative)' :
                       runtime.status === 'BUSY' ? 'var(--aur-accent-2)' :
                       'var(--aur-accent)';

  return (
    <GlassPanel>
      <div style={{ padding: 14 }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <StatusDot status={runtime.status} />
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--aur-ink)' }}>
              Runtime {runtime.runtime_id.slice(0, 12)}...
            </span>
          </div>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
            background: statusColor, color: '#000', textTransform: 'uppercase',
          }}>
            {runtime.status}
          </span>
        </div>

        {/* Model info */}
        {runtime.model && (
          <div style={{
            padding: '8px 10px', background: 'var(--aur-bg-elevated)', borderRadius: 6,
            border: '1px solid var(--aur-border)', marginBottom: 6,
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              Loaded Model
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                Model: <span style={{ color: 'var(--aur-ink)', fontWeight: 600 }}>{runtime.model.model_name}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                Status: <span style={{ color: statusColor, fontWeight: 500 }}>{runtime.model_load_status}</span>
              </div>
              {runtime.gpu_name && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  GPU: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{runtime.gpu_name}</span>
                </div>
              )}
              {runtime.vram_mb && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  VRAM: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{(runtime.vram_mb / 1024).toFixed(1)} GB</span>
                </div>
              )}
              {runtime.framework && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  Framework: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{runtime.framework}</span>
                </div>
              )}
              {runtime.pytorch_version && (
                <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                  PyTorch: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{runtime.pytorch_version}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)' }}>
            Inferences: <span style={{ color: 'var(--aur-ink)', fontWeight: 500 }}>{runtime.total_inferences}</span>
          </div>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)' }}>
            Errors: <span style={{ color: runtime.total_errors > 0 ? 'var(--aur-negative)' : 'var(--aur-ink)', fontWeight: 500 }}>
              {runtime.total_errors}
            </span>
          </div>
        </div>

        {/* Error message */}
        {runtime.error_message && (
          <div style={{ fontSize: 10, color: 'var(--aur-negative)', marginTop: 6, fontStyle: 'italic' }}>
            {runtime.error_message}
          </div>
        )}
      </div>
    </GlassPanel>
  );
}

function Tag({ label }: { label: string }) {
  return (
    <span style={{
      fontSize: 9, padding: '2px 6px', borderRadius: 4,
      background: 'var(--aur-glass-strong)', color: 'var(--aur-accent)',
    }}>
      {label}
    </span>
  );
}

export const ComputePage: React.FC = () => {
  const { emit } = useEventBus();
  const [status, setStatus] = useState<ComputeStatus | null>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealth | null>(null);
  const [runtimes, setRuntimes] = useState<RuntimeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const [s, rh, rt] = await Promise.all([
        getComputeStatus(),
        getRuntimeHealth().catch(() => null),
        listRuntimes().catch(() => ({ runtimes: [], count: 0 })),
      ]);
      setStatus(s);
      setRuntimeHealth(rh);
      setRuntimes(rt.runtimes);
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
            <StatusCell label="BACKEND" value={status?.enabled ? 'ONLINE' : 'OFFLINE'} status={status?.enabled ? 'READY' : 'DISABLED'} />
            <StatusCell label="GPU" value={status?.gpu_enabled ? 'ON' : 'OFF'} status={status?.gpu_enabled ? 'READY' : 'DISABLED'} />
            <StatusCell label="MODE" value={status?.mode || 'CPU'} />
            <StatusCell label="ACTIVE" value={status?.active_provider || 'CPU'} />
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
          {status?.providers.map(p => (
            <ProviderCard key={p.provider_id} provider={p} />
          ))}
        </div>
      </div>

      {/* Runtime Status */}
      <GlassPanel>
        <div style={{ padding: 4 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
            Model Runtime
          </div>
          {runtimeHealth ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              <StatusCell label="STATUS" value={runtimeHealth.status.toUpperCase()} status={runtimeHealth.status === 'ok' ? 'READY' : 'ERROR'} />
              <StatusCell label="RUNTIMES" value={String(runtimeHealth.runtimes)} />
              <StatusCell label="MODELS" value={String(runtimeHealth.registry_models)} />
              <StatusCell label="INFERENCE JOBS" value={String(runtimeHealth.inference_jobs)} />
            </div>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)', fontStyle: 'italic' }}>
              Runtime not available
            </div>
          )}
        </div>
      </GlassPanel>

      {/* Active Runtimes */}
      {runtimes.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
            Active Runtimes
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
            {runtimes.map(rt => (
              <RuntimeCard key={rt.runtime_id} runtime={rt} />
            ))}
          </div>
        </div>
      )}

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

function StatusCell({ label, value, status }: { label: string; value: string; status?: string }) {
  return (
    <div style={{ padding: '10px 14px', background: 'var(--aur-bg-elevated)', borderRadius: 8 }}>
      <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {status && <StatusDot status={status} />}
        <span style={{ fontSize: 13, fontWeight: 600 }}>{value}</span>
      </div>
    </div>
  );
}

export default ComputePage;
