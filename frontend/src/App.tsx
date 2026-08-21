import React, { useState, useEffect, useCallback } from 'react';
import { Timeframe, OHLCBar, IndicatorSeries, AnalysisMetrics } from './types';
import { fetchOHLCV, computeAllIndicators, getAnalysisMetrics, getDataSourceInfo } from './services/data';
import { TopBar } from './components/TopBar';
import { Watchlist } from './components/Watchlist';
import { PriceChart } from './components/PriceChart';
import { AnalysisPanel } from './components/AnalysisPanel';
import { LandingPage } from './pages/LandingPage';
import { AssetExplorer } from './pages/AssetExplorer';
import { ResearchLab } from './pages/ResearchLab';
import { AnalysisWorkspace } from './pages/AnalysisWorkspace';
import { SettingsPage } from './pages/SettingsPage';

type Page = 'landing' | 'terminal' | 'explorer' | 'research' | 'analysis' | 'settings';

function App() {
  const [page, setPage] = useState<Page>('landing');
  const [selectedAsset, setSelectedAsset] = useState('BTC-USD');
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>('1D');
  const [bars, setBars] = useState<OHLCBar[]>([]);
  const [overlays, setOverlays] = useState<IndicatorSeries[]>([]);
  const [metrics, setMetrics] = useState<AnalysisMetrics | null>(null);
  const [dataSource, setDataSource] = useState<{ isDemo: boolean; provider: string; stale: boolean }>({ isDemo: true, provider: 'loading...', stale: false });
  const [dataMode, setDataMode] = useState<'demo' | 'live'>(() => {
    return (localStorage.getItem('aurora_data_mode') as 'demo' | 'live') || 'demo';
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOHLCV(selectedAsset, selectedTimeframe, 200);
      setBars(result.bars);
      setOverlays(computeAllIndicators(result.bars));
      setMetrics(getAnalysisMetrics(result.bars));
      setDataSource({ isDemo: result.isDemo, provider: result.provider, stale: result.stale });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [selectedAsset, selectedTimeframe]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    getDataSourceInfo().then(setDataSource);
  }, []);

  const handleDataModeChange = (mode: 'demo' | 'live') => {
    setDataMode(mode);
    localStorage.setItem('aurora_data_mode', mode);
    loadData();
  };

  const handleSelectAsset = (symbol: string) => {
    setSelectedAsset(symbol);
    setPage('terminal');
  };

  const lastBar = bars[bars.length - 1];

  if (page === 'landing') {
    return (
      <div style={styles.app}>
        <LandingPage onNavigate={setPage} />
      </div>
    );
  }

  return (
    <div style={styles.app}>
      <NavBar page={page} setPage={setPage} dataMode={dataMode} />
      {page === 'terminal' && (
        <div style={styles.terminalLayout}>
          <Watchlist selectedAsset={selectedAsset} onSelect={setSelectedAsset} />
          <div style={styles.terminalMain}>
            {loading ? (
              <div style={styles.loadingState}>
                <div style={styles.spinner} />
                <span>Loading market data...</span>
              </div>
            ) : error ? (
              <div style={styles.errorState}>
                <span style={styles.errorIcon}>!</span>
                <span>{error}</span>
                <button style={styles.retryBtn} onClick={loadData}>Retry</button>
              </div>
            ) : (
              <>
                <PriceChart bars={bars} overlays={overlays} panels={[]} />
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
                  <span style={{ marginLeft: 8, color: '#8b949e' }}>
                    Source: {dataSource.provider}
                  </span>
                  <span style={
                    dataSource.isDemo ? styles.demoLabel :
                    dataSource.stale ? styles.staleLabel :
                    styles.liveLabel
                  }>
                    {dataSource.isDemo ? 'DEMO' : dataSource.stale ? 'STALE' : 'LIVE'}
                  </span>
                </div>
              </>
            )}
          </div>
          <AnalysisPanel metrics={metrics} symbol={selectedAsset} />
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
}> = ({ page, setPage, dataMode }) => {
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
  terminalMain: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  dataBar: { display: 'flex', gap: 16, padding: '6px 16px', background: '#0d1117', borderTop: '1px solid #21262d', fontSize: 12, color: '#8b949e', fontFamily: 'monospace', alignItems: 'center' },
  demoLabel: { marginLeft: 'auto', color: '#f0883e', fontWeight: 700, fontSize: 11 },
  liveLabel: { marginLeft: 'auto', color: '#26a69a', fontWeight: 700, fontSize: 11 },
  staleLabel: { marginLeft: 'auto', color: '#d29922', fontWeight: 700, fontSize: 11 },
  loadingState: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#8b949e' },
  errorState: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#f85149' },
  errorIcon: { width: 32, height: 32, borderRadius: '50%', background: 'rgba(248,81,73,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, fontWeight: 700 },
  retryBtn: { background: 'rgba(38,166,154,0.2)', border: '1px solid #26a69a', color: '#26a69a', padding: '8px 20px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  spinner: { width: 24, height: 24, border: '2px solid #21262d', borderTopColor: '#26a69a', borderRadius: '50%', animation: 'spin 1s linear infinite' },
};

export default App;
