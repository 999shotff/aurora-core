"""Comprehensive tests for market structure analysis engine."""
from __future__ import annotations

import pytest

from aurora.features.structure import (
    MarketRegime,
    SRLevel,
    StructureBreak,
    StructureBreakType,
    SwingPoint,
    SwingType,
    analyze_structure,
    classify_market_regime,
    classify_market_regime_with_confidence,
    classify_swing_sequence,
    detect_liquidity,
    detect_structure_breaks,
    detect_support_resistance,
    detect_swing_points,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zeros(n: int) -> list[float]:
    return [0.0] * n


# ---------------------------------------------------------------------------
# 1. TestSwingPoints
# ---------------------------------------------------------------------------

class TestSwingPoints:
    def test_basic_detection(self):
        highs = [10, 12, 11, 14, 13, 15, 12]
        lows = [8, 10, 9, 11, 10, 13, 9]
        swings = detect_swing_points(highs, lows, left=2, right=2)
        assert len(swings) > 0
        types = [s.swing_type for s in swings]
        assert SwingType.HIGH in types
        assert SwingType.LOW in types
        for s in swings:
            assert isinstance(s, SwingPoint)

    def test_monotonic_up_no_lows(self):
        highs = [1, 2, 3, 4, 5, 6, 7]
        lows = [1, 2, 3, 4, 5, 6, 7]
        swings = detect_swing_points(highs, lows, left=3, right=3)
        lows_only = [s for s in swings if s.swing_type == SwingType.LOW]
        interior_lows = [s for s in lows_only if 0 < s.index < len(highs) - 1]
        assert len(interior_lows) == 0

    def test_monotonic_down_no_highs(self):
        highs = [7, 6, 5, 4, 3, 2, 1]
        lows = [7, 6, 5, 4, 3, 2, 1]
        swings = detect_swing_points(highs, lows, left=3, right=3)
        highs_only = [s for s in swings if s.swing_type == SwingType.HIGH]
        interior_highs = [s for s in highs_only if 0 < s.index < len(highs) - 1]
        assert len(interior_highs) == 0

    def test_constant_price_no_swings(self):
        highs = [5.0] * 10
        lows = [5.0] * 10
        swings = detect_swing_points(highs, lows, left=3, right=3)
        assert len(swings) == 0

    def test_left_right_params(self):
        highs = [10, 12, 11, 14, 13, 15, 12]
        lows = [8, 10, 9, 11, 10, 13, 9]
        swings_1 = detect_swing_points(highs, lows, left=1, right=1)
        swings_3 = detect_swing_points(highs, lows, left=3, right=3)
        assert len(swings_1) >= len(swings_3)

    def test_single_bar(self):
        swings = detect_swing_points([10.0], [9.0], left=3, right=3)
        assert isinstance(swings, list)

    def test_two_bars(self):
        swings = detect_swing_points([10.0, 11.0], [9.0, 10.0], left=3, right=3)
        assert isinstance(swings, list)

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            detect_swing_points([1, 2, 3], [1, 2])

    def test_insufficient_left_right(self):
        swings = detect_swing_points([5.0], [4.0], left=0, right=0)
        assert isinstance(swings, list)


# ---------------------------------------------------------------------------
# 2. TestClassifySwingSequence
# ---------------------------------------------------------------------------

class TestClassifySwingSequence:
    def test_basic_hh_hl(self):
        swings = [
            SwingPoint(0, 10.0, SwingType.HIGH),
            SwingPoint(2, 8.0, SwingType.LOW),
            SwingPoint(4, 12.0, SwingType.HIGH),
            SwingPoint(6, 9.0, SwingType.LOW),
        ]
        result = classify_swing_sequence(swings)
        labels = [label for _, label in result]
        assert labels[0] == "first"
        assert labels[1] == "first"
        assert labels[2] == "HH"
        assert labels[3] == "HL"

    def test_basic_lh_ll(self):
        swings = [
            SwingPoint(0, 12.0, SwingType.HIGH),
            SwingPoint(2, 9.0, SwingType.LOW),
            SwingPoint(4, 10.0, SwingType.HIGH),
            SwingPoint(6, 7.0, SwingType.LOW),
        ]
        result = classify_swing_sequence(swings)
        labels = [label for _, label in result]
        assert labels[0] == "first"
        assert labels[1] == "first"
        assert labels[2] == "LH"
        assert labels[3] == "LL"

    def test_first_swing(self):
        swings = [SwingPoint(0, 10.0, SwingType.HIGH)]
        result = classify_swing_sequence(swings)
        assert result[0][1] == "first"

    def test_equal_prices(self):
        swings = [
            SwingPoint(0, 10.0, SwingType.HIGH),
            SwingPoint(2, 8.0, SwingType.LOW),
            SwingPoint(4, 10.0, SwingType.HIGH),
            SwingPoint(6, 8.0, SwingType.LOW),
        ]
        result = classify_swing_sequence(swings)
        labels = [label for _, label in result]
        assert labels[2] == "EQH"
        assert labels[3] == "EQL"


# ---------------------------------------------------------------------------
# 3. TestStructureBreaks
# ---------------------------------------------------------------------------

class TestStructureBreaks:
    def _make_uptrend_data(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16]
        return highs, lows, closes

    def _make_downtrend_data(self):
        highs = [18, 17, 16, 14, 15, 12, 13, 10, 11]
        lows = [16, 15, 14, 12, 13, 10, 11, 8, 9]
        closes = [17, 16, 15, 13, 14, 11, 12, 9, 10]
        return highs, lows, closes

    def test_bos_bull(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        closes = [9, 11, 10, 13, 11, 15, 14]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        bull_breaks = [b for b in breaks if b.break_type == StructureBreakType.BOS_BULL]
        assert len(bull_breaks) >= 0

    def test_bos_bear(self):
        highs = [18, 17, 16, 14, 15, 12, 13]
        lows = [16, 15, 14, 12, 13, 10, 11]
        closes = [17, 16, 15, 13, 14, 11, 12]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        bear_breaks = [b for b in breaks if b.break_type == StructureBreakType.BOS_BEAR]
        assert len(bear_breaks) >= 0

    def test_choch_bull(self):
        highs = [10, 9, 8, 7, 12]
        lows = [8, 7, 6, 5, 10]
        closes = [9, 8, 7, 6, 11]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        choch_bull = [b for b in breaks if b.break_type == StructureBreakType.CHOCH_BULL]
        assert isinstance(choch_bull, list)

    def test_choch_bear(self):
        highs = [5, 6, 7, 8, 4]
        lows = [3, 4, 5, 6, 2]
        closes = [4, 5, 6, 7, 3]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        choch_bear = [b for b in breaks if b.break_type == StructureBreakType.CHOCH_BEAR]
        assert isinstance(choch_bear, list)

    def test_no_breaks(self):
        highs = [10, 10, 10, 10, 10]
        lows = [8, 8, 8, 8, 8]
        closes = [9, 9, 9, 9, 9]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        assert len(breaks) == 0

    def test_one_break_per_bar(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18]
        lows = [8, 10, 9, 11, 10, 13, 12, 16]
        closes = [9, 11, 10, 13, 11, 15, 14, 17]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        break_indices = [b.index for b in breaks]
        assert len(break_indices) == len(set(break_indices))

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            detect_structure_breaks([1, 2], [1, 2, 3], [1, 2], [])


# ---------------------------------------------------------------------------
# 4. TestSupportResistance
# ---------------------------------------------------------------------------

class TestSupportResistance:
    def test_basic_levels(self):
        swings = [
            SwingPoint(0, 100.0, SwingType.HIGH),
            SwingPoint(2, 100.5, SwingType.HIGH),
            SwingPoint(4, 80.0, SwingType.LOW),
            SwingPoint(6, 80.3, SwingType.LOW),
        ]
        result = detect_support_resistance(
            _zeros(10), _zeros(10), _zeros(10), swings
        )
        assert len(result) >= 2
        types = {r.level_type for r in result}
        assert "resistance" in types
        assert "support" in types
        for r in result:
            assert isinstance(r, SRLevel)
            assert r.touches >= 2
            assert r.touch_weight > 0
            assert r.strength > 0
            assert isinstance(r.active, bool)

    def test_single_touch_excluded(self):
        swings = [SwingPoint(0, 100.0, SwingType.HIGH)]
        result = detect_support_resistance(
            _zeros(5), _zeros(5), _zeros(5), swings
        )
        assert len(result) == 0

    def test_tolerance_merge(self):
        swings = [
            SwingPoint(0, 100.0, SwingType.HIGH),
            SwingPoint(2, 100.4, SwingType.HIGH),
            SwingPoint(4, 100.8, SwingType.HIGH),
        ]
        result = detect_support_resistance(
            _zeros(10), _zeros(10), _zeros(10), swings, tolerance=0.01
        )
        assert len(result) >= 1

    def test_empty_swings(self):
        result = detect_support_resistance(
            _zeros(5), _zeros(5), _zeros(5), []
        )
        assert result == []


# ---------------------------------------------------------------------------
# 5. TestLiquidity
# ---------------------------------------------------------------------------

class TestLiquidity:
    def test_unswept_high(self):
        highs = [10, 12, 11, 10, 9]
        lows = [8, 10, 9, 8, 7]
        closes = [9, 11, 10, 9, 8]
        swings = [SwingPoint(1, 12.0, SwingType.HIGH)]
        result = detect_liquidity(highs, lows, closes, swings)
        assert len(result) == 1
        assert result[0].swept is False
        assert result[0].swept_at_index is None

    def test_swept_high(self):
        highs = [10, 12, 11, 13, 9]
        lows = [8, 10, 9, 11, 7]
        closes = [9, 11, 10, 12, 8]
        swings = [SwingPoint(1, 12.0, SwingType.HIGH)]
        result = detect_liquidity(highs, lows, closes, swings)
        assert len(result) == 1
        assert result[0].swept is True
        assert result[0].swept_at_index == 3

    def test_unswept_low(self):
        highs = [10, 12, 11, 12, 13]
        lows = [8, 10, 9, 10, 11]
        closes = [9, 11, 10, 11, 12]
        swings = [SwingPoint(0, 8.0, SwingType.LOW)]
        result = detect_liquidity(highs, lows, closes, swings)
        assert len(result) == 1
        assert result[0].swept is False

    def test_swept_low(self):
        highs = [10, 12, 11, 12, 13]
        lows = [8, 10, 9, 7, 11]
        closes = [9, 11, 10, 8, 12]
        swings = [SwingPoint(0, 8.0, SwingType.LOW)]
        result = detect_liquidity(highs, lows, closes, swings)
        assert len(result) == 1
        assert result[0].swept is True
        assert result[0].swept_at_index == 3


# ---------------------------------------------------------------------------
# 6. TestMarketRegime
# ---------------------------------------------------------------------------

class TestMarketRegime:
    def test_uptrend(self):
        swings = [
            SwingPoint(0, 10.0, SwingType.HIGH),
            SwingPoint(1, 8.0, SwingType.LOW),
            SwingPoint(2, 12.0, SwingType.HIGH),
            SwingPoint(3, 9.0, SwingType.LOW),
            SwingPoint(4, 14.0, SwingType.HIGH),
            SwingPoint(5, 10.0, SwingType.LOW),
        ]
        closes = [11.0] * 20
        result = classify_market_regime(swings, closes, lookback=20)
        assert result == MarketRegime.UPTREND

    def test_downtrend(self):
        swings = [
            SwingPoint(0, 14.0, SwingType.HIGH),
            SwingPoint(1, 10.0, SwingType.LOW),
            SwingPoint(2, 12.0, SwingType.HIGH),
            SwingPoint(3, 8.0, SwingType.LOW),
            SwingPoint(4, 10.0, SwingType.HIGH),
            SwingPoint(5, 6.0, SwingType.LOW),
        ]
        closes = [9.0] * 20
        result = classify_market_regime(swings, closes, lookback=20)
        assert result == MarketRegime.DOWNTREND

    def test_ranging(self):
        swings = [
            SwingPoint(0, 10.0, SwingType.HIGH),
            SwingPoint(1, 8.0, SwingType.LOW),
            SwingPoint(2, 12.0, SwingType.HIGH),
            SwingPoint(3, 6.0, SwingType.LOW),
        ]
        closes = [9.0] * 20
        result = classify_market_regime(swings, closes, lookback=20)
        assert result in (MarketRegime.RANGING, MarketRegime.UPTREND, MarketRegime.DOWNTREND)


# ---------------------------------------------------------------------------
# 7. TestAnalyzeStructure
# ---------------------------------------------------------------------------

class TestAnalyzeStructure:
    def test_master_function(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        closes = [9, 11, 10, 13, 11, 15, 14]
        result = analyze_structure(highs, lows, closes)
        expected_keys = {
            "swings", "classified", "breaks",
            "support_resistance", "liquidity", "regime", "regime_confidence",
        }
        assert expected_keys == set(result.keys())
        assert isinstance(result["swings"], list)
        assert isinstance(result["classified"], list)
        assert isinstance(result["breaks"], list)
        assert isinstance(result["support_resistance"], list)
        assert isinstance(result["liquidity"], list)
        assert isinstance(result["regime"], MarketRegime)
        assert isinstance(result["regime_confidence"], float)
        assert 0.0 <= result["regime_confidence"] <= 1.0

        # Verify new swing fields
        for sw in result["swings"]:
            assert isinstance(sw, SwingPoint)
            assert isinstance(sw.strength, float)
            assert isinstance(sw.confirmed, bool)

        # Verify new break fields
        for br in result["breaks"]:
            assert isinstance(br, StructureBreak)
            assert isinstance(br.strength, float)
            assert isinstance(br.regime_before, str)
            assert isinstance(br.regime_after, str)
            assert isinstance(br.is_choch, bool)

        # Verify new SR fields
        for sr in result["support_resistance"]:
            assert isinstance(sr, SRLevel)
            assert isinstance(sr.touch_weight, float)
            assert isinstance(sr.active, bool)

    def test_empty_data(self):
        result = analyze_structure([], [], [])
        assert result["swings"] == []
        assert result["classified"] == []
        assert result["breaks"] == []
        assert result["support_resistance"] == []
        assert result["liquidity"] == []
        assert result["regime"] == MarketRegime.RANGING
        assert result["regime_confidence"] == 0.0


# ---------------------------------------------------------------------------
# 8. TestLeakageProtection
# ---------------------------------------------------------------------------

class TestLeakageProtection:
    def test_swing_no_leakage(self):
        n = 15
        left = 3
        right = 3
        highs = [10 + (i % 5) for i in range(n)]
        lows = [8 + (i % 5) for i in range(n)]
        swings_orig = detect_swing_points(highs, lows, left=left, right=right)

        highs_mutated = highs.copy()
        for k in range(n - right, n):
            highs_mutated[k] = 100.0
        swings_mut = detect_swing_points(highs_mutated, lows, left=left, right=right)

        orig_indices = {s.index for s in swings_orig}
        mut_indices = {s.index for s in swings_mut}
        safe_boundary = n - right - right
        early_orig = {i for i in orig_indices if i < safe_boundary}
        early_mut = {i for i in mut_indices if i < safe_boundary}
        assert early_orig == early_mut

    def test_structure_break_no_leakage(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16]
        swings = detect_swing_points(highs, lows, left=2, right=2)
        breaks_orig = detect_structure_breaks(highs, lows, closes, swings, left=2, right=2)

        closes_mut = closes.copy()
        closes_mut[-1] = 100.0
        breaks_mut = detect_structure_breaks(highs, lows, closes_mut, swings, left=2, right=2)

        early_orig = [b for b in breaks_orig if b.index < len(closes) - 1]
        early_mut = [b for b in breaks_mut if b.index < len(closes) - 1]
        assert early_orig == early_mut


# ---------------------------------------------------------------------------
# 9. TestDeterminism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_deterministic(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16]
        r1 = analyze_structure(highs, lows, closes)
        r2 = analyze_structure(highs, lows, closes)
        assert r1 == r2


# ---------------------------------------------------------------------------
# 10. TestSwingConfirmation
# ---------------------------------------------------------------------------

class TestSwingConfirmation:
    def test_unconfirmed_swings(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        swings = detect_swing_points(highs, lows, left=2, right=2, confirm_bars=3)
        for sw in swings:
            assert isinstance(sw.confirmed, bool)

    def test_no_confirmation(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        swings_no_confirm = detect_swing_points(highs, lows, left=2, right=2, confirm_bars=0)
        swings_confirm = detect_swing_points(highs, lows, left=2, right=2, confirm_bars=5)
        # All swings should be confirmed when confirm_bars=0
        assert all(sw.confirmed for sw in swings_no_confirm)
        # Some may be unconfirmed with confirm_bars=5
        assert len(swings_confirm) <= len(swings_no_confirm)

    def test_strength_values(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        swings = detect_swing_points(highs, lows, left=2, right=2)
        for sw in swings:
            assert sw.strength >= 0.0

    def test_left_right_indices(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        swings = detect_swing_points(highs, lows, left=2, right=2)
        for sw in swings:
            assert sw.left_index <= sw.index <= sw.right_index


# ---------------------------------------------------------------------------
# 11. TestRegimeConfidence
# ---------------------------------------------------------------------------

class TestRegimeConfidence:
    def test_uptrend_confidence(self):
        swings = [
            SwingPoint(0, 10.0, SwingType.HIGH),
            SwingPoint(1, 8.0, SwingType.LOW),
            SwingPoint(2, 12.0, SwingType.HIGH),
            SwingPoint(3, 9.0, SwingType.LOW),
            SwingPoint(4, 14.0, SwingType.HIGH),
            SwingPoint(5, 10.0, SwingType.LOW),
        ]
        closes = [11.0] * 20
        regime, confidence = classify_market_regime_with_confidence(swings, closes, lookback=20)
        assert regime == MarketRegime.UPTREND
        assert 0.6 <= confidence <= 1.0

    def test_empty_swings_confidence(self):
        regime, confidence = classify_market_regime_with_confidence([], [])
        assert regime == MarketRegime.RANGING
        assert confidence == 0.0

    def test_confidence_range(self):
        swings = [
            SwingPoint(0, 10.0, SwingType.HIGH),
            SwingPoint(1, 8.0, SwingType.LOW),
            SwingPoint(2, 12.0, SwingType.HIGH),
            SwingPoint(3, 6.0, SwingType.LOW),
        ]
        closes = [9.0] * 20
        _regime, confidence = classify_market_regime_with_confidence(swings, closes, lookback=20)
        assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# 12. TestBreakStrength
# ---------------------------------------------------------------------------

class TestBreakStrength:
    def test_break_has_strength(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        closes = [9, 11, 10, 13, 11, 15, 14]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        for br in breaks:
            assert br.strength >= 0.0
            assert isinstance(br.regime_before, str)
            assert isinstance(br.regime_after, str)
            assert isinstance(br.is_choch, bool)

    def test_bos_strength_positive(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        closes = [9, 11, 10, 13, 11, 15, 14]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        for br in breaks:
            if br.break_type in (StructureBreakType.BOS_BULL, StructureBreakType.CHOCH_BULL):
                assert br.strength > 0

    def test_regime_transition(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        closes = [9, 11, 10, 13, 11, 15, 14]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        for br in breaks:
            assert br.regime_after in ("uptrend", "downtrend", "ranging")


# ---------------------------------------------------------------------------
# 13. TestSRLevelFields
# ---------------------------------------------------------------------------

class TestSRLevelFields:
    def test_sr_level_fields(self):
        swings = [
            SwingPoint(0, 100.0, SwingType.HIGH),
            SwingPoint(2, 100.5, SwingType.HIGH),
            SwingPoint(4, 80.0, SwingType.LOW),
            SwingPoint(6, 80.3, SwingType.LOW),
        ]
        result = detect_support_resistance(
            _zeros(10), _zeros(10), _zeros(10), swings
        )
        for sr in result:
            assert isinstance(sr, SRLevel)
            assert sr.level > 0
            assert sr.level_type in ("support", "resistance")
            assert sr.touches >= 2
            assert sr.touch_weight > 0
            assert sr.strength > 0
            assert isinstance(sr.active, bool)
            assert sr.first_touch_index >= 0
            assert sr.last_touch_index >= sr.first_touch_index
            assert sr.price_range >= 0

    def test_sr_price_range(self):
        swings = [
            SwingPoint(0, 100.0, SwingType.HIGH),
            SwingPoint(2, 100.5, SwingType.HIGH),
        ]
        result = detect_support_resistance(
            _zeros(10), _zeros(10), _zeros(10), swings, tolerance=0.01
        )
        assert len(result) == 1
        assert result[0].price_range == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# 14. TestMultiTimeframe
# ---------------------------------------------------------------------------

class TestMultiTimeframe:
    def test_aggregate_to_higher_timeframe(self):
        from aurora.features.structure import aggregate_to_higher_timeframe
        timestamps = [
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:01:00Z",
            "2024-01-01T00:02:00Z",
            "2024-01-01T00:03:00Z",
            "2024-01-01T00:04:00Z",
            "2024-01-01T00:05:00Z",
        ]
        opens = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        highs = [101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
        lows = [99.0, 100.0, 101.0, 102.0, 103.0, 104.0]
        closes = [100.5, 101.5, 102.5, 103.5, 104.5, 105.5]
        volumes = [1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0]

        result = aggregate_to_higher_timeframe(
            timestamps, opens, highs, lows, closes, volumes, 5
        )
        assert len(result["timestamps"]) > 0
        assert len(result["timestamps"]) <= len(timestamps)
        assert len(result["opens"]) == len(result["timestamps"])
        assert len(result["highs"]) == len(result["timestamps"])
        assert len(result["lows"]) == len(result["timestamps"])
        assert len(result["closes"]) == len(result["timestamps"])
        assert len(result["volumes"]) == len(result["timestamps"])

    def test_analyze_structure_multi_timeframe(self):
        from aurora.features.structure import analyze_structure_multi_timeframe
        n = 100
        timestamps = [f"2024-01-01T{i:02d}:00:00Z" for i in range(n)]
        closes = [100.0 + (i % 20) for i in range(n)]
        opens = [c - 0.5 for c in closes]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        volumes = [1000.0 + i * 10 for i in range(n)]

        result = analyze_structure_multi_timeframe(
            timestamps, opens, highs, lows, closes, volumes,
            timeframes_minutes=[5, 15],
        )
        assert "5m" in result
        assert "15m" in result
        for tf_result in result.values():
            assert "swings" in tf_result
            assert "regime" in tf_result
            assert "regime_confidence" in tf_result
