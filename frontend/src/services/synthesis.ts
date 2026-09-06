/**
 * LLM-5 Synthesis Service — API client for evidence-grounded synthesis.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { API_BASE } from './config';

export interface SynthesisRequest {
  question: string;
  investigation_id?: string;
  evidence_ids?: string[];
  finding_ids?: string[];
  memory_ids?: string[];
  domain?: string;
}

export interface EvidenceAssessment {
  evidence_id: string;
  source: string;
  evidence_type: string;
  domain: string;
  claim: string;
  freshness: string;
  relevance: string;
  reliability: string;
  direct_vs_derived: string;
  limitations: string[];
}

export interface FindingAssessment {
  finding_id: string;
  statement: string;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  status: string;
  confidence: string;
  uncertainty: string[];
  reasoning_summary: string;
}

export interface Hypothesis {
  hypothesis_id: string;
  statement: string;
  supporting_evidence: string[];
  contradicting_evidence: string[];
  assumptions: string[];
  confidence: string;
  status: string;
}

export interface ContradictionAssessment {
  contradiction_id: string;
  contradiction_type: string;
  evidence_a: string;
  evidence_b: string;
  description: string;
  severity: string;
}

export interface UncertaintyAssessment {
  element: string;
  kind: string;
  description: string;
  impact: string;
  reduction_path: string | null;
}

export interface Scenario {
  scenario_id: string;
  label: string;
  assumptions: string[];
  evidence_basis: string[];
  trigger_conditions: string[];
  implications: string[];
  uncertainty: string[];
}

export interface EvidenceGap {
  gap_id: string;
  description: string;
  why_it_matters: string;
  status: string;
}

export interface DecisionConsideration {
  consideration: string;
  evidence_basis: string[];
  confidence: string;
  key_uncertainty: string;
}

export interface ProvenanceRecord {
  conclusion: string;
  finding_ids: string[];
  evidence_ids: string[];
  source_ids: string[];
  reasoning_chain: string[];
}

export interface SynthesisResult {
  synthesis_id: string;
  question: string;
  executive_summary: string;
  key_findings: FindingAssessment[];
  hypotheses: Hypothesis[];
  contradictions: ContradictionAssessment[];
  known_facts: string[];
  supported_inferences: string[];
  assumptions: string[];
  unknowns: string[];
  scenarios: Scenario[];
  decision_considerations: DecisionConsideration[];
  evidence_gaps: EvidenceGap[];
  limitations: string[];
  provenance: ProvenanceRecord[];
  synthesis_status: string;
  evidence_assessments: EvidenceAssessment[];
  uncertainty_assessments: UncertaintyAssessment[];
  causal_level: string;
  timestamp: number;
}

export async function executeSynthesis(req: SynthesisRequest): Promise<SynthesisResult> {
  const resp = await fetch(`${API_BASE}/api/v1/synthesis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!resp.ok) throw new Error(`Synthesis failed: ${resp.status}`);
  return resp.json();
}

export async function getSynthesis(synthesisId: string): Promise<SynthesisResult> {
  const resp = await fetch(`${API_BASE}/api/v1/synthesis/${synthesisId}`);
  if (!resp.ok) throw new Error(`Synthesis not found: ${resp.status}`);
  return resp.json();
}

export async function getSynthesisHealth(): Promise<{ status: string; service: string }> {
  const resp = await fetch(`${API_BASE}/api/v1/synthesis/health`);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}
