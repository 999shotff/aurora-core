import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../services/data';

interface SettingsPageProps {
  dataMode: 'demo' | 'live';
  onDataModeChange: (mode: 'demo' | 'live') => void;
}

interface Settings {
  chartTheme: 'dark' | 'light';
  defaultTimeframe: string;
  indicators: {
    sma: boolean;
    ema: boolean;
    rsi: boolean;
    macd: boolean;
    bollinger: boolean;
    atr: boolean;
  };
  fontSize: 'small' | 'medium' | 'large';
  chartStyle: 'candlestick' | 'line' | 'area';
}

interface ProviderStatus {
  name: string;
  healthy: boolean;
  lastUpdate: string;
}

const DEFAULT_SETTINGS: Settings = {
  chartTheme: 'dark',
  defaultTimeframe: '1D',
  indicators: {
    sma: true,
    ema: true,
    rsi: true,
    macd: true,
    bollinger: true,
    atr: false,
  },
  fontSize: 'medium',
  chartStyle: 'candlestick',
};

const TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1D', '1W', '1M'];
const FONT_SIZES = ['small', 'medium', 'large'] as const;
const CHART_STYLES = ['candlestick', 'line', 'area'] as const;

const STORAGE_KEY = 'aurora_settings';

const VERSION = '0.2.0';
const BUILD_DATE = '2026-08-22';
const EXPLORATION_PHASE = 'M24-Market-Structure';

const PROVIDERS: ProviderStatus[] = [
  { name: 'Yahoo Finance', healthy: true, lastUpdate: '2026-08-22T00:00:00Z' },
  { name: 'CoinGecko', healthy: true, lastUpdate: '2026-08-22T00:00:00Z' },
  { name: 'Open Exchange Rates', healthy: false, lastUpdate: '2026-08-20T08:12:00Z' },
  { name: 'Binance Public API', healthy: true, lastUpdate: '2026-08-22T00:00:00Z' },
];

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      indicators: {
        ...DEFAULT_SETTINGS.indicators,
        ...parsed.indicators,
      },
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function saveSettings(settings: Settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // localStorage unavailable
  }
}

const FONT_SIZE_MAP: Record<string, string> = {
  small: '12px',
  medium: '14px',
  large: '16px',
};

const FONT_SIZE_LABELS: Record<string, string> = {
  small: 'Compact',
  medium: 'Default',
  large: 'Large',
};

const TIMEFRAME_LABELS: Record<string, string> = {
  '1m': '1 Minute',
  '5m': '5 Minutes',
  '15m': '15 Minutes',
  '1h': '1 Hour',
  '4h': '4 Hours',
  '1D': 'Daily',
  '1W': 'Weekly',
  '1M': 'Monthly',
};

const INDICATOR_LABELS: Record<string, string> = {
  sma: 'SMA (20)',
  ema: 'EMA (12)',
  rsi: 'RSI (14)',
  macd: 'MACD (12, 26, 9)',
  bollinger: 'Bollinger (20, 2)',
  atr: 'ATR (14)',
};

const INDICATOR_DESCRIPTIONS: Record<string, string> = {
  sma: 'Simple Moving Average — 20-period',
  ema: 'Exponential Moving Average — 12-period',
  rsi: 'Relative Strength Index — 14-period',
  macd: 'MACD Line, Signal, Histogram',
  bollinger: 'Bollinger Bands — 20-period, 2 std dev',
  atr: 'Average True Range — 14-period volatility',
};

function timeSince(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  } catch {
    return 'unknown';
  }
}

const SettingsPage: React.FC<SettingsPageProps> = ({ dataMode, onDataModeChange }) => {
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  const updateSetting = useCallback(<K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value };
      saveSettings(next);
      return next;
    });
  }, []);

  const toggleIndicator = useCallback((key: keyof Settings['indicators']) => {
    setSettings(prev => {
      const next = {
        ...prev,
        indicators: {
          ...prev.indicators,
          [key]: !prev.indicators[key],
        },
      };
      saveSettings(next);
      return next;
    });
  }, []);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
        setBackendHealthy(res.ok);
      } catch {
        setBackendHealthy(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const enabledCount = Object.values(settings.indicators).filter(Boolean).length;

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <h1 style={styles.logo}>
            AURORA <span style={styles.logoAccent}>CORE</span>
          </h1>
          <span style={styles.headerTag}>Settings</span>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.grid}>

          {/* Data Mode Selector */}
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>Data Mode</h2>
            <p style={styles.sectionDescription}>Switch between simulated demo data and live market feeds.</p>
            <div style={styles.modeSelector}>
              <button
                onClick={() => onDataModeChange('demo')}
                style={{
                  ...styles.modeBtn,
                  ...(dataMode === 'demo' ? styles.modeBtnActive : {}),
                }}
              >
                <span style={styles.modeBtnIcon}>◉</span>
                <div style={styles.modeBtnContent}>
                  <span style={styles.modeBtnLabel}>DEMO</span>
                  <span style={styles.modeBtnSub}>Simulated data</span>
                </div>
                {dataMode === 'demo' && <span style={styles.modeIndicator} />}
              </button>
              <button
                onClick={() => onDataModeChange('live')}
                style={{
                  ...styles.modeBtn,
                  ...(dataMode === 'live' ? styles.modeBtnActiveLive : {}),
                }}
              >
                <span style={{ ...styles.modeBtnIcon, color: dataMode === 'live' ? '#3fb950' : '#6e7681' }}>●</span>
                <div style={styles.modeBtnContent}>
                  <span style={styles.modeBtnLabel}>LIVE</span>
                  <span style={styles.modeBtnSub}>Real-time feeds</span>
                </div>
                {dataMode === 'live' && <span style={{ ...styles.modeIndicator, background: '#3fb950' }} />}
              </button>
            </div>
            <div style={{
              ...styles.modeStatus,
              background: dataMode === 'live' ? 'rgba(63, 185, 80, 0.1)' : 'rgba(139, 148, 158, 0.08)',
              borderColor: dataMode === 'live' ? 'rgba(63, 185, 80, 0.3)' : 'rgba(139, 148, 158, 0.2)',
            }}>
              <span style={{
                ...styles.modeStatusDot,
                background: dataMode === 'live' ? '#3fb950' : '#8b949e',
              }} />
              <span style={styles.modeStatusText}>
                {dataMode === 'live'
                  ? 'Live market data — connecting to upstream providers'
                  : 'Demo mode — using simulated market data'}
              </span>
            </div>
          </section>

          {/* Chart Settings */}
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>Chart Settings</h2>
            <p style={styles.sectionDescription}>Configure chart appearance and default timeframe.</p>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Theme</label>
              <div style={styles.toggleRow}>
                <button
                  onClick={() => updateSetting('chartTheme', 'dark')}
                  style={{
                    ...styles.toggleBtn,
                    ...(settings.chartTheme === 'dark' ? styles.toggleBtnActive : {}),
                  }}
                >
                  <span style={styles.toggleIcon}>🌙</span> Dark
                </button>
                <button
                  onClick={() => updateSetting('chartTheme', 'light')}
                  style={{
                    ...styles.toggleBtn,
                    ...(settings.chartTheme === 'light' ? styles.toggleBtnActiveLight : {}),
                  }}
                >
                  <span style={styles.toggleIcon}>☀️</span> Light
                </button>
              </div>
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Default Timeframe</label>
              <div style={styles.timeframeGrid}>
                {TIMEFRAMES.map(tf => (
                  <button
                    key={tf}
                    onClick={() => updateSetting('defaultTimeframe', tf)}
                    style={{
                      ...styles.timeframeBtn,
                      ...(settings.defaultTimeframe === tf ? styles.timeframeBtnActive : {}),
                    }}
                  >
                    <span style={styles.timeframeValue}>{tf}</span>
                    <span style={styles.timeframeLabel}>{TIMEFRAME_LABELS[tf]}</span>
                  </button>
                ))}
              </div>
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Chart Style</label>
              <div style={styles.toggleRow}>
                {CHART_STYLES.map(cs => (
                  <button
                    key={cs}
                    onClick={() => updateSetting('chartStyle', cs)}
                    style={{
                      ...styles.toggleBtn,
                      ...(settings.chartStyle === cs ? styles.toggleBtnActive : {}),
                      textTransform: 'capitalize',
                    }}
                  >
                    {cs}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Indicator Settings */}
          <section style={styles.section}>
            <div style={styles.sectionHeaderRow}>
              <div>
                <h2 style={styles.sectionTitle}>Indicators</h2>
                <p style={styles.sectionDescription}>Toggle visibility on the chart.</p>
              </div>
              <span style={styles.indicatorCount}>{enabledCount} active</span>
            </div>

            <div style={styles.indicatorList}>
              {(Object.keys(settings.indicators) as Array<keyof Settings['indicators']>).map(key => {
                const enabled = settings.indicators[key];
                return (
                  <div
                    key={key}
                    style={styles.indicatorRow}
                    onClick={() => toggleIndicator(key)}
                  >
                    <div style={styles.indicatorInfo}>
                      <span style={styles.indicatorName}>{INDICATOR_LABELS[key]}</span>
                      <span style={styles.indicatorDesc}>{INDICATOR_DESCRIPTIONS[key]}</span>
                    </div>
                    <div
                      style={{
                        ...styles.toggleSwitch,
                        background: enabled ? '#26a69a' : '#21262d',
                      }}
                    >
                      <div
                        style={{
                          ...styles.toggleKnob,
                          transform: enabled ? 'translateX(20px)' : 'translateX(0)',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Appearance Settings */}
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>Appearance</h2>
            <p style={styles.sectionDescription}>Adjust display preferences.</p>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Font Size</label>
              <div style={styles.toggleRow}>
                {FONT_SIZES.map(fs => (
                  <button
                    key={fs}
                    onClick={() => updateSetting('fontSize', fs)}
                    style={{
                      ...styles.toggleBtn,
                      ...(settings.fontSize === fs ? styles.toggleBtnActive : {}),
                    }}
                  >
                    <span style={{ fontSize: FONT_SIZE_MAP[fs] }}>Aa</span>
                    <span>{FONT_SIZE_LABELS[fs]}</span>
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Connection Status */}
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>Connection Status</h2>
            <p style={styles.sectionDescription}>Backend health and provider connectivity.</p>

            <div style={{
              ...styles.healthPanel,
              borderColor: backendHealthy === true
                ? 'rgba(63, 185, 80, 0.3)'
                : backendHealthy === false
                  ? 'rgba(248, 81, 73, 0.3)'
                  : '#21262d',
            }}>
              <div style={styles.healthRow}>
                <div style={styles.healthLeft}>
                  <span style={{
                    ...styles.healthDot,
                    background: backendHealthy === true ? '#3fb950' : backendHealthy === false ? '#f85149' : '#e3b341',
                  }} />
                  <span style={styles.healthLabel}>Backend API</span>
                </div>
                <span style={{
                  ...styles.healthStatus,
                  color: backendHealthy === true ? '#3fb950' : backendHealthy === false ? '#f85149' : '#e3b341',
                }}>
                  {backendHealthy === true ? 'Healthy' : backendHealthy === false ? 'Unreachable' : 'Checking...'}
                </span>
              </div>
              <div style={styles.healthRow}>
                <div style={styles.healthLeft}>
                  <span style={{ ...styles.healthDot, background: '#6e7681' }} />
                  <span style={styles.healthLabel}>Endpoint</span>
                </div>
                <span style={{ ...styles.healthStatus, color: '#8b949e', fontFamily: 'monospace', fontSize: '12px' }}>
                  {API_BASE.replace('https://', '')}
                </span>
              </div>
            </div>

            <h3 style={styles.providerTitle}>Data Providers</h3>
            <div style={styles.providerList}>
              {PROVIDERS.map(p => (
                <div key={p.name} style={styles.providerRow}>
                  <div style={styles.providerLeft}>
                    <span style={{
                      ...styles.providerDot,
                      background: p.healthy ? '#3fb950' : '#f85149',
                    }} />
                    <div style={styles.providerInfo}>
                      <span style={styles.providerName}>{p.name}</span>
                      <span style={styles.providerMeta}>Last update: {timeSince(p.lastUpdate)}</span>
                    </div>
                  </div>
                  <span style={{
                    ...styles.providerBadge,
                    background: p.healthy ? 'rgba(63, 185, 80, 0.12)' : 'rgba(248, 81, 73, 0.12)',
                    color: p.healthy ? '#3fb950' : '#f85149',
                    borderColor: p.healthy ? 'rgba(63, 185, 80, 0.3)' : 'rgba(248, 81, 73, 0.3)',
                  }}>
                    {p.healthy ? 'Healthy' : 'Stale'}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* About */}
          <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
            <h2 style={styles.sectionTitle}>About Aurora Core</h2>
            <div style={styles.aboutGrid}>
              <div style={styles.aboutCard}>
                <div style={styles.aboutRow}>
                  <span style={styles.aboutLabel}>Version</span>
                  <span style={styles.aboutValue}>{VERSION}</span>
                </div>
                <div style={styles.aboutRow}>
                  <span style={styles.aboutLabel}>Build</span>
                  <span style={styles.aboutValue}>{BUILD_DATE}</span>
                </div>
                <div style={styles.aboutRow}>
                  <span style={styles.aboutLabel}>Phase</span>
                  <span style={styles.aboutValue}>{EXPLORATION_PHASE}</span>
                </div>
                <div style={styles.aboutRow}>
                  <span style={styles.aboutLabel}>License</span>
                  <span style={styles.aboutValue}>MIT</span>
                </div>
              </div>

              <div style={styles.aboutCard}>
                <p style={styles.aboutDescription}>
                  Aurora Core is an open-source quantitative research framework for
                  multi-asset market analysis. Built for systematic hypothesis development,
                  validation, and transparent reporting.
                </p>
                <p style={styles.aboutDescription}>
                  This system is an <strong style={{ color: '#e3b341' }}>EXPERIMENTAL</strong> research
                  tool. It does not provide financial advice, trading signals, or guaranteed
                  predictions. All backtest results are in-sample and do not guarantee future
                  performance.
                </p>
              </div>
            </div>

            <div style={styles.deploymentBanner}>
              <div style={styles.deploymentText}>NO_DEPLOYMENT_SIGNAL</div>
              <p style={styles.deploymentSubtext}>
                No component of this software constitutes a trading signal, investment advice,
                or guarantee of performance. Users assume full responsibility for any
                investment decisions.
              </p>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#010409',
    color: '#c9d1d9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
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
    padding: '0 32px',
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
  },
  logo: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#e6edf3',
    letterSpacing: '2px',
    margin: 0,
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
  main: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '32px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '24px',
  },
  section: {
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '14px',
    padding: '28px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#e6edf3',
    margin: '0 0 4px 0',
  },
  sectionDescription: {
    fontSize: '13px',
    color: '#8b949e',
    margin: '0 0 24px 0',
    lineHeight: '1.5',
  },
  sectionHeaderRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '4px',
  },
  indicatorCount: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#26a69a',
    padding: '4px 10px',
    background: 'rgba(38, 166, 154, 0.12)',
    border: '1px solid rgba(38, 166, 154, 0.3)',
    borderRadius: '6px',
  },

  // Data Mode
  modeSelector: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '16px',
  },
  modeBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px',
    background: 'rgba(1, 4, 9, 0.5)',
    border: '1px solid #21262d',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    position: 'relative',
    overflow: 'hidden',
    color: '#8b949e',
  },
  modeBtnActive: {
    background: 'rgba(139, 148, 158, 0.08)',
    border: '1px solid rgba(139, 148, 158, 0.3)',
    color: '#e6edf3',
  },
  modeBtnActiveLive: {
    background: 'rgba(63, 185, 80, 0.08)',
    border: '1px solid rgba(63, 185, 80, 0.3)',
    color: '#e6edf3',
  },
  modeBtnIcon: {
    fontSize: '20px',
    color: '#8b949e',
    flexShrink: 0,
  },
  modeBtnContent: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '2px',
  },
  modeBtnLabel: {
    fontSize: '15px',
    fontWeight: 700,
    letterSpacing: '1px',
  },
  modeBtnSub: {
    fontSize: '11px',
    color: '#6e7681',
  },
  modeIndicator: {
    position: 'absolute',
    top: '8px',
    right: '8px',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#8b949e',
  },
  modeStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid',
  },
  modeStatusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  modeStatusText: {
    fontSize: '12px',
    color: '#c9d1d9',
  },

  // Fields
  fieldGroup: {
    marginBottom: '20px',
  },
  fieldLabel: {
    display: 'block',
    fontSize: '12px',
    fontWeight: 600,
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '10px',
  },
  toggleRow: {
    display: 'flex',
    gap: '8px',
  },
  toggleBtn: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '10px 14px',
    background: 'rgba(1, 4, 9, 0.5)',
    border: '1px solid #21262d',
    borderRadius: '8px',
    color: '#8b949e',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  toggleBtnActive: {
    background: 'rgba(38, 166, 154, 0.12)',
    border: '1px solid rgba(38, 166, 154, 0.4)',
    color: '#26a69a',
  },
  toggleBtnActiveLight: {
    background: 'rgba(227, 179, 65, 0.12)',
    border: '1px solid rgba(227, 179, 65, 0.4)',
    color: '#e3b341',
  },
  toggleIcon: {
    fontSize: '14px',
  },

  // Timeframes
  timeframeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '8px',
  },
  timeframeBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '2px',
    padding: '10px 6px',
    background: 'rgba(1, 4, 9, 0.5)',
    border: '1px solid #21262d',
    borderRadius: '8px',
    color: '#8b949e',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  timeframeBtnActive: {
    background: 'rgba(38, 166, 154, 0.12)',
    border: '1px solid rgba(38, 166, 154, 0.4)',
    color: '#26a69a',
  },
  timeframeValue: {
    fontSize: '14px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  timeframeLabel: {
    fontSize: '10px',
    color: '#6e7681',
  },

  // Indicators
  indicatorList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  indicatorRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 14px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  indicatorInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  indicatorName: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e6edf3',
    fontFamily: 'monospace',
  },
  indicatorDesc: {
    fontSize: '11px',
    color: '#6e7681',
  },
  toggleSwitch: {
    width: '42px',
    height: '22px',
    borderRadius: '11px',
    padding: '2px',
    transition: 'background 0.2s',
    flexShrink: 0,
  },
  toggleKnob: {
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    background: '#e6edf3',
    transition: 'transform 0.2s',
  },

  // Connection Status
  healthPanel: {
    background: 'rgba(1, 4, 9, 0.5)',
    border: '1px solid',
    borderRadius: '10px',
    padding: '16px',
    marginBottom: '20px',
  },
  healthRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
  },
  healthLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  healthDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  healthLabel: {
    fontSize: '13px',
    color: '#c9d1d9',
  },
  healthStatus: {
    fontSize: '13px',
    fontWeight: 600,
  },

  providerTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    margin: '0 0 12px 0',
  },
  providerList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  providerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 14px',
    borderRadius: '8px',
    background: 'rgba(1, 4, 9, 0.3)',
  },
  providerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  providerDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  providerInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1px',
  },
  providerName: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e6edf3',
  },
  providerMeta: {
    fontSize: '11px',
    color: '#6e7681',
  },
  providerBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '3px 10px',
    borderRadius: '6px',
    border: '1px solid',
  },

  // About
  aboutGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
    marginTop: '20px',
  },
  aboutCard: {
    background: 'rgba(1, 4, 9, 0.5)',
    border: '1px solid #21262d',
    borderRadius: '10px',
    padding: '20px',
  },
  aboutRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0',
    borderBottom: '1px solid rgba(33, 38, 45, 0.5)',
  },
  aboutLabel: {
    fontSize: '13px',
    color: '#8b949e',
  },
  aboutValue: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e6edf3',
    fontFamily: 'monospace',
  },
  aboutDescription: {
    fontSize: '13px',
    color: '#8b949e',
    lineHeight: '1.6',
    margin: '0 0 12px 0',
  },

  deploymentBanner: {
    marginTop: '24px',
    padding: '24px 32px',
    background: 'rgba(248, 81, 73, 0.06)',
    border: '2px solid rgba(248, 81, 73, 0.4)',
    borderRadius: '12px',
    textAlign: 'center',
  },
  deploymentText: {
    fontSize: '20px',
    fontWeight: 800,
    color: '#f85149',
    letterSpacing: '3px',
    textTransform: 'uppercase',
    marginBottom: '8px',
  },
  deploymentSubtext: {
    fontSize: '12px',
    color: '#8b949e',
    lineHeight: '1.5',
    margin: 0,
  },
};

export { SettingsPage };
