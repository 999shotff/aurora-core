import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { Timeframe, OHLCBar, IndicatorSeries, AnalysisMetrics } from './types';
import { fetchOHLCV, computeAllIndicators, getAnalysisMetrics, getDataSourceInfo, INDICATOR_GROUPS } from './services/data';
import { MarketStreamService, type ConnectionState } from './services/stream';
import { TopBar } from './components/TopBar';
import { Watchlist } from './components/Watchlist';
import { PriceChart } from './components/PriceChart';
import { AnalysisPanel } from './components/AnalysisPanel';
import { IndicatorSelector } from './components/IndicatorSelector';
import { MarketStructurePanel } from './components/MarketStructurePanel';
import { MarketContextPanel } from './components/MarketContextPanel';
import { ConnectionStatus } from './components/ConnectionStatus';
import { LandingPage } from './pages/LandingPage';
import { AssetExplorer } from './pages/AssetExplorer';
import { ResearchLab } from './pages/ResearchLab';
import { AnalysisWorkspace } from './pages/AnalysisWorkspace';
import { SettingsPage } from './pages/SettingsPage';
import { isIntradayTimeframe } from './lib/timeframes';
import { saveIndicatorState, loadIndicatorState } from './lib/persistence';

type Page = 'landing' | 'terminal' | 'explorer' | 'research' | 'analysis' | 'settings';

const REST_FALLBACK_INTERVAL = 60_000;

function App() {
  const initial = loadIndicatorState();
  const [page, setPage] = useState<Page>('landing');
  const [selectedAsset, setSelectedAsset] = useState(initial?.selectedAsset ?? 'BTC-USD');
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>((initial?.selectedTimeframe as Timeframe) ?? '1D');
  const [bars, setBars] = useState<OHLCBar[]>([]);
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
  const barsRef = useRef<OHLCBar[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MarketStreamService | null>(null);
  const connectionProviderRef = useRef<string>('');

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
    setPage('terminal');
  };

  const handleToggleIndicator = (id: string) => {
    setEnabledIndicators(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleParamUpdate = useCallback((indicatorId: string, paramId: string, value: number) => {
    setIndicatorParams(prev => ({
      ...prev,
      [indicatorId]: { ...(prev[indicatorId] ?? {}), [paramId]: value },
    }));
  }, []);

  const handleParamReset = useCallback((indicatorId: string) => {
    setIndicatorParams(prev => {
      const next = { ...prev };
      delete next[indicatorId];
      return next;
    });
  }, []);

  const lastBar = bars[bars.length - 1];
  const isIntraday = isIntradayTimeframe(selectedTimeframe);
  const oscillatorIds = new Set(
    INDICATOR_GROUPS.filter(g => !g.overlay).flatMap(g => g.subSeries)
  );
  const oscillatorSeries = overlays.filter(s => oscillatorIds.has(s.name));

  if (page === 'landing') {
    return (
      <div style={styles.app}>
        <LandingPage onNavigate={setPage as (page: string) => void} />
      </div>
    );
  }

  return (
    <div style={styles.app}>
      <NavBar page={page} setPage={setPage} dataMode={dataMode} connectionState={connectionState} provider={connectionProviderRef.current} isDemo={dataSource.isDemo} />
      {page === 'terminal' && (
        <div style={styles.terminalLayout} className="terminal-layout">
          <div style={styles.watchlistPanel} className="watchlist-panel">
            <Watchlist selectedAsset={selectedAsset} onSelect={setSelectedAsset} />
          </div>
          <div style={styles.terminalMain}>
            <TopBar
              selectedAsset={selectedAsset}
              selectedTimeframe={selectedTimeframe}
              onAssetChange={setSelectedAsset}
              onTimeframeChange={setSelectedTimeframe}
              isDemo={dataSource.isDemo}
              stale={dataSource.stale}
              provider={dataSource.provider}
            />
            {loading ? (
              <div style={styles.loadingState}>
                <div style={styles.spinner} />
                <span>Loading market data...</span>
              </div>
            ) : backendDown ? (
              <div style={styles.backendDownState}>
                <span style={styles.backendDownIcon}>⚠</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#f85149' }}>BACKEND UNAVAILABLE</span>
                <span style={{ fontSize: 13, color: '#8b949e' }}>The market data service is not responding.</span>
                <span style={{ fontSize: 12, color: '#8b949e' }}>Please check the backend or try again later.</span>
                <button style={styles.retryBtn} onClick={() => loadData()}>Retry</button>
              </div>
            ) : error ? (
              <div style={styles.errorState}>
                <span style={styles.errorIcon}>!</span>
                <span>{error}</span>
                <button style={styles.retryBtn} onClick={() => loadData()}>Retry</button>
              </div>
            ) : emptyData ? (
              <div style={styles.backendDownState}>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#f0883e' }}>NO DATA AVAILABLE</span>
                <span style={{ fontSize: 13, color: '#8b949e' }}>The backend returned no valid bars for this asset/timeframe.</span>
                <button style={styles.retryBtn} onClick={() => loadData()}>Retry</button>
              </div>
            ) : (
              <>
                <div style={styles.chartArea}>
                  <PriceChart bars={bars} overlays={overlays.filter(s => !oscillatorIds.has(s.name))} panels={oscillatorSeries} structureEnabled={structureEnabled} isIntraday={isIntraday} />
                </div>
                <div style={styles.dataBar}>
                  {lastBar && (
                    <>
                      <span>O: {lastBar.open.toFixed(2)}</span>
                      <span>H: {lastBar.high.toFixed(2)}</span>
                      <span>L: {lastBar.low.toFixed(2)}</span>
                      <span>C: {lastBar.close.toFixed(2)}</span>
                      <span>Vol: {lastBar.volume.toLocaleString()}</span>
                    </>
                  )}
                  <span style={{ marginLeft: 'auto', color: '#8b949e', fontSize: 10 }}>
                    Research: NO_DEPLOYMENT_SIGNAL
                  </span>
                  <button
                    onClick={() => setStructureEnabled(p => !p)}
                    style={{
                      background: structureEnabled ? 'rgba(38,166,154,0.2)' : 'none',
                      border: '1px solid #21262d',
                      color: structureEnabled ? '#26a69a' : '#8b949e',
                      padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
                      fontSize: 10, fontWeight: 600,
                    }}
                  >
                    STRUCTURE {structureEnabled ? 'ON' : 'OFF'}
                  </button>
                  <button
                    onClick={() => setContextEnabled(p => !p)}
                    style={{
                      background: contextEnabled ? 'rgba(33,150,243,0.2)' : 'none',
                      border: '1px solid #21262d',
                      color: contextEnabled ? '#2196F3' : '#8b949e',
                      padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
                      fontSize: 10, fontWeight: 600,
                    }}
                  >
                    CONTEXT {contextEnabled ? 'ON' : 'OFF'}
                  </button>
                </div>
              </>
            )}
          </div>
          <div style={styles.analysisPanel} className="analysis-panel">
            <AnalysisPanel
              metrics={metrics}
              symbol={selectedAsset}
              isDemo={dataSource.isDemo}
              stale={dataSource.stale}
              provider={dataSource.provider}
              activeOverlays={overlays}
            />
          </div>
          <IndicatorSelector enabled={enabledIndicators} onToggle={handleToggleIndicator} indicatorParams={indicatorParams} onParamUpdate={handleParamUpdate} onParamReset={handleParamReset} />
          <MarketStructurePanel bars={bars} enabled={structureEnabled} />
          <MarketContextPanel asset={selectedAsset} timeframe={selectedTimeframe} bars={bars} visible={contextEnabled} />
        </div>
      )}
      {page === 'explorer' && (
        <AssetExplorer onSelectAsset={handleSelectAsset} />
      )}
      {page === 'research' && (
        <ResearchLab />
      )}
      {page === 'analysis' && (
        <AnalysisWorkspace symbol={selectedAsset} bars={bars} />
      )}
      {page === 'settings' && (
        <SettingsPage dataMode={dataMode} onDataModeChange={handleDataModeChange} />
      )}
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
  const links: { id: Page; label: string }[] = [
    { id: 'landing', label: 'Home' },
    { id: 'terminal', label: 'Terminal' },
    { id: 'explorer', label: 'Explorer' },
    { id: 'research', label: 'Research' },
    { id: 'analysis', label: 'Analysis' },
    { id: 'settings', label: 'Settings' },
  ];
  return (
    <nav style={styles.nav}>
      <div style={styles.navBrand}>
        <span style={styles.navLogo}>A</span>
        <span style={styles.navTitle}>AURORA CORE</span>
        <span style={dataMode === 'live' ? styles.liveModeBadge : styles.demoModeBadge}>
          {dataMode === 'live' ? 'LIVE' : 'DEMO'}
        </span>
        <ConnectionStatus state={connectionState} provider={provider} isDemo={isDemo} />
      </div>
      <div style={styles.navLinks}>
        {links.map(l => (
          <button
            key={l.id}
            onClick={() => setPage(l.id)}
            style={page === l.id ? styles.navLinkActive : styles.navLink}
          >
            {l.label}
          </button>
        ))}
      </div>
    </nav>
  );
};

const styles: Record<string, React.CSSProperties> = {
  app: { display: 'flex', flexDirection: 'column', height: '100vh', background: '#010409', color: '#f0f6fc', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif', overflow: 'hidden' },
  nav: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', height: 48, background: 'rgba(13,17,23,0.8)', backdropFilter: 'blur(12px)', borderBottom: '1px solid #21262d', flexShrink: 0 },
  navBrand: { display: 'flex', alignItems: 'center', gap: 10 },
  navLogo: { width: 28, height: 28, borderRadius: 6, background: 'linear-gradient(135deg, #26a69a, #2196F3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 900, color: '#fff' },
  navTitle: { fontSize: 14, fontWeight: 700, letterSpacing: 0.5 },
  navLinks: { display: 'flex', gap: 4 },
  navLink: { background: 'none', border: 'none', color: '#8b949e', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 500, transition: 'all 0.15s' },
  navLinkActive: { background: 'rgba(38,166,154,0.15)', border: 'none', color: '#26a69a', padding: '6px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  liveModeBadge: { fontSize: 9, background: '#26a69a', color: '#000', padding: '2px 8px', borderRadius: 4, fontWeight: 800, letterSpacing: 0.5 },
  demoModeBadge: { fontSize: 9, background: '#f0883e', color: '#000', padding: '2px 8px', borderRadius: 4, fontWeight: 800, letterSpacing: 0.5 },
  terminalLayout: { display: 'flex', flex: 1, overflow: 'hidden' },
  watchlistPanel: { display: 'flex', flexShrink: 0 },
  terminalMain: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 },
  analysisPanel: { display: 'flex', flexShrink: 0 },
  chartArea: { flex: 1, overflow: 'hidden', minHeight: 0 },
  dataBar: { display: 'flex', gap: 16, padding: '6px 16px', background: '#0d1117', borderTop: '1px solid #21262d', fontSize: 12, color: '#8b949e', fontFamily: 'monospace', alignItems: 'center', flexShrink: 0 },
  loadingState: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#8b949e' },
  errorState: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#f85149' },
  backendDownState: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#f85149' },
  backendDownIcon: { width: 48, height: 48, borderRadius: '50%', background: 'rgba(248,81,73,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 },
  errorIcon: { width: 32, height: 32, borderRadius: '50%', background: 'rgba(248,81,73,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, fontWeight: 700 },
  retryBtn: { background: 'rgba(38,166,154,0.2)', border: '1px solid #26a69a', color: '#26a69a', padding: '8px 20px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  spinner: { width: 24, height: 24, border: '2px solid #21262d', borderTopColor: '#26a69a', borderRadius: '50%', animation: 'spin 1s linear infinite' },
};

export default App;
