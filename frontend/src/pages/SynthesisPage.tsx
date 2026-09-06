/**
 * LLM-5 Synthesis Page — Evidence-Grounded Synthesis & Decision Intelligence.
 *
 * Question → Evidence Assessment → Findings → Hypotheses → Contradictions →
 * Uncertainty → Scenarios → Decision Considerations → Evidence Gaps → Provenance
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { GlassPanel, LoadingState, EmptyState } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import {
  executeSynthesis,
  getSynthesisHealth,
  type SynthesisResult,
  type FindingAssessment,
  type Hypothesis,
  type UncertaintyAssessment,
  type Scenario,
  type EvidenceGap,
  type ContradictionAssessment,
} from '../services/synthesis';

const STATUS_COLORS: Record<string, string> = {
  COMPLETE: 'var(--aur-positive)',
  PARTIAL: 'var(--aur-warning)',
  INDETERMINATE: 'var(--aur-ink-dim)',
  INSUFFICIENT_EVIDENCE: 'var(--aur-negative)',
  FAILED: 'var(--aur-negative)',
};

const CONFIDENCE_COLORS: Record<string, string> = {
  VERY_HIGH: 'var(--aur-positive)',
  HIGH: '#7C9EFF',
  MODERATE: 'var(--aur-warning)',
  LOW: 'var(--aur-accent-2)',
  VERY_LOW: 'var(--aur-negative)',
  UNDETERMINED: 'var(--aur-ink-dim)',
};

const HYPOTHESIS_STATUS_ICONS: Record<string, string> = {
  SUPPORTED: '\u2714',
  PARTIALLY_SUPPORTED: '\u25CB',
  CONTRADICTED: '\u2718',
  UNRESOLVED: '?',
  INSUFFICIENT_EVIDENCE: '\u2014',
};

function ConfidenceBadge({ level }: { level: string }) {
  const color = CONFIDENCE_COLORS[level] || 'var(--aur-ink-dim)';
  return (
    <span style={{
      display: 'inline-block', padding: '1px 8px', borderRadius: 4,
      fontSize: 10, fontWeight: 600, background: color, color: '#000',
      textTransform: 'uppercase',
    }}>
      {level.replace('_', ' ')}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || 'var(--aur-ink-dim)';
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: 6,
      fontSize: 11, fontWeight: 700, background: color, color: '#000',
      textTransform: 'uppercase',
    }}>
      {status.replace('_', ' ')}
    </span>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 700, color: 'var(--aur-accent)',
      textTransform: 'uppercase', letterSpacing: '0.08em',
      marginBottom: 8, marginTop: 16,
    }}>
      {children}
    </div>
  );
}

function FindingCard({ finding }: { finding: FindingAssessment }) {
  return (
    <GlassPanel>
      <div style={{ padding: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <ConfidenceBadge level={finding.confidence} />
          <StatusBadge status={finding.status} />
        </div>
        <div style={{ fontSize: 13, color: 'var(--aur-ink)', lineHeight: 1.5, marginBottom: 4 }}>
          {finding.statement}
        </div>
        {finding.reasoning_summary && (
          <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', fontStyle: 'italic' }}>
            {finding.reasoning_summary}
          </div>
        )}
        <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 4 }}>
          Evidence: {finding.supporting_evidence.length} supporting, {finding.contradicting_evidence.length} contradicting
        </div>
      </div>
    </GlassPanel>
  );
}

function HypothesisCard({ hypothesis, rank }: { hypothesis: Hypothesis; rank: number }) {
  const icon = HYPOTHESIS_STATUS_ICONS[hypothesis.status] || '?';
  return (
    <GlassPanel>
      <div style={{ padding: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 16 }}>{icon}</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink-dim)' }}>H{rank}</span>
          <ConfidenceBadge level={hypothesis.confidence} />
          <StatusBadge status={hypothesis.status} />
        </div>
        <div style={{ fontSize: 13, color: 'var(--aur-ink)', lineHeight: 1.5, marginBottom: 4 }}>
          {hypothesis.statement}
        </div>
        {hypothesis.assumptions.length > 0 && (
          <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>
            Assumptions: {hypothesis.assumptions.join('; ')}
          </div>
        )}
        <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 2 }}>
          {hypothesis.supporting_evidence.length} supporting, {hypothesis.contradicting_evidence.length} contradicting
        </div>
      </div>
    </GlassPanel>
  );
}

function UncertaintyCard({ item }: { item: UncertaintyAssessment }) {
  const kindColors: Record<string, string> = {
    KNOWN: 'var(--aur-positive)',
    SUPPORTED_INFERENCE: 'var(--aur-warning)',
    ASSUMPTION: 'var(--aur-accent-2)',
    UNKNOWN: 'var(--aur-ink-dim)',
    CONTRADICTED: 'var(--aur-negative)',
    UNAVAILABLE: 'var(--aur-negative)',
  };
  const color = kindColors[item.kind] || 'var(--aur-ink-dim)';
  return (
    <div style={{
      padding: '8px 12px', borderLeft: `3px solid ${color}`,
      background: 'var(--aur-bg-elevated)', borderRadius: 4, marginBottom: 6,
    }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color, textTransform: 'uppercase' }}>
          {item.kind.replace('_', ' ')}
        </span>
        {item.impact && (
          <span style={{ fontSize: 9, color: 'var(--aur-ink-faint)' }}>Impact: {item.impact}</span>
        )}
      </div>
      <div style={{ fontSize: 12, color: 'var(--aur-ink)' }}>{item.element}</div>
      <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', marginTop: 2 }}>{item.description}</div>
      {item.reduction_path && (
        <div style={{ fontSize: 10, color: 'var(--aur-accent)', marginTop: 2 }}>
          Reduction: {item.reduction_path}
        </div>
      )}
    </div>
  );
}

function ContradictionCard({ item }: { item: ContradictionAssessment }) {
  return (
    <div style={{
      padding: '8px 12px', borderLeft: '3px solid var(--aur-negative)',
      background: 'var(--aur-bg-elevated)', borderRadius: 4, marginBottom: 6,
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-negative)', textTransform: 'uppercase', marginBottom: 4 }}>
        {item.contradiction_type.replace('_', ' ')} — Severity: {item.severity}
      </div>
      <div style={{ fontSize: 12, color: 'var(--aur-ink)' }}>{item.description}</div>
      <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 2 }}>
        {item.evidence_a} vs {item.evidence_b}
      </div>
    </div>
  );
}

export const SynthesisPage: React.FC = () => {
  const { emit } = useEventBus();
  const [question, setQuestion] = useState('');
  const [domain, setDomain] = useState('general');
  const [result, setResult] = useState<SynthesisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<{ status: string } | null>(null);

  useEffect(() => {
    emit('navigation', 'Synthesis opened', 'live');
    getSynthesisHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const handleSynthesize = useCallback(async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await executeSynthesis({ question: question.trim(), domain });
      setResult(res);
      emit('synthesis', `Synthesis complete: ${res.synthesis_status}`, res.synthesis_status === 'COMPLETE' ? 'live' : 'derived');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Synthesis failed');
    } finally {
      setLoading(false);
    }
  }, [question, domain]);

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflow: 'auto' }}>
      <GlassPanel>
        <div style={{ padding: 16 }}>
          <h2 style={{ margin: '0 0 4px', fontSize: 18, color: 'var(--aur-ink)' }}>
            Evidence-Grounded Synthesis
          </h2>
          <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', marginBottom: 12 }}>
            LLM-5 — Decision Intelligence. Synthesizes evidence into findings, hypotheses, and decision considerations.
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="Ask a question to synthesize evidence..."
              onKeyDown={e => { if (e.key === 'Enter') handleSynthesize(); }}
              style={{
                flex: 1, minWidth: 200, padding: '8px 12px',
                background: 'var(--aur-bg-elevated)', border: '1px solid var(--aur-border)',
                borderRadius: 8, color: 'var(--aur-ink)', fontSize: 14,
              }}
            />
            <select
              value={domain}
              onChange={e => setDomain(e.target.value)}
              style={{
                padding: '8px 12px', background: 'var(--aur-bg-elevated)',
                border: '1px solid var(--aur-border)', borderRadius: 8,
                color: 'var(--aur-ink)', fontSize: 13,
              }}
            >
              <option value="general">General</option>
              <option value="market">Market</option>
              <option value="geo">Geo</option>
              <option value="research">Research</option>
            </select>
            <button
              onClick={handleSynthesize}
              disabled={loading || !question.trim()}
              style={{
                padding: '8px 20px', background: 'var(--aur-accent)', border: 'none',
                borderRadius: 8, color: '#fff', fontSize: 14, fontWeight: 600,
                cursor: loading ? 'wait' : 'pointer', opacity: loading || !question.trim() ? 0.5 : 1,
              }}
            >
              {loading ? 'Synthesizing...' : 'Synthesize'}
            </button>
          </div>

          {health && (
            <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 8 }}>
              Engine: {health.status} | LLM-5 v0.1.0
            </div>
          )}
        </div>
      </GlassPanel>

      {error && (
        <div style={{ color: 'var(--aur-negative)', fontSize: 13, padding: '0 4px' }}>{error}</div>
      )}

      {loading && <LoadingState label="Synthesizing evidence..." />}

      {!loading && !result && !error && (
        <EmptyState
          message="No synthesis yet"
          hint="Enter a question and click Synthesize to analyze evidence"
        />
      )}

      {result && (
        <>
          <GlassPanel>
            <div style={{ padding: 16 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                <StatusBadge status={result.synthesis_status} />
                <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>
                  {result.synthesis_id}
                </span>
                <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>
                  Causal: {result.causal_level}
                </span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--aur-ink)', lineHeight: 1.6 }}>
                {result.executive_summary}
              </div>
            </div>
          </GlassPanel>

          {result.key_findings.length > 0 && (
            <>
              <SectionTitle>Key Findings</SectionTitle>
              {result.key_findings.map(f => (
                <FindingCard key={f.finding_id} finding={f} />
              ))}
            </>
          )}

          {result.hypotheses.length > 0 && (
            <>
              <SectionTitle>Hypotheses</SectionTitle>
              {result.hypotheses.map((h, i) => (
                <HypothesisCard key={h.hypothesis_id} hypothesis={h} rank={i + 1} />
              ))}
            </>
          )}

          {result.contradictions.length > 0 && (
            <>
              <SectionTitle>Contradictions</SectionTitle>
              {result.contradictions.map(c => (
                <ContradictionCard key={c.contradiction_id} item={c} />
              ))}
            </>
          )}

          {result.uncertainty_assessments.length > 0 && (
            <>
              <SectionTitle>Uncertainty Assessment</SectionTitle>
              {result.uncertainty_assessments.map((u, i) => (
                <UncertaintyCard key={i} item={u} />
              ))}
            </>
          )}

          {result.known_facts.length > 0 && (
            <>
              <SectionTitle>Known Facts</SectionTitle>
              <GlassPanel>
                <div style={{ padding: 12 }}>
                  {result.known_facts.map((f, i) => (
                    <div key={i} style={{ fontSize: 12, color: 'var(--aur-ink)', padding: '3px 0', borderBottom: '1px solid var(--aur-border-soft)' }}>
                      {f}
                    </div>
                  ))}
                </div>
              </GlassPanel>
            </>
          )}

          {result.scenarios.length > 0 && (
            <>
              <SectionTitle>Scenarios</SectionTitle>
              {result.scenarios.map(s => (
                <GlassPanel key={s.scenario_id}>
                  <div style={{ padding: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--aur-ink)', marginBottom: 4 }}>{s.label}</div>
                    {s.assumptions.length > 0 && (
                      <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', marginBottom: 4 }}>
                        <strong>Assumptions:</strong> {s.assumptions.join('; ')}
                      </div>
                    )}
                    {s.trigger_conditions.length > 0 && (
                      <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', marginBottom: 4 }}>
                        <strong>Triggers:</strong> {s.trigger_conditions.join('; ')}
                      </div>
                    )}
                    {s.implications.length > 0 && (
                      <div style={{ fontSize: 11, color: 'var(--aur-accent)', marginBottom: 4 }}>
                        <strong>Implications:</strong> {s.implications.join('; ')}
                      </div>
                    )}
                    {s.uncertainty.length > 0 && (
                      <div style={{ fontSize: 10, color: 'var(--aur-warning)' }}>
                        Uncertainty: {s.uncertainty.join('; ')}
                      </div>
                    )}
                  </div>
                </GlassPanel>
              ))}
            </>
          )}

          {result.decision_considerations.length > 0 && (
            <>
              <SectionTitle>Decision Considerations</SectionTitle>
              {result.decision_considerations.map((d, i) => (
                <div key={i} style={{
                  padding: '8px 12px', borderLeft: '3px solid var(--aur-accent-2)',
                  background: 'var(--aur-bg-elevated)', borderRadius: 4, marginBottom: 6,
                }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                    <ConfidenceBadge level={d.confidence} />
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--aur-ink)' }}>{d.consideration}</div>
                  {d.key_uncertainty && (
                    <div style={{ fontSize: 10, color: 'var(--aur-warning)', marginTop: 2 }}>
                      Uncertainty: {d.key_uncertainty}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {result.evidence_gaps.length > 0 && (
            <>
              <SectionTitle>Evidence Gaps</SectionTitle>
              {result.evidence_gaps.map(g => (
                <div key={g.gap_id} style={{
                  padding: '8px 12px', borderLeft: '3px solid var(--aur-ink-dim)',
                  background: 'var(--aur-bg-elevated)', borderRadius: 4, marginBottom: 6,
                }}>
                  <div style={{ fontSize: 12, color: 'var(--aur-ink)' }}>{g.description}</div>
                  {g.why_it_matters && (
                    <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
                      {g.why_it_matters}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {result.provenance.length > 0 && (
            <>
              <SectionTitle>Provenance</SectionTitle>
              <GlassPanel>
                <div style={{ padding: 12 }}>
                  {result.provenance.map((p, i) => (
                    <details key={i} style={{ marginBottom: 8 }}>
                      <summary style={{ fontSize: 11, color: 'var(--aur-ink)', cursor: 'pointer', fontWeight: 500 }}>
                        {p.conclusion.substring(0, 80)}...
                      </summary>
                      <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', padding: '4px 0 4px 12px' }}>
                        <div>Evidence: {p.evidence_ids.join(', ')}</div>
                        <div>Sources: {p.source_ids.join(', ')}</div>
                        <div>Chain: {p.reasoning_chain.join(' → ')}</div>
                      </div>
                    </details>
                  ))}
                </div>
              </GlassPanel>
            </>
          )}

          {result.limitations.length > 0 && (
            <>
              <SectionTitle>Limitations</SectionTitle>
              <GlassPanel>
                <div style={{ padding: 12 }}>
                  {result.limitations.map((l, i) => (
                    <div key={i} style={{ fontSize: 11, color: 'var(--aur-warning)', padding: '2px 0' }}>
                      • {l}
                    </div>
                  ))}
                </div>
              </GlassPanel>
            </>
          )}
        </>
      )}
    </div>
  );
};

export default SynthesisPage;
