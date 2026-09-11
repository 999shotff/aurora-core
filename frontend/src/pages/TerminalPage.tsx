/**
 * AURORA Terminal — Unified Intelligence Workspace.
 *
 * Premium desktop-first workstation integrating all AURORA subsystems.
 * Command bar, provider status, primary workspace, secondary panels.
 *
 * Reuses existing components. No duplicate logic.
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import {
  Terminal,
  LineChart,
  Globe2,
  BrainCircuit,
  FlaskConical,
  Database,
  Cpu,
  BarChart3,
  Newspaper,
  Shield,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { GlassPanel, LoadingState, EmptyState, StatusBadge } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import {
  runUnifiedAnalysis,
  type UnifiedAssessment,
  type DirectionalBias,
  type EvidenceClass,
} from '../services/analysis';
import { getComputeStatus, type ComputeStatus } from '../services/compute';
import { reasonHealth } from '../services/reasoning';
import {
  TerminalCommandBar,
  ProviderStatusPanel,
  MacroWorkspacePanel,
  NewsResearchPanel,
  RiskPortfolioPanel,
} from '../components/terminal';

// Lazy-load existing panels for secondary workspace
const EvidenceGraphView = lazy(() =>
  import('../components/llm2/EvidenceGraphView').then(m => ({ default: m.EvidenceGraphView }))
);
const ReasoningPanel = lazy(() =>
  import('../components/llm2/ReasoningPanel').then(m => ({ default: m.ReasoningPanel }))
);

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

const EVIDENCE_COLORS: Record<EvidenceClass, string> = {
  OBSERVED: 'var(--aur-positive)',
  DERIVED: 'var(--aur-accent)',
  STATISTICAL: 'var(--aur-accent-2)',
  SIMULATED: 'var(--aur-warning)',
  HYPOTHESIS: 'var(--aur-ink-dim)',
  UNAVAILABLE: 'var(--aur-negative)',
};

type WorkspaceTab = 'command' | 'market' | 'macro' | 'research' | 'ai' | 'geo' | 'risk';

const WORKSPACE_TABS: { id: WorkspaceTab; label: string; icon: React.ReactNode }[] = [
  { id: 'command', label: 'Command Center', icon: <Terminal size={14} /> },
  { id: 'market', label: 'Market', icon: <LineChart size={14} /> },
  { id: 'macro', label: 'Macro', icon: <Globe2 size={14} /> },
  { id: 'research', label: 'Research', icon: <Newspaper size={14} /> },
  { id: 'ai', label: 'AI Intelligence', icon: <BrainCircuit size={14} /> },
  { id: 'geo', label: 'Geo', icon: <Globe2 size={14} /> },
  { id: 'risk', label: 'Risk', icon: <Shield size={14} /> },
];

const SECONDARY_TABS: { id: string; label: string }[] = [
  { id: 'evidence', label: 'Evidence Graph' },
  { id: 'ai-reason', label: 'AI Reasoning' },
  { id: 'macro-panel', label: 'Macro' },
  { id: 'news', label: 'News' },
  { id: 'risk-panel', label: 'Risk' },
];

/* ── Assessment Card ─────────────────────────────────────────────────────── */

function AssessmentCard({ assessment }: { assessment: UnifiedAssessment }) {
  const [expanded, setExpanded] = useState(false);
  const biasColor = BIAS_COLORS[assessment.directional_bias];

  return (
    <GlassPanel variant="strong">
      <div style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
          <div
            style={{
              fontSize: 48,
              fontWeight: 700,
              fontFamily: 'var(--aur-font-display)',
              color: biasColor,
              lineHeight: 1,
              letterSpacing: '-0.02em',
            }}
          >
            {BIAS_ICONS[assessment.directional_bias]}
          </div>
          <div>
            <div
              style={{
                fontSize: 22,
                fontWeight: 700,
                fontFamily: 'var(--aur-font-display)',
                color: 'var(--aur-ink)',
                letterSpacing: '-0.01em',
              }}
            >
              {assessment.directional_bias}
            </div>
            <div style={{ fontSize: 12, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
              {assessment.asset && `${assessment.asset} `}
              {assessment.timeframe && assessment.timeframe}
            </div>
          </div>
          <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 2 }}>
              Strength
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--aur-ink)' }}>{assessment.strength}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase', marginBottom: 2 }}>
              Confidence
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--aur-ink)' }}>
              {assessment.confidence.replace('_', ' ')}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)', textTransform: 'uppercase' }}>Evidence</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--aur-ink)' }}>
            {assessment.evidence_agreement_ratio} agreement
          </span>
          <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>
            ({assessment.observed_count} observed, {assessment.derived_count} derived,{' '}
            {assessment.simulated_count} simulated, {assessment.hypothesis_count} hypothetical)
          </span>
        </div>

        {assessment.regime && assessment.regime !== 'UNKNOWN' && (
          <div style={{ fontSize: 11, color: 'var(--aur-accent)', marginBottom: 8 }}>Regime: {assessment.regime}</div>
        )}

        <div
          style={{
            fontSize: 13,
            color: 'var(--aur-ink)',
            lineHeight: 1.6,
            padding: '10px 14px',
            background: 'var(--aur-bg-elevated)',
            borderRadius: 8,
            marginBottom: 12,
          }}
        >
          {assessment.assessment}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          style={{ fontSize: 11, color: 'var(--aur-accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
        >
          {expanded ? '\u25B2 Hide detail' : '\u25BC Show evidence detail'}
        </button>

        {expanded && (
          <div style={{ marginTop: 12 }}>
            {assessment.supporting_factors.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-positive)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Supporting Factors
                </div>
                {assessment.supporting_factors.map((f, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 11,
                      color: 'var(--aur-ink)',
                      padding: '2px 0',
                      paddingLeft: 8,
                      borderLeft: '2px solid var(--aur-positive)',
                    }}
                  >
                    {f}
                  </div>
                ))}
              </div>
            )}

            {assessment.contradicting_factors.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-negative)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Contradicting Factors
                </div>
                {assessment.contradicting_factors.map((f, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 11,
                      color: 'var(--aur-ink)',
                      padding: '2px 0',
                      paddingLeft: 8,
                      borderLeft: '2px solid var(--aur-negative)',
                    }}
                  >
                    {f}
                  </div>
                ))}
              </div>
            )}

            {assessment.provenance.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--aur-accent-2)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Provenance
                </div>
                {assessment.provenance.map((p, i) => (
                  <div key={i} style={{ fontSize: 10, color: 'var(--aur-ink-dim)', padding: '2px 0', display: 'flex', gap: 8 }}>
                    <span
                      style={{
                        padding: '1px 6px',
                        borderRadius: 4,
                        background: EVIDENCE_COLORS[p.evidence_class as EvidenceClass] || 'var(--aur-ink-dim)',
                        color: '#000',
                        fontSize: 9,
                        fontWeight: 700,
                      }}
                    >
                      {p.evidence_class}
                    </span>
                    <span>{p.source_type}</span>
                    <span style={{ color: 'var(--aur-ink-faint)' }}>{p.methodology}</span>
                  </div>
                ))}
              </div>
            )}

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

/* ── Market Quick View ────────────────────────────────────────────────────── */

function MarketQuickView({ onNavigate }: { onNavigate: (path: string) => void }) {
  return (
    <GlassPanel>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <LineChart size={14} color="var(--aur-accent)" />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--aur-ink-faint)', textTransform: 'uppercase' }}>
            Market Observatory
          </span>
        </div>
        <div
          style={{
            padding: '10px 14px',
            background: 'var(--aur-bg-elevated)',
            borderRadius: 8,
            border: '1px solid var(--aur-border-soft)',
            cursor: 'pointer',
          }}
          onClick={() => onNavigate('/market')}
        >
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--aur-ink)', marginBottom: 4 }}>
            Open Full Market Workspace
          </div>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)' }}>
            Price charts, indicators, market structure, analysis panels
          </div>
        </div>
      </div>
    </GlassPanel>
  );
}

/* ── Geo Quick View ───────────────────────────────────────────────────────── */

function GeoQuickView({ onNavigate }: { onNavigate: (path: string) => void }) {
  return (
    <GlassPanel>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Globe2 size={14} color="var(--aur-accent)" />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--aur-ink-faint)', textTransform: 'uppercase' }}>
            Geo Observatory
          </span>
        </div>
        <div
          style={{
            padding: '10px 14px',
            background: 'var(--aur-bg-elevated)',
            borderRadius: 8,
            border: '1px solid var(--aur-border-soft)',
            cursor: 'pointer',
          }}
          onClick={() => onNavigate('/geo')}
        >
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--aur-ink)', marginBottom: 4 }}>
            Open Full Geo Workspace
          </div>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)' }}>
            Cesium globe, satellite scenes, asset observations, timeline
          </div>
        </div>
      </div>
    </GlassPanel>
  );
}

/* ── Main Terminal Page ───────────────────────────────────────────────────── */

export const TerminalPage: React.FC = () => {
  const { emit } = useEventBus();
  const navigate = useNavigate();
  const [question, setQuestion] = useState('');
  const [asset, setAsset] = useState('');
  const [assessment, setAssessment] = useState<UnifiedAssessment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [computeStatus, setComputeStatus] = useState<ComputeStatus | null>(null);
  const [llmProvider, setLlmProvider] = useState<string>('stub');
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('command');
  const [secondaryTab, setSecondaryTab] = useState('evidence');

  useEffect(() => {
    emit('navigation', 'Terminal opened', 'live');
    getComputeStatus().then(setComputeStatus).catch(() => {});
    reasonHealth()
      .then(h => {
        if (h?.providers?.default) setLlmProvider(h.providers.default);
      })
      .catch(() => {});
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

  const renderPrimaryWorkspace = () => {
    switch (activeTab) {
      case 'command':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Command input */}
            <GlassPanel>
              <div style={{ padding: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder="Ask AURORA anything..."
                  onKeyDown={e => {
                    if (e.key === 'Enter') handleAnalyze();
                  }}
                  style={{
                    flex: 1,
                    minWidth: 200,
                    padding: '10px 14px',
                    background: 'var(--aur-bg-elevated)',
                    border: '1px solid var(--aur-border)',
                    borderRadius: 8,
                    color: 'var(--aur-ink)',
                    fontSize: 14,
                  }}
                />
                <input
                  value={asset}
                  onChange={e => setAsset(e.target.value)}
                  placeholder="Asset (optional)"
                  style={{
                    width: 120,
                    padding: '10px 14px',
                    background: 'var(--aur-bg-elevated)',
                    border: '1px solid var(--aur-border)',
                    borderRadius: 8,
                    color: 'var(--aur-ink)',
                    fontSize: 13,
                  }}
                />
                <button
                  onClick={handleAnalyze}
                  disabled={loading || !question.trim()}
                  style={{
                    padding: '10px 20px',
                    background: 'var(--aur-accent)',
                    border: 'none',
                    borderRadius: 8,
                    color: '#fff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: loading ? 'wait' : 'pointer',
                    opacity: loading || !question.trim() ? 0.5 : 1,
                  }}
                >
                  {loading ? 'Analyzing...' : 'Analyze'}
                </button>
              </div>
            </GlassPanel>

            {error && (
              <div
                style={{
                  color: 'var(--aur-negative)',
                  fontSize: 12,
                  padding: '8px 12px',
                  background: 'rgba(248,113,113,0.1)',
                  borderRadius: 8,
                }}
              >
                {error}
              </div>
            )}

            {loading && <LoadingState label="Running unified analysis..." />}

            {!loading && !assessment && !error && (
              <EmptyState message="No analysis yet" hint="Enter a question to run AURORA unified analysis" />
            )}

            {assessment && <AssessmentCard assessment={assessment} />}
          </div>
        );

      case 'market':
        return <MarketQuickView onNavigate={navigate} />;

      case 'macro':
        return <MacroWorkspacePanel />;

      case 'research':
        return <NewsResearchPanel />;

      case 'ai':
        return (
          <Suspense fallback={<LoadingState label="Loading AI Intelligence..." />}>
            <ReasoningPanel />
          </Suspense>
        );

      case 'geo':
        return <GeoQuickView onNavigate={navigate} />;

      case 'risk':
        return <RiskPortfolioPanel />;

      default:
        return null;
    }
  };

  const renderSecondaryPanel = () => {
    switch (secondaryTab) {
      case 'evidence':
        return (
          <Suspense fallback={<LoadingState label="Loading evidence graph..." />}>
            <EvidenceGraphView refreshInterval={10000} />
          </Suspense>
        );
      case 'ai-reason':
        return (
          <Suspense fallback={<LoadingState label="Loading reasoning..." />}>
            <ReasoningPanel />
          </Suspense>
        );
      case 'macro-panel':
        return <MacroWorkspacePanel />;
      case 'news':
        return <NewsResearchPanel />;
      case 'risk-panel':
        return <RiskPortfolioPanel />;
      default:
        return null;
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* ── Top Bar ────────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 16px',
          borderBottom: '1px solid var(--aur-border-soft)',
          background: 'var(--aur-bg-base)',
          flexShrink: 0,
        }}
      >
        <TerminalCommandBar />

        {/* Compute status pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 10px',
            borderRadius: 6,
            background: computeStatus?.enabled ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${computeStatus?.enabled ? 'rgba(52,211,153,0.28)' : 'rgba(255,255,255,0.1)'}`,
            fontSize: 10,
            fontWeight: 600,
          }}
        >
          <Cpu size={10} />
          {computeStatus?.enabled ? 'GPU ON' : 'GPU OFF'}
        </div>

        {/* LLM Provider pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 10px',
            borderRadius: 6,
            background: llmProvider !== 'stub' ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${llmProvider !== 'stub' ? 'rgba(99,102,241,0.28)' : 'rgba(255,255,255,0.1)'}`,
            fontSize: 10,
            fontWeight: 600,
          }}
        >
          <BrainCircuit size={10} />
          {llmProvider.toUpperCase()}
        </div>
      </div>

      {/* ── Main Layout: Primary + Secondary ──────────────────────────── */}
      <div
        style={{
          display: 'flex',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        {/* Primary Workspace */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Workspace tabs */}
          <div
            style={{
              display: 'flex',
              gap: 2,
              padding: '8px 16px 0',
              borderBottom: '1px solid var(--aur-border-soft)',
              overflowX: 'auto',
              flexShrink: 0,
            }}
          >
            {WORKSPACE_TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 14px',
                  background: activeTab === tab.id ? 'var(--aur-glass-strong)' : 'transparent',
                  border: 'none',
                  borderBottom: activeTab === tab.id ? '2px solid var(--aur-accent)' : '2px solid transparent',
                  color: activeTab === tab.id ? 'var(--aur-ink)' : 'var(--aur-ink-dim)',
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  borderRadius: '8px 8px 0 0',
                  transition: 'background 0.15s, color 0.15s',
                }}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Primary content */}
          <div
            style={{
              flex: 1,
              overflow: 'auto',
              padding: 16,
            }}
          >
            {renderPrimaryWorkspace()}
          </div>
        </div>

        {/* Secondary Panels (right side) */}
        <div
          style={{
            width: 360,
            borderLeft: '1px solid var(--aur-border-soft)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            flexShrink: 0,
          }}
        >
          {/* Provider Status */}
          <div style={{ padding: '8px 8px 0', flexShrink: 0 }}>
            <ProviderStatusPanel compact />
          </div>

          {/* Secondary tab bar */}
          <div
            style={{
              display: 'flex',
              gap: 2,
              padding: '6px 8px 0',
              overflowX: 'auto',
              flexShrink: 0,
            }}
          >
            {SECONDARY_TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setSecondaryTab(tab.id)}
                style={{
                  padding: '5px 8px',
                  background: secondaryTab === tab.id ? 'var(--aur-glass-strong)' : 'transparent',
                  border: 'none',
                  borderBottom: secondaryTab === tab.id ? '2px solid var(--aur-accent)' : '2px solid transparent',
                  color: secondaryTab === tab.id ? 'var(--aur-ink)' : 'var(--aur-ink-dim)',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  borderRadius: '6px 6px 0 0',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Secondary content */}
          <div
            style={{
              flex: 1,
              overflow: 'auto',
              padding: 8,
            }}
          >
            {renderSecondaryPanel()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TerminalPage;
