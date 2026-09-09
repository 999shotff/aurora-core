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
export type WorkloadType = 'INFERENCE' | 'EMBEDDINGS' | 'VISION' | 'TRAINING' | 'BENCHMARK' | 'RUNTIME_DISCOVER' | 'RUNTIME_LOAD' | 'RUNTIME_UNLOAD' | 'RUNTIME_HEALTH' | 'RUNTIME_INFER' | 'CUSTOM';
export type RuntimeStatus = 'UNAVAILABLE' | 'DISCOVERING' | 'LOADING' | 'READY' | 'BUSY' | 'UNLOADING' | 'ERROR';
export type ModelLoadStatus = 'NOT_LOADED' | 'LOADING' | 'LOADED' | 'UNLOADING' | 'ERROR';
export type InferenceStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TIMEOUT' | 'CANCELLED';

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

export interface ModelConfig {
  model_id: string;
  model_name: string;
  model_revision: string | null;
  framework: string;
  dtype: string;
  device: string;
  max_input_tokens: number;
  max_output_tokens: number;
  required_vram_gb: number;
  capabilities: string[];
  description: string;
  source: string;
  source_url: string | null;
}

export interface RuntimeInfo {
  runtime_id: string;
  status: RuntimeStatus;
  model: ModelConfig | null;
  model_load_status: ModelLoadStatus;
  worker_id: string | null;
  provider_type: string | null;
  gpu_name: string | null;
  vram_mb: number | null;
  cuda_version: string | null;
  framework: string | null;
  pytorch_version: string | null;
  model_memory_mb: number | null;
  loaded_at: number | null;
  last_inference_at: number | null;
  total_inferences: number;
  total_errors: number;
  uptime_seconds: number;
  error_message: string | null;
}

export interface InferenceResult {
  job_id: string;
  inference_id: string;
  model_id: string;
  model_name: string | null;
  worker_id: string;
  runtime_id: string;
  status: InferenceStatus;
  prompt_hash: string;
  output: string | null;
  output_hash: string | null;
  tokens_generated: number;
  generation_time_seconds: number;
  tokens_per_second: number;
  model_version: string | null;
  device: string | null;
  gpu_name: string | null;
  framework: string | null;
  dtype: string | null;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  error: string | null;
}

export interface RuntimeHealth {
  status: string;
  runtimes: number;
  registry_models: number;
  inference_jobs: number;
  timestamp: number;
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

// ============================================================
// Runtime API
// ============================================================

export async function getRuntimeHealth(): Promise<RuntimeHealth> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/health`);
  if (!resp.ok) throw new Error(`Runtime health failed: ${resp.status}`);
  return resp.json();
}

export async function listRuntimes(): Promise<{ runtimes: RuntimeInfo[]; count: number }> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/runtimes`);
  if (!resp.ok) throw new Error(`List runtimes failed: ${resp.status}`);
  return resp.json();
}

export async function getRuntime(runtimeId: string): Promise<RuntimeInfo> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/runtimes/${runtimeId}`);
  if (!resp.ok) throw new Error(`Get runtime failed: ${resp.status}`);
  return resp.json();
}

export async function discoverRuntime(workerId: string): Promise<{
  worker_id: string;
  runtime_id: string;
  status: RuntimeStatus;
  gpu_name: string | null;
  vram_mb: number | null;
  cuda_version: string | null;
  pytorch_version: string | null;
  available_models: string[];
  error: string | null;
}> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/runtimes/discover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ worker_id: workerId }),
  });
  if (!resp.ok) throw new Error(`Discover runtime failed: ${resp.status}`);
  return resp.json();
}

export async function loadModel(params: {
  model_id: string;
  worker_id: string;
  dtype?: string;
}): Promise<{
  worker_id: string;
  runtime_id: string;
  model_id: string;
  status: ModelLoadStatus;
  load_time_seconds: number | null;
  model_memory_mb: number | null;
  error: string | null;
}> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/runtimes/load`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Load model failed: ${resp.status}`);
  return resp.json();
}

export async function unloadModel(params: {
  worker_id: string;
  runtime_id: string;
}): Promise<{
  worker_id: string;
  runtime_id: string;
  model_id: string;
  status: ModelLoadStatus;
  error: string | null;
}> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/runtimes/unload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Unload model failed: ${resp.status}`);
  return resp.json();
}

export async function runInference(params: {
  model_id: string;
  prompt: string;
  max_new_tokens?: number;
  temperature?: number;
  top_p?: number;
  timeout_seconds?: number;
}): Promise<InferenceResult> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/inference`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Inference failed: ${resp.status}`);
  return resp.json();
}

export async function listInferenceJobs(): Promise<{ jobs: InferenceResult[]; count: number }> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/inference`);
  if (!resp.ok) throw new Error(`List inference jobs failed: ${resp.status}`);
  return resp.json();
}

export async function getRegistryModels(): Promise<ModelConfig[]> {
  const resp = await fetch(`${API_BASE}/api/v1/runtime/registry/models`);
  if (!resp.ok) throw new Error(`Get registry models failed: ${resp.status}`);
  return resp.json();
}

// ============================================================
// OpenAI-Compatible Remote Provider API
// ============================================================

export interface OpenAICompatibleTestResult {
  status: 'CONNECTED' | 'AUTHENTICATION_ERROR' | 'MODEL_UNAVAILABLE' | 'UNREACHABLE' | 'ERROR';
  provider: string;
  base_url: string;
  model: string;
  latency_ms: number;
  message: string;
  available_models?: string[];
}

export interface OpenAICompatibleConfigResult {
  status: 'CONFIGURED' | 'ERROR';
  provider: string;
  base_url: string;
  model: string;
  execution: string;
  gpu_required: boolean;
}

export interface OpenAICompatibleStatus {
  provider: string;
  status: 'NOT_CONFIGURED' | 'CONFIGURED' | 'CONNECTED';
  base_url?: string;
  model?: string;
  execution: string;
  gpu_required: boolean;
  api_key_configured?: boolean;
  api_key_redacted?: string;
}

export interface OpenAICompatibleInferResult {
  status: 'COMPLETED' | 'AUTHENTICATION_ERROR' | 'MODEL_NOT_FOUND' | 'REMOTE_UNAVAILABLE' | 'ERROR';
  output?: string;
  provenance?: Record<string, unknown>;
  error?: string;
}

export async function testOpenAICompatible(params: {
  base_url: string;
  api_key: string;
  model: string;
  provider_name?: string;
}): Promise<OpenAICompatibleTestResult> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/providers/openai-compatible/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Test connection failed: ${resp.status}`);
  return resp.json();
}

export async function configureOpenAICompatible(params: {
  base_url: string;
  api_key: string;
  model: string;
  provider_name?: string;
}): Promise<OpenAICompatibleConfigResult> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/providers/openai-compatible/configure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Configure failed: ${resp.status}`);
  return resp.json();
}

export async function getOpenAICompatibleStatus(): Promise<OpenAICompatibleStatus> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/providers/openai-compatible/status`);
  if (!resp.ok) throw new Error(`Status failed: ${resp.status}`);
  return resp.json();
}

export async function inferOpenAICompatible(params: {
  messages: Array<{ role: string; content: string }>;
  max_tokens?: number;
  temperature?: number;
  timeout?: number;
}): Promise<OpenAICompatibleInferResult> {
  const resp = await fetch(`${API_BASE}/api/v1/compute/providers/openai-compatible/infer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error(`Inference failed: ${resp.status}`);
  return resp.json();
}
