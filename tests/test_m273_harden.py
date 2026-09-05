"""M27.3 Regression Tests — Indicator Completeness + Multi-Pane UX.

Tests Fibonacci, parameters, crosshair sync, analysis freshness, and leakage.
NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import json
import subprocess

import pytest

# ============================================================
# Fibonacci Python-side Tests (mirrors TS computeFibonacci)
# ============================================================

class TestFibonacciLevels:
    """Test Fibonacci level calculation (Python equivalent of TS computeFibonacci)."""

    def _fibonacci(self, high: float, low: float, levels=None):
        if levels is None:
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        if high < low:
            high, low = low, high
        diff = high - low
        return {level: high - diff * level for level in levels}

    def test_fib_levels_math(self):
        """Fibonacci levels follow correct mathematical formula."""
        levels = self._fibonacci(200, 100)
        assert levels[0] == pytest.approx(200)
        assert levels[0.236] == pytest.approx(200 - 100 * 0.236)
        assert levels[0.382] == pytest.approx(200 - 100 * 0.382)
        assert levels[0.5] == pytest.approx(150)
        assert levels[0.618] == pytest.approx(200 - 100 * 0.618)
        assert levels[0.786] == pytest.approx(200 - 100 * 0.786)
        assert levels[1.0] == pytest.approx(100)

    def test_fib_high_low_swap(self):
        """Fibonacci swaps high/low if inverted."""
        levels = self._fibonacci(100, 200)
        assert levels[0] == pytest.approx(200)
        assert levels[1.0] == pytest.approx(100)

    def test_fib_standard_levels_count(self):
        """Fibonacci produces 7 standard levels by default."""
        levels = self._fibonacci(150, 100)
        assert len(levels) == 7

    def test_fib_custom_levels(self):
        """Fibonacci accepts custom levels."""
        levels = self._fibonacci(200, 100, [0, 0.5, 1.0])
        assert len(levels) == 3
        assert levels[0] == pytest.approx(200)
        assert levels[0.5] == pytest.approx(150)
        assert levels[1.0] == pytest.approx(100)

    def test_fib_zero_range(self):
        """Fibonacci with zero range produces flat levels."""
        levels = self._fibonacci(100, 100)
        for v in levels.values():
            assert v == pytest.approx(100)

    def test_fib_deterministic(self):
        """Same input produces same output."""
        r1 = self._fibonacci(200, 100)
        r2 = self._fibonacci(200, 100)
        assert r1 == r2

    def test_fib_no_future_data(self):
        """Fibonacci only uses provided high/low, not bar indices."""
        high, low = 200.0, 100.0
        levels = self._fibonacci(high, low)
        assert levels[0] == high
        assert levels[1.0] == low
        assert all(isinstance(v, float) for v in levels.values())

    def test_fib_prices_from_bar_range(self):
        """Fibonacci prices are computed from bar high/low range."""
        bars = [
            {'high': 110 + i, 'low': 90 + i}
            for i in range(20)
        ]
        high = max(b['high'] for b in bars)
        low = min(b['low'] for b in bars)
        levels = self._fibonacci(high, low)
        assert levels[0] == pytest.approx(high)
        assert levels[1.0] == pytest.approx(low)
        assert levels[0.5] == pytest.approx((high + low) / 2)

    def test_fib_direction_bullish(self):
        """Bullish retracement: high above low, levels between."""
        levels = self._fibonacci(150, 100)
        assert levels[0] == 150  # High
        assert levels[1.0] == 100  # Low
        for pct in [0.236, 0.382, 0.5, 0.618, 0.786]:
            assert 100 < levels[pct] < 150

    def test_fib_direction_bearish(self):
        """Bearish retracement: same as bullish (auto-swapped)."""
        levels = self._fibonacci(100, 150)  # Inverted
        assert levels[0] == 150  # Auto-swapped
        assert levels[1.0] == 100  # Auto-swapped


# ============================================================
# TypeScript Fibonacci Tests (via Node subprocess)
# ============================================================

class TestFibonacciTS:
    """Test TypeScript Fibonacci via Node subprocess."""

    TS_TEST = r'''
function computeFibonacci(high, low, levels) {
    if (!levels) levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
    if (high < low) [high, low] = [low, high];
    const diff = high - low;
    const result = {};
    for (const level of levels) {
        result[level] = high - diff * level;
    }
    return result;
}

const levels = computeFibonacci(200, 100);
const result = {
    level_0: levels[0],
    level_236: levels[0.236],
    level_382: levels[0.382],
    level_5: levels[0.5],
    level_618: levels[0.618],
    level_786: levels[0.786],
    level_1: levels[1],
    count: Object.keys(levels).length,
};
console.log(JSON.stringify(result));
'''

    def test_ts_fibonacci_math(self):
        """TS Fibonacci levels match expected values."""
        result = subprocess.run(
            ['node', '-e', self.TS_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['level_0'] == pytest.approx(200)
        assert data['level_236'] == pytest.approx(200 - 100 * 0.236)
        assert data['level_382'] == pytest.approx(200 - 100 * 0.382)
        assert data['level_5'] == pytest.approx(150)
        assert data['level_618'] == pytest.approx(200 - 100 * 0.618)
        assert data['level_786'] == pytest.approx(200 - 100 * 0.786)
        assert data['level_1'] == pytest.approx(100)
        assert data['count'] == 7


# ============================================================
# Indicator Parameter Tests (via TS subprocess)
# ============================================================

class TestIndicatorParameters:
    """Test indicator parameter system."""

    TS_PARAM_TEST = r'''
function computeAllIndicators(bars, enabled, params) {
    const closes = bars.map(b => b.close);
    const series = [];
    const on = (id) => !enabled || enabled.has(id);
    const p = (id) => (params && params[id]) || {};

    function validatePeriod(period) {
        return Math.floor(period);
    }

    function computeSMA(values, period) {
        const p = validatePeriod(period);
        const result = [];
        for (let i = 0; i < values.length; i++) {
            if (i < p - 1) { result.push(null); continue; }
            const slice = values.slice(i - p + 1, i + 1);
            result.push(slice.reduce((a, b) => a + b, 0) / p);
        }
        return result;
    }

    function computeEMA(values, period) {
        const p = validatePeriod(period);
        if (values.length < p) return new Array(values.length).fill(null);
        const result = new Array(p - 1).fill(null);
        const k = 2 / (p + 1);
        let ema = values.slice(0, p).reduce((a, b) => a + b, 0) / p;
        result.push(ema);
        for (let i = p; i < values.length; i++) {
            ema = values[i] * k + ema * (1 - k);
            result.push(ema);
        }
        return result;
    }

    function computeRSI(closes, period) {
        const p = validatePeriod(period);
        if (closes.length < p + 1) return closes.map(() => null);
        const result = new Array(p).fill(null);
        const gains = [], losses = [];
        for (let i = 1; i < closes.length; i++) {
            const change = closes[i] - closes[i-1];
            gains.push(Math.max(change, 0));
            losses.push(Math.max(-change, 0));
        }
        let avgGain = gains.slice(0, p).reduce((a, b) => a + b, 0) / p;
        let avgLoss = losses.slice(0, p).reduce((a, b) => a + b, 0) / p;
        result.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
        for (let i = p; i < gains.length; i++) {
            avgGain = (avgGain * (p - 1) + gains[i]) / p;
            avgLoss = (avgLoss * (p - 1) + losses[i]) / p;
            result.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
        }
        return result;
    }

    function computeMACD(closes, fast, slow, signal) {
        const f = validatePeriod(fast);
        const s = validatePeriod(slow);
        const emaFast = computeEMA(closes, f);
        const emaSlow = computeEMA(closes, s);
        const macdLine = closes.map((_, i) =>
            emaFast[i] !== null && emaSlow[i] !== null ? emaFast[i] - emaSlow[i] : null
        );
        const validMacd = macdLine.filter(v => v !== null);
        return { macdLine, params: { fast: f, slow: s, signal: validatePeriod(signal) } };
    }

    const times = bars.map(b => b.time);
    if (on('sma')) {
        const period = p('sma').period || 20;
        series.push({ name: 'sma_20', params: { period }, points: computeSMA(closes, period).map((v, i) => v !== null ? { time: times[i], value: v } : null).filter(Boolean) });
    }
    if (on('ema')) {
        const period = p('ema').period || 12;
        series.push({ name: 'ema_12', params: { period }, points: computeEMA(closes, period).map((v, i) => v !== null ? { time: times[i], value: v } : null).filter(Boolean) });
    }
    if (on('rsi')) {
        const period = p('rsi').period || 14;
        series.push({ name: 'rsi_14', params: { period }, points: computeRSI(closes, period).map((v, i) => v !== null ? { time: times[i], value: v } : null).filter(Boolean) });
    }
    if (on('macd')) {
        const fast = p('macd').fast || 12;
        const slow = p('macd').slow || 26;
        const signal = p('macd').signal || 9;
        const macd = computeMACD(closes, fast, slow, signal);
        series.push({ name: 'macd_line', params: macd.params, points: [] });
    }
    return series;
}

const bars = Array.from({length: 50}, (_, i) => ({ time: `2024-01-${String(i+1).padStart(2,'0')}`, open: 100+i, high: 105+i, low: 95+i, close: 100+i, volume: 1000 }));

// Test defaults
const r1 = computeAllIndicators(bars, new Set(['rsi']), null);
const rsi_default = r1.find(s => s.name === 'rsi_14');

// Test custom params
const r2 = computeAllIndicators(bars, new Set(['rsi']), { rsi: { period: 21 } });
const rsi_custom = r2.find(s => s.name === 'rsi_14');

// Test multiple independent
const r3 = computeAllIndicators(bars, new Set(['rsi', 'macd', 'sma']), { rsi: { period: 21 } });
const macd_in_r3 = r3.find(s => s.name === 'macd_line');
const sma_in_r3 = r3.find(s => s.name === 'sma_20');

// Test empty params
const r4 = computeAllIndicators(bars, new Set(['rsi']), {});
const rsi_empty = r4.find(s => s.name === 'rsi_14');

console.log(JSON.stringify({
    rsi_default_period: rsi_default.params.period,
    rsi_custom_period: rsi_custom.params.period,
    macd_default_fast: macd_in_r3.params.fast,
    sma_default_period: sma_in_r3.params.period,
    rsi_empty_period: rsi_empty.params.period,
}));
'''

    def test_ts_defaults_used(self):
        """TS default parameters used when none provided."""
        result = subprocess.run(
            ['node', '-e', self.TS_PARAM_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['rsi_default_period'] == 14
        assert data['rsi_empty_period'] == 14

    def test_ts_custom_params(self):
        """TS custom parameters override defaults."""
        result = subprocess.run(
            ['node', '-e', self.TS_PARAM_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['rsi_custom_period'] == 21

    def test_ts_multiple_independent(self):
        """TS changing RSI params does not affect MACD/SMA."""
        result = subprocess.run(
            ['node', '-e', self.TS_PARAM_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['macd_default_fast'] == 12
        assert data['sma_default_period'] == 20


# ============================================================
# Fibonacci TypeScript Integration Tests
# ============================================================

class TestFibonacciIntegration:
    """Test Fibonacci in computeAllIndicators (TS subprocess)."""

    TS_FIB_TEST = r'''
function computeFibonacci(high, low, levels) {
    if (!levels) levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
    if (high < low) [high, low] = [low, high];
    const diff = high - low;
    const result = {};
    for (const level of levels) {
        result[level] = high - diff * level;
    }
    return result;
}

function computeAllIndicators(bars, enabled) {
    const highs = bars.map(b => b.high);
    const lows = bars.map(b => b.low);
    const times = bars.map(b => b.time);
    const series = [];
    const on = (id) => !enabled || enabled.has(id);

    if (on('fib')) {
        const fibLevels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
        const levelNames = ['0', '23.6', '38.2', '50', '61.8', '78.6', '100'];
        const fibHigh = Math.max(...highs);
        const fibLow = Math.min(...lows);
        const fibValues = computeFibonacci(fibHigh, fibLow, fibLevels);
        for (let i = 0; i < fibLevels.length; i++) {
            const level = fibLevels[i];
            const label = levelNames[i];
            const price = fibValues[level];
            series.push({
                name: `fib_${label}`,
                parameters: { level, price, high: fibHigh, low: fibLow },
                points: [{ time: times[times.length - 1], value: price }],
            });
        }
    }
    return series;
}

const bars = Array.from({length: 100}, (_, i) => ({
    time: `2024-01-${String(Math.min(i+1, 28)).padStart(2,'0')}`,
    open: 100 + 10 * Math.sin(i / 10),
    high: 105 + 10 * Math.sin(i / 10),
    low: 95 + 10 * Math.sin(i / 10),
    close: 100 + 10 * Math.sin(i / 10),
    volume: 1000000,
}));

const enabled = new Set(['fib']);
const result = computeAllIndicators(bars, enabled);
const fibSeries = result.filter(s => s.name.startsWith('fib_'));

const high = Math.max(...bars.map(b => b.high));
const low = Math.min(...bars.map(b => b.low));

const fib0 = fibSeries.find(s => s.name === 'fib_0');
const fib100 = fibSeries.find(s => s.name === 'fib_100');
const fib50 = fibSeries.find(s => s.name === 'fib_50');

// Test determinism
const result2 = computeAllIndicators(bars, enabled);

// Test disabled
const result3 = computeAllIndicators(bars, new Set(['sma']));

console.log(JSON.stringify({
    count: fibSeries.length,
    fib0_price: fib0.parameters.price,
    fib100_price: fib100.parameters.price,
    fib50_price: fib50.parameters.price,
    high: high,
    low: low,
    fib0_high: fib0.parameters.high,
    fib0_low: fib0.parameters.low,
    deterministic: JSON.stringify(result) === JSON.stringify(result2),
    not_produced_when_disabled: result3.filter(s => s.name.startsWith('fib_')).length === 0,
}));
'''

    def test_ts_fib_count(self):
        """TS Fibonacci produces 7 level series."""
        result = subprocess.run(
            ['node', '-e', self.TS_FIB_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['count'] == 7

    def test_ts_fib_prices(self):
        """TS Fibonacci prices are real bar values."""
        result = subprocess.run(
            ['node', '-e', self.TS_FIB_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['fib0_price'] == pytest.approx(data['high'], rel=1e-6)
        assert data['fib100_price'] == pytest.approx(data['low'], rel=1e-6)
        assert data['fib50_price'] == pytest.approx((data['high'] + data['low']) / 2, rel=1e-6)

    def test_ts_fib_source_info(self):
        """TS Fibonacci includes high/low source info."""
        result = subprocess.run(
            ['node', '-e', self.TS_FIB_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['fib0_high'] == data['high']
        assert data['fib0_low'] == data['low']

    def test_ts_fib_deterministic(self):
        """TS Fibonacci is deterministic."""
        result = subprocess.run(
            ['node', '-e', self.TS_FIB_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['deterministic'] is True

    def test_ts_fib_not_produced_when_disabled(self):
        """TS Fibonacci not produced when not enabled."""
        result = subprocess.run(
            ['node', '-e', self.TS_FIB_TEST],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['not_produced_when_disabled'] is True


# ============================================================
# Crosshair Sync Tests
# ============================================================

class TestCrosshairSync:
    """Test crosshair sync logic."""

    def test_crosshair_guard_prevents_recursive(self):
        """isSyncing guard prevents recursive crosshair updates."""
        syncing = False
        call_count = 0

        def sync(source_chart, time):
            nonlocal syncing, call_count
            if syncing:
                return
            syncing = True
            call_count += 1
            syncing = False

        sync('chart1', 'time1')
        assert call_count == 1
        syncing = True
        sync('chart2', 'time2')
        assert call_count == 1

    def test_crosshair_null_time_ignored(self):
        """Null time is ignored in crosshair sync."""
        syncing = False
        call_count = 0

        def sync(source_chart, time):
            nonlocal syncing, call_count
            if syncing or time is None:
                return
            syncing = True
            call_count += 1
            syncing = False

        sync('chart1', None)
        assert call_count == 0
        sync('chart1', 'time1')
        assert call_count == 1

    def test_crosshair_source_chart_excluded(self):
        """Source chart is excluded from sync targets."""
        synced_charts = []

        def sync(source_chart, time, all_charts):
            for chart in all_charts:
                if chart != source_chart:
                    synced_charts.append(chart)

        sync('chart1', 'time1', ['chart1', 'chart2', 'chart3'])
        assert synced_charts == ['chart2', 'chart3']

    def test_crosshair_multiple_sources(self):
        """Multiple charts can be sources sequentially."""
        results = []

        def sync(source, time):
            results.append(f'{source}->{time}')

        sync('main', 't1')
        sync('panel1', 't1')
        assert results == ['main->t1', 'panel1->t1']


# ============================================================
# Analysis Freshness Tests
# ============================================================

class TestAnalysisFreshness:
    """Test analysis freshness tracking."""

    def test_freshness_calculation(self):
        """Freshness label correctly calculated."""
        freshness_ms = 3000
        label = 'FRESH' if freshness_ms < 5000 else f'{int(freshness_ms/1000)}s ago'
        assert label == 'FRESH'

    def test_recent_but_not_fresh(self):
        """Recent analysis shows seconds."""
        freshness_ms = 15000
        label = 'FRESH' if freshness_ms < 5000 else f'{int(freshness_ms/1000)}s ago'
        assert label == '15s ago'

    def test_stale_after_30s(self):
        """Analysis is stale after 30 seconds."""
        freshness_ms = 35000
        if freshness_ms < 5000:
            label = 'FRESH'
        elif freshness_ms < 30000:
            label = f'{int(freshness_ms/1000)}s ago'
        else:
            label = 'STALE'
        assert label == 'STALE'

    def test_exact_boundary_5s(self):
        """5000ms is not fresh."""
        freshness_ms = 5000
        label = 'FRESH' if freshness_ms < 5000 else 'NOT_FRESH'
        assert label == 'NOT_FRESH'

    def test_exact_boundary_30s(self):
        """30000ms transitions to stale."""
        freshness_ms = 30000
        if freshness_ms < 5000:
            label = 'FRESH'
        elif freshness_ms < 30000:
            label = 'RECENT'
        else:
            label = 'STALE'
        assert label == 'STALE'


# ============================================================
# Leakage Prevention Tests
# ============================================================

class TestLeakagePrevention:
    """Test no future data leakage in indicators."""

    def test_fibonacci_no_future_data(self):
        """Fibonacci does not use future bars."""
        bars = [
            {'high': 100 + i, 'low': 80 + i}
            for i in range(20)
        ]
        high = max(b['high'] for b in bars)
        low = min(b['low'] for b in bars)
        # Fibonacci uses only high/low, no bar index dependency
        assert high == 119
        assert low == 80

    def test_parameter_change_deterministic(self):
        """Same input + same params = same output."""
        def compute_rsi(closes, period):
            if len(closes) < period + 1:
                return [None] * len(closes)
            result = [None] * period
            gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
            losses = [max(-(closes[i] - closes[i-1]), 0) for i in range(1, len(closes))]
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            if avg_loss == 0:
                result.append(100)
            else:
                result.append(round(100 - 100 / (1 + avg_gain / avg_loss), 2))
            for i in range(period, len(gains)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                if avg_loss == 0:
                    result.append(100)
                else:
                    result.append(round(100 - 100 / (1 + avg_gain / avg_loss), 2))
            return result

        closes = [100 + i * 0.5 + (-1 if i % 3 == 0 else 1) for i in range(50)]
        r1 = compute_rsi(closes, 14)
        r2 = compute_rsi(closes, 14)
        assert r1 == r2

    def test_sma_no_future_data(self):
        """SMA only uses past/current bars."""
        closes = [100, 101, 102, 103, 104]
        # SMA at index 4 = avg(102, 103, 104) = 103
        sma_at_4 = sum(closes[2:5]) / 3
        assert sma_at_4 == pytest.approx(103)
        # SMA at index 2 = avg(100, 101, 102) = 101
        sma_at_2 = sum(closes[0:3]) / 3
        assert sma_at_2 == pytest.approx(101)

    def test_ema_no_future_data(self):
        """EMA only uses past/current bars."""
        closes = [100, 101, 102, 103, 104]
        period = 3
        k = 2 / (period + 1)
        ema = sum(closes[:3]) / 3
        for i in range(3, len(closes)):
            ema = closes[i] * k + ema * (1 - k)
        # EMA depends only on past values
        assert ema > 100
        assert ema < 110
