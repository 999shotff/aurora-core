import React, { useEffect, useRef, useCallback } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, HistogramData, LineData, Time } from 'lightweight-charts';
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

export const PriceChart: React.FC<Props> = ({ bars, overlays, panels: _panels, structureEnabled = false, isIntraday = false }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const overlayRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const panelRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());

  const cleanupOverlays = useCallback(() => {
    const chart = chartRef.current;
    if (!chart) return;
    for (const series of overlayRef.current.values()) {
      try { chart.removeSeries(series); } catch { /* removed */ }
    }
    overlayRef.current.clear();
  }, []);

  const cleanupPanels = useCallback(() => {
    const chart = chartRef.current;
    if (!chart) return;
    for (const series of panelRef.current.values()) {
      try { chart.removeSeries(series); } catch { /* removed */ }
    }
    panelRef.current.clear();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0a0e17' }, textColor: '#d1d4dc' },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      crosshair: { mode: 0 },
      timeScale: { borderColor: '#1e222d', timeVisible: isIntraday, rightOffset: 5 },
      rightPriceScale: { borderColor: '#1e222d', scaleMargins: { top: 0.05, bottom: 0.2 } },
      width: containerRef.current.clientWidth,
      height: 500,
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

    chartRef.current = chart;
    candleRef.current = candleSeries;
    volumeRef.current = volumeSeries;

    const resizeObserver = new ResizeObserver(entries => {
      if (entries[0]) {
        chart.applyOptions({ width: entries[0].contentRect.width });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      cleanupOverlays();
      cleanupPanels();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.applyOptions({ timeScale: { timeVisible: isIntraday } });
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
    if (!chartRef.current) return;
    cleanupOverlays();

    for (const ov of overlays) {
      const color = OVERLAY_COLORS[ov.name] ?? '#FFFFFF';
      const lineSeries = chartRef.current.addLineSeries({
        color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
      });
      const data: LineData[] = ov.points.map(p => ({
        time: barTimeToChartTime(p.time),
        value: p.value,
      }));
      if (data.length > 0) {
        lineSeries.setData(data);
      }
      overlayRef.current.set(ov.name, lineSeries);
    }
  }, [overlays, cleanupOverlays]);

  return <div ref={containerRef} style={{ width: '100%', height: 500 }} />;
};
