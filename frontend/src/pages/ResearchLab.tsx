import React, { useState } from 'react';

type PhaseId = 'foundation' | 'classical' | 'advanced' | 'ensemble' | 'gate';

interface MilestoneResult {
  id: string;
  title: string;
  status: 'COMPLETE' | 'EXPERIMENTAL' | 'INCONCLUSIVE';
  date: string;
  tests: number;
  methodology: string;
  validation: string;
  keyFindings: string[];
  limitations: string[];
}

const MILESTONES: Record<PhaseId, MilestoneResult[]> = {
  foundation: [
    {
      id: 'M1',
      title: 'Model Interface Foundation',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 646,
      methodology: 'Typed Pydantic model interface (ModelInput/ModelOutput) with immutable data contracts, schema versioning, and leakage flag propagation.',
      validation: '58 tests covering frozen immutability, extra field rejection, probability bounds, leakage in test/train contexts, schema mismatch.',
      keyFindings: [
        'ModelInput/ModelOutput interfaces enforce temporal separation at data layer',
        'Leakage flags carried explicitly, not inferred',
        'ModelRegistry provides versioned storage with compatibility checks',
        'Abstention mechanism prevents forced predictions',
      ],
      limitations: ['No actual model implementations', 'No temporal validation integration', 'No calibration implementation'],
    },
    {
      id: 'M2',
      title: 'Statistical Baseline Adapters',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 697,
      methodology: 'MajorityClass, DeterministicRandom, BuyAndHold baselines. No hardcoded 0.50 — baselines computed from actual training labels.',
      validation: '51 tests: class frequency calculation, tie-breaking, determinism, leakage rejection, unfitted abstention, registry integration.',
      keyFindings: [
        'MajorityClass baseline is data-dependent, not hardcoded',
        'DeterministicRandom produces reproducible outputs with same seed',
        'BuyAndHold always predicts up with P=1.0',
        'All baselines abstain when unfitted',
      ],
      limitations: ['MajorityClass only predicts one class (by design)', 'No online learning', 'No calibration implemented'],
    },
    {
      id: 'M3',
      title: 'Classical ML Adapters + Benchmark Harness',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 747,
      methodology: 'Logistic Regression (SGD + L2), Decision Tree (Gini), Random Forest (bagged ensemble). Pure Python, zero new dependencies. Chronological train/val/test split.',
      validation: '50 tests: fitting, prediction, probability bounds, temporal separation, leakage protection, baseline comparison, reproducibility.',
      keyFindings: [
        'All models produce valid probabilities in [0,1] that sum to 1.0',
        'Chronological splitting verified: train ≤ val ≤ test',
        'No new dependencies — pure Python sufficient',
        'Benchmark harness produces reproducible results',
      ],
      limitations: ['Binary classification only', 'No hyperparameter tuning', 'No feature selection'],
    },
    {
      id: 'M4',
      title: 'ML Correctness, Calibration & Model-Selection',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 798,
      methodology: 'Mathematical verification of sigmoid, numerical stability, decision tree splits, probability integrity. Brier score + ECE calibration metrics. Model selection on validation only.',
      validation: '51 tests: sigmoid properties, extreme values, tree splitting, probability bounds, Brier score, calibration evaluation, temporal separation, edge cases.',
      keyFindings: [
        'Sigmoid verified numerically stable for extreme inputs',
        'All models produce finite probabilities with no NaN/Inf',
        'Model selection correctly uses validation data only',
        'Calibration evaluation does NOT imply calibrated probabilities',
      ],
      limitations: ['No automatic calibration', 'No hyperparameter tuning', 'Binary classification only'],
    },
    {
      id: 'M5',
      title: 'Feature Selection + Robustness Analysis',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 837,
      methodology: '7 production features: leakage audit, stability analysis, univariate screening, redundancy check. All features SAFE for production.',
      validation: '39 tests across 14 categories: feature inventory, temporal leakage, stability criteria, univariate evaluation, ablation.',
      keyFindings: [
        'All 7 production features pass leakage audit (SAFE)',
        'Feature stability verified across chronological periods',
        'MajorityClassAdapter is input-agnostic — accuracy_delta always 0.0',
        'No features pass selection criterion with input-agnostic baseline',
      ],
      limitations: ['MajorityClassAdapter is input-agnostic', 'Synthetic data only', 'Small sample sizes (n=100)'],
    },
  ],
  classical: [
    {
      id: 'M6',
      title: 'Temporal Real-Data Logistic Regression',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 873,
      methodology: 'Logistic regression on real yfinance data (BTC-USD, SPY, QQQ). 14 engineered features. Walk-forward with chronological split.',
      validation: '36 tests: feature coefficients, ablation, temporal robustness, statistical evaluation, reproducibility.',
      keyFindings: [
        'Real market data successfully loaded from yfinance',
        'All features SAFE — no future information leakage',
        'Logistic regression accuracy ~51-52% — marginal at best',
        'Model does NOT outperform majority class baseline',
      ],
      limitations: ['Small sample sizes', 'Single model only', 'No hyperparameter search', 'Synthetic patterns in real data'],
    },
    {
      id: 'M7',
      title: 'Real Market Validation',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 905,
      methodology: 'Walk-forward validation on BTC-USD, SPY, QQQ with LR, DT, RF. 28 features including RSI, MACD, Bollinger Bands. Transaction cost modeling.',
      validation: '32 tests: walk-forward methodology, hyperparameter search, multiple-testing correction, regime analysis.',
      keyFindings: [
        'Decision Tree on BTC-USD shows +2.1% delta (WEAK)',
        'All other models underperform baseline',
        'All hypothesis classifications: INCONCLUSIVE',
        'Transaction costs not modeled in accuracy evaluation',
      ],
      limitations: ['Only 2 years of data', 'Small sample sizes', 'No order book features', 'Simplified transaction costs'],
    },
    {
      id: 'M8',
      title: 'Real Market Data Validation',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 905,
      methodology: 'Genuine historical market data (2 years). LR, DT, RF on BTC-USD (731 rows), SPY (501), QQQ (501). Walk-forward + regime analysis.',
      validation: 'Leakage audit, data provenance, baseline calculation, feature evaluation (25 features), walk-forward.',
      keyFindings: [
        'Real market data successfully loaded: 3 instruments, 1,733 records',
        'Decision Tree on BTC-USD: 52.4% vs 50.3% baseline (+2.1%, WEAK)',
        'All other models REJECTED — below instrument-specific baselines',
        'Regime sample sizes insufficient for robust conclusions',
      ],
      limitations: ['Transaction costs simplified', 'Regime samples insufficient', 'No hyperparameter optimization', 'No ensemble methods'],
    },
  ],
  advanced: [
    {
      id: 'M9',
      title: 'Feature Engineering + Model Research',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 947,
      methodology: '39 features across 7 groups. Hyperparameter search (15 trials). Feature ablation. Walk-forward validation.',
      validation: 'Z-test, Cohen\'s h, Bonferroni/Holm/BH-FDR correction. Walk-forward with chronological split.',
      keyFindings: [
        'Best model: BTC-USD Logistic Regression 47.6% vs 50.3% baseline (-2.7%)',
        'All models below baseline — REJECTED',
        'Structure features show marginal +2.2% on BTC-USD (not significant)',
        'No statistically significant predictive edge found',
      ],
      limitations: ['Only 2 years of data', '1 walk-forward window per instrument', 'No ensemble methods', 'No order book features'],
    },
    {
      id: 'M10',
      title: 'Advanced Signal & Target Research',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 966,
      methodology: '6 target types (directional, magnitude, volatility-conditioned, event, persistence). 29 market-structure features. Cross-asset features. Feature interactions.',
      validation: 'Multi-horizon targets (h=1,2,5,10). Thresholded targets. Regime-conditional analysis. Statistical testing with correction.',
      keyFindings: [
        'No target formulation produces significant improvement',
        '29 market-structure features tested — none statistically significant',
        'Cross-asset information does not improve prediction',
        'Feature interactions do not provide incremental value',
      ],
      limitations: ['Computational constraints — full evaluation timed out', 'No regime analysis', 'Only 1 window per instrument'],
    },
    {
      id: 'M11',
      title: 'Data Expansion + Advanced Signal Architecture',
      status: 'COMPLETE',
      date: '2026-08-16',
      tests: 983,
      methodology: '5 years of data (BTC-USD 1,827 rows). 31 walk-forward windows. Market microstructure proxies (11 features). Ensemble voting/weighted.',
      validation: 'Multiple walk-forward windows (31 for BTC-USD). Additional baselines (momentum, mean-reversion). Experiment registry.',
      keyFindings: [
        'Extended data confirms no predictive signal',
        'BTC-USD mean accuracy 49.9% vs 50.5% baseline (31 windows)',
        'High variance across windows: 38% to 60%',
        'Ensembles do not outperform individual models',
      ],
      limitations: ['Microstructure features are PROXIES only', 'External data unavailable', 'No sentiment features'],
    },
    {
      id: 'M12',
      title: 'Market Prediction Architecture Research',
      status: 'COMPLETE',
      date: '2026-08-18',
      tests: 1001,
      methodology: '6 target types with configurable parameters. Market-state classification. Risk-aware metrics (Sharpe, drawdown, turnover). Abstention analysis.',
      validation: 'Walk-forward (31 windows BTC-USD, 20 SPY/QQQ). Bonferroni correction. Risk-aware evaluation.',
      keyFindings: [
        'Every directional experiment shows negative delta (model below baseline)',
        'BTC-USD h=5: +1.5% (p=0.460, NOT significant)',
        'All Sharpe ratios negative — no positive risk-adjusted returns',
        'After Bonferroni correction: 0/12 experiments significant',
      ],
      limitations: ['Microstructure features are PROXIES', 'External data unavailable', 'Only LR used in final evaluation'],
    },
    {
      id: 'M13',
      title: 'External Data + Advanced Model Research',
      status: 'COMPLETE',
      date: '2026-08-19',
      tests: 1024,
      methodology: '9 external data sources (VIX, Treasury, USD, Gold, Oil, ETH, QQQ, TLT, IWM). 26 external features. Cross-asset mapping.',
      validation: 'Walk-forward (31 windows BTC-USD, 20 SPY/QQQ). 18 experiments total. Bonferroni correction.',
      keyFindings: [
        'Adding 26 external features does NOT improve predictive performance',
        'External-only configurations show marginal positive delta (not significant)',
        'Ablation confirms external features are not contributing',
        '0/18 experiments significant after correction',
      ],
      limitations: ['No news/sentiment data', 'No on-chain data', 'No VIX term structure', 'Linear model only'],
    },
  ],
  ensemble: [
    {
      id: 'M14',
      title: 'Advanced Model + Ensemble + Feature Selection',
      status: 'EXPERIMENTAL',
      date: '2026-08-20',
      tests: 1046,
      methodology: 'Gradient Boosting (pure Python). Ensemble voting (LR+DT). Feature selection (permutation importance). Calibration analysis.',
      validation: 'Grid search on validation set. Permutation importance. Diversity analysis. Calibration evaluation.',
      keyFindings: [
        'Gradient Boosting achieves highest accuracy but never exceeds baseline',
        'All Sharpe ratios negative — no positive risk-adjusted returns',
        'Ensemble voting does not improve over individual models',
        '0/15 experiments significant after correction',
      ],
      limitations: ['Pure Python GB not optimized', 'Moderate prediction agreement (0.56-0.72)', 'Feature selection identifies same 10 features across instruments'],
    },
  ],
  gate: [
    {
      id: 'M15',
      title: 'Research Decision Gate + Prediction-Formulation Audit',
      status: 'COMPLETE',
      date: '2026-08-20',
      tests: 0,
      methodology: 'Comprehensive audit of M8.5–M14 (114+ experiments). Prediction-target audit. Baseline audit. Data sufficiency analysis. Failure-mode analysis.',
      validation: 'Architecture audit, feature information audit, temporal resolution analysis, economic-value audit, statistical power assessment.',
      keyFindings: [
        'Daily OHLCV directional prediction does NOT produce a statistically significant edge',
        '114+ experiments across 7 milestones — 0 significant after correction',
        'All Sharpe ratios negative',
        'The bottleneck is not the architecture — it is the information content of the data',
        'STOP_PREDICTIVE_RESEARCH — evidence is conclusive',
      ],
      limitations: [
        'Daily OHLCV only — no order book, sentiment, on-chain',
        'Pure Python implementations',
        '3 liquid instruments tested',
        '5 years of data may not cover all regimes',
      ],
    },
  ],
};

const PHASES: { id: PhaseId; label: string; group: string; color: string }[] = [
  { id: 'foundation', label: 'M1–M5', group: 'Foundation', color: '#58a6ff' },
  { id: 'classical', label: 'M6–M8', group: 'Classical ML', color: '#3fb950' },
  { id: 'advanced', label: 'M9–M13', group: 'Advanced Features', color: '#bc8cff' },
  { id: 'ensemble', label: 'M14', group: 'Ensemble', color: '#f0883e' },
  { id: 'gate', label: 'M15', group: 'Decision Gate', color: '#f85149' },
];

const STATUS_COLORS: Record<string, string> = {
  COMPLETE: '#3fb950',
  EXPERIMENTAL: '#f0883e',
  INCONCLUSIVE: '#e3b341',
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#010409',
    color: '#c9d1d9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    lineHeight: 1.6,
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
  },
  header: {
    position: 'sticky',
    top: 0,
    zIndex: 50,
    background: 'rgba(1, 4, 9, 0.85)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #21262d',
    padding: '16px 0',
  },
  headerInner: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#e6edf3',
    letterSpacing: '2px',
    textTransform: 'uppercase',
  },
  logoAccent: { color: '#26a69a' },
  headerTag: {
    fontSize: '13px',
    color: '#8b949e',
    padding: '4px 12px',
    border: '1px solid #21262d',
    borderRadius: '6px',
  },
  hero: {
    padding: '80px 0 60px',
    textAlign: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  heroBackground: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'radial-gradient(ellipse at center, rgba(248, 81, 73, 0.06) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  heroBadge: {
    display: 'inline-block',
    padding: '6px 16px',
    borderRadius: '9999px',
    background: 'rgba(248, 81, 73, 0.1)',
    border: '1px solid rgba(248, 81, 73, 0.3)',
    color: '#f85149',
    fontSize: '12px',
    fontWeight: 600,
    letterSpacing: '1px',
    textTransform: 'uppercase',
    marginBottom: '24px',
  },
  heroTitle: {
    fontSize: '48px',
    fontWeight: 800,
    color: '#e6edf3',
    marginBottom: '16px',
    lineHeight: '1.1',
    letterSpacing: '-1px',
  },
  heroSubtitle: {
    fontSize: '18px',
    color: '#8b949e',
    maxWidth: '700px',
    margin: '0 auto',
    lineHeight: 1.6,
  },
  noDeploymentBanner: {
    margin: '40px auto',
    maxWidth: '600px',
    padding: '24px 32px',
    background: 'rgba(248, 81, 73, 0.08)',
    border: '2px solid rgba(248, 81, 73, 0.5)',
    borderRadius: '12px',
    textAlign: 'center',
    backdropFilter: 'blur(8px)',
  },
  noDeploymentText: {
    fontSize: '24px',
    fontWeight: 800,
    color: '#f85149',
    letterSpacing: '3px',
    textTransform: 'uppercase',
    marginBottom: '8px',
  },
  noDeploymentSubtext: {
    fontSize: '13px',
    color: '#8b949e',
    lineHeight: 1.5,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '16px',
    margin: '48px 0',
  },
  statCard: {
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '12px',
    padding: '24px',
    textAlign: 'center',
  },
  statValue: {
    fontSize: '32px',
    fontWeight: 700,
    color: '#26a69a',
    marginBottom: '4px',
  },
  statLabel: {
    fontSize: '13px',
    color: '#8b949e',
  },
  separator: {
    border: 'none',
    borderTop: '1px solid #21262d',
    margin: '48px 0',
  },
  sectionTitle: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#e6edf3',
    marginBottom: '8px',
  },
  sectionSubtitle: {
    fontSize: '15px',
    color: '#8b949e',
    marginBottom: '32px',
    lineHeight: 1.5,
  },
  dataDisclaimer: {
    background: 'rgba(240, 136, 62, 0.08)',
    border: '1px solid rgba(240, 136, 62, 0.3)',
    borderRadius: '10px',
    padding: '20px 24px',
    marginBottom: '32px',
  },
  dataDisclaimerTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#f0883e',
    marginBottom: '8px',
  },
  dataDisclaimerText: {
    fontSize: '13px',
    color: '#c9d1d9',
    lineHeight: 1.5,
  },
  phaseTabContainer: {
    display: 'flex',
    gap: '8px',
    marginBottom: '32px',
    flexWrap: 'wrap',
  },
  phaseTab: {
    padding: '10px 20px',
    borderRadius: '8px',
    border: '1px solid #21262d',
    background: 'rgba(13, 17, 23, 0.5)',
    color: '#8b949e',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  phaseTabActive: {
    background: 'rgba(38, 166, 154, 0.15)',
    color: '#26a69a',
    border: '1px solid rgba(38, 166, 154, 0.4)',
  },
  phaseHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '24px',
  },
  phaseLabel: {
    fontSize: '12px',
    fontWeight: 600,
    letterSpacing: '1px',
    textTransform: 'uppercase',
    padding: '4px 10px',
    borderRadius: '6px',
  },
  phaseGroupName: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#e6edf3',
  },
  milestoneCard: {
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '14px',
    padding: '28px',
    marginBottom: '20px',
    transition: 'border-color 0.2s',
  },
  milestoneHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '12px',
  },
  milestoneId: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#26a69a',
    letterSpacing: '1px',
    marginBottom: '4px',
  },
  milestoneTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#e6edf3',
    marginBottom: '8px',
  },
  milestoneMeta: {
    display: 'flex',
    gap: '16px',
    flexWrap: 'wrap',
    fontSize: '13px',
    color: '#8b949e',
  },
  milestoneMetaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  statusBadge: {
    display: 'inline-block',
    padding: '4px 10px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.5px',
    textTransform: 'uppercase',
  },
  sectionLabel: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '8px',
    marginTop: '20px',
  },
  sectionContent: {
    fontSize: '14px',
    color: '#c9d1d9',
    lineHeight: 1.6,
  },
  findingsList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  findingItem: {
    fontSize: '14px',
    color: '#c9d1d9',
    lineHeight: 1.5,
    marginBottom: '8px',
    paddingLeft: '20px',
    position: 'relative',
  },
  findingDot: {
    position: 'absolute',
    left: 0,
    top: '7px',
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#3fb950',
  },
  limitationDot: {
    position: 'absolute',
    left: 0,
    top: '7px',
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#f0883e',
  },
  conclusionSection: {
    background: 'rgba(13, 17, 23, 0.4)',
    border: '1px solid #21262d',
    borderRadius: '16px',
    padding: '40px',
    marginTop: '48px',
    marginBottom: '64px',
  },
  conclusionTitle: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#e6edf3',
    marginBottom: '16px',
  },
  conclusionText: {
    fontSize: '15px',
    color: '#c9d1d9',
    lineHeight: 1.7,
    marginBottom: '16px',
  },
  conclusionHighlight: {
    background: 'rgba(248, 81, 73, 0.1)',
    border: '1px solid rgba(248, 81, 73, 0.3)',
    borderRadius: '10px',
    padding: '20px 24px',
    margin: '24px 0',
  },
  conclusionHighlightText: {
    fontSize: '14px',
    color: '#c9d1d9',
    lineHeight: 1.6,
  },
  conclusionHighlightStrong: {
    color: '#f85149',
    fontWeight: 700,
  },
  futureGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '16px',
    marginTop: '24px',
  },
  futureCard: {
    background: 'rgba(1, 4, 9, 0.6)',
    border: '1px solid #21262d',
    borderRadius: '10px',
    padding: '20px',
  },
  futureTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#e6edf3',
    marginBottom: '8px',
  },
  futureText: {
    fontSize: '13px',
    color: '#8b949e',
    lineHeight: 1.5,
  },
  footer: {
    borderTop: '1px solid #21262d',
    padding: '32px 0',
    textAlign: 'center',
  },
  footerText: {
    fontSize: '12px',
    color: '#6e7681',
    lineHeight: 1.5,
  },
  tableContainer: {
    overflowX: 'auto',
    marginTop: '16px',
    marginBottom: '16px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    padding: '10px 12px',
    borderBottom: '1px solid #21262d',
    color: '#8b949e',
    fontWeight: 600,
    fontSize: '12px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  td: {
    padding: '8px 12px',
    borderBottom: '1px solid rgba(33, 38, 45, 0.5)',
    color: '#c9d1d9',
  },
  tdRejected: { color: '#f85149' },
  tdInconclusive: { color: '#e3b341' },
  tdWeak: { color: '#f0883e' },
};

function getStatusColor(status: string): string {
  return STATUS_COLORS[status] ?? '#8b949e';
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statValue}>{value}</div>
      <div style={styles.statLabel}>{label}</div>
    </div>
  );
}

function MilestoneCard({ milestone }: { milestone: MilestoneResult }) {
  const [expanded, setExpanded] = useState(false);
  const statusColor = getStatusColor(milestone.status);

  return (
    <div
      style={styles.milestoneCard}
      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#30363d'; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#21262d'; }}
    >
      <div style={styles.milestoneHeader}>
        <div>
          <div style={styles.milestoneId}>{milestone.id}</div>
          <div style={styles.milestoneTitle}>{milestone.title}</div>
          <div style={styles.milestoneMeta}>
            <span style={styles.milestoneMetaItem}>{milestone.date}</span>
            {milestone.tests > 0 && (
              <span style={styles.milestoneMetaItem}>{milestone.tests} tests</span>
            )}
          </div>
        </div>
        <span
          style={{
            ...styles.statusBadge,
            background: `${statusColor}18`,
            color: statusColor,
            border: `1px solid ${statusColor}40`,
          }}
        >
          {milestone.status}
        </span>
      </div>

      <div style={styles.sectionLabel}>Methodology</div>
      <div style={styles.sectionContent}>{milestone.methodology}</div>

      <div style={styles.sectionLabel}>Validation</div>
      <div style={styles.sectionContent}>{milestone.validation}</div>

      <div
        style={{ cursor: 'pointer', color: '#26a69a', fontSize: '13px', fontWeight: 600, marginTop: '16px' }}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? '▾ Hide details' : '▸ Show key findings & limitations'}
      </div>

      {expanded && (
        <>
          <div style={styles.sectionLabel}>Key Findings</div>
          <ul style={styles.findingsList}>
            {milestone.keyFindings.map((f, i) => (
              <li key={i} style={styles.findingItem}>
                <span style={styles.findingDot} />
                {f}
              </li>
            ))}
          </ul>

          <div style={styles.sectionLabel}>Limitations</div>
          <ul style={styles.findingsList}>
            {milestone.limitations.map((l, i) => (
              <li key={i} style={styles.findingItem}>
                <span style={styles.limitationDot} />
                {l}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

const ResearchLab: React.FC = () => {
  const [activePhase, setActivePhase] = useState<PhaseId | 'all'>('all');

  const totalExperiments = 114;
  const significantResults = 0;
  const bestAccuracyDelta = '+2.1%';
  const bestSharpe = 'Negative (all)';

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <span style={styles.logo}>
            AURORA <span style={styles.logoAccent}>CORE</span>
          </span>
          <span style={styles.headerTag}>Research Lab</span>
        </div>
      </header>

      <main style={styles.container}>
        <section style={styles.hero}>
          <div style={styles.heroBackground} />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={styles.heroBadge}>HISTORICAL RESEARCH RESULTS</div>
            <h1 style={styles.heroTitle}>M1–M15 Research Archive</h1>
            <p style={styles.heroSubtitle}>
              Complete record of 114+ experiments across 7 milestones. All results are
              historical — no live market data is displayed or generated on this page.
            </p>
          </div>
        </section>

        <div style={styles.noDeploymentBanner}>
          <div style={styles.noDeploymentText}>NO_DEPLOYMENT_SIGNAL</div>
          <div style={styles.noDeploymentSubtext}>
            No model provides actionable predictive signal. Daily OHLCV directional
            prediction does not produce a statistically significant edge.
          </div>
        </div>

        <div style={styles.statsGrid}>
          <StatCard value="114+" label="Total Experiments" />
          <StatCard value="0" label="Significant Results" />
          <StatCard value={bestAccuracyDelta} label="Best Accuracy Delta" />
          <StatCard value={bestSharpe} label="Best Sharpe Ratio" />
          <StatCard value="1,046" label="Total Tests Passed" />
          <StatCard value="0/114" label="Sig. After Correction" />
        </div>

        <hr style={styles.separator} />

        <div style={styles.dataDisclaimer}>
          <div style={styles.dataDisclaimerTitle}>Historical Research Only — No Live Market Data</div>
          <div style={styles.dataDisclaimerText}>
            This page displays historical research results from completed experiments
            (M1–M15). No live market data is fetched, generated, or displayed. All
            numbers, accuracies, and metrics are from archived experiment reports stored
            in <code>docs/</code>. The data source for historical experiments was
            yfinance (BTC-USD, SPY, QQQ — 5 years daily OHLCV).
          </div>
        </div>

        <h2 style={styles.sectionTitle}>Research Phases</h2>
        <p style={styles.sectionSubtitle}>
          Filter by phase to explore the research timeline. Each milestone shows its
          methodology, validation approach, key findings, and limitations.
        </p>

        <div style={styles.phaseTabContainer}>
          <button
            style={{
              ...styles.phaseTab,
              ...(activePhase === 'all' ? styles.phaseTabActive : {}),
            }}
            onClick={() => setActivePhase('all')}
          >
            All Phases
          </button>
          {PHASES.map((p) => (
            <button
              key={p.id}
              style={{
                ...styles.phaseTab,
                ...(activePhase === p.id ? styles.phaseTabActive : {}),
              }}
              onClick={() => setActivePhase(p.id)}
            >
              <span style={{ color: p.color, marginRight: '6px' }}>●</span>
              {p.label} {p.group}
            </button>
          ))}
        </div>

        {(activePhase === 'all' ? PHASES : PHASES.filter((p) => p.id === activePhase)).map((phase) => (
          <div key={phase.id} style={{ marginBottom: '48px' }}>
            <div style={styles.phaseHeader}>
              <span
                style={{
                  ...styles.phaseLabel,
                  background: `${phase.color}18`,
                  color: phase.color,
                  border: `1px solid ${phase.color}40`,
                }}
              >
                {phase.label}
              </span>
              <span style={styles.phaseGroupName}>{phase.group}</span>
            </div>

            {MILESTONES[phase.id].map((m) => (
              <MilestoneCard key={m.id} milestone={m} />
            ))}
          </div>
        ))}

        <hr style={styles.separator} />

        <div style={styles.conclusionSection}>
          <h2 style={styles.conclusionTitle}>Final Conclusion — M15 Decision Gate</h2>

          <p style={styles.conclusionText}>
            After 114+ experiments across 7 milestones, 4 model families, 105 features,
            6 target types, 3 instruments, and 5 years of daily data, the research
            program reached a definitive conclusion.
          </p>

          <div style={styles.conclusionHighlight}>
            <div style={{ ...styles.noDeploymentText, marginBottom: '12px' }}>
              NO_DEPLOYMENT_SIGNAL
            </div>
            <p style={styles.conclusionHighlightText}>
              <span style={styles.conclusionHighlightStrong}>
                Daily OHLCV directional prediction of liquid assets does not produce a
                statistically significant edge with current methodology.
              </span>
              {' '}Zero experiments survive multiple-testing correction. All Sharpe ratios
              are negative. The framework produces reliable negative results — this is
              scientific value.
            </p>
          </div>

          <p style={styles.conclusionText}>
            <strong>M15 Decision: STOP_PREDICTIVE_RESEARCH.</strong> The evidence is not
            ambiguous. Continuing predictive research without fundamentally new data
            sources or a specific, testable hypothesis would be unfounded.
          </p>

          <p style={styles.conclusionText}>
            The bottleneck is not the architecture — it is the information content of the
            data. All 105 features are derived from OHLCV. No independent information
            sources are available. The efficient market hypothesis holds strongest at
            daily frequency for liquid instruments.
          </p>

          <div style={{ ...styles.sectionLabel, marginTop: '32px' }}>
            Production Readiness Assessment
          </div>
          <div style={styles.tableContainer}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Requirement</th>
                  <th style={styles.th}>Status</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Validated predictive model', 'NOT MET'],
                  ['Statistically supported edge', 'NOT MET'],
                  ['Robust walk-forward performance', 'NOT MET'],
                  ['Transaction-cost viability', 'NOT MET'],
                  ['Risk viability (positive Sharpe)', 'NOT MET'],
                  ['Stable performance', 'NOT MET'],
                  ['Reproducible model', 'MET'],
                  ['Complete provenance', 'MET'],
                  ['Sufficient negative evidence', 'MET'],
                ].map(([req, status], i) => (
                  <tr key={i}>
                    <td style={styles.td}>{req}</td>
                    <td style={{ ...styles.td, color: status === 'MET' ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                      {status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={styles.sectionLabel}>Historical Result Summary (M8.5–M14)</div>
          <div style={styles.tableContainer}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Milestone</th>
                  <th style={styles.th}>Experiments</th>
                  <th style={styles.th}>Best Delta</th>
                  <th style={styles.th}>Best p-value</th>
                  <th style={styles.th}>Sig. After</th>
                  <th style={styles.th}>Status</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['M8.5', '24', '+0.22 Sharpe', 'N/A', '0', 'NO_DEPLOYMENT'],
                  ['M9', '9', '+2.1% DT/BTC', 'N/A', '0', 'NO_DEPLOYMENT'],
                  ['M10', '9', '-2.7% LR/BTC', '0.097', '0', 'NO_DEPLOYMENT'],
                  ['M11', '10', '0.0% LR/SPY', '~0.4', '0', 'NO_DEPLOYMENT'],
                  ['M12', '5+31w', '-0.6% mean', '~0.13', '0', 'NO_DEPLOYMENT'],
                  ['M13', '24', '+1.5% BTC h=5', '0.460', '0', 'NO_DEPLOYMENT'],
                  ['M14', '18', '+1.9% QQQ GB', '0.394', '0', 'NO_DEPLOYMENT'],
                  ['M15', '—', '—', '—', '—', 'DECISION_GATE'],
                  ['TOTAL', '114+', '—', '—', '0', 'NO_DEPLOYMENT'],
                ].map(([ms, exp, delta, pv, sig, status], i) => (
                  <tr key={i} style={i === 8 ? { background: 'rgba(38, 166, 154, 0.05)' } : {}}>
                    <td style={{ ...styles.td, fontWeight: i === 8 ? 700 : 400 }}>{ms}</td>
                    <td style={styles.td}>{exp}</td>
                    <td style={styles.td}>{delta}</td>
                    <td style={styles.td}>{pv}</td>
                    <td style={styles.td}>{sig}</td>
                    <td style={{ ...styles.td, color: status === 'DECISION_GATE' ? '#f85149' : '#8b949e', fontWeight: 600 }}>
                      {status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={styles.sectionLabel}>If Research Resumes</div>
          <div style={styles.futureGrid}>
            <div style={styles.futureCard}>
              <div style={styles.futureTitle}>Volatility Forecasting</div>
              <div style={styles.futureText}>
                Same OHLCV data, different target. Volatility is more predictable
                than direction. High justification, low complexity.
              </div>
            </div>
            <div style={styles.futureCard}>
              <div style={styles.futureTitle}>Alternative Data Sources</div>
              <div style={styles.futureText}>
                News sentiment, on-chain metrics, order book data. Independent
                information sources that are not derived from price.
              </div>
            </div>
            <div style={styles.futureCard}>
              <div style={styles.futureTitle}>Research Product Architecture</div>
              <div style={styles.futureText}>
                Analytics platform (charts, diagnostics, experiment tracking)
                rather than trading signals. Moderate justification.
              </div>
            </div>
          </div>
        </div>

        <footer style={styles.footer}>
          <div style={styles.footerText}>
            AURORA CORE Research Lab — Historical results from completed experiments.
            <br />
            No live market data. No trading signals. No deployment.
            <br />
            © 2026 Aurora Core. Experimental research system.
          </div>
        </footer>
      </main>
    </div>
  );
};

export { ResearchLab };
