import React, { useState, useEffect, useCallback, useRef } from 'react';
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Re-fetch when the user's live/demo preference (Settings) changes. Note this
  // is a soft preference — fetchOHLCV auto-detects real backend availability
  // rather than being hard-switched by this flag; see engineering report.
  const dataModeMounted = useRef(false);
  useEffect(() => {
    if (!dataModeMounted.current) { dataModeMounted.current = true; return; }
    emit('connection', `Data mode preference set to ${dataMode}`, 'live');
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataMode]);

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
  const oscillatorIds = new Set(INDICATOR_GROUPS.filter(g => !g.overlay).flatMap(g => g.subSeries));
  const oscillatorSeries = overlays.filter(s => oscillatorIds.has(s.name));

  return (
    <div className="aur-market-wrap" style={{ display: 'flex', overflow: 'hidden' }}>
      <div style={{ display: 'flex', flexShrink: 0 }}>
        <Watchlist selectedAsset={selectedAsset} onSelect={setSelectedAsset} />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
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
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--aur-ink-dim)' }}>
            <div style={{ width: 24, height: 24, border: '2px solid var(--aur-border-soft)', borderTopColor: 'var(--aur-accent)', borderRadius: '50%', animation: 'aur-spin 1s linear infinite' }} />
            <span>Loading market data…</span>
          </div>
        ) : backendDown ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--aur-negative)' }}>
            <span style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(248,113,113,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 }}>⚠</span>
            <span style={{ fontSize: 18, fontWeight: 700 }}>BACKEND UNAVAILABLE</span>
            <span style={{ fontSize: 13, color: 'var(--aur-ink-dim)' }}>The market data service is not responding.</span>
            <button onClick={() => loadData()} style={{ background: 'rgba(124,158,255,0.15)', border: '1px solid var(--aur-accent)', color: 'var(--aur-accent)', padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Retry</button>
          </div>
        ) : error ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--aur-negative)' }}>
            <span>{error}</span>
            <button onClick={() => loadData()} style={{ background: 'rgba(124,158,255,0.15)', border: '1px solid var(--aur-accent)', color: 'var(--aur-accent)', padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Retry</button>
          </div>
        ) : emptyData ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--aur-warning)' }}>NO DATA AVAILABLE</span>
            <span style={{ fontSize: 13, color: 'var(--aur-ink-dim)' }}>The backend returned no valid bars for this asset/timeframe.</span>
            <button onClick={() => loadData()} style={{ background: 'rgba(124,158,255,0.15)', border: '1px solid var(--aur-accent)', color: 'var(--aur-accent)', padding: '8px 20px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Retry</button>
          </div>
        ) : (
          <>
            <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
              <PriceChart bars={bars} overlays={overlays.filter(s => !oscillatorIds.has(s.name))} panels={oscillatorSeries} structureEnabled={structureEnabled} isIntraday={isIntraday} />
            </div>
            <div style={{ display: 'flex', gap: 16, padding: '6px 16px', background: 'var(--aur-bg-elevated)', borderTop: '1px solid var(--aur-border-soft)', fontSize: 12, color: 'var(--aur-ink-dim)', fontFamily: 'Space Grotesk, monospace', alignItems: 'center', flexShrink: 0 }}>
              {lastBar && (<><span>O: {lastBar.open.toFixed(2)}</span><span>H: {lastBar.high.toFixed(2)}</span><span>L: {lastBar.low.toFixed(2)}</span><span>C: {lastBar.close.toFixed(2)}</span><span>Vol: {lastBar.volume.toLocaleString()}</span></>)}
              <button
                onClick={() => { setStructureEnabled(p => !p); emit('structure_analysis', `Structure overlay ${!structureEnabled ? 'enabled' : 'disabled'}`, 'live'); }}
                style={{ marginLeft: 'auto', background: structureEnabled ? 'rgba(124,158,255,0.15)' : 'none', border: '1px solid var(--aur-border-soft)', color: structureEnabled ? 'var(--aur-accent)' : 'var(--aur-ink-dim)', padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 10, fontWeight: 600 }}
              >STRUCTURE {structureEnabled ? 'ON' : 'OFF'}</button>
              <button
                onClick={() => setContextEnabled(p => !p)}
                style={{ background: contextEnabled ? 'rgba(255,138,101,0.15)' : 'none', border: '1px solid var(--aur-border-soft)', color: contextEnabled ? 'var(--aur-accent-2)' : 'var(--aur-ink-dim)', padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 10, fontWeight: 600 }}
              >CONTEXT {contextEnabled ? 'ON' : 'OFF'}</button>
            </div>
          </>
        )}
      </div>
      <div style={{ display: 'flex', flexShrink: 0 }}>
        <AnalysisPanel metrics={metrics} symbol={selectedAsset} isDemo={dataSource.isDemo} stale={dataSource.stale} provider={dataSource.provider} activeOverlays={overlays} />
      </div>
      <IndicatorSelector enabled={enabledIndicators} onToggle={handleToggleIndicator} indicatorParams={indicatorParams} onParamUpdate={handleParamUpdate} onParamReset={handleParamReset} />
      <MarketStructurePanel bars={bars} enabled={structureEnabled} />
      <MarketContextPanel asset={selectedAsset} timeframe={selectedTimeframe} bars={bars} visible={contextEnabled} />
      <style>{`@keyframes aur-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};
