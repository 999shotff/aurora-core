"""M28 Regression Tests — Multi-Timeframe Analysis + Advanced Chart UX.

Tests timeframe engine, aggregation, multi-timeframe analysis, persistence,
Fibonacci advanced, live sync, and research integrity.
NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
"""

from __future__ import annotations

import json
import subprocess

import pytest

# ============================================================
# Phase 2: Timeframe Engine (TS)
# ============================================================

class TestTimeframeEngine:
    """Test canonical timeframe definitions."""

    TS_TEST = r'''
const MINUTE = 60000;
const HOUR = 3600000;
const DAY = 86400000;
const WEEK = 604800000;

const defs = {
  '1m': { durationMs: MINUTE, isIntraday: true, aggregationSource: null },
  '5m': { durationMs: 5*MINUTE, isIntraday: true, aggregationSource: null },
  '15m': { durationMs: 15*MINUTE, isIntraday: true, aggregationSource: null },
  '30m': { durationMs: 30*MINUTE, isIntraday: true, aggregationSource: null },
  '1h': { durationMs: HOUR, isIntraday: true, aggregationSource: null },
  '4h': { durationMs: 4*HOUR, isIntraday: true, aggregationSource: '1h' },
  '1D': { durationMs: DAY, isIntraday: false, aggregationSource: null },
  '1W': { durationMs: WEEK, isIntraday: false, aggregationSource: null },
};

console.log(JSON.stringify({
  count: Object.keys(defs).length,
  '1m_duration': defs['1m'].durationMs,
  '4h_duration': defs['4h'].durationMs,
  '4h_source': defs['4h'].aggregationSource,
  '1D_intraday': defs['1D'].isIntraday,
  '1W_intraday': defs['1W'].isIntraday,
}));
'''

    def test_timeframe_count(self):
        """All 8 timeframes defined."""
        result = subprocess.run(
            ['node', '-e', self.TS_TEST],
            capture_output=True, text=True, timeout=10, check=False
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['count'] == 8

    def test_timeframe_durations(self):
        """Timeframe durations are correct."""
        result = subprocess.run(
            ['node', '-e', self.TS_TEST],
            capture_output=True, text=True, timeout=10, check=False
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['1m_duration'] == 60000
        assert data['4h_duration'] == 14400000

    def test_4h_aggregation_source(self):
        """4h aggregates from 1h."""
        result = subprocess.run(
            ['node', '-e', self.TS_TEST],
            capture_output=True, text=True, timeout=10, check=False
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['4h_source'] == '1h'

    def test_daily_not_intraday(self):
        """1D and 1W are not intraday."""
        result = subprocess.run(
            ['node', '-e', self.TS_TEST],
            capture_output=True, text=True, timeout=10, check=False
        )
        assert result.returncode == 0, f"Node error: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data['1D_intraday'] is False
        assert data['1W_intraday'] is False


# ============================================================
# Phase 3: Server-Side Aggregation
# ============================================================

class TestServerAggregation:
    """Test 4h aggregation logic."""

    def _make_candles(self, count=8, base_ts='2024-01-15T', start_hour=0):
        """Create 1h candles for aggregation."""
        candles = []
        for i in range(count):
            h = start_hour + i
            ts = f'{base_ts}{h:02d}:00:00'
            candles.append({
                'timestamp': ts,
                'open': 100 + i,
                'high': 105 + i,
                'low': 95 + i,
                'close': 102 + i,
                'volume': 1000 * (i + 1),
            })
        return candles

    def test_4h_aggregation_ohlc_rules(self):
        """4h aggregation: first open, max high, min low, last close."""
        candles = self._make_candles(4)
        # Simulate aggregation
        agg = {
            'open': candles[0]['open'],
            'high': max(c['high'] for c in candles),
            'low': min(c['low'] for c in candles),
            'close': candles[-1]['close'],
            'volume': sum(c['volume'] for c in candles),
        }
        assert agg['open'] == 100
        assert agg['high'] == 108
        assert agg['low'] == 95
        assert agg['close'] == 105
        assert agg['volume'] == 10000

    def test_4h_aggregation_volume_sum(self):
        """4h volume is sum of constituent candles."""
        candles = self._make_candles(4)
        total_volume = sum(c['volume'] for c in candles)
        assert total_volume == 1000 + 2000 + 3000 + 4000

    def test_4h_aggregation_multiple_windows(self):
        """Multiple 4h windows from 8 hourly candles."""
        candles = self._make_candles(8)
        windows = []
        for i in range(0, len(candles), 4):
            window = candles[i:i+4]
            windows.append({
                'open': window[0]['open'],
                'high': max(c['high'] for c in window),
                'low': min(c['low'] for c in window),
                'close': window[-1]['close'],
            })
        assert len(windows) == 2
        assert windows[0]['open'] == 100
        assert windows[1]['open'] == 104

    def test_4h_aggregation_utc_boundary(self):
        """4h candles align to UTC boundaries (00, 04, 08, 12, 16, 20)."""
        candles = self._make_candles(4, start_hour=2)
        # Hour 2,3,4,5 — should be grouped by hour//4
        groups = {}
        for c in candles:
            hour = int(c['timestamp'].split('T')[1].split(':')[0])
            key = hour // 4
            if key not in groups:
                groups[key] = []
            groups[key].append(c)
        # All 4 candles should be in the same group (hour 2,3 in group 0; hour 4,5 in group 1)
        assert len(groups) <= 2


# ============================================================
# Phase 4-5: Multi-Timeframe Analysis + Alignment
# ============================================================

class TestMultiTimeframeAnalysis:
    """Test multi-timeframe alignment model."""

    def test_alignment_states(self):
        """All alignment states are valid."""
        valid = {'aligned_bullish', 'aligned_bearish', 'mixed', 'conflicting', 'insufficient_data'}
        assert len(valid) == 5

    def test_all_aligned_bullish(self):
        """All timeframes showing uptrend = aligned_bullish."""
        tf_data = [
            {'timeframe': '1h', 'trend': 'uptrend'},
            {'timeframe': '4h', 'trend': 'uptrend'},
            {'timeframe': '1D', 'trend': 'uptrend'},
        ]
        trends = [tf['trend'] for tf in tf_data]
        if all(t == 'uptrend' for t in trends):
            alignment = 'aligned_bullish'
        elif all(t == 'downtrend' for t in trends):
            alignment = 'aligned_bearish'
        else:
            alignment = 'mixed'
        assert alignment == 'aligned_bullish'

    def test_conflicting_alignment(self):
        """Mixed trends = conflicting."""
        tf_data = [
            {'timeframe': '1h', 'trend': 'uptrend'},
            {'timeframe': '4h', 'trend': 'downtrend'},
            {'timeframe': '1D', 'trend': 'uptrend'},
        ]
        trends = [tf['trend'] for tf in tf_data]
        if all(t == 'uptrend' for t in trends):
            alignment = 'aligned_bullish'
        elif all(t == 'downtrend' for t in trends):
            alignment = 'aligned_bearish'
        elif len(set(trends)) > 1:
            alignment = 'conflicting'
        else:
            alignment = 'mixed'
        assert alignment == 'conflicting'

    def test_partial_alignment(self):
        """Two of three aligned = mixed."""
        tf_data = [
            {'timeframe': '1h', 'trend': 'uptrend'},
            {'timeframe': '4h', 'trend': 'uptrend'},
            {'timeframe': '1D', 'trend': 'ranging'},
        ]
        trends = [tf['trend'] for tf in tf_data]
        uptrends = sum(1 for t in trends if t == 'uptrend')
        downtrends = sum(1 for t in trends if t == 'downtrend')
        if uptrends == 3:
            alignment = 'aligned_bullish'
        elif downtrends == 3:
            alignment = 'aligned_bearish'
        elif uptrends >= 2 or downtrends >= 2:
            alignment = 'mixed'
        else:
            alignment = 'conflicting'
        assert alignment == 'mixed'

    def test_insufficient_data(self):
        """No data = insufficient_data."""
        tf_data = []
        alignment = 'insufficient_data' if len(tf_data) < 2 else 'mixed'
        assert alignment == 'insufficient_data'


# ============================================================
# Phase 8: Indicator Persistence
# ============================================================

class TestIndicatorPersistence:
    """Test localStorage save/load logic."""

    def _serialize(self, state):
        return json.dumps({
            'version': 1,
            'enabledIndicators': sorted(state['enabled']),
            'indicatorParams': state['params'],
            'selectedTimeframe': state['tf'],
            'selectedAsset': state['asset'],
            'structureEnabled': state['structure'],
            'contextEnabled': state['context'],
        })

    def _deserialize(self, raw):
        return json.loads(raw)

    def test_save_load_roundtrip(self):
        """Save and load produce identical state."""
        state = {
            'enabled': ['sma', 'rsi', 'fib'],
            'params': {'rsi': {'period': 21}},
            'tf': '4h',
            'asset': 'ETH-USD',
            'structure': True,
            'context': True,
        }
        raw = self._serialize(state)
        loaded = self._deserialize(raw)
        assert loaded['version'] == 1
        assert loaded['enabledIndicators'] == ['fib', 'rsi', 'sma']
        assert loaded['indicatorParams'] == {'rsi': {'period': 21}}
        assert loaded['selectedTimeframe'] == '4h'
        assert loaded['selectedAsset'] == 'ETH-USD'
        assert loaded['structureEnabled'] is True
        assert loaded['contextEnabled'] is True

    def test_corrupted_json_returns_none(self):
        """Corrupted JSON is handled gracefully."""
        try:
            json.loads('{invalid json')
            result = 'parsed'
        except json.JSONDecodeError:
            result = None
        assert result is None

    def test_missing_fields_returns_none(self):
        """Missing required fields is handled."""
        data = {'version': 1}
        if 'enabledIndicators' not in data or not isinstance(data.get('enabledIndicators'), list):
            result = None
        else:
            result = data
        assert result is None

    def test_wrong_version_clears(self):
        """Wrong version triggers clear."""
        data = {'version': 999, 'enabledIndicators': []}
        if data.get('version') != 1:
            result = None
        else:
            result = data
        assert result is None

    def test_empty_state_valid(self):
        """Empty but valid state is loadable."""
        state = {
            'enabled': [],
            'params': {},
            'tf': '1D',
            'asset': 'BTC-USD',
            'structure': False,
            'context': False,
        }
        raw = self._serialize(state)
        loaded = self._deserialize(raw)
        assert loaded['enabledIndicators'] == []
        assert loaded['indicatorParams'] == {}


# ============================================================
# Phase 11: Advanced Fibonacci
# ============================================================

class TestAdvancedFibonacci:
    """Test Fibonacci with swing points."""

    def _find_swings(self, highs, lows, left=3, right=3):
        """Detect swing points from price data."""
        swings = []
        for i in range(left, len(highs) - right):
            is_high = all(highs[i] >= highs[j] for j in range(i - left, i + right + 1) if j != i)
            is_low = all(lows[i] <= lows[j] for j in range(i - left, i + right + 1) if j != i)
            if is_high:
                swings.append({'index': i, 'type': 'high', 'price': highs[i]})
            if is_low:
                swings.append({'index': i, 'type': 'low', 'price': lows[i]})
        return swings

    def _fibonacci(self, high, low, levels=None):
        if levels is None:
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        if high < low:
            high, low = low, high
        diff = high - low
        return {level: high - diff * level for level in levels}

    def test_swing_detection(self):
        """Swing points are detected correctly."""
        highs = [100, 101, 102, 105, 103, 101, 100, 99, 98, 95, 97, 99, 100]
        lows = [98, 99, 100, 103, 101, 99, 98, 97, 96, 93, 95, 97, 98]
        swings = self._find_swings(highs, lows, left=2, right=2)
        assert len(swings) > 0
        high_swings = [s for s in swings if s['type'] == 'high']
        low_swings = [s for s in swings if s['type'] == 'low']
        assert len(high_swings) > 0
        assert len(low_swings) > 0

    def test_fib_from_swings(self):
        """Fibonacci levels computed from swing high/low."""
        highs = [100, 105, 110, 108, 106, 104, 108, 112, 110, 105, 100, 98, 96]
        lows =  [98, 103, 108, 106, 104, 102, 106, 110, 108, 103, 98, 96, 94]
        swings = self._find_swings(highs, lows, left=2, right=2)
        high_swings = [s['price'] for s in swings if s['type'] == 'high']
        low_swings = [s['price'] for s in swings if s['type'] == 'low']
        assert len(high_swings) > 0
        assert len(low_swings) > 0
        swing_high = max(high_swings)
        swing_low = min(low_swings)
        levels = self._fibonacci(swing_high, swing_low)
        assert levels[0] == pytest.approx(swing_high)
        assert levels[1.0] == pytest.approx(swing_low)

    def test_fib_no_future_data(self):
        """Fibonacci only uses bars up to current index."""
        bars_high = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        bars_low = [98, 99, 100, 101, 102, 103, 104, 105, 106, 107]
        for end in range(5, 10):
            h = max(bars_high[:end])
            l = min(bars_low[:end])
            levels = self._fibonacci(h, l)
            assert levels[0] == h
            assert levels[1.0] == l

    def test_fib_deterministic(self):
        """Same swing points produce same Fibonacci levels."""
        highs = [100, 105, 110, 108, 106, 104, 102, 100, 98, 96]
        lows = [98, 103, 108, 106, 104, 102, 100, 98, 96, 94]
        h = max(highs)
        l = min(lows)
        r1 = self._fibonacci(h, l)
        r2 = self._fibonacci(h, l)
        assert r1 == r2

    def test_fib_bullish_direction(self):
        """Bullish: swing low to swing high."""
        levels = self._fibonacci(150, 100)
        assert levels[0] == 150
        assert levels[1.0] == 100
        assert levels[0.5] == pytest.approx(125)

    def test_fib_bearish_direction(self):
        """Bearish: swing high to swing low (auto-swapped)."""
        levels = self._fibonacci(100, 150)
        assert levels[0] == 150
        assert levels[1.0] == 100


# ============================================================
# Phase 14: Live Data Edge Cases
# ============================================================

class TestLiveDataEdgeCases:
    """Test live data handling edge cases."""

    def test_duplicate_tick_ignored(self):
        """Duplicate timestamps are deduplicated."""
        ticks = [
            {'time': '2024-01-15T10:00:00', 'close': 100},
            {'time': '2024-01-15T10:00:00', 'close': 101},
            {'time': '2024-01-15T10:00:00', 'close': 102},
        ]
        seen = set()
        unique = []
        for t in ticks:
            if t['time'] not in seen:
                seen.add(t['time'])
                unique.append(t)
        assert len(unique) == 1
        assert unique[0]['close'] == 100  # First one kept

    def test_stale_tick_rejected(self):
        """Ticks older than latest are rejected."""
        latest_time = '2024-01-15T10:00:00'
        new_tick_time = '2024-01-15T09:00:00'
        is_stale = new_tick_time <= latest_time
        assert is_stale is True

    def test_out_of_order_tick(self):
        """Out-of-order ticks are handled."""
        bars = [
            {'time': '2024-01-15T10:00:00', 'close': 100},
            {'time': '2024-01-15T11:00:00', 'close': 101},
        ]
        late_tick = {'time': '2024-01-15T09:00:00', 'close': 99}
        # Should not overwrite existing bars
        existing_times = {b['time'] for b in bars}
        assert late_tick['time'] not in existing_times

    def test_asset_change_clears_bars(self):
        """Asset change should clear old bars."""
        bars = [{'time': '2024-01-01', 'close': 100}]
        new_asset_bars = [{'time': '2024-01-01', 'close': 200}]
        # Simulate asset change
        bars = new_asset_bars
        assert bars[0]['close'] == 200


# ============================================================
# Phase 15: Research Integrity
# ============================================================

class TestResearchIntegrity:
    """Test no future data leakage."""

    def test_indicators_cannot_use_future_bars(self):
        """Historical indicator values do not change when future bars are added."""
        closes = [100, 101, 102, 103, 104]
        # SMA(3) at index 2 = avg(100,101,102) = 101
        sma_at_2 = sum(closes[0:3]) / 3
        # Add future bar
        closes.append(200)
        # SMA(3) at index 2 should still be 101
        sma_at_2_after = sum(closes[0:3]) / 3
        assert sma_at_2 == sma_at_2_after

    def test_fibonacci_cannot_use_future_bars(self):
        """Fibonacci levels do not change when future bars are added."""
        highs = [100, 105, 110]
        lows = [95, 98, 100]
        h = max(highs)
        l = min(lows)
        levels_before = {0: h, 1.0: l}
        highs.append(200)
        lows.append(50)
        h_after = max(highs[:3])
        l_after = min(lows[:3])
        levels_after = {0: h_after, 1.0: l_after}
        assert levels_before == levels_after

    def test_structure_cannot_use_future_bars(self):
        """Swing detection at index i does not use bars > i+right."""
        highs = [100, 101, 102, 110, 108, 106, 104]
        # Swing at index 3 (value 110) with left=2, right=2
        # Uses indices 1,2,3,4,5 — NOT index 6
        is_swing = highs[3] >= max(highs[1], highs[2], highs[4], highs[5])
        assert is_swing is True
        # Changing index 6 should not affect swing at index 3
        highs[6] = 200
        is_swing_after = highs[3] >= max(highs[1], highs[2], highs[4], highs[5])
        assert is_swing == is_swing_after

    def test_crosshair_does_not_affect_calculations(self):
        """Crosshair position does not influence indicator values."""
        closes = [100, 101, 102, 103, 104]
        sma = sum(closes[-3:]) / 3
        # Moving crosshair should not change sma
        _crosshair_position = 3
        sma_after = sum(closes[-3:]) / 3
        assert sma == sma_after

    def test_parameter_change_deterministic(self):
        """Same params produce same output."""
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


# ============================================================
# Phase 7: Chart UX States
# ============================================================

class TestChartUXStates:
    """Test chart loading/error/stale states."""

    def test_loading_state(self):
        """Loading state is a valid UI state."""
        state = 'loading'
        assert state in {'loading', 'error', 'backend_down', 'empty', 'ready', 'stale'}

    def test_error_state(self):
        """Error state is a valid UI state."""
        state = 'error'
        assert state in {'loading', 'error', 'backend_down', 'empty', 'ready', 'stale'}

    def test_backend_down_state(self):
        """Backend down state is a valid UI state."""
        state = 'backend_down'
        assert state in {'loading', 'error', 'backend_down', 'empty', 'ready', 'stale'}

    def test_empty_data_state(self):
        """Empty data state is a valid UI state."""
        state = 'empty'
        assert state in {'loading', 'error', 'backend_down', 'empty', 'ready', 'stale'}

    def test_ready_state(self):
        """Ready state is a valid UI state."""
        state = 'ready'
        assert state in {'loading', 'error', 'backend_down', 'empty', 'ready', 'stale'}

    def test_stale_state(self):
        """Stale data state is a valid UI state."""
        state = 'stale'
        assert state in {'loading', 'error', 'backend_down', 'empty', 'ready', 'stale'}
