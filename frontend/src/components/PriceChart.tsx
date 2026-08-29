import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, HistogramData, LineData, Time, LogicalRange } from 'lightweight-charts';
import type { OHLCBar, IndicatorSeries } from '../types';
import { detectSwingPoints, detectStructureBreaks } from '../services/structure';

interface Props {
  bars: OHLCBar[];
  overlays: IndicatorSeries[];
  panels: IndicatorSeries[];
  structureEnabled?: boolean;
  isIntraday?: boolean;
}

function barTimeToChartTime(time: string): Time {
  if (/^\d{4}-\d{2}-\d{2}$/.test(time)) {
    return time as unknown as Time;
  }
  const d = new Date(time.includes('Z') ? time : time + 'Z');
  return (Math.floor(d.getTime() / 1000)) as unknown as Time;
}

const OVERLAY_COLORS: Record<string, string> = {
  sma_20: '#2196F3', sma_50: '#64B5F6',
  ema_12: '#FF9800', ema_26: '#FFB74D',
  bb_upper: '#9C27B0', bb_middle: '#9C27B0', bb_lower: '#9C27B0',
  ichimoku_tenkan: '#00BCD4', ichimoku_kijun: '#FF5722',
  ichimoku_senkou_a: 'rgba(0,188,212,0.3)', ichimoku_senkou_b: 'rgba(255,87,34,0.3)',
  vwap: '#E91E63',
  pivot_pp: '#FFD700', pivot_r1: '#FF6B6B', pivot_r2: '#FF6B6B', pivot_r3: '#FF6B6B',
  pivot_s1: '#4CAF50', pivot_s2: '#4CAF50', pivot_s3: '#4CAF50',
};

const PANEL_GROUP_COLORS: Record<string, string[]> = {
  rsi: ['#AB47BC'],
  macd: ['#42A5F5', '#EF5350', '#78909C'],
  stochastic: ['#FF9800', '#03A9F4'],
  adx: ['#E53935', '#1E88E5', '#43A047'],
  cci: ['#66BB6A'],
  roc: ['#FDD835'],
  williamsr: ['#26C6DA'],
  atr: ['#8D6E63'],
  obv: ['#EC407A'],
  mfi: ['#5C6BC0'],
};

const PANEL_BG_COLORS: Record<string, string> = {
  rsi: 'rgba(171,71,188,0.08)',
  macd: 'rgba(66,165,245,0.08)',
  stochastic: 'rgba(255,152,0,0.08)',
  adx: 'rgba(229,57,53,0.08)',
  cci: 'rgba(102,187,106,0.08)',
  roc: 'rgba(253,216,53,0.08)',
  williamsr: 'rgba(38,198,218,0.08)',
  atr: 'rgba(141,110,99,0.08)',
  obv: 'rgba(236,64,150,0.08)',
  mfi: 'rgba(92,107,192,0.08)',
};

const PANEL_LABELS: Record<string, string> = {
  rsi: 'RSI',
  macd: 'MACD',
  stochastic: 'Stochastic',
  adx: 'ADX/DMI',
  cci: 'CCI',
  roc: 'ROC',
  williamsr: 'Williams %R',
  atr: 'ATR',
  obv: 'OBV',
  mfi: 'MFI',
};

const PANEL_THRESHOLDS: Record<string, { upper?: number; lower?: number; mid?: number }> = {
  rsi: { upper: 70, lower: 30, mid: 50 },
  stochastic: { upper: 80, lower: 20, mid: 50 },
  williamsr: { upper: -20, lower: -80, mid: -50 },
};

type PanelGroup = {
  groupId: string;
  series: IndicatorSeries[];
};

function groupPanelSeries(panels: IndicatorSeries[]): PanelGroup[] {
  const groupMap = new Map<string, IndicatorSeries[]>();

  for (const s of panels) {
    const groupId = extractGroupId(s.name);
    if (!groupMap.has(groupId)) groupMap.set(groupId, []);
    groupMap.get(groupId)!.push(s);
  }

  return Array.from(groupMap.entries()).map(([groupId, series]) => ({
    groupId,
    series,
  }));
}

function extractGroupId(name: string): string {
  const prefixMap: Record<string, string> = {
    rsi: 'rsi',
    macd_line: 'macd', macd_signal: 'macd', macd_histogram: 'macd',
    stoch_k: 'stochastic', stoch_d: 'stochastic',
    adx_line: 'adx', adx_plus_di: 'adx', adx_minus_di: 'adx',
    cci: 'cci',
    roc: 'roc',
    williamsr: 'williamsr',
    atr: 'atr',
    obv: 'obv',
    mfi: 'mfi',
  };

  for (const [prefix, group] of Object.entries(prefixMap)) {
    if (name === prefix || name.startsWith(prefix + '_')) return group;
  }

  return name.split('_')[0];
}

export const PriceChart: React.FC<Props> = ({ bars, overlays, panels, structureEnabled = false, isIntraday = false }) => {
  const outerRef = useRef<HTMLDivElement>(null);
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const mainChartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const overlayRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());

  const panelChartsRef = useRef<IChartApi[]>([]);
  const panelContainerRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const panelSeriesRefs = useRef<Map<string, ISeriesApi<'Line' | 'Histogram'>[]>>(new Map());

  const syncCallbacksRef = useRef<Array<{ chart: IChartApi; cb: (range: unknown) => void }>>([]);
  const isSyncingRef = useRef(false);

  const panelGroups = useMemo(() => groupPanelSeries(panels), [panels]);

  const cleanupOverlays = useCallback(() => {
    const chart = mainChartRef.current;
    if (!chart) return;
    for (const series of overlayRef.current.values()) {
      try { chart.removeSeries(series); } catch { /* removed */ }
    }
    overlayRef.current.clear();
  }, []);

  const cleanupPanels = useCallback(() => {
    for (const seriesArr of panelSeriesRefs.current.values()) {
      for (const _s of seriesArr) {
        try { /* series removed with chart */ } catch { /* removed */ }
      }
    }
    panelSeriesRefs.current.clear();

    for (const chart of panelChartsRef.current) {
      try { chart.remove(); } catch { /* removed */ }
    }
    panelChartsRef.current = [];
  }, []);

  useEffect(() => {
    if (!mainContainerRef.current) return;

    const chart = createChart(mainContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0a0e17' }, textColor: '#d1d4dc' },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      crosshair: { mode: 0 },
      timeScale: { borderColor: '#1e222d', timeVisible: isIntraday, rightOffset: 5 },
      rightPriceScale: { borderColor: '#1e222d', scaleMargins: { top: 0.05, bottom: 0.2 } },
      width: mainContainerRef.current.clientWidth,
      height: mainContainerRef.current.clientHeight || 400,
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350',
      borderUpColor: '#26a69a', borderDownColor: '#ef5350',
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    mainChartRef.current = chart;
    candleRef.current = candleSeries;
    volumeRef.current = volumeSeries;

    const resizeObserver = new ResizeObserver(entries => {
      if (entries[0]) {
        chart.applyOptions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        });
      }
    });
    resizeObserver.observe(mainContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      cleanupOverlays();
      cleanupPanels();
      chart.remove();
      mainChartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (mainChartRef.current) {
      mainChartRef.current.applyOptions({ timeScale: { timeVisible: isIntraday } });
    }
  }, [isIntraday]);

  useEffect(() => {
    if (!candleRef.current || !volumeRef.current) return;
    if (bars.length === 0) {
      candleRef.current.setData([]);
      volumeRef.current.setData([]);
      return;
    }

    const candleData: CandlestickData[] = bars.map(b => ({
      time: barTimeToChartTime(b.time),
      open: b.open, high: b.high, low: b.low, close: b.close,
    }));
    candleRef.current.setData(candleData);

    const volumeData: HistogramData[] = bars.map(b => ({
      time: barTimeToChartTime(b.time),
      value: b.volume,
      color: b.close >= b.open ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.3)',
    }));
    volumeRef.current.setData(volumeData);

    if (structureEnabled && bars.length > 4) {
      const highs = bars.map(b => b.high);
      const lows = bars.map(b => b.low);
      const closes = bars.map(b => b.close);

      const swings = detectSwingPoints(highs, lows, 3, 3);
      const markers = swings.map(sp => ({
        time: barTimeToChartTime(bars[sp.index]?.time ?? bars[0].time),
        position: sp.swing_type === 'high' ? 'aboveBar' as const : 'belowBar' as const,
        color: sp.swing_type === 'high' ? '#FF9800' : '#2196F3',
        shape: sp.swing_type === 'high' ? 'arrowDown' as const : 'arrowUp' as const,
        text: sp.swing_type === 'high' ? 'SH' : 'SL',
      }));

      const breaks = detectStructureBreaks(highs, lows, closes, swings, 3, 3);
      for (const br of breaks) {
        const bar = bars[br.index];
        if (!bar) continue;
        markers.push({
          time: barTimeToChartTime(bar.time),
          position: br.break_type.includes('bull') ? 'belowBar' as const : 'aboveBar' as const,
          color: br.break_type.includes('choch') ? '#E91E63' : '#26a69a',
          shape: 'arrowUp' as const,
          text: br.break_type.includes('choch') ? 'CH' : 'BOS',
        });
      }

      markers.sort((a, b) => (a.time as number) - (b.time as number));
      candleRef.current?.setMarkers(markers);
    } else {
      candleRef.current?.setMarkers([]);
    }
  }, [bars, structureEnabled]);

  useEffect(() => {
    const chart = mainChartRef.current;
    if (!chart) return;

    const existingNames = new Set(overlayRef.current.keys());
    const newNames = new Set(overlays.map(o => o.name));

    for (const name of existingNames) {
      if (!newNames.has(name)) {
        const series = overlayRef.current.get(name);
        if (series) {
          try { chart.removeSeries(series); } catch { /* removed */ }
          overlayRef.current.delete(name);
        }
      }
    }

    for (const ov of overlays) {
      const existing = overlayRef.current.get(ov.name);
      const data: LineData[] = ov.points.map(p => ({
        time: barTimeToChartTime(p.time),
        value: p.value,
      }));
      if (existing) {
        if (data.length > 0) existing.setData(data);
      } else {
        const color = OVERLAY_COLORS[ov.name] ?? '#FFFFFF';
        const lineSeries = chart.addLineSeries({
          color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
        });
        if (data.length > 0) lineSeries.setData(data);
        overlayRef.current.set(ov.name, lineSeries);
      }
    }
  }, [overlays]);

  useEffect(() => {
    const mainChart = mainChartRef.current;
    if (!mainChart) return;

    cleanupPanels();

    if (panelGroups.length === 0) return;

    const allCharts: IChartApi[] = [];

    for (const group of panelGroups) {
      const container = document.createElement('div');
      container.style.cssText = `width:100%;height:120px;background:${PANEL_BG_COLORS[group.groupId] ?? '#0a0e17'};border-top:1px solid #1e222d;position:relative;flex-shrink:0;`;
      panelContainerRefs.current.set(group.groupId, container);

      if (outerRef.current) {
        outerRef.current.appendChild(container);
      }

      const chart = createChart(container, {
        layout: { background: { type: ColorType.Solid, color: '#0a0e17' }, textColor: '#d1d4dc' },
        grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
        crosshair: { mode: 0 },
        timeScale: {
          borderColor: '#1e222d',
          timeVisible: isIntraday,
          rightOffset: 5,
          visible: true,
        },
        rightPriceScale: { borderColor: '#1e222d', scaleMargins: { top: 0.1, bottom: 0.1 } },
        width: container.clientWidth,
        height: 120,
      });

      allCharts.push(chart);

      const colors = PANEL_GROUP_COLORS[group.groupId] ?? ['#FFFFFF'];
      const seriesArr: ISeriesApi<'Line' | 'Histogram'>[] = [];

      for (let i = 0; i < group.series.length; i++) {
        const s = group.series[i];
        const color = colors[i % colors.length];
        const isHistogram = s.name.includes('histogram');

        if (isHistogram) {
          const histSeries = chart.addHistogramSeries({
            color,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          const data: HistogramData[] = s.points.map(p => ({
            time: barTimeToChartTime(p.time),
            value: p.value,
            color: p.value >= 0 ? 'rgba(38,166,154,0.6)' : 'rgba(239,83,80,0.6)',
          }));
          if (data.length > 0) histSeries.setData(data);
          seriesArr.push(histSeries);
        } else {
          const lineSeries = chart.addLineSeries({
            color,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          const data: LineData[] = s.points.map(p => ({
            time: barTimeToChartTime(p.time),
            value: p.value,
          }));
          if (data.length > 0) lineSeries.setData(data);
          seriesArr.push(lineSeries);
        }
      }

      panelSeriesRefs.current.set(group.groupId, seriesArr);

      const thresholds = PANEL_THRESHOLDS[group.groupId];
      if (thresholds) {
        const addLevelLine = (value: number, color: string, style: number) => {
          const levelSeries = chart.addLineSeries({
            color,
            lineWidth: 1,
            lineStyle: style,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          levelSeries.setData([
            { time: barTimeToChartTime('2000-01-01'), value },
            { time: barTimeToChartTime('2099-12-31'), value },
          ]);
        };
        if (thresholds.upper !== undefined) {
          addLevelLine(thresholds.upper, 'rgba(255,255,255,0.15)', 2);
        }
        if (thresholds.lower !== undefined) {
          addLevelLine(thresholds.lower, 'rgba(255,255,255,0.15)', 2);
        }
        if (thresholds.mid !== undefined) {
          addLevelLine(thresholds.mid, 'rgba(255,255,255,0.08)', 1);
        }
      }

      const label = document.createElement('div');
      label.textContent = PANEL_LABELS[group.groupId] ?? group.groupId;
      label.style.cssText = 'position:absolute;top:2px;left:6px;font-size:10px;font-weight:600;color:#8b949e;pointer-events:none;z-index:10;';
      container.appendChild(label);
    }

    panelChartsRef.current = allCharts;

    const syncFromSource = (sourceChart: IChartApi, sourceRange: LogicalRange | null) => {
      if (isSyncingRef.current) return;
      isSyncingRef.current = true;

      for (const targetChart of allCharts) {
        if (targetChart === sourceChart) continue;
        targetChart.timeScale().setVisibleLogicalRange(sourceRange!);
      }

      if (mainChart !== sourceChart && sourceRange) {
        mainChart.timeScale().setVisibleLogicalRange(sourceRange);
      }

      isSyncingRef.current = false;
    };

    const mainCb = (range: LogicalRange | null) => {
      if (isSyncingRef.current || !range) return;
      isSyncingRef.current = true;
      for (const targetChart of allCharts) {
        targetChart.timeScale().setVisibleLogicalRange(range);
      }
      isSyncingRef.current = false;
    };
    mainChart.timeScale().subscribeVisibleLogicalRangeChange(mainCb);
    syncCallbacksRef.current.push({ chart: mainChart, cb: mainCb });

    for (const panelChart of allCharts) {
      const cb = (range: LogicalRange | null) => {
        syncFromSource(panelChart, range);
      };
      panelChart.timeScale().subscribeVisibleLogicalRangeChange(cb);
      syncCallbacksRef.current.push({ chart: panelChart, cb });
    }

    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        for (const pc of allCharts) {
          pc.applyOptions({ width: w });
        }
      }
    });
    if (outerRef.current) {
      resizeObserver.observe(outerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
      for (const { chart, cb } of syncCallbacksRef.current) {
        try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(cb); } catch { /* ok */ }
      }
      syncCallbacksRef.current = [];

      for (const [_id, container] of panelContainerRefs.current.entries()) {
        try { container.remove(); } catch { /* removed */ }
      }
      panelContainerRefs.current.clear();

      for (const chart of allCharts) {
        try { chart.remove(); } catch { /* removed */ }
      }
      panelChartsRef.current = [];
      panelSeriesRefs.current.clear();
    };
  }, [panelGroups, isIntraday]);

  useEffect(() => {
    for (const group of panelGroups) {
      const seriesArr = panelSeriesRefs.current.get(group.groupId);
      if (!seriesArr) continue;

      for (let i = 0; i < group.series.length; i++) {
        const s = group.series[i];
        const seriesApi = seriesArr[i];
        if (!seriesApi) continue;

        const isHistogram = s.name.includes('histogram');
        if (isHistogram) {
          const data: HistogramData[] = s.points.map(p => ({
            time: barTimeToChartTime(p.time),
            value: p.value,
            color: p.value >= 0 ? 'rgba(38,166,154,0.6)' : 'rgba(239,83,80,0.6)',
          }));
          (seriesApi as ISeriesApi<'Histogram'>).setData(data);
        } else {
          const data: LineData[] = s.points.map(p => ({
            time: barTimeToChartTime(p.time),
            value: p.value,
          }));
          (seriesApi as ISeriesApi<'Line'>).setData(data);
        }
      }
    }
  }, [panelGroups]);

  return (
    <div ref={outerRef} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div ref={mainContainerRef} style={{ width: '100%', flex: 1, minHeight: 0 }} />
    </div>
  );
};
