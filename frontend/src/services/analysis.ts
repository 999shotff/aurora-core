/**
 * Unified Analysis — API client.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import { API_BASE } from './config';

export type EvidenceClass = 'OBSERVED' | 'DERIVED' | 'STATISTICAL' | 'SIMULATED' | 'HYPOTHESIS' | 'UNAVAILABLE';
export type DirectionalBias = 'UP' | 'DOWN' | 'NEUTRAL' | 'MIXED' | 'INSUFFICIENT_DATA';
export type AssessmentStrength = 'LOW' | 'MODERATE' | 'HIGH';

export interface UnifiedAssessment {
  assessment_id: string;
  question: string;
  assessment: string;
  directional_bias: DirectionalBias;
  strength: AssessmentStrength;
  confidence: string;
  evidence_summary: string;
  total_inputs: number;
  observed_count: number;
  derived_count: number;
  simulated_count: number;
  hypothesis_count: number;
  evidence_agreement_ratio: string;
  supporting_factors: string[];
  contradicting_factors: string[];
  behavioral_factors: string[];
  cycle_hypotheses: string[];
  regime: string;
  uncertainty: string[];
  limitations: string[];
  source_inputs: string[];
  provenance: Array<{
    source_id: string;
    source_type: string;
    evidence_class: EvidenceClass;
    methodology: string;
  }>;
  asset: string | null;
  timeframe: string | null;
  domain: string;
  timestamp: number;
  computation_time_ms: number;
}

export interface UnifiedAnalysisRequest {
  question: string;
  asset?: string;
  timeframe?: string;
  domain?: string;
  market_context?: Record<string, unknown>;
  indicator_data?: Record<string, unknown>;
  structure_data?: Record<string, unknown>;
  run_persona?: boolean;
  run_cycles?: boolean;
}

export async function runUnifiedAnalysis(req: UnifiedAnalysisRequest): Promise<UnifiedAssessment> {
  const resp = await fetch(`${API_BASE}/api/v1/analysis/unified`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!resp.ok) throw new Error(`Analysis failed: ${resp.status}`);
  return resp.json();
}

export async function getAssessment(id: string): Promise<UnifiedAssessment> {
  const resp = await fetch(`${API_BASE}/api/v1/analysis/unified/${id}`);
  if (!resp.ok) throw new Error(`Assessment not found: ${resp.status}`);
  return resp.json();
}

export async function getAnalysisHealth(): Promise<{ status: string; service: string }> {
  const resp = await fetch(`${API_BASE}/api/v1/analysis/unified/health`);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}
