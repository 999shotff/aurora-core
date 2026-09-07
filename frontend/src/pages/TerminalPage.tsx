/**
 * AURORA Terminal — unified intelligence workspace.
 *
 * Bloomberg-inspired information density with Liquid Glass design.
 * One primary assessment card + expandable detail panels.
 *
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { GlassPanel, LoadingState, EmptyState, StatusBadge } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import {
  runUnifiedAnalysis,
  getAnalysisHealth,
  type UnifiedAssessment,
  type DirectionalBias,
  type EvidenceClass,
} from '../services/analysis';
import { getComputeStatus, type ComputeStatus } from '../services/compute';

const BIAS_COLORS: Record<DirectionalBias, string> = {
  UP: 'var(--aur-positive)',
  DOWN: 'var(--aur-negative)',
  NEUTRAL: 'var(--aur-ink-dim)',
  MIXED: 'var(--aur-warning)',
  INSUFFICIENT_DATA: 'var(--aur-ink-faint)',
};

const BIAS_ICONS: Record<DirectionalBias, string> = {
  UP: '\u25B2',
  DOWN: '\u25BC',
  NEUTRAL: '\u2500',
  MIXED: '\u25C6',
  INSUFFICIENT_DATA: '?',
};

const STRENGTH_COLORS: Record<string, string> = {
  LOW: 'var(--aur-ink-dim)',
  MODERATE: 'var(--aur-warning)',
  HIGH: 'var(--aur-positive)',
};

const EVIDENCE_COLORS: Record<EvidenceClass, string> = {
  OBSERVED: 'var(--aur-positive)',
  DERIVED: 'var(--aur-accent)',
  STATISTICAL: 'var(--aur-accent-2)',
  SIMULATED: 'var(--aur-warning)',
  HYPOTHESIS: 'var(--aur-ink-dim)',
  UNAVAILABLE: 'var(--aur-negative)',
};

function PrimaryAssessmentCard({ assessment }: { assessment: UnifiedAssessment }) {
  const [expanded, setExpanded] = useState(false);
  const biasColor = BIAS_COLORS[assessment.directional_bias];

  return (
    <GlassPanel variant="strong">
      <div style={{ padding: 20 }}>
        {/* Primary signal */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
          <div style={{
            fontSize: 48, fontWeight: 700, fontFamily: 'var(--aur-font-display)',
            color: biasColor, lineHeight: 1, letterSpacing: '-0.02em',
          }}>
            {BIAS_ICONS[assessment.directional_bias]}
          </div>
          <div>
            <div style={{
              fontSize: 22, fontWeight: 700, fontFamily: 'var(--aur-font-display)',
              color: 'var(--aur-ink)', letterSpacing: '-0.01em',
            }}>
              {assessment.directional_bias}
            </div>
            <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
              {assessment.asset && `${assessment.asset} `}
              {assessment.timeframe && assessment.timeframe}
            </div>
          </div>
          <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 2 }}>Strength</div>
            <div style={{
              fontSize: 16, fontWeight: 700,
              color: STRENGTH_COLORS[assessment.strength] || 'var(--aur-ink-dim)',
            }}>
              {assessment.strength}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 2 }}>Confidence</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--aur-ink)' }}>
              {assessment.confidence.replace('_', ' ')}
            </div>
          </div>
        </div>

        {/* Evidence bar */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase' }}>Evidence</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--aur-ink)' }}>
            {assessment.evidence_agreement_ratio} agreement
          </span>
          <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>
            ({assessment.observed_count} observed, {assessment.derived_count} derived, {assessment.simulated_count} simulated, {assessment.hypothesis_count} hypothetical)
          </span>
        </div>

        {/* Regime */}
        {assessment.regime && assessment.regime !== 'UNKNOWN' && (
          <div style={{ fontSize: 11, color: 'var(--aur-accent)', marginBottom: 8 }}>
            Regime: {assessment.regime}
          </div>
        )}

        {/* Assessment text */}
        <div style={{
          fontSize: 13, color: 'var(--aur-ink)', lineHeight: 1.6,
          padding: '10px 14px', background: 'var(--aur-bg-elevated)',
          borderRadius: 8, marginBottom: 12,
        }}>
          {assessment.assessment}
        </div>

        {/* Expandable detail */}
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            fontSize: 11, color: 'var(--aur-accent)', background: 'none',
            border: 'none', cursor: 'pointer', padding: 0,
          }}
        >
          {expanded ? '\u25B2 Hide detail' : '\u25BC Show evidence detail'}
        </button>

        {expanded && (
          <div style={{ marginTop: 12 }}>
            {/* Supporting factors */}
            {assessment.supporting_factors.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-positive)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Supporting Factors
                </div>
                {assessment.supporting_factors.map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--aur-ink)', padding: '2px 0', paddingLeft: 8, borderLeft: '2px solid var(--aur-positive)' }}>
                    {f}
                  </div>
                ))}
              </div>
            )}

            {/* Contradicting factors */}
            {assessment.contradicting_factors.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-negative)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Contradicting Factors
                </div>
                {assessment.contradicting_factors.map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--aur-ink)', padding: '2px 0', paddingLeft: 8, borderLeft: '2px solid var(--aur-negative)' }}>
                    {f}
                  </div>
                ))}
              </div>
            )}

            {/* Behavioral factors */}
            {assessment.behavioral_factors.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-warning)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Behavioral Simulation (SIMULATED)
                </div>
                {assessment.behavioral_factors.map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--aur-ink)', padding: '2px 0', paddingLeft: 8, borderLeft: '2px solid var(--aur-warning)' }}>
                    {f}
                  </div>
                ))}
              </div>
            )}

            {/* Cycle hypotheses */}
            {assessment.cycle_hypotheses.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-ink-dim)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Cycle Hypotheses (HYPOTHESIS)
                </div>
                {assessment.cycle_hypotheses.map((f, i) => (
                  <div key={i} style={{ fontSize: 11, color: 'var(--aur-ink)', padding: '2px 0', paddingLeft: 8, borderLeft: '2px solid var(--aur-ink-dim)' }}>
                    {f}
                  </div>
                ))}
              </div>
            )}

            {/* Provenance */}
            {assessment.provenance.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-accent-2)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Provenance
                </div>
                {assessment.provenance.map((p, i) => (
                  <div key={i} style={{ fontSize: 10, color: 'var(--aur-ink-dim)', padding: '2px 0', display: 'flex', gap: 8 }}>
                    <span style={{
                      padding: '1px 6px', borderRadius: 4,
                      background: EVIDENCE_COLORS[p.evidence_class as EvidenceClass] || 'var(--aur-ink-dim)',
                      color: '#000', fontSize: 9, fontWeight: 700,
                    }}>
                      {p.evidence_class}
                    </span>
                    <span>{p.source_type}</span>
                    <span style={{ color: 'var(--aur-ink-faint)' }}>{p.methodology}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Limitations */}
            {assessment.limitations.length > 0 && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-warning)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Limitations
                </div>
                {assessment.limitations.map((l, i) => (
                  <div key={i} style={{ fontSize: 10, color: 'var(--aur-warning)', padding: '2px 0' }}>
                    {l}
                  </div>
                ))}
              </div>
            )}

            <div style={{ fontSize: 9, color: 'var(--aur-ink-faint)', marginTop: 8 }}>
              {assessment.total_inputs} input(s) | {assessment.computation_time_ms.toFixed(0)}ms | {assessment.assessment_id}
            </div>
          </div>
        )}
      </div>
    </GlassPanel>
  );
}

export const TerminalPage: React.FC = () => {
  const { emit } = useEventBus();
  const [question, setQuestion] = useState('');
  const [asset, setAsset] = useState('');
  const [assessment, setAssessment] = useState<UnifiedAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [computeStatus, setComputeStatus] = useState<ComputeStatus | null>(null);

  useEffect(() => {
    emit('navigation', 'Terminal opened', 'live');
    getAnalysisHealth().catch(() => {});
    getComputeStatus().then(setComputeStatus).catch(() => {});
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runUnifiedAnalysis({
        question: question.trim(),
        asset: asset.trim() || undefined,
        run_persona: false,
        run_cycles: false,
      });
      setAssessment(res);
      emit('analysis', `Assessment: ${res.directional_bias}`, 'live');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }, [question, asset]);

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 14, height: '100%', overflow: 'auto' }}>
      {/* Top bar: search + compute status */}
      <GlassPanel>
        <div style={{ padding: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Ask AURORA..."
            onKeyDown={e => { if (e.key === 'Enter') handleAnalyze(); }}
            style={{
              flex: 1, minWidth: 200, padding: '10px 14px',
              background: 'var(--aur-bg-elevated)', border: '1px solid var(--aur-border)',
              borderRadius: 8, color: 'var(--aur-ink)', fontSize: 14,
            }}
          />
          <input
            value={asset}
            onChange={e => setAsset(e.target.value)}
            placeholder="Asset (optional)"
            style={{
              width: 120, padding: '10px 14px',
              background: 'var(--aur-bg-elevated)', border: '1px solid var(--aur-border)',
              borderRadius: 8, color: 'var(--aur-ink)', fontSize: 13,
            }}
          />
          <button
            onClick={handleAnalyze}
            disabled={loading || !question.trim()}
            style={{
              padding: '10px 20px', background: 'var(--aur-accent)', border: 'none',
              borderRadius: 8, color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer', opacity: loading || !question.trim() ? 0.5 : 1,
            }}
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>

          {/* Compute status pill */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 10px', borderRadius: 6,
            background: computeStatus?.enabled ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${computeStatus?.enabled ? 'rgba(52,211,153,0.28)' : 'rgba(255,255,255,0.1)'}`,
            fontSize: 10, fontWeight: 600,
          }}>
            <span style={{
              width: 5, height: 5, borderRadius: '50%',
              background: computeStatus?.enabled ? 'var(--aur-positive)' : 'var(--aur-ink-dim)',
            }} />
            {computeStatus?.enabled ? 'GPU ON' : 'GPU OFF'}
          </div>
        </div>
      </GlassPanel>

      {error && (
        <div style={{ color: 'var(--aur-negative)', fontSize: 12, padding: '8px 12px', background: 'rgba(248,113,113,0.1)', borderRadius: 8 }}>
          {error}
        </div>
      )}

      {loading && <LoadingState label="Running unified analysis..." />}

      {!loading && !assessment && !error && (
        <EmptyState
          message="No analysis yet"
          hint="Enter a question to run AURORA unified analysis"
        />
      )}

      {assessment && <PrimaryAssessmentCard assessment={assessment} />}
    </div>
  );
};

export default TerminalPage;
