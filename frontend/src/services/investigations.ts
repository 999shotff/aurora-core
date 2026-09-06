/**
 * LLM-4: Investigation API client.
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { API_BASE } from './config';

const BASE = `${API_BASE}/api/v1/investigations`;

export interface InvestigationObjective {
  query: string;
  domain?: string;
  subject?: string;
  scope?: string;
  temporal_range?: Record<string, unknown>;
  constraints?: string[];
  idempotency_key?: string;
}

export interface InvestigationSummary {
  investigation_id: string;
  status: string;
  domain: string;
  query: string;
  subject: string;
  created_at: number;
  updated_at: number;
  started_at: number | null;
  completed_at: number | null;
  evidence_count: number;
  findings_count: number;
  tools_used: string[];
}

export interface InvestigationEvent {
  event_id: string;
  timestamp: number;
  event_type: string;
  summary: string;
  references: string[];
}

export interface InvestigationFinding {
  finding_id: string;
  statement: string;
  classification: string;
  confidence: number;
  status: string;
  evidence_refs: string[];
}

export interface InvestigationResultData {
  status: string;
  executive_summary: string;
  findings: InvestigationFinding[];
  evidence_refs: string[];
  uncertainties: string[];
  conflicts: string[];
  tools_used: string[];
}

export async function createInvestigation(
  objective: InvestigationObjective,
): Promise<InvestigationSummary> {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(objective),
  });
  return res.json();
}

export async function listInvestigations(
  params?: { status?: string; domain?: string; limit?: number },
): Promise<{ investigations: InvestigationSummary[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.domain) query.set('domain', params.domain);
  if (params?.limit) query.set('limit', String(params.limit));
  const res = await fetch(`${BASE}?${query}`);
  return res.json();
}

export async function getInvestigation(
  id: string,
): Promise<InvestigationSummary> {
  const res = await fetch(`${BASE}/${id}`);
  return res.json();
}

export async function startInvestigation(
  id: string,
): Promise<InvestigationSummary> {
  const res = await fetch(`${BASE}/${id}/start`, { method: 'POST' });
  return res.json();
}

export async function cancelInvestigation(
  id: string,
): Promise<{ investigation_id: string; status: string }> {
  const res = await fetch(`${BASE}/${id}/cancel`, { method: 'POST' });
  return res.json();
}

export async function reopenInvestigation(
  id: string,
): Promise<{ investigation_id: string; status: string }> {
  const res = await fetch(`${BASE}/${id}/reopen`, { method: 'POST' });
  return res.json();
}

export async function getInvestigationEvents(
  id: string,
): Promise<{ investigation_id: string; events: InvestigationEvent[] }> {
  const res = await fetch(`${BASE}/${id}/events`);
  return res.json();
}

export async function getInvestigationFindings(
  id: string,
): Promise<{ investigation_id: string; findings: InvestigationFinding[] }> {
  const res = await fetch(`${BASE}/${id}/findings`);
  return res.json();
}

export async function getInvestigationResult(
  id: string,
): Promise<{ investigation_id: string; result: InvestigationResultData | null }> {
  const res = await fetch(`${BASE}/${id}/result`);
  return res.json();
}
