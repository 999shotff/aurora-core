import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, HistogramData, LineData } from 'lightweight-charts';
import { OHLCBar, IndicatorSeries } from '../types';
import { detectSwingPoints, detectStructureBreaks, SwingPoint, StructureBreak } from '../services/structure';

interface Props {
  bars: OHLCBar[];
  overlays: IndicatorSeries[];
  panels: IndicatorSeries[];
  structureEnabled?: boolean;
}

export const PriceChart: React.FC<Props> = ({ bars, overlays, panels, structureEnabled = false }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: '#0a0e17' }, textColor: '#d1d4dc' },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      crosshair: { mode: 0 },
      timeScale: { borderColor: '#1e222d', timeVisible: true },
      rightPriceScale: { borderColor: '#1e222d' },
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
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!candleRef.current || !volumeRef.current) return;

    const candleData: CandlestickData[] = bars.map(b => ({
      time: b.time as unknown as number,
      open: b.open, high: b.high, low: b.low, close: b.close,
    }));
    candleRef.current.setData(candleData);

    const volumeData: HistogramData[] = bars.map(b => ({
      time: b.time as unknown as number,
      value: b.volume,
      color: b.close >= b.open ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.3)',
    }));
    volumeRef.current.setData(volumeData);

    // Add structure markers if enabled
    if (structureEnabled && bars.length > 4) {
      const highs = bars.map(b => b.high);
      const lows = bars.map(b => b.low);
      const closes = bars.map(b => b.close);
      const timeToBar: Record<string, number> = {};
      bars.forEach((b, i) => { timeToBar[b.time] = i; });

      const swings = detectSwingPoints(highs, lows, 3, 3);
      const markers = swings.map(sp => ({
        time: bars[sp.index]?.time as unknown as number,
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
          time: bar.time as unknown as number,
          position: br.break_type.includes('bull') ? 'belowBar' as const : 'aboveBar' as const,
          color: br.break_type.includes('choch') ? '#E91E63' : '#26a69a',
          shape: 'circle' as const,
          text: br.break_type.includes('choch') ? 'CH' : 'BOS',
        });
      }

      markers.sort((a, b) => (a.time as number) - (b.time as number));
      candleRef.current?.setMarkers(markers);
    }
  }, [bars, structureEnabled]);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = chartRef.current;

    // Remove old overlay series (simple: recreate all)
    // In production, track series by name for efficiency
    const overlayColors: Record<string, string> = {
      sma_20: '#2196F3', sma_50: '#64B5F6',
      ema_12: '#FF9800', ema_26: '#FFB74D',
      bb_upper: '#9C27B0', bb_middle: '#9C27B0', bb_lower: '#9C27B0',
      ichimoku_tenkan: '#00BCD4', ichimoku_kijun: '#FF5722',
      ichimoku_senkou_a: 'rgba(0,188,212,0.3)', ichimoku_senkou_b: 'rgba(255,87,34,0.3)',
      vwap: '#E91E63',
    };

    for (const ov of overlays) {
      const color = overlayColors[ov.name] ?? '#FFFFFF';
      const lineSeries = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      const data: LineData[] = ov.points.map(p => ({
        time: p.time as unknown as number,
        value: p.value,
      }));
      lineSeries.setData(data);
    }
  }, [overlays]);

  return <div ref={containerRef} style={{ width: '100%', height: 500 }} />;
};
