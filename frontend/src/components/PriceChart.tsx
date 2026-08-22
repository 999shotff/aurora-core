import React, { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, HistogramData, LineData } from 'lightweight-charts';
import { OHLCBar, IndicatorSeries } from '../types';

interface Props {
  bars: OHLCBar[];
  overlays: IndicatorSeries[];
  panels: IndicatorSeries[];
}

export const PriceChart: React.FC<Props> = ({ bars, overlays, panels }) => {
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
  }, [bars]);

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
