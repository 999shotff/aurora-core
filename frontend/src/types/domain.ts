/**
 * Domain models shared across Aurora Core's shell pages
 * (Command Center, Intelligence, Research, Evidence, Reports, Neural Field).
 *
 * DataOrigin is load-bearing: every record that reaches the UI carries it,
 * so components can render a LIVE / DEMO / DERIVED / UNAVAILABLE badge
 * instead of presenting synthetic data as if it were real.
 */

export type DataOrigin = 'live' | 'demo' | 'derived' | 'unavailable';

export interface Sourced<T> {
  data: T;
  origin: DataOrigin;
  /** ISO timestamp this record was retrieved or generated */
  retrievedAt: string;
  /** Human-readable source, e.g. "Aurora Market Service" or "Demo Adapter" */
  source: string;
}

export type ConfidenceBand = 'low' | 'medium' | 'high';

export interface Investigation {
  id: string;
  title: string;
  question: string;
  status: 'active' | 'paused' | 'concluded';
  domain: 'market' | 'geo' | 'research' | 'general';
  confidence: ConfidenceBand;
  evidenceCount: number;
  createdAt: string;
  updatedAt: string;
}

export type EvidenceSourceType = 'satellite' | 'market-data' | 'document' | 'derived-metric' | 'note';

export interface EvidenceItem {
  id: string;
  investigationId: string | null;
  title: string;
  description: string;
  sourceType: EvidenceSourceType;
  source: string;
  timestamp: string;
  confidence: ConfidenceBand;
  status: 'unverified' | 'corroborated' | 'contested';
  metadata: Record<string, string>;
}

export interface Claim {
  id: string;
  investigationId: string;
  text: string;
  supportingEvidenceIds: string[];
  contradictingEvidenceIds: string[];
  confidence: ConfidenceBand;
}

export interface ReportRecord {
  id: string;
  title: string;
  investigationId: string | null;
  author: string;
  generatedAt: string;
  executiveSummary: string;
  findingsCount: number;
  confidence: ConfidenceBand;
  format: 'pdf' | 'csv' | 'md';
}

/** Neural Field: reflects real application processing state, not decoration. */
export type NeuralStage =
  | 'perception'
  | 'ingestion'
  | 'feature_extraction'
  | 'domain_analysis'
  | 'evidence_graph'
  | 'synthesis'
  | 'result';

export interface NeuralNode {
  id: string;
  stage: NeuralStage;
  label: string;
  active: boolean;
  detail?: string;
}

export interface NeuralEdge {
  from: string;
  to: string;
  active: boolean;
}

export type ProcessingEventKind =
  | 'connection'
  | 'data_fetch'
  | 'indicator_toggle'
  | 'structure_analysis'
  | 'navigation'
  | 'evidence_indexed'
  | 'synthesis';

export interface ProcessingEvent {
  id: string;
  kind: ProcessingEventKind;
  label: string;
  detail?: string;
  timestamp: string;
  origin: DataOrigin;
}
