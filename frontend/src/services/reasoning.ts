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

interface ReasonRequest {
  query: string;
  domain?: string;
  task?: string;
  context_ids?: string[];
  constraints?: string[];
  evidence?: EvidenceItem[];
}

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
}> {
  const res = await fetch(`${API_BASE}/api/v1/reason/health`);
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return res.json();
}
