/**
 * Compute Fabric — API client.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { API_BASE } from './config';

export type ComputeProviderType = 'CPU' | 'GOOGLE_COLAB' | 'LIGHTNING';
export type ComputeProviderStatus = 'DISABLED' | 'NOT_CONFIGURED' | 'STARTING' | 'READY' | 'BUSY' | 'DEGRADED' | 'DISCONNECTED' | 'STOPPING' | 'STOPPED' | 'ERROR' | 'UNKNOWN';
export type ComputeMode = 'AUTO' | 'CPU' | 'GOOGLE_COLAB' | 'LIGHTNING';
export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'TIMEOUT';
export type WorkloadType = 'INFERENCE' | 'EMBEDDINGS' | 'VISION' | 'TRAINING' | 'CUSTOM';

export interface ComputeCapabilities {
  inference: boolean;
  embeddings: boolean;
  vision: boolean;
  training: boolean;
  max_concurrency: number;
  gpu_name: string | null;
  vram_gb: number | null;
  cuda_version: string | null;
  framework: string | null;
  python_version: string | null;
}

export interface ComputeProviderInfo {
  provider_id: string;
  provider_type: ComputeProviderType;
  name: string;
  status: ComputeProviderStatus;
  capabilities: ComputeCapabilities;
  last_health_check: number | null;
  last_heartbeat: number | null;
  worker_id: string | null;
  error_message: string | null;
}

export interface ComputeStatus {
  enabled: boolean;
  mode: ComputeMode;
  active_provider: string | null;
  providers: ComputeProviderInfo[];
  active_jobs: number;
  total_jobs_completed: number;
  last_updated: number;
}

export interface ComputeJob {
  job_id: string;
  workload_type: WorkloadType;
  provider_id: string;
  provider_type: ComputeProviderType;
  status: JobStatus;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  error: string | null;
}

export interface ComputeHealth {
  status: string;
  service: string;
  version: string;
  enabled: boolean;
  mode: string;
  providers: Record<string, string>;
  active_jobs: number;
  total_completed: number;
}

export async function getComputeStatus(): Promise<ComputeStatus> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/status`);
  if (!resp.ok) throw new Error(`Compute status failed: ${resp.status}`);
  return resp.json();
}

export async function getComputeHealth(): Promise<ComputeHealth> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/health`);
  if (!resp.ok) throw new Error(`Compute health failed: ${resp.status}`);
  return resp.json();
}

export async function getComputeProviders(): Promise<{ providers: ComputeProviderInfo[] }> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/providers`);
  if (!resp.ok) throw new Error(`Compute providers failed: ${resp.status}`);
  return resp.json();
}

export async function enableCompute(): Promise<ComputeStatus> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/enable`, { method: 'POST' });
  if (!resp.ok) throw new Error(`Enable compute failed: ${resp.status}`);
  return resp.json();
}

export async function disableCompute(): Promise<ComputeStatus> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/disable`, { method: 'POST' });
  if (!resp.ok) throw new Error(`Disable compute failed: ${resp.status}`);
  return resp.json();
}

export async function setComputeMode(mode: ComputeMode): Promise<ComputeStatus> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  if (!resp.ok) throw new Error(`Set compute mode failed: ${resp.status}`);
  return resp.json();
}
