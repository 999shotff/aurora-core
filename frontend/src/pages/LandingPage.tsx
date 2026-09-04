import React from 'react';

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#010409',
    color: '#c9d1d9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    lineHeight: 1.6,
    overflow: 'hidden',
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
  },
  nav: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
    background: 'rgba(1, 4, 9, 0.85)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #21262d',
    padding: '16px 0',
  },
  navInner: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#e6edf3',
    letterSpacing: '2px',
    textDecoration: 'none',
    textTransform: 'uppercase',
  },
  logoAccent: {
    color: '#26a69a',
  },
  navLinks: {
    display: 'flex',
    gap: '32px',
    listStyle: 'none',
    margin: 0,
    padding: 0,
  },
  navLink: {
    color: '#8b949e',
    textDecoration: 'none',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'color 0.2s',
    cursor: 'pointer',
  },
  heroSection: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
    padding: '120px 24px 80px',
    position: 'relative',
    overflow: 'hidden',
  },
  heroBackground: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'radial-gradient(ellipse at center, rgba(38, 166, 154, 0.08) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  heroContent: {
    maxWidth: '800px',
    position: 'relative',
    zIndex: 1,
  },
  heroBadge: {
    display: 'inline-block',
    padding: '6px 16px',
    borderRadius: '9999px',
    background: 'rgba(38, 166, 154, 0.1)',
    border: '1px solid rgba(38, 166, 154, 0.3)',
    color: '#26a69a',
    fontSize: '12px',
    fontWeight: '600',
    letterSpacing: '1px',
    textTransform: 'uppercase',
    marginBottom: '24px',
  },
  heroTitle: {
    fontSize: '64px',
    fontWeight: '800',
    color: '#e6edf3',
    marginBottom: '24px',
    lineHeight: '1.1',
    letterSpacing: '-1px',
  },
  heroSubtitle: {
    fontSize: '20px',
    color: '#8b949e',
    maxWidth: '600px',
    margin: '0 auto 48px',
    lineHeight: '1.6',
  },
  heroCTA: {
    display: 'inline-flex',
    gap: '16px',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  btnPrimary: {
    display: 'inline-block',
    padding: '14px 32px',
    background: 'linear-gradient(135deg, #26a69a, #2d9f93)',
    color: '#010409',
    borderRadius: '8px',
    fontWeight: '600',
    fontSize: '16px',
    textDecoration: 'none',
    border: 'none',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s',
  },
  btnSecondary: {
    display: 'inline-block',
    padding: '14px 32px',
    background: 'transparent',
    color: '#c9d1d9',
    borderRadius: '8px',
    fontWeight: '600',
    fontSize: '16px',
    textDecoration: 'none',
    border: '1px solid #21262d',
    cursor: 'pointer',
    transition: 'border-color 0.2s',
  },
  section: {
    padding: '100px 24px',
    position: 'relative',
  },
  sectionContainer: {
    maxWidth: '1200px',
    margin: '0 auto',
  },
  sectionHeader: {
    textAlign: 'center',
    marginBottom: '64px',
  },
  sectionTitle: {
    fontSize: '36px',
    fontWeight: '700',
    color: '#e6edf3',
    marginBottom: '16px',
  },
  sectionSubtitle: {
    fontSize: '18px',
    color: '#8b949e',
    maxWidth: '600px',
    margin: '0 auto',
  },
  featureGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '24px',
  },
  featureCard: {
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '12px',
    padding: '32px',
    transition: 'border-color 0.2s, transform 0.2s',
  },
  featureIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    marginBottom: '20px',
    background: 'rgba(38, 166, 154, 0.1)',
    border: '1px solid rgba(38, 166, 154, 0.2)',
  },
  featureTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#e6edf3',
    marginBottom: '12px',
  },
  featureDescription: {
    fontSize: '15px',
    color: '#8b949e',
    lineHeight: '1.6',
  },
  methodologyGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '20px',
    marginTop: '48px',
  },
  methodologyCard: {
    background: 'rgba(13, 17, 23, 0.4)',
    border: '1px solid #21262d',
    borderRadius: '12px',
    padding: '24px',
    transition: 'border-color 0.2s',
  },
  methodologyPhase: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#26a69a',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '8px',
  },
  methodologyTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#e6edf3',
    marginBottom: '8px',
  },
  methodologyDescription: {
    fontSize: '14px',
    color: '#8b949e',
    lineHeight: '1.5',
  },
  warningBanner: {
    background: 'rgba(240, 136, 62, 0.08)',
    border: '1px solid rgba(240, 136, 62, 0.3)',
    borderRadius: '12px',
    padding: '32px',
    marginTop: '48px',
  },
  warningTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#f0883e',
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  warningText: {
    fontSize: '15px',
    color: '#c9d1d9',
    lineHeight: '1.6',
  },
  warningList: {
    marginTop: '16px',
    paddingLeft: '0',
    listStyle: 'none',
  },
  warningListItem: {
    fontSize: '14px',
    color: '#8b949e',
    marginBottom: '8px',
    paddingLeft: '16px',
    position: 'relative',
  },
  warningDot: {
    position: 'absolute',
    left: 0,
    top: '6px',
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#f0883e',
  },
  statGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '32px',
    marginTop: '48px',
  },
  statCard: {
    textAlign: 'center',
    padding: '32px 24px',
    background: 'rgba(13, 17, 23, 0.4)',
    border: '1px solid #21262d',
    borderRadius: '12px',
  },
  statValue: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#26a69a',
    marginBottom: '8px',
  },
  statLabel: {
    fontSize: '14px',
    color: '#8b949e',
  },
  integritySection: {
    background: 'rgba(13, 17, 23, 0.4)',
    border: '1px solid #21262d',
    borderRadius: '16px',
    padding: '48px',
  },
  integrityGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '32px',
    marginTop: '32px',
  },
  integrityCard: {
    padding: '24px',
    border: '1px solid #21262d',
    borderRadius: '12px',
    background: 'rgba(1, 4, 9, 0.6)',
  },
  integrityTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#e6edf3',
    marginBottom: '12px',
  },
  integrityText: {
    fontSize: '14px',
    color: '#8b949e',
    lineHeight: '1.6',
  },
  deploymentSignal: {
    display: 'inline-block',
    padding: '8px 16px',
    background: 'rgba(240, 136, 62, 0.15)',
    border: '2px solid #f0883e',
    borderRadius: '8px',
    color: '#f0883e',
    fontWeight: '700',
    fontSize: '14px',
    letterSpacing: '1px',
    marginTop: '24px',
  },
  footer: {
    borderTop: '1px solid #21262d',
    padding: '48px 0',
    background: 'rgba(1, 4, 9, 0.8)',
  },
  footerGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '48px',
    marginBottom: '48px',
  },
  footerColumn: {
    // intentionally empty
  },
  footerTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#e6edf3',
    marginBottom: '16px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  footerLink: {
    display: 'block',
    color: '#8b949e',
    textDecoration: 'none',
    fontSize: '14px',
    marginBottom: '8px',
    transition: 'color 0.2s',
  },
  footerBottom: {
    borderTop: '1px solid #21262d',
    paddingTop: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '16px',
  },
  footerCopyright: {
    fontSize: '13px',
    color: '#8b949e',
  },
  footerDisclaimer: {
    fontSize: '12px',
    color: '#6e7681',
    maxWidth: '800px',
    marginTop: '24px',
    lineHeight: '1.6',
    fontStyle: 'italic',
  },
  dataGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '24px',
  },
  dataCard: {
    background: 'rgba(13, 17, 23, 0.6)',
    border: '1px solid #21262d',
    borderRadius: '12px',
    padding: '28px',
  },
  dataCardTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#e6edf3',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  dataIcon: {
    width: '40px',
    height: '40px',
    borderRadius: '8px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(38, 166, 154, 0.1)',
    border: '1px solid rgba(38, 166, 154, 0.2)',
    fontSize: '18px',
    flexShrink: 0,
  },
  dataList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  dataListItem: {
    fontSize: '14px',
    color: '#8b949e',
    padding: '8px 0',
    borderBottom: '1px solid rgba(33, 38, 45, 0.5)',
  },
  dataListItemLast: {
    fontSize: '14px',
    color: '#8b949e',
    padding: '8px 0',
  },
  badgeGreen: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    background: 'rgba(38, 166, 154, 0.15)',
    color: '#26a69a',
    fontSize: '12px',
    fontWeight: '600',
    marginLeft: '8px',
  },
  badgeOrange: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    background: 'rgba(240, 136, 62, 0.15)',
    color: '#f0883e',
    fontSize: '12px',
    fontWeight: '600',
    marginLeft: '8px',
  },
};

const LandingPage: React.FC<{ onNavigate?: (page: string) => void }> = ({ onNavigate }) => {
  return (
    <div style={styles.page}>
      <nav style={styles.nav}>
        <div style={styles.navInner}>
          <a href="#" style={styles.logo}>
            AURORA <span style={styles.logoAccent}>CORE</span>
          </a>
          <ul style={styles.navLinks}>
            <li><a href="#features" style={styles.navLink}>Features</a></li>
            <li><a href="#methodology" style={styles.navLink}>Methodology</a></li>
            <li><a href="#data" style={styles.navLink}>Data</a></li>
            <li><a href="#integrity" style={styles.navLink}>Integrity</a></li>
          </ul>
        </div>
      </nav>

      <section style={styles.heroSection}>
        <div style={styles.heroBackground} />
        <div style={styles.heroContent}>
          <div style={styles.heroBadge}>EXPERIMENTAL RESEARCH SYSTEM</div>
          <h1 style={styles.heroTitle}>
            Market Research<br />
            Infrastructure
          </h1>
          <p style={styles.heroSubtitle}>
            Open-source quantitative research framework for multi-asset market analysis.
            Transparent methodology, reproducible experiments, full data provenance.
          </p>
          <div style={styles.heroCTA}>
            <button
              onClick={() => onNavigate?.('market')}
              style={styles.btnPrimary}
            >
              OPEN TERMINAL
            </button>
            <a href="#features" style={styles.btnSecondary}>
              Explore Features
            </a>
          </div>
        </div>
      </section>

      <section id="features" style={styles.section}>
        <div style={styles.sectionContainer}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Core Capabilities</h2>
            <p style={styles.sectionSubtitle}>
              Built for systematic market research with transparency at every layer.
            </p>
          </div>
          <div style={styles.featureGrid}>
            <div style={styles.featureCard}>
              <div style={styles.featureIcon}>📊</div>
              <h3 style={styles.featureTitle}>Real-time Market Data</h3>
              <p style={styles.featureDescription}>
                Live price feeds for crypto, commodities, equity indices, ETFs, and forex.
                Powered by Yahoo Finance with automatic timezone normalization to UTC.
              </p>
            </div>
            <div style={styles.featureCard}>
              <div style={styles.featureIcon}>📈</div>
              <h3 style={styles.featureTitle}>Technical Analysis</h3>
              <p style={styles.featureDescription}>
                RSI, MACD, ATR, Bollinger Bands, and SMA indicators computed deterministically.
                Fully configurable parameters with complete provenance tracking.
              </p>
            </div>
            <div style={styles.featureCard}>
              <div style={styles.featureIcon}>🔬</div>
              <h3 style={styles.featureTitle}>Research Integrity</h3>
              <p style={styles.featureDescription}>
                Strict separation between exploration and deployment. All hypotheses start as
                UNTESTED. No in-sample performance is treated as evidence of edge.
              </p>
            </div>
            <div style={styles.featureCard}>
              <div style={styles.featureIcon}>🌐</div>
              <h3 style={styles.featureTitle}>Multi-Asset Support</h3>
              <p style={styles.featureDescription}>
                Unified interface across 10+ asset classes including BTC, ETH, Gold, Silver,
                SPY, QQQ, Nifty 50, and major forex pairs with per-asset decimal precision.
              </p>
            </div>
            <div style={styles.featureCard}>
              <div style={styles.featureIcon}>🔧</div>
              <h3 style={styles.featureTitle}>Open Architecture</h3>
              <p style={styles.featureDescription}>
                Modular plugin system with TypeScript/Python adapters. Local-first design
                with no cloud dependency for core functionality.
              </p>
            </div>
            <div style={styles.featureCard}>
              <div style={styles.featureIcon}>📦</div>
              <h3 style={styles.featureTitle}>Data Provenance</h3>
              <p style={styles.featureDescription}>
                Full audit trail from raw data ingestion to final analysis. Every feature,
                target, and computation carries a ProvenanceRecord with formula definition.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="methodology" style={{ ...styles.section, background: 'rgba(13, 17, 23, 0.3)' }}>
        <div style={styles.sectionContainer}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>M1–M15 Research Approach</h2>
            <p style={styles.sectionSubtitle}>
              A structured framework for systematic market hypothesis development and testing.
            </p>
          </div>
          <div style={styles.methodologyGrid}>
            <div style={styles.methodologyCard}>
              <div style={styles.methodologyPhase}>Phase 1</div>
              <h4 style={styles.methodologyTitle}>M1–M3: Foundation</h4>
              <p style={styles.methodologyDescription}>
                Data ingestion, normalization, and quality validation. Deterministic
                indicator computation with full reproducibility.
              </p>
            </div>
            <div style={styles.methodologyCard}>
              <div style={styles.methodologyPhase}>Phase 2</div>
              <h4 style={styles.methodologyTitle}>M4–M6: Exploration</h4>
              <p style={styles.methodologyDescription}>
                Hypothesis generation across all methodologies including technical,
                statistical, and alternative approaches.
              </p>
            </div>
            <div style={styles.methodologyCard}>
              <div style={styles.methodologyPhase}>Phase 3</div>
              <h4 style={styles.methodologyTitle}>M7–M9: Validation</h4>
              <p style={styles.methodologyDescription}>
                Walk-forward testing, out-of-sample validation, and robustness checks
                across parameter variations and market regimes.
              </p>
            </div>
            <div style={styles.methodologyCard}>
              <div style={styles.methodologyPhase}>Phase 4</div>
              <h4 style={styles.methodologyTitle}>M10–M12: Integration</h4>
              <p style={styles.methodologyDescription}>
                Champion-challenger framework with predetermined classification rules.
                Evaluation gates prevent premature promotion.
              </p>
            </div>
            <div style={styles.methodologyCard}>
              <div style={styles.methodologyPhase}>Phase 5</div>
              <h4 style={styles.methodologyTitle}>M13–M15: Production</h4>
              <p style={styles.methodologyDescription}>
                Operational deployment only after rigorous evaluation. Continuous
                monitoring with automatic degradation detection.
              </p>
            </div>
          </div>
          <div style={styles.warningBanner}>
            <h4 style={styles.warningTitle}>
              <span>⚠</span> Research Methodology Disclaimer
            </h4>
            <p style={styles.warningText}>
              All methodologies (Fibonacci, Gann, Astrology, Liquidity, etc.) enter
              the same hypothesis-testing framework with no special credibility assumptions.
              Classification is based on statistical evidence, not theoretical elegance.
            </p>
          </div>
        </div>
      </section>

      <section id="data" style={styles.section}>
        <div style={styles.sectionContainer}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Data Infrastructure</h2>
            <p style={styles.sectionSubtitle}>
              Reliable, verifiable data pipelines with complete traceability.
            </p>
          </div>
          <div style={styles.dataGrid}>
            <div style={styles.dataCard}>
              <div style={styles.dataCardTitle}>
                <span style={styles.dataIcon}>⚡</span>
                Data Sources
              </div>
              <ul style={styles.dataList}>
                <li style={styles.dataListItem}>Yahoo Finance <span style={styles.badgeGreen}>PRIMARY</span></li>
                <li style={styles.dataListItem}>Open Exchange Rates</li>
                <li style={styles.dataListItem}>CoinGecko (crypto backup)</li>
                <li style={styles.dataListItem}>Binance public API</li>
                <li style={styles.dataListItemLast}>Custom CSV/Parquet ingestion</li>
              </ul>
            </div>
            <div style={styles.dataCard}>
              <div style={styles.dataCardTitle}>
                <span style={styles.dataIcon}>🔄</span>
                Processing Pipeline
              </div>
              <ul style={styles.dataList}>
                <li style={styles.dataListItem}>UTC normalization</li>
                <li style={styles.dataListItem}>Missing data detection</li>
                <li style={styles.dataListItem}>Duplicate removal</li>
                <li style={styles.dataListItem}>OHLC integrity validation</li>
                <li style={styles.dataListItemLast}>Volume anomaly flagging</li>
              </ul>
            </div>
            <div style={styles.dataCard}>
              <div style={styles.dataCardTitle}>
                <span style={styles.dataIcon}>📋</span>
                Quality Classification
              </div>
              <ul style={styles.dataList}>
                <li style={styles.dataListItem}>GOOD: High confidence data</li>
                <li style={styles.dataListItem}>PARTIAL: Missing some fields</li>
                <li style={styles.dataListItem}>OCR_REQUIRED: Needs OCR processing</li>
                <li style={styles.dataListItemLast}>FAILED: Cannot process</li>
              </ul>
            </div>
          </div>
          <div style={styles.statGrid}>
            <div style={styles.statCard}>
              <div style={styles.statValue}>10+</div>
              <div style={styles.statLabel}>Asset Classes</div>
            </div>
            <div style={styles.statCard}>
              <div style={styles.statValue}>8</div>
              <div style={styles.statLabel}>Timeframes</div>
            </div>
            <div style={styles.statCard}>
              <div style={styles.statValue}>100%</div>
              <div style={styles.statLabel}>Deterministic</div>
            </div>
            <div style={styles.statCard}>
              <div style={styles.statValue}>UTC</div>
              <div style={styles.statLabel}>Internal Time</div>
            </div>
          </div>
        </div>
      </section>

      <section id="integrity" style={{ ...styles.section, background: 'rgba(13, 17, 23, 0.3)' }}>
        <div style={styles.sectionContainer}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>Research Integrity</h2>
            <p style={styles.sectionSubtitle}>
              Transparent standards for rigorous quantitative research.
            </p>
          </div>
          <div style={styles.integritySection}>
            <div style={styles.integrityGrid}>
              <div style={styles.integrityCard}>
                <h4 style={styles.integrityTitle}>Reproducibility</h4>
                <p style={styles.integrityText}>
                  Every experiment must have a reproducible configuration. Deterministic
                  calculations stay outside the language model. Models are interchangeable
                  candidates, not ground truth.
                </p>
              </div>
              <div style={styles.integrityCard}>
                <h4 style={styles.integrityTitle}>Temporal Validation</h4>
                <p style={styles.integrityText}>
                  Never use random train/test splitting for temporal market data. Always use
                  chronological, walk-forward, or expanding-window validation. Feature
                  timestamps must precede prediction timestamps.
                </p>
              </div>
              <div style={styles.integrityCard}>
                <h4 style={styles.integrityTitle}>Leakage Prevention</h4>
                <p style={styles.integrityText}>
                  Run leakage checks before any experiment. Future target information must
                  never enter the feature set. A leakage detection failure must fail the
                  entire experiment.
                </p>
              </div>
              <div style={styles.integrityCard}>
                <h4 style={styles.integrityTitle}>Multiple Testing</h4>
                <p style={styles.integrityText}>
                  Prepare for multiple-testing correction. Do not treat the best result
                  among hundreds as automatically significant. Report all robustness results,
                  not just the best parameter set.
                </p>
              </div>
              <div style={styles.integrityCard}>
                <h4 style={styles.integrityTitle}>Baseline Comparison</h4>
                <p style={styles.integrityText}>
                  Always compare against a buy-and-hold baseline. Predetermined classification
                  rules must be defined before running experiments. Never classify based on
                  in-sample performance alone.
                </p>
              </div>
              <div style={styles.integrityCard}>
                <h4 style={styles.integrityTitle}>LLM Experimentation</h4>
                <p style={styles.integrityText}>
                  LLM extraction is an EXPERIMENT, not a replacement for deterministic
                  systems. Output is untrusted data requiring schema validation and source
                  grounding. Every LLM claim needs an exact source-text span.
                </p>
              </div>
            </div>

            <div style={{ textAlign: 'center', marginTop: '40px' }}>
              <div style={styles.deploymentSignal}>
                NO_DEPLOYMENT_SIGNAL
              </div>
              <p style={{ ...styles.integrityText, marginTop: '16px', fontSize: '13px', color: '#6e7681' }}>
                This system is an EXPERIMENTAL research tool. No component of this software constitutes
                a trading signal, investment advice, or guarantee of performance.
              </p>
            </div>
          </div>

          <div style={styles.warningBanner}>
            <h4 style={styles.warningTitle}>
              <span>⚠</span> Critical Disclaimers
            </h4>
            <ul style={styles.warningList}>
              <li style={styles.warningListItem}>
                <span style={styles.warningDot} />
                No guarantee of profits, returns, or capital preservation
              </li>
              <li style={styles.warningListItem}>
                <span style={styles.warningDot} />
                No guarantee of prediction accuracy or market timing
              </li>
              <li style={styles.warningListItem}>
                <span style={styles.warningDot} />
                No claim of superior returns or proven trading edge
              </li>
              <li style={styles.warningListItem}>
                <span style={styles.warningDot} />
                Past backtest performance does not indicate future results
              </li>
              <li style={styles.warningListItem}>
                <span style={styles.warningDot} />
                Experimental research only; not for live trading without extensive verification
              </li>
            </ul>
          </div>
        </div>
      </section>

      <footer style={styles.footer}>
        <div style={styles.container}>
          <div style={styles.footerGrid}>
            <div style={styles.footerColumn}>
              <h5 style={styles.footerTitle}>Platform</h5>
              <a href="#features" style={styles.footerLink}>Features</a>
              <a href="#methodology" style={styles.footerLink}>Methodology</a>
              <a href="#data" style={styles.footerLink}>Data Infrastructure</a>
              <a href="#integrity" style={styles.footerLink}>Research Integrity</a>
            </div>
            <div style={styles.footerColumn}>
              <h5 style={styles.footerTitle}>Research</h5>
              <a href="#" style={styles.footerLink}>Documentation</a>
              <a href="#" style={styles.footerLink}>Experiment Registry</a>
              <a href="#" style={styles.footerLink}>Methodology Taxonomy</a>
              <a href="#" style={styles.footerLink}>Data Provenance</a>
            </div>
            <div style={styles.footerColumn}>
              <h5 style={styles.footerTitle}>Community</h5>
              <a href="#" style={styles.footerLink}>GitHub</a>
              <a href="#" style={styles.footerLink}>Discussions</a>
              <a href="#" style={styles.footerLink}>Contributing</a>
              <a href="#" style={styles.footerLink}>License</a>
            </div>
            <div style={styles.footerColumn}>
              <h5 style={styles.footerTitle}>Legal</h5>
              <a href="#" style={styles.footerLink}>Terms of Use</a>
              <a href="#" style={styles.footerLink}>Privacy Policy</a>
              <a href="#" style={styles.footerLink}>Disclaimer</a>
              <a href="#" style={styles.footerLink}>Risk Disclosure</a>
            </div>
          </div>
          <div style={styles.footerBottom}>
            <div style={styles.footerCopyright}>
              © 2026 Aurora Core. Open-source under MIT License.
            </div>
          </div>
          <p style={styles.footerDisclaimer}>
            IMPORTANT: AURORA CORE is an experimental research platform. It does not provide
            financial advice, trading signals, or guaranteed predictions. All backtest results
            are in-sample and do not guarantee future performance. Users assume full responsibility
            for any investment decisions. Past performance does not indicate future results.
          </p>
        </div>
      </footer>
    </div>
  );
};

export { LandingPage };
