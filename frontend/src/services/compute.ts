/**
 * Compute Fabric — API client (v2).
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { API_BASE } from './config';

export type ComputeProviderType = 'CPU' | 'GOOGLE_COLAB' | 'LIGHTNING';
export type ComputeProviderStatus = 'DISABLED' | 'NOT_CONFIGURED' | 'CONFIGURED' | 'CONNECTING' | 'AUTHENTICATING' | 'HEALTH_CHECK' | 'STARTING' | 'READY' | 'BUSY' | 'DEGRADED' | 'DISCONNECTED' | 'STOPPING' | 'STOPPED' | 'ERROR' | 'UNKNOWN';
export type WorkerStatus = 'OFFLINE' | 'CONNECTING' | 'AUTHENTICATING' | 'READY' | 'BUSY' | 'UNHEALTHY' | 'DISCONNECTED' | 'SHUTTING_DOWN';
export type ComputeMode = 'AUTO' | 'CPU' | 'GOOGLE_COLAB' | 'LIGHTNING';
export type JobStatus = 'QUEUED' | 'ASSIGNED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'TIMEOUT';
export type WorkloadType = 'INFERENCE' | 'EMBEDDINGS' | 'VISION' | 'TRAINING' | 'BENCHMARK' | 'CUSTOM';

export interface GPUInfo {
  name: string;
  vendor: string;
  vram_mb: number;
  cuda_version: string | null;
  driver_version: string | null;
  compute_capability: string | null;
  available_memory_mb: number;
  runtime_info: string | null;
}

export interface ComputeCapabilities {
  inference: boolean;
  embeddings: boolean;
  vision: boolean;
  training: boolean;
  benchmark: boolean;
  max_concurrency: number;
  gpu: GPUInfo | null;
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
  worker_status: WorkerStatus;
  error_message: string | null;
}

export interface ComputeStatus {
  enabled: boolean;
  mode: ComputeMode;
  active_provider: string | null;
  providers: ComputeProviderInfo[];
  active_jobs: number;
  total_jobs_completed: number;
  gpu_enabled: boolean;
  last_updated: number;
}

export interface ComputeJob {
  job_id: string;
  workload_type: WorkloadType;
  provider_id: string;
  provider_type: ComputeProviderType;
  worker_id: string | null;
  status: JobStatus;
  progress: number;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  input_hash: string | null;
  result_hash: string | null;
  error: string | null;
}

export interface ComputeHealth {
  status: string;
  service: string;
  version: string;
  protocol_version: string;
  enabled: boolean;
  mode: string;
  providers: Record<string, string>;
  active_jobs: number;
  total_completed: number;
}

export interface BenchmarkResult {
  worker_id: string;
  provider_type: ComputeProviderType;
  gpu: GPUInfo;
  matrix_size: number;
  iterations: number;
  execution_time_seconds: number;
  gflops: number | null;
  result_checksum: string;
  status: 'NOT_RUN' | 'RUNNING' | 'PASSED' | 'FAILED';
  timestamp: number;
  error: string | null;
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

export async function listJobs(limit: number = 50): Promise<{ jobs: ComputeJob[]; total: number }> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/jobs?limit=${limit}`);
  if (!resp.ok) throw new Error(`List jobs failed: ${resp.status}`);
  return resp.json();
}

export async function submitJob(params: {
  workload_type: WorkloadType;
  provider_preference?: ComputeProviderType;
  payload?: Record<string, unknown>;
  timeout_seconds?: number;
}): Promise<ComputeJob> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Submit job failed: ${resp.status}`);
  return resp.json();
}

export async function cancelJob(jobId: string): Promise<{ cancelled: boolean; job_id: string }> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/jobs/${jobId}/cancel`, { method: 'POST' });
  if (!resp.ok) throw new Error(`Cancel job failed: ${resp.status}`);
  return resp.json();
}

export async function runBenchmark(params: {
  provider_type: ComputeProviderType;
  matrix_size?: number;
  iterations?: number;
}): Promise<BenchmarkResult> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/benchmark`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Benchmark failed: ${resp.status}`);
  return resp.json();
}
