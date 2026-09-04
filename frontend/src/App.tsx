import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { Timeframe, OHLCBar, IndicatorSeries, AnalysisMetrics } from './types';
import { fetchOHLCV, computeAllIndicators, getAnalysisMetrics, getDataSourceInfo } from './services/data';
import { MarketStreamService, type ConnectionState } from './services/stream';
import { TopBar } from './components/TopBar';
import { Watchlist } from './components/Watchlist';
import { PriceChart } from './components/PriceChart';
import { AnalysisPanel } from './components/AnalysisPanel';
import { IndicatorSelector } from './components/IndicatorSelector';
import { MarketStructurePanel } from './components/MarketStructurePanel';
import { CommandPalette } from './components/CommandPalette';
import { MarketContextPanel } from './components/MarketContextPanel';
import { ConnectionStatus } from './components/ConnectionStatus';
import { LandingPage } from './pages/LandingPage';
import { AssetExplorer } from './pages/AssetExplorer';
import { ResearchLab } from './pages/ResearchLab';
import { ResearchWorkspace } from './pages/ResearchWorkspace';
import { GeoExplorer } from './pages/GeoExplorer';
import { AnalysisWorkspace } from './pages/AnalysisWorkspace';
import { SettingsPage } from './pages/SettingsPage';
import { CommandCenter } from './pages/CommandCenter';
import { Intelligence } from './pages/Intelligence';
import { Evidence } from './pages/Evidence';
import { NeuralField } from './pages/NeuralField';
import { Reports } from './pages/Reports';
import { isIntradayTimeframe } from './lib/timeframes';
import { saveIndicatorState, loadIndicatorState } from './lib/persistence';
import { useResponsive } from './lib/useResponsive';

type Page = 'landing' | 'command' | 'market' | 'geo' | 'intelligence' | 'research' | 'evidence' | 'neuralfield' | 'reports' | 'workspace' | 'analysis' | 'settings';

const REST_FALLBACK_INTERVAL = 60_000;

function getPageFromHash(): Page {
  const hash = window.location.hash.replace('#', '');
  if (['landing', 'command', 'market', 'geo', 'intelligence', 'research', 'evidence', 'neuralfield', 'reports', 'workspace', 'analysis', 'settings'].includes(hash)) {
    return hash as Page;
  }
  return 'landing';
}

function App() {
  const initial = loadIndicatorState();
  const { isMobile } = useResponsive();
  const [page, setPage] = useState<Page>(() => getPageFromHash());
  const [selectedAsset, setSelectedAsset] = useState(initial?.selectedAsset ?? 'BTC-USD');
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>((initial?.selectedTimeframe as Timeframe) ?? '1D');
  const [bars, setBars] = useState<OHLCBar[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [overlays, setOverlays] = useState<IndicatorSeries[]>([]);
  const [metrics, setMetrics] = useState<AnalysisMetrics | null>(null);
  const [dataSource, setDataSource] = useState<{ isDemo: boolean; provider: string; stale: boolean }>({ isDemo: true, provider: 'loading...', stale: false });
  const [dataMode, setDataMode] = useState<'demo' | 'live'>(() => {
    return (localStorage.getItem('aurora_data_mode') as 'demo' | 'live') || 'live';
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendDown, setBackendDown] = useState(false);
  const [emptyData, setEmptyData] = useState(false);
  const [enabledIndicators, setEnabledIndicators] = useState<Set<string>>(
    () => new Set(initial?.enabledIndicators ?? ['sma', 'ema', 'rsi', 'macd', 'bb', 'atr'])
  );
  const [indicatorParams, setIndicatorParams] = useState<Record<string, Record<string, number>>>(initial?.indicatorParams ?? {});
  const [structureEnabled, setStructureEnabled] = useState(initial?.structureEnabled ?? false);
  const [contextEnabled, setContextEnabled] = useState(initial?.contextEnabled ?? false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('offline');
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const barsRef = useRef<OHLCBar[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MarketStreamService | null>(null);
  const connectionProviderRef = useRef<string>('');

  const navigate = useCallback((p: Page) => {
    window.location.hash = p;
    setPage(p);
  }, []);

  useEffect(() => {
    const handler = () => setPage(getPageFromHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const loadData = useCallback(async (isPoll = false) => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    if (!isPoll) {
      setLoading(true);
      setError(null);
      setBackendDown(false);
      setEmptyData(false);
    }
    try {
      const result = await fetchOHLCV(selectedAsset, selectedTimeframe, 200);
      if (controller.signal.aborted) return;
      if (result.empty) {
        setEmptyData(true);
      } else {
        barsRef.current = result.bars;
        setBars(result.bars);
        setOverlays(computeAllIndicators(result.bars, enabledIndicators, indicatorParams));
        setMetrics(getAnalysisMetrics(result.bars));
        setDataSource({ isDemo: result.isDemo, provider: result.provider, stale: result.stale });
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      const msg = e instanceof Error ? e.message : 'Failed to load data';
      if (msg === 'BACKEND UNAVAILABLE') {
        setBackendDown(true);
      } else {
        setError(msg);
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [selectedAsset, selectedTimeframe, enabledIndicators, indicatorParams]);

  useEffect(() => {
    const stream = new MarketStreamService({
      onConnectionChange: (state) => {
        setConnectionState(state);
        if (state === 'fallback') {
          loadData(true);
        }
      },
      onInitialData: (initialBars, asset, tf, provider, isDemo) => {
        if (asset !== selectedAsset || tf !== selectedTimeframe) return;
        connectionProviderRef.current = provider;
        const mappedBars = initialBars.map(b => ({ ...b, time: (b as unknown as { timestamp: string }).timestamp ?? b.time }));
        barsRef.current = mappedBars;
        setBars(mappedBars);
        setOverlays(computeAllIndicators(mappedBars, enabledIndicators, indicatorParams));
        setMetrics(getAnalysisMetrics(mappedBars));
        setDataSource({ isDemo, provider, stale: false });
        setLoading(false);
        setError(null);
        setBackendDown(false);
        setEmptyData(mappedBars.length === 0);
      },
      onUpdate: (bar, asset, tf) => {
        if (asset !== selectedAsset || tf !== selectedTimeframe) return;
        const mappedBar = { ...bar, time: (bar as unknown as { timestamp: string }).timestamp ?? bar.time };
        setBars(prev => {
          const next = [...prev];
          if (next.length > 0 && next[next.length - 1].time === mappedBar.time) {
            next[next.length - 1] = mappedBar;
          } else {
            next.push(mappedBar);
          }
          barsRef.current = next;
          setOverlays(computeAllIndicators(next, enabledIndicators, indicatorParams));
          setMetrics(getAnalysisMetrics(next));
          return next;
        });
      },
      onError: (_code, message) => {
        setError(message);
      },
    });
    streamRef.current = stream;
    return () => { stream.destroy(); };
  }, []);

  useEffect(() => {
    streamRef.current?.subscribe(selectedAsset, selectedTimeframe);
  }, [selectedAsset, selectedTimeframe]);

  useEffect(() => {
    if (fallbackRef.current) clearInterval(fallbackRef.current);
    if (connectionState === 'fallback' || connectionState === 'offline') {
      fallbackRef.current = setInterval(() => loadData(true), REST_FALLBACK_INTERVAL);
    }
    return () => { if (fallbackRef.current) clearInterval(fallbackRef.current); };
  }, [connectionState, loadData]);

  useEffect(() => {
    loadData();
    return () => { abortRef.current?.abort(); };
  }, [selectedAsset, selectedTimeframe]);

  useEffect(() => {
    if (barsRef.current.length > 0) {
      setOverlays(computeAllIndicators(barsRef.current, enabledIndicators, indicatorParams));
    }
  }, [enabledIndicators, indicatorParams]);

  useEffect(() => {
    getDataSourceInfo().then(info => {
      setDataSource({ ...info, stale: false });
      setBackendDown(info.provider === 'mock (no backend)');
    });
  }, []);

  useEffect(() => {
    saveIndicatorState({
      enabledIndicators,
      indicatorParams,
      selectedTimeframe,
      selectedAsset,
      structureEnabled,
      contextEnabled,
    });
  }, [enabledIndicators, indicatorParams, selectedTimeframe, selectedAsset, structureEnabled, contextEnabled]);

  const handleDataModeChange = (mode: 'demo' | 'live') => {
    setDataMode(mode);
    localStorage.setItem('aurora_data_mode', mode);
    loadData();
  };

  const handleSelectAsset = (symbol: string) => {
    setSelectedAsset(symbol);
    navigate('market');
  };

  const handleToggleIndicator = (id: string) => {
    setEnabledIndicators(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleParamUpdate = useCallback((indicatorId: string, paramId: string, value: number) => {
    setIndicatorParams(prev => ({
      ...prev,
      [indicatorId]: { ...(prev[indicatorId] || {}), [paramId]: value },
    }));
  }, []);

  const showTerminal = page === 'market';

  return (
    <div style={styles.root}>
      <a href="#main-content" style={styles.skipLink}>Skip to main content</a>
      <NavBar page={page} setPage={navigate} dataMode={dataMode} connectionState={connectionState} provider={dataSource.provider} isDemo={dataSource.isDemo} />

      <main id="main-content" style={styles.main} role="main">
        {page === 'landing' && <LandingPage onNavigate={(p) => navigate(p as Page)} />}
        {page === 'command' && <CommandCenter onNavigate={(p) => navigate(p as Page)} />}
        {page === 'market' && (
          <div style={styles.terminalLayout}>
            {sidebarOpen && (
              <aside style={isMobile ? styles.sidebarMobile : styles.sidebar}>
                <Watchlist onSelectAsset={handleSelectAsset} />
              </aside>
            )}
            <div style={styles.terminalMain}>
              <TopBar symbol={selectedAsset} timeframe={selectedTimeframe} onTimeframeChange={setSelectedTimeframe} dataSource={dataSource} loading={loading} error={error} backendDown={backendDown} emptyData={emptyData} />
              {isMobile && (
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  style={styles.sidebarToggle}
                  aria-label="Toggle watchlist"
                >
                  {sidebarOpen ? '✕ Hide Watchlist' : '☰ Watchlist'}
                </button>
              )}
              <div style={styles.chartArea}>
                <PriceChart bars={bars} overlays={overlays} timeframe={selectedTimeframe} loading={loading} />
              </div>
              <div style={styles.bottomPanels}>
                <div style={styles.panelColumn}>
                  <IndicatorSelector enabledIndicators={enabledIndicators} onToggle={handleToggleIndicator} indicatorParams={indicatorParams} onParamUpdate={handleParamUpdate} />
                </div>
                <div style={styles.panelColumn}>
                  <AnalysisPanel metrics={metrics} bars={bars} />
                </div>
                {structureEnabled && <div style={styles.panelColumn}><MarketStructurePanel bars={bars} /></div>}
                {contextEnabled && <div style={styles.panelColumn}><MarketContextPanel symbol={selectedAsset} bars={bars} dataSource={dataSource} /></div>}
              </div>
            </div>
          </div>
        )}
        {page === 'geo' && <GeoExplorer />}
        {page === 'intelligence' && <Intelligence symbol={selectedAsset} />}
        {page === 'research' && <ResearchLab />}
        {page === 'evidence' && <Evidence />}
        {page === 'neuralfield' && <NeuralField />}
        {page === 'reports' && <Reports />}
        {page === 'workspace' && <ResearchWorkspace />}
        {page === 'analysis' && <AnalysisWorkspace symbol={selectedAsset} bars={bars} />}
        {page === 'settings' && <SettingsPage dataMode={dataMode} onDataModeChange={handleDataModeChange} />}
      </main>
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onNavigate={(p) => navigate(p as Page)}
      />
    </div>
  );
}

const NavBar: React.FC<{
  page: Page;
  setPage: (p: Page) => void;
  dataMode: 'demo' | 'live';
  connectionState: ConnectionState;
  provider: string;
  isDemo: boolean;
}> = ({ page, setPage, dataMode, connectionState, provider, isDemo }) => {
  const { isMobile } = useResponsive();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const sections = [
    { label: 'COMMAND', items: [{ id: 'command' as Page, label: 'Command Center' }] },
    { label: 'OBSERVE', items: [
      { id: 'market' as Page, label: 'Market Observatory' },
      { id: 'geo' as Page, label: 'Geo Observatory' },
    ]},
    { label: 'ANALYZE', items: [
      { id: 'intelligence' as Page, label: 'Intelligence' },
      { id: 'research' as Page, label: 'Research' },
      { id: 'evidence' as Page, label: 'Evidence' },
    ]},
    { label: 'VISUALIZE', items: [
      { id: 'neuralfield' as Page, label: 'Neural Field' },
    ]},
    { label: 'OUTPUT', items: [
      { id: 'reports' as Page, label: 'Reports' },
    ]},
    { label: 'SYSTEM', items: [
      { id: 'settings' as Page, label: 'Settings' },
    ]},
  ];

  return (
    <nav style={styles.nav}>
      <div style={styles.navBrand}>
        <span style={styles.navLogo}>A</span>
        {!isMobile && <span style={styles.navTitle}>AURORA CORE</span>}
        <span style={dataMode === 'live' ? styles.liveModeBadge : styles.demoModeBadge}>
          {dataMode === 'live' ? 'LIVE' : 'DEMO'}
        </span>
        {!isMobile && <ConnectionStatus state={connectionState} provider={provider} isDemo={isDemo} />}
      </div>
      {!isMobile ? (
        <div style={styles.navSections}>
          {sections.map(section => (
            <div key={section.label} style={styles.navSection}>
              <div style={styles.navSectionLabel}>{section.label}</div>
              <div style={styles.navSectionItems}>
                {section.items.map(item => (
                  <button
                    key={item.id}
                    onClick={() => setPage(item.id)}
                    style={page === item.id ? styles.navLinkActive : styles.navLink}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          style={styles.hamburgerBtn}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileMenuOpen}
        >
          ☰
        </button>
      )}
      <div style={{ display: 'flex', gap: '6px', marginLeft: 'auto', alignItems: 'center' }}>
        <span style={{ padding: '3px 8px', borderRadius: '4px', background: '#21262d', border: '1px solid #30363d', fontSize: '10px', color: '#8b949e', fontFamily: 'monospace' }}>⌘K</span>
        <button onClick={() => setPage('landing')} style={styles.navHomeBtn}>Home</button>
      </div>
      {isMobile && mobileMenuOpen && (
        <div style={styles.mobileMenu}>
          {sections.map(section => (
            <div key={section.label} style={styles.mobileSection}>
              <div style={styles.mobileSectionLabel}>{section.label}</div>
              {section.items.map(item => (
                <button
                  key={item.id}
                  onClick={() => { setPage(item.id); setMobileMenuOpen(false); }}
                  style={page === item.id ? styles.mobileLinkActive : styles.mobileLink}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ))}
          <div style={{ padding: '8px 12px', borderTop: '1px solid #21262d' }}>
            <ConnectionStatus state={connectionState} provider={provider} isDemo={isDemo} />
          </div>
        </div>
      )}
    </nav>
  );
};

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#0d1117',
    color: '#e6edf3',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
  },
  skipLink: {
    position: 'absolute',
    top: '-40px',
    left: 0,
    background: '#26a69a',
    color: '#0d1117',
    padding: '8px',
    zIndex: 10000,
    textDecoration: 'none',
    fontWeight: 600,
    ':focus': {
      top: 0,
    },
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '0 16px',
    height: '48px',
    background: 'rgba(13, 17, 23, 0.95)',
    borderBottom: '1px solid #21262d',
    backdropFilter: 'blur(8px)',
    flexShrink: 0,
    zIndex: 100,
  },
  navBrand: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginRight: '16px',
  },
  navLogo: {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    background: 'linear-gradient(135deg, #26a69a, #1a7f75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: '14px',
    color: '#fff',
  },
  navTitle: {
    fontWeight: 700,
    fontSize: '13px',
    color: '#e6edf3',
    letterSpacing: '0.5px',
  },
  liveModeBadge: {
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '9px',
    fontWeight: 700,
    background: 'rgba(63, 185, 80, 0.15)',
    color: '#3fb950',
    border: '1px solid rgba(63, 185, 80, 0.3)',
  },
  demoModeBadge: {
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '9px',
    fontWeight: 700,
    background: 'rgba(227, 179, 65, 0.15)',
    color: '#e3b341',
    border: '1px solid rgba(227, 179, 65, 0.3)',
  },
  navSections: {
    display: 'flex',
    gap: '4px',
    flex: 1,
  },
  navSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
  },
  navSectionLabel: {
    fontSize: '8px',
    color: '#484f58',
    fontWeight: 700,
    letterSpacing: '0.5px',
    marginRight: '2px',
    textTransform: 'uppercase',
  },
  navSectionItems: {
    display: 'flex',
    gap: '1px',
  },
  navLink: {
    background: 'transparent',
    border: 'none',
    padding: '4px 8px',
    color: '#8b949e',
    fontSize: '11px',
    cursor: 'pointer',
    borderRadius: '4px',
    whiteSpace: 'nowrap',
  },
  navLinkActive: {
    background: 'rgba(38, 166, 154, 0.1)',
    border: 'none',
    padding: '4px 8px',
    color: '#26a69a',
    fontSize: '11px',
    cursor: 'pointer',
    borderRadius: '4px',
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  navHomeBtn: {
    background: 'transparent',
    border: '1px solid #21262d',
    padding: '4px 8px',
    color: '#8b949e',
    fontSize: '10px',
    cursor: 'pointer',
    borderRadius: '4px',
    marginLeft: 'auto',
  },
  main: {
    flex: 1,
    overflow: 'auto',
  },
  terminalLayout: {
    display: 'flex',
    height: '100%',
  },
  sidebar: {
    width: '240px',
    borderRight: '1px solid #21262d',
    overflow: 'auto',
    flexShrink: 0,
  },
  sidebarMobile: {
    position: 'fixed',
    top: '48px',
    left: 0,
    bottom: 0,
    width: '280px',
    background: '#0d1117',
    borderRight: '1px solid #21262d',
    overflow: 'auto',
    zIndex: 100,
  },
  sidebarToggle: {
    padding: '6px 12px',
    background: '#161b22',
    border: '1px solid #21262d',
    borderBottom: '1px solid #21262d',
    color: '#8b949e',
    fontSize: '12px',
    cursor: 'pointer',
    textAlign: 'left',
  },
  terminalMain: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  chartArea: {
    flex: 1,
    minHeight: 0,
  },
  bottomPanels: {
    display: 'flex',
    gap: '1px',
    borderTop: '1px solid #21262d',
    maxHeight: '200px',
    overflow: 'auto',
    flexDirection: 'row' as const,
  },
  panelColumn: {
    flex: 1,
    minWidth: '200px',
    overflow: 'auto',
    borderRight: '1px solid #21262d',
  },
  hamburgerBtn: {
    background: 'transparent',
    border: '1px solid #30363d',
    borderRadius: '4px',
    color: '#e6edf3',
    fontSize: '18px',
    padding: '4px 8px',
    cursor: 'pointer',
    marginLeft: 'auto',
  },
  mobileMenu: {
    position: 'fixed',
    top: '48px',
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(13, 17, 23, 0.98)',
    backdropFilter: 'blur(8px)',
    zIndex: 999,
    overflow: 'auto',
    padding: '16px',
  },
  mobileSection: {
    marginBottom: '16px',
  },
  mobileSectionLabel: {
    fontSize: '10px',
    fontWeight: 600,
    color: '#8b949e',
    letterSpacing: '0.5px',
    marginBottom: '6px',
    padding: '0 12px',
  },
  mobileLink: {
    display: 'block',
    width: '100%',
    padding: '10px 12px',
    background: 'transparent',
    border: 'none',
    borderRadius: '6px',
    color: '#8b949e',
    fontSize: '14px',
    cursor: 'pointer',
    textAlign: 'left',
  },
  mobileLinkActive: {
    display: 'block',
    width: '100%',
    padding: '10px 12px',
    background: 'rgba(38, 166, 154, 0.1)',
    border: 'none',
    borderRadius: '6px',
    color: '#26a69a',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    textAlign: 'left',
  },
};

export default App;
