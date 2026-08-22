"""M24.1 Production Verification Tests."""
from __future__ import annotations

from aurora.features.structure import (
    MarketRegime,
    SRLevel,
    StructureBreak,
    SwingPoint,
    SwingType,
    aggregate_to_higher_timeframe,
    analyze_structure,
    analyze_structure_multi_timeframe,
    classify_market_regime_with_confidence,
    detect_structure_breaks,
    detect_support_resistance,
    detect_swing_points,
)


class TestOHLCNormalization:
    def test_basic_ohlc_analysis(self):
        result = analyze_structure(
            [10, 12, 11, 14, 13, 16, 15],
            [8, 10, 9, 11, 10, 13, 12],
            [9, 11, 10, 13, 11, 15, 14],
        )
        assert len(result["swings"]) > 0
        assert isinstance(result["regime"], MarketRegime)

    def test_empty_ohlc(self):
        result = analyze_structure([], [], [])
        assert result["swings"] == []
        assert result["breaks"] == []

    def test_single_bar(self):
        result = analyze_structure([100], [90], [95])
        assert isinstance(result["swings"], list)

    def test_all_fields_present(self):
        result = analyze_structure(
            [10, 12, 11, 14, 13, 16, 15, 18, 17],
            [8, 10, 9, 11, 10, 13, 12, 15, 14],
            [9, 11, 10, 13, 11, 15, 14, 17, 16],
        )
        expected = {
            "swings", "classified", "breaks",
            "support_resistance", "liquidity", "regime", "regime_confidence",
        }
        assert expected == set(result.keys())


class TestTimestampNormalization:
    def test_daily_aggregation(self):
        ts = [
            "2024-01-01T00:00:00Z",
            "2024-01-02T00:00:00Z",
            "2024-01-03T00:00:00Z",
        ]
        r = aggregate_to_higher_timeframe(
            ts, [100, 101, 102], [105, 106, 107],
            [95, 96, 97], [102, 103, 104], [1000, 1100, 1200], 1440,
        )
        assert len(r["timestamps"]) > 0

    def test_intraday_aggregation(self):
        ts = [f"2024-01-01T09:{30 + i}:00Z" for i in range(6)]
        opens = [100 + i for i in range(6)]
        r = aggregate_to_higher_timeframe(
            ts, opens, [o + 1 for o in opens],
            [o - 1 for o in opens], [o + 0.5 for o in opens],
            [100 * (i + 1) for i in range(6)], 5,
        )
        assert len(r["timestamps"]) <= 6
        assert len(r["opens"]) == len(r["timestamps"])

    def test_empty_timestamps(self):
        r = aggregate_to_higher_timeframe([], [], [], [], [], [], 60)
        assert r["timestamps"] == []


class TestInvalidCandleRejection:
    def test_nan_in_highs(self):
        highs = [10, float("nan"), 11, 14, 13]
        lows = [8, 10, 9, 11, 10]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        assert isinstance(swings, list)

    def test_zero_prices(self):
        result = analyze_structure([0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0])
        assert result["swings"] == []

    def test_negative_prices(self):
        result = analyze_structure(
            [-10, -8, -9, -7, -6], [-12, -10, -11, -9, -8], [-11, -9, -10, -8, -7],
        )
        assert isinstance(result["swings"], list)


class TestStructureOverlayData:
    def test_swing_fields(self):
        swings = detect_swing_points(
            [10, 12, 11, 14, 13, 16, 15],
            [8, 10, 9, 11, 10, 13, 12], left=2, right=2,
        )
        for sw in swings:
            assert isinstance(sw, SwingPoint)
            assert isinstance(sw.index, int)
            assert isinstance(sw.price, (int, float))
            assert isinstance(sw.strength, float)
            assert isinstance(sw.confirmed, bool)

    def test_break_fields(self):
        highs = [10, 12, 11, 14, 13, 16, 15]
        lows = [8, 10, 9, 11, 10, 13, 12]
        closes = [9, 11, 10, 13, 11, 15, 14]
        swings = detect_swing_points(highs, lows, left=1, right=1)
        breaks = detect_structure_breaks(highs, lows, closes, swings, left=1, right=1)
        for br in breaks:
            assert isinstance(br, StructureBreak)
            assert isinstance(br.strength, float)
            assert isinstance(br.is_choch, bool)

    def test_sr_fields(self):
        swings = [
            SwingPoint(0, 100.0, SwingType.HIGH),
            SwingPoint(2, 100.5, SwingType.HIGH),
            SwingPoint(4, 80.0, SwingType.LOW),
            SwingPoint(6, 80.3, SwingType.LOW),
        ]
        zeros = [0.0] * 10
        result = detect_support_resistance(zeros, zeros, zeros, swings)
        for sr in result:
            assert isinstance(sr, SRLevel)
            assert sr.touches >= 2
            assert isinstance(sr.active, bool)


class TestRegimeConfidence:
    def test_confidence_range(self):
        regime, conf = classify_market_regime_with_confidence(
            [
                SwingPoint(0, 10.0, SwingType.HIGH),
                SwingPoint(1, 8.0, SwingType.LOW),
                SwingPoint(2, 12.0, SwingType.HIGH),
                SwingPoint(3, 9.0, SwingType.LOW),
            ],
            [11.0] * 20,
        )
        assert 0.0 <= conf <= 1.0
        assert isinstance(regime, MarketRegime)

    def test_empty_swings(self):
        regime, conf = classify_market_regime_with_confidence([], [])
        assert regime == MarketRegime.RANGING
        assert conf == 0.0


class TestMultiTimeframe:
    def test_analyze_multi_timeframe(self):
        n = 100
        ts = [f"2024-01-01T{i:02d}:00:00Z" for i in range(n)]
        closes = [100.0 + (i % 20) for i in range(n)]
        r = analyze_structure_multi_timeframe(
            ts, [c - 0.5 for c in closes], [c + 1.0 for c in closes],
            [c - 1.0 for c in closes], closes, [1000.0 + i * 10 for i in range(n)],
            timeframes_minutes=[5, 15],
        )
        assert "5m" in r
        assert "15m" in r
        for tf_result in r.values():
            assert "swings" in tf_result
            assert "regime" in tf_result


class TestDeterminism:
    def test_same_input_same_output(self):
        highs = [10, 12, 11, 14, 13, 16, 15, 18, 17]
        lows = [8, 10, 9, 11, 10, 13, 12, 15, 14]
        closes = [9, 11, 10, 13, 11, 15, 14, 17, 16]
        r1 = analyze_structure(highs, lows, closes)
        r2 = analyze_structure(highs, lows, closes)
        assert r1 == r2
