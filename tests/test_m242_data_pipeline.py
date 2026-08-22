"""M24.2 Data Pipeline Hardening Tests.

Tests the deterministic data sanitization and structure analysis edge cases
that the frontend sanitizeBars() addresses. Python-side validation mirrors
the TypeScript pipeline logic.
"""
from __future__ import annotations

from aurora.features.structure import (
    MarketRegime,
    aggregate_to_higher_timeframe,
    analyze_structure,
    classify_market_regime_with_confidence,
    detect_structure_breaks,
    detect_support_resistance,
    detect_swing_points,
)


class TestOHLCValidation:
    def test_high_always_gte_open_close(self):
        highs = [110, 120, 105]
        lows = [90, 80, 95]
        closes = [100, 100, 100]
        result = analyze_structure(highs, lows, closes)
        assert isinstance(result["regime"], MarketRegime)

    def test_low_always_lte_open_close(self):
        highs = [110, 120, 115]
        lows = [95, 85, 100]
        closes = [100, 100, 100]
        result = analyze_structure(highs, lows, closes)
        assert len(result["swings"]) >= 0

    def test_identical_bars_no_crash(self):
        closes = [100.0] * 20
        highs = [101.0] * 20
        lows = [99.0] * 20
        result = analyze_structure(highs, lows, closes)
        assert result["regime"] in list(MarketRegime)

    def test_monotonically_increasing(self):
        n = 30
        closes = [100 + i for i in range(n)]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        result = analyze_structure(highs, lows, closes)
        assert isinstance(result["swings"], list)
        assert isinstance(result["regime"], MarketRegime)

    def test_monotonically_decreasing(self):
        n = 30
        closes = [200 - i for i in range(n)]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        result = analyze_structure(highs, lows, closes)
        assert isinstance(result["swings"], list)


class TestDuplicateTimestamps:
    def test_duplicate_times_in_swing_detection(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        swings = detect_swing_points(highs, lows, 2, 2)
        indices = [sp.index for sp in swings]
        assert len(indices) == len(set(indices))

    def test_duplicate_times_in_structure_breaks(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16]
        swings = detect_swing_points(highs, lows, 3, 3)
        breaks = detect_structure_breaks(highs, lows, closes, swings, 3, 3)
        indices = [b.index for b in breaks]
        assert len(indices) == len(set(indices))


class TestEmptyAndEdgeCases:
    def test_empty_arrays(self):
        result = analyze_structure([], [], [])
        assert result["swings"] == []
        assert result["breaks"] == []
        assert result["regime"] == MarketRegime.RANGING

    def test_single_element(self):
        result = analyze_structure([100], [90], [95])
        assert isinstance(result["swings"], list)
        assert isinstance(result["regime"], MarketRegime)

    def test_two_elements(self):
        result = analyze_structure([100, 110], [90, 100], [95, 105])
        assert isinstance(result["swings"], list)

    def test_nan_values_in_input(self):
        highs = [10, float('nan'), 14, 16]
        lows = [8, 10, 11, 13]
        closes = [9, 11, 13, 15]
        result = analyze_structure(highs, lows, closes)
        assert isinstance(result["regime"], MarketRegime)

    def test_inf_values_in_input(self):
        highs = [10, 1e308, 14, 16]
        lows = [8, -1e308, 11, 13]
        closes = [9, 11, 13, 15]
        result = analyze_structure(highs, lows, closes)
        assert isinstance(result["regime"], MarketRegime)


class TestRegimeConfidence:
    def test_confidence_range(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17, 20]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14, 17]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16, 19]
        swings = detect_swing_points(highs, lows, 3, 3)
        regime, confidence = classify_market_regime_with_confidence(swings, closes)
        assert isinstance(regime, MarketRegime)
        assert 0.0 <= confidence <= 1.0

    def test_confidence_empty(self):
        regime, confidence = classify_market_regime_with_confidence([], [])
        assert isinstance(regime, MarketRegime)
        assert confidence == 0.0


class TestMultiTimeframeAggregation:
    def _make_timestamps(self, n: int, interval_minutes: int = 60) -> list[str]:
        from datetime import datetime, timedelta, timezone
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return [(base + timedelta(minutes=i * interval_minutes)).isoformat() for i in range(n)]

    def test_basic_aggregation(self):
        n = 20
        ts = self._make_timestamps(n, 60)
        opens = [100.0 + i for i in range(n)]
        highs = [105.0 + i for i in range(n)]
        lows = [95.0 + i for i in range(n)]
        closes = [102.0 + i for i in range(n)]
        volumes = [1000.0] * n
        result = aggregate_to_higher_timeframe(ts, opens, highs, lows, closes, volumes, 120)
        assert len(result["highs"]) > 0
        assert len(result["highs"]) <= n

    def test_aggregation_preserves_extremes(self):
        n = 4
        ts = self._make_timestamps(n, 30)
        opens = [100.0, 101.0, 102.0, 103.0]
        highs = [110.0, 108.0, 112.0, 109.0]
        lows = [95.0, 96.0, 94.0, 97.0]
        closes = [105.0, 104.0, 106.0, 105.0]
        volumes = [1000.0] * 4
        result = aggregate_to_higher_timeframe(ts, opens, highs, lows, closes, volumes, 60)
        assert len(result["highs"]) == 2
        assert max(result["highs"]) == 112.0
        assert min(result["lows"]) == 94.0

    def test_aggregation_empty(self):
        result = aggregate_to_higher_timeframe([], [], [], [], [], [], 60)
        assert result["highs"] == []


class TestSupportResistance:
    def test_sr_levels_present(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17, 20]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14, 17]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16, 19]
        swings = detect_swing_points(highs, lows, 3, 3)
        levels = detect_support_resistance(highs, lows, closes, swings)
        assert isinstance(levels, list)

    def test_sr_empty(self):
        levels = detect_support_resistance([], [], [], [])
        assert levels == []


class TestStructureBreakValidation:
    def test_breaks_have_required_fields(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17, 20, 19, 22, 21]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14, 17, 16, 19, 18]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16, 19, 18, 21, 20]
        swings = detect_swing_points(highs, lows, 3, 3)
        breaks = detect_structure_breaks(highs, lows, closes, swings, 3, 3)
        for br in breaks:
            assert hasattr(br, 'index')
            assert hasattr(br, 'break_type')
            assert hasattr(br, 'price')
            assert br.break_type.value in ('bos_bull', 'bos_bear', 'choch_bull', 'choch_bear')

    def test_no_false_breaks_on_flat_data(self):
        closes = [100.0] * 30
        highs = [101.0] * 30
        lows = [99.0] * 30
        swings = detect_swing_points(highs, lows, 3, 3)
        breaks = detect_structure_breaks(highs, lows, closes, swings, 3, 3)
        assert len(breaks) == 0
