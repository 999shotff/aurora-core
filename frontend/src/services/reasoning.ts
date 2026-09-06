import { API_BASE } from './config';

export interface ReasoningPoint {
  point: string;
  grounding: 'SUPPORTED_BY_EVIDENCE' | 'INFERENCE' | 'UNCERTAIN' | 'ABSTAINED';
  evidence_refs: string[];
}

export interface ReasoningResponse {
  request_id: string;
  status: string;
  answer: string;
  summary: string;
  evidence_refs: string[];
  reasoning_points: ReasoningPoint[];
  uncertainties: string[];
  conflicts: string[];
  abstention_reason: string | null;
  provider: string;
  model: string;
  context_hash: string;
  grounding_score: number;
}

export interface ToolReasonResponse extends ReasoningResponse {
  tools_executed: number;
  evidence_nodes: number;
  evidence_graph_summary: string;
}

export interface EvidenceItem {
  evidence_id: string;
  source: string;
  domain: string;
  claim: string;
  value?: string;
  timestamp?: string;
  confidence?: number;
  provenance?: string;
  quality?: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  permissions: string[];
  deterministic: boolean;
  timeout: number;
  input_schema: Record<string, unknown>;
}

export interface EvidenceGraphNode {
  evidence_id: string;
  tool_name: string;
  evidence_type: string;
  data_summary: string;
  source_refs: string[];
  created_at: number;
}

export interface EvidenceGraphEdge {
  source_id: string;
  target_id: string;
  relationship: string;
  confidence: number;
  description: string;
  created_at: number;
}

export interface EvidenceGraphData {
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
  node_count: number;
  edge_count: number;
  contradiction_count: number;
}

export interface SafetyLogEntry {
  timestamp: number;
  tool_name: string;
  input_hash: string;
  output_hash: string;
  permissions_used: string[];
  execution_time_ms: number;
  success: boolean;
  error: string | null;
  planning_context: string;
}

interface ReasonRequest {
  query: string;
  domain?: string;
  task?: string;
  context_ids?: string[];
  constraints?: string[];
  evidence?: EvidenceItem[];
}

interface ToolReasonRequest {
  query: string;
  domain?: string;
  goal?: string;
  context_ids?: string[];
  constraints?: string[];
}

interface WorkflowRequest {
  domain: string;
  params: Record<string, unknown>;
}

// ── LLM-1 Endpoints ──────────────────────────────────────────────────────

export async function reason(params: ReasonRequest): Promise<ReasoningResponse> {
  const res = await fetch(`${API_BASE}/api/v1/reason`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Reasoning failed: HTTP ${res.status}`);
  }

  return res.json();
}

export async function reasonHealth(): Promise<{
  status: string;
  providers: Record<string, unknown>;
  llm2_tools: number;
  evidence_nodes: number;
}> {
  const res = await fetch(`${API_BASE}/api/v1/reason/health`);
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return res.json();
}

// ── LLM-2 Endpoints ──────────────────────────────────────────────────────

export async function reasonWithTools(params: ToolReasonRequest): Promise<ToolReasonResponse> {
  const res = await fetch(`${API_BASE}/api/v1/reason/tool`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Tool reasoning failed: HTTP ${res.status}`);
  }

  return res.json();
}

export async function executeWorkflow(params: WorkflowRequest): Promise<{
  status: string;
  domain: string;
  result: Record<string, unknown>;
}> {
  const res = await fetch(`${API_BASE}/api/v1/reason/workflow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `Workflow failed: HTTP ${res.status}`);
  }

  return res.json();
}

export async function listTools(): Promise<{
  tools: ToolInfo[];
  tool_count: number;
}> {
  const res = await fetch(`${API_BASE}/api/v1/reason/tools`);
  if (!res.ok) throw new Error(`List tools failed: HTTP ${res.status}`);
  return res.json();
}

export async function getEvidenceGraph(): Promise<EvidenceGraphData> {
  const res = await fetch(`${API_BASE}/api/v1/reason/evidence-graph`);
  if (!res.ok) throw new Error(`Evidence graph failed: HTTP ${res.status}`);
  return res.json();
}

export async function getSafetyLog(): Promise<{
  log: SafetyLogEntry[];
  total_entries: number;
}> {
  const res = await fetch(`${API_BASE}/api/v1/reason/safety-log`);
  if (!res.ok) throw new Error(`Safety log failed: HTTP ${res.status}`);
  return res.json();
}
