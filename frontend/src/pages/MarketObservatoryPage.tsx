import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { Timeframe, OHLCBar, IndicatorSeries, AnalysisMetrics } from '../types';
import { fetchOHLCV, computeAllIndicators, getAnalysisMetrics, getDataSourceInfo, INDICATOR_GROUPS } from '../services/data';
import { MarketStreamService, type ConnectionState } from '../services/stream';
import { TopBar } from '../components/TopBar';
import { Watchlist } from '../components/Watchlist';
import { PriceChart } from '../components/PriceChart';
import { AnalysisPanel } from '../components/AnalysisPanel';
import { IndicatorSelector } from '../components/IndicatorSelector';
import { MarketStructurePanel } from '../components/MarketStructurePanel';
import { MarketContextPanel } from '../components/MarketContextPanel';
import { isIntradayTimeframe } from '../lib/timeframes';
import { saveIndicatorState, loadIndicatorState } from '../lib/persistence';
import { useEventBus } from '../lib/eventBus';
import { useDataMode } from '../lib/dataMode';

const REST_FALLBACK_INTERVAL = 60_000;

type BottomTab = 'indicators' | 'analysis' | 'structure' | 'context';

export const MarketObservatoryPage: React.FC = () => {
  const { emit } = useEventBus();
  const { dataMode } = useDataMode();
  const initial = loadIndicatorState();
  const [selectedAsset, setSelectedAsset] = useState(initial?.selectedAsset ?? 'BTC-USD');
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>((initial?.selectedTimeframe as Timeframe) ?? '1D');
  const [bars, setBars] = useState<OHLCBar[]>([]);
  const [overlays, setOverlays] = useState<IndicatorSeries[]>([]);
  const [metrics, setMetrics] = useState<AnalysisMetrics | null>(null);
  const [dataSource, setDataSource] = useState<{ isDemo: boolean; provider: string; stale: boolean }>({ isDemo: true, provider: 'loading...', stale: false });
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
  const [activeBottomTab, setActiveBottomTab] = useState<BottomTab>('analysis');
  const [watchlistOpen, setWatchlistOpen] = useState(true);
  const barsRef = useRef<OHLCBar[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MarketStreamService | null>(null);
  const connectionProviderRef = useRef<string>('');
  const lastConnRef = useRef<ConnectionState | null>(null);

  const loadData = useCallback(async (isPoll = false) => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    if (!isPoll) { setLoading(true); setError(null); setBackendDown(false); setEmptyData(false); }
    try {
      const result = await fetchOHLCV(selectedAsset, selectedTimeframe, 200);
      if (controller.signal.aborted) return;
      if (result.empty) {
        setEmptyData(true);
        setMetrics(getAnalysisMetrics([]));
      } else {
        barsRef.current = result.bars;
        setBars(result.bars);
        setOverlays(computeAllIndicators(result.bars, enabledIndicators, indicatorParams));
        setMetrics(getAnalysisMetrics(result.bars));
        setDataSource({ isDemo: result.isDemo, provider: result.provider, stale: result.stale });
        emit('data_fetch', `${selectedAsset} · ${selectedTimeframe} loaded`, result.isDemo ? 'demo' : 'live', `${result.bars.length} bars via ${result.provider}`);
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      const msg = e instanceof Error ? e.message : 'Failed to load data';
      if (msg === 'BACKEND UNAVAILABLE') { setBackendDown(true); emit('data_fetch', 'Market backend unavailable', 'unavailable'); }
      else setError(msg);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [selectedAsset, selectedTimeframe, enabledIndicators, indicatorParams]);

  useEffect(() => {
    const stream = new MarketStreamService({
      onConnectionChange: (state) => {
        setConnectionState(state);
        if (lastConnRef.current !== state) {
          emit('connection', `Market stream ${state}`, state === 'live' ? 'live' : state === 'fallback' ? 'derived' : 'unavailable');
          lastConnRef.current = state;
        }
        if (state === 'fallback') loadData(true);
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
        setLoading(false); setError(null); setBackendDown(false);
        setEmptyData(mappedBars.length === 0);
      },
      onUpdate: (bar, asset, tf) => {
        if (asset !== selectedAsset || tf !== selectedTimeframe) return;
        const mappedBar = { ...bar, time: (bar as unknown as { timestamp: string }).timestamp ?? bar.time };
        setBars(prev => {
          const next = [...prev];
          if (next.length > 0 && next[next.length - 1].time === mappedBar.time) next[next.length - 1] = mappedBar;
          else next.push(mappedBar);
          barsRef.current = next;
          setOverlays(computeAllIndicators(next, enabledIndicators, indicatorParams));
          setMetrics(getAnalysisMetrics(next));
          return next;
        });
      },
      onError: (_code, message) => setError(message),
    });
    streamRef.current = stream;
    return () => { stream.destroy(); };
  }, []);

  useEffect(() => { streamRef.current?.subscribe(selectedAsset, selectedTimeframe); }, [selectedAsset, selectedTimeframe]);

  useEffect(() => {
    if (fallbackRef.current) clearInterval(fallbackRef.current);
    if (connectionState === 'fallback' || connectionState === 'offline') {
      fallbackRef.current = setInterval(() => loadData(true), REST_FALLBACK_INTERVAL);
    }
    return () => { if (fallbackRef.current) clearInterval(fallbackRef.current); };
  }, [connectionState, loadData]);

  useEffect(() => { loadData(); return () => { abortRef.current?.abort(); }; }, [selectedAsset, selectedTimeframe]); // eslint-disable-line react-hooks/exhaustive-deps

  const dataModeMounted = useRef(false);
  useEffect(() => {
    if (!dataModeMounted.current) { dataModeMounted.current = true; return; }
    emit('connection', `Data mode preference set to ${dataMode}`, 'live');
    loadData();
  }, [dataMode]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (barsRef.current.length > 0) setOverlays(computeAllIndicators(barsRef.current, enabledIndicators, indicatorParams));
  }, [enabledIndicators, indicatorParams]);

  useEffect(() => {
    getDataSourceInfo().then(info => {
      setDataSource({ ...info, stale: false });
      setBackendDown(info.provider === 'mock (no backend)');
    });
  }, []);

  useEffect(() => {
    saveIndicatorState({ enabledIndicators, indicatorParams, selectedTimeframe, selectedAsset, structureEnabled, contextEnabled });
  }, [enabledIndicators, indicatorParams, selectedTimeframe, selectedAsset, structureEnabled, contextEnabled]);

  const handleToggleIndicator = (id: string) => {
    setEnabledIndicators(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      emit('indicator_toggle', `${id.toUpperCase()} ${next.has(id) ? 'enabled' : 'disabled'}`, 'live');
      return next;
    });
  };
  const handleParamUpdate = useCallback((indicatorId: string, paramId: string, value: number) => {
    setIndicatorParams(prev => ({ ...prev, [indicatorId]: { ...(prev[indicatorId] ?? {}), [paramId]: value } }));
  }, []);
  const handleParamReset = useCallback((indicatorId: string) => {
    setIndicatorParams(prev => { const next = { ...prev }; delete next[indicatorId]; return next; });
  }, []);

  const lastBar = bars[bars.length - 1];
  const isIntraday = isIntradayTimeframe(selectedTimeframe);
  const oscillatorIds = useMemo(() => new Set(INDICATOR_GROUPS.filter(g => !g.overlay).flatMap(g => g.subSeries)), []);
  const oscillatorSeries = useMemo(() => overlays.filter(s => oscillatorIds.has(s.name)), [overlays, oscillatorIds]);

  const hasData = bars.length > 0 && !loading && !backendDown && !error && !emptyData;

  return (
    <div className="aur-market-wrap">
      <div className="market-layout">
        <TopBar
          selectedAsset={selectedAsset}
          selectedTimeframe={selectedTimeframe}
          onAssetChange={setSelectedAsset}
          onTimeframeChange={setSelectedTimeframe}
          isDemo={dataSource.isDemo}
          stale={dataSource.stale}
          provider={dataSource.provider}
        />

        <div className="market-body">
          {watchlistOpen && (
            <div className="market-watchlist-pane">
              <Watchlist selectedAsset={selectedAsset} onSelect={setSelectedAsset} />
            </div>
          )}

          <div className="market-main">
            <div className="market-chart-area">
              {loading ? (
                <div className="market-state-overlay">
                  <div className="market-spinner" />
                  <span>Loading market data</span>
                </div>
              ) : backendDown ? (
                <div className="market-state-overlay market-state-error">
                  <div className="market-state-icon">&#9888;</div>
                  <span className="market-state-title">MARKET DATA UNAVAILABLE</span>
                  <span className="market-state-detail">The market data service is not responding.</span>
                  <button className="market-retry-btn" onClick={() => loadData()}>Retry</button>
                </div>
              ) : error ? (
                <div className="market-state-overlay market-state-error">
                  <div className="market-state-icon">&#9888;</div>
                  <span className="market-state-title">ERROR</span>
                  <span className="market-state-detail">{error}</span>
                  <button className="market-retry-btn" onClick={() => loadData()}>Retry</button>
                </div>
              ) : emptyData ? (
                <div className="market-state-overlay">
                  <div className="market-state-icon">&#9744;</div>
                  <span className="market-state-title">NO DATA AVAILABLE</span>
                  <span className="market-state-detail">The backend returned no valid bars for this asset/timeframe.</span>
                  <button className="market-retry-btn" onClick={() => loadData()}>Retry</button>
                </div>
              ) : (
                <PriceChart
                  bars={bars}
                  overlays={overlays.filter(s => !oscillatorIds.has(s.name))}
                  panels={oscillatorSeries}
                  structureEnabled={structureEnabled}
                  isIntraday={isIntraday}
                />
              )}
            </div>

            {hasData && (
              <div className="market-ohlc-bar">
                <div className="market-ohlc-values">
                  {lastBar && (
                    <>
                      <span className="ohlc-label">O</span><span className="ohlc-value">{lastBar.open.toFixed(2)}</span>
                      <span className="ohlc-label">H</span><span className="ohlc-value">{lastBar.high.toFixed(2)}</span>
                      <span className="ohlc-label">L</span><span className="ohlc-value">{lastBar.low.toFixed(2)}</span>
                      <span className="ohlc-label">C</span><span className="ohlc-value">{lastBar.close.toFixed(2)}</span>
                      <span className="ohlc-label">Vol</span><span className="ohlc-value">{lastBar.volume.toLocaleString()}</span>
                    </>
                  )}
                </div>
                <div className="market-ohlc-controls">
                  <button
                    className={`market-toggle-btn ${structureEnabled ? 'market-toggle-on' : ''}`}
                    onClick={() => { setStructureEnabled(p => !p); emit('structure_analysis', `Structure overlay ${!structureEnabled ? 'enabled' : 'disabled'}`, 'live'); }}
                  >
                    STRUCTURE {structureEnabled ? 'ON' : 'OFF'}
                  </button>
                  <button
                    className={`market-toggle-btn market-toggle-accent2 ${contextEnabled ? 'market-toggle-on-accent2' : ''}`}
                    onClick={() => setContextEnabled(p => !p)}
                  >
                    CONTEXT {contextEnabled ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>
            )}

            {hasData && (
              <div className="market-bottom-tabs">
                <div className="market-tab-bar">
                  <button
                    className={`market-tab ${activeBottomTab === 'indicators' ? 'market-tab-active' : ''}`}
                    onClick={() => setActiveBottomTab('indicators')}
                  >INDICATORS</button>
                  <button
                    className={`market-tab ${activeBottomTab === 'analysis' ? 'market-tab-active' : ''}`}
                    onClick={() => setActiveBottomTab('analysis')}
                  >ANALYSIS</button>
                  <button
                    className={`market-tab ${activeBottomTab === 'structure' ? 'market-tab-active' : ''}`}
                    onClick={() => setActiveBottomTab('structure')}
                  >STRUCTURE</button>
                  <button
                    className={`market-tab ${activeBottomTab === 'context' ? 'market-tab-active' : ''}`}
                    onClick={() => setActiveBottomTab('context')}
                  >CONTEXT</button>
                  <div className="market-tab-spacer" />
                  <button
                    className={`market-tab market-tab-toggle ${watchlistOpen ? 'market-tab-active' : ''}`}
                    onClick={() => setWatchlistOpen(p => !p)}
                    title="Toggle watchlist"
                  >WATCHLIST</button>
                </div>
                <div className="market-tab-content">
                  {activeBottomTab === 'indicators' && (
                    <IndicatorSelector
                      enabled={enabledIndicators}
                      onToggle={handleToggleIndicator}
                      indicatorParams={indicatorParams}
                      onParamUpdate={handleParamUpdate}
                      onParamReset={handleParamReset}
                      compact
                    />
                  )}
                  {activeBottomTab === 'analysis' && (
                    <AnalysisPanel
                      metrics={metrics}
                      symbol={selectedAsset}
                      isDemo={dataSource.isDemo}
                      stale={dataSource.stale}
                      provider={dataSource.provider}
                      activeOverlays={overlays}
                    />
                  )}
                  {activeBottomTab === 'structure' && (
                    <MarketStructurePanel bars={bars} enabled={structureEnabled} />
                  )}
                  {activeBottomTab === 'context' && (
                    <MarketContextPanel
                      asset={selectedAsset}
                      timeframe={selectedTimeframe}
                      bars={bars}
                      visible={true}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
