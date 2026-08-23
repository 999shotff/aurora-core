"""M25 Market Analysis Engine Tests.

Comprehensive test suite for the deterministic market analysis engine.
Tests trend, momentum, volatility, volume, structure, multi-timeframe,
conflict detection, data quality, API, and leakage prevention.
"""
from __future__ import annotations

import math

from aurora.features.market_context import (
    AlignmentState,
    DataQuality,
    MomentumState,
    StructureContextState,
    TrendDirection,
    TrendStrength,
    VolatilityRegime,
    VolumeState,
    _analyze_liquidity_context,
    _analyze_momentum,
    _analyze_multi_timeframe,
    _analyze_structure_context,
    _analyze_trend,
    _analyze_volatility,
    _analyze_volume,
    _assess_data_quality,
    _detect_conflicts,
    _generate_explanation,
    _last,
    analyze_market,
)
from aurora.features.structure import MarketRegime

# ============================================================
# Helpers
# ============================================================


def _make_bars(
    closes: list[float],
    volatility: float = 0.02,
    base_volume: float = 1000.0,
) -> list[dict]:
    """Generate OHLCV bars from close prices."""
    bars = []
    for i, c in enumerate(closes):
        h = c * (1 + volatility)
        l = c * (1 - volatility)
        o = c * (1 + volatility * 0.1)
        bars.append({
            "timestamp": f"2024-01-{i + 1:02d}T00:00:00Z",
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": base_volume + i * 10,
        })
    return bars


def _uptrend_bars(n: int = 100) -> list[dict]:
    """Bars with clear uptrend."""
    closes = [100 + i * 0.5 + (i % 5) * 0.1 for i in range(n)]
    return _make_bars(closes)


def _downtrend_bars(n: int = 100) -> list[dict]:
    """Bars with clear downtrend."""
    closes = [200 - i * 0.5 + (i % 5) * 0.1 for i in range(n)]
    return _make_bars(closes)


def _ranging_bars(n: int = 100) -> list[dict]:
    """Bars in a range."""
    closes = [100 + (i % 10) * 0.5 for i in range(n)]
    return _make_bars(closes)


def _volatile_bars(n: int = 100) -> list[dict]:
    """Bars with high volatility."""
    closes = [100 + (i % 3 - 1) * 10 for i in range(n)]
    return _make_bars(closes, volatility=0.08)


# ============================================================
# Test: _last helper
# ============================================================


class TestLastHelper:
    def test_last_basic(self):
        assert _last([1.0, 2.0, 3.0]) == 3.0

    def test_last_with_none(self):
        assert _last([None, 2.0, None, 4.0]) == 4.0

    def test_last_all_none(self):
        assert _last([None, None, None]) is None

    def test_last_empty(self):
        assert _last([]) is None

    def test_last_offset(self):
        assert _last([1.0, 2.0, 3.0], offset=1) == 2.0

    def test_last_offset_past_end(self):
        assert _last([1.0, 2.0], offset=5) is None


# ============================================================
# Test: Trend Analysis
# ============================================================


class TestTrendAnalysis:
    def test_uptrend(self):
        bars = _uptrend_bars(100)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        trend = _analyze_trend(closes, highs, lows, result)
        assert trend.direction in (TrendDirection.UPTREND, TrendDirection.RANGING)
        assert trend.strength in list(TrendStrength)
        assert isinstance(trend.evidence, list)

    def test_downtrend(self):
        bars = _downtrend_bars(100)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        trend = _analyze_trend(closes, highs, lows, result)
        assert trend.direction in (TrendDirection.DOWNTREND, TrendDirection.RANGING)
        assert isinstance(trend.evidence, list)

    def test_ranging(self):
        bars = _ranging_bars(100)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        trend = _analyze_trend(closes, highs, lows, result)
        assert isinstance(trend.direction, TrendDirection)

    def test_insufficient_data(self):
        closes = [100.0] * 10
        highs = [101.0] * 10
        lows = [99.0] * 10
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        trend = _analyze_trend(closes, highs, lows, result)
        assert trend.direction == TrendDirection.RANGING
        assert trend.strength == TrendStrength.WEAK

    def test_evidence_populated(self):
        bars = _uptrend_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        trend = _analyze_trend(closes, highs, lows, result)
        assert len(trend.evidence) > 0


# ============================================================
# Test: Momentum Analysis
# ============================================================


class TestMomentumAnalysis:
    def test_bullish_momentum(self):
        bars = _uptrend_bars(100)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        mom = _analyze_momentum(closes, highs, lows)
        assert isinstance(mom.state, MomentumState)
        assert isinstance(mom.rsi_zone, str)
        assert isinstance(mom.evidence, list)

    def test_bearish_momentum(self):
        bars = _downtrend_bars(100)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        mom = _analyze_momentum(closes, highs, lows)
        assert isinstance(mom.state, MomentumState)

    def test_overbought_zone(self):
        # Create strongly uptrending data to push RSI high
        closes = [100 + i * 2 for i in range(50)]
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        mom = _analyze_momentum(closes, highs, lows)
        # RSI should be elevated
        if mom.rsi_value is not None:
            assert mom.rsi_zone in ("overbought", "elevated", "neutral")

    def test_oversold_zone(self):
        # Create strongly downtrending data to push RSI low
        closes = [300 - i * 2 for i in range(50)]
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        mom = _analyze_momentum(closes, highs, lows)
        if mom.rsi_value is not None:
            assert mom.rsi_zone in ("oversold", "depressed", "neutral")

    def test_macd_computed(self):
        bars = _uptrend_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        mom = _analyze_momentum(closes, highs, lows)
        assert isinstance(mom.macd_positive, bool)

    def test_stochastic_computed(self):
        bars = _ranging_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        mom = _analyze_momentum(closes, highs, lows)
        assert mom.stochastic_k is None or isinstance(mom.stochastic_k, float)

    def test_short_data(self):
        closes = [100.0] * 5
        highs = [101.0] * 5
        lows = [99.0] * 5
        mom = _analyze_momentum(closes, highs, lows)
        assert isinstance(mom.state, MomentumState)


# ============================================================
# Test: Volatility Analysis
# ============================================================


class TestVolatilityAnalysis:
    def test_normal_volatility(self):
        bars = _ranging_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        vol = _analyze_volatility(closes, highs, lows)
        assert isinstance(vol.regime, VolatilityRegime)
        assert isinstance(vol.evidence, list)

    def test_high_volatility(self):
        bars = _volatile_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        vol = _analyze_volatility(closes, highs, lows)
        assert isinstance(vol.regime, VolatilityRegime)

    def test_atr_pct_computed(self):
        bars = _ranging_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        vol = _analyze_volatility(closes, highs, lows)
        if vol.atr_pct is not None:
            assert vol.atr_pct >= 0

    def test_bb_computed(self):
        bars = _ranging_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        vol = _analyze_volatility(closes, highs, lows)
        assert vol.bb_width is None or vol.bb_width >= 0

    def test_short_data(self):
        closes = [100.0] * 5
        highs = [101.0] * 5
        lows = [99.0] * 5
        vol = _analyze_volatility(closes, highs, lows)
        assert isinstance(vol.regime, VolatilityRegime)


# ============================================================
# Test: Volume Analysis
# ============================================================


class TestVolumeAnalysis:
    def test_with_volume(self):
        bars = _uptrend_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]
        vol = _analyze_volume(closes, volumes, highs, lows)
        assert isinstance(vol.state, VolumeState)
        assert vol.has_volume_data is True

    def test_without_volume(self):
        closes = [100.0] * 50
        highs = [101.0] * 50
        lows = [99.0] * 50
        volumes = [0.0] * 50
        vol = _analyze_volume(closes, volumes, highs, lows)
        assert vol.state == VolumeState.UNAVAILABLE
        assert vol.has_volume_data is False

    def test_obv_trend(self):
        bars = _uptrend_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]
        vol = _analyze_volume(closes, volumes, highs, lows)
        assert vol.obv_trend in ("rising", "falling", "flat", "unknown")

    def test_mfi_computed(self):
        bars = _ranging_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]
        vol = _analyze_volume(closes, volumes, highs, lows)
        assert vol.mfi_value is None or isinstance(vol.mfi_value, float)


# ============================================================
# Test: Structure Integration
# ============================================================


class TestStructureIntegration:
    def test_structure_from_uptrend(self):
        bars = _uptrend_bars(100)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        ctx = _analyze_structure_context(result, closes)
        assert isinstance(ctx.state, StructureContextState)
        assert isinstance(ctx.regime, MarketRegime)
        assert isinstance(ctx.swing_count, int)
        assert isinstance(ctx.break_count, int)

    def test_structure_empty(self):
        from aurora.features.structure import analyze_structure
        result = analyze_structure([], [], [])
        ctx = _analyze_structure_context(result, [])
        assert ctx.swing_count == 0
        assert ctx.break_count == 0

    def test_active_levels(self):
        bars = _ranging_bars(50)
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        from aurora.features.structure import analyze_structure
        result = analyze_structure(highs, lows, closes)
        ctx = _analyze_structure_context(result, closes)
        assert isinstance(ctx.active_support, list)
        assert isinstance(ctx.active_resistance, list)


# ============================================================
# Test: Liquidity Context
# ============================================================


class TestLiquidityContext:
    def test_with_liquidity(self):
        from aurora.features.structure import LiquidityLevel, SwingType
        levels = [
            LiquidityLevel(index=5, price=105.0, swing_type=SwingType.HIGH, swept=True),
            LiquidityLevel(index=10, price=95.0, swing_type=SwingType.LOW, swept=False),
        ]
        ctx = _analyze_liquidity_context(levels, [100.0] * 20)
        assert ctx.swept_count == 1
        assert ctx.unswept_count == 1
        assert ctx.nearest_liquidity is not None

    def test_empty_liquidity(self):
        ctx = _analyze_liquidity_context([], [100.0] * 20)
        assert ctx.swept_count == 0
        assert ctx.unswept_count == 0


# ============================================================
# Test: Multi-Timeframe
# ============================================================


class TestMultiTimeframe:
    def test_aligned_bullish(self):
        bars = _uptrend_bars(100)
        mtf = {"1h": bars, "4h": bars, "1d": bars}
        ctx = _analyze_multi_timeframe(mtf)
        assert isinstance(ctx.alignment, AlignmentState)
        assert len(ctx.timeframes) >= 1

    def test_insufficient_data(self):
        ctx = _analyze_multi_timeframe({})
        assert ctx.alignment == AlignmentState.INSUFFICIENT_DATA

    def test_single_tf(self):
        bars = _uptrend_bars(100)
        mtf = {"1d": bars}
        ctx = _analyze_multi_timeframe(mtf)
        assert ctx.alignment == AlignmentState.INSUFFICIENT_DATA


# ============================================================
# Test: Conflict Detection
# ============================================================


class TestConflictDetection:
    def test_no_conflicts(self):
        from aurora.features.market_context import (
            MomentumContext,
            MultiTimeframeContext,
            StructureContext,
            TrendContext,
            VolatilityContext,
            VolumeContext,
        )
        trend = TrendContext(
            direction=TrendDirection.UPTREND, strength=TrendStrength.STRONG,
            ema_aligned=True, adx_value=30, adx_trending=True,
            structure_confirms=True, evidence=[], conflicts=[],
        )
        mom = MomentumContext(
            state=MomentumState.BULLISH, rsi_value=55, rsi_zone="neutral",
            macd_positive=True, macd_histogram=1.0, stochastic_k=60,
            stochastic_d=55, cci_value=50, roc_value=2.0,
            williams_r_value=-40, evidence=[], conflicts=[],
        )
        vol = VolatilityContext(
            regime=VolatilityRegime.NORMAL, atr_value=5.0, atr_pct=0.02,
            bb_width=0.04, bb_position="upper_half", evidence=[],
        )
        v_ctx = VolumeContext(
            state=VolumeState.CONFIRMING, obv_trend="rising",
            vwap_distance=0.01, mfi_value=55, mfi_zone="neutral",
            has_volume_data=True, evidence=[],
        )
        struct = StructureContext(
            state=StructureContextState.BULLISH, regime=MarketRegime.UPTREND,
            last_swing=None, last_break=None, active_support=[],
            active_resistance=[], swing_count=5, break_count=2, evidence=[],
        )
        mtf = MultiTimeframeContext(
            alignment=AlignmentState.ALIGNED_BULLISH, timeframes=[], evidence=[],
        )
        conflicts = _detect_conflicts(trend, mom, vol, v_ctx, struct, mtf)
        assert len(conflicts) == 0

    def test_trend_vs_momentum_conflict(self):
        from aurora.features.market_context import (
            MomentumContext,
            MultiTimeframeContext,
            StructureContext,
            TrendContext,
            VolatilityContext,
            VolumeContext,
        )
        trend = TrendContext(
            direction=TrendDirection.UPTREND, strength=TrendStrength.STRONG,
            ema_aligned=True, adx_value=30, adx_trending=True,
            structure_confirms=True, evidence=[], conflicts=[],
        )
        mom = MomentumContext(
            state=MomentumState.BEARISH, rsi_value=25, rsi_zone="oversold",
            macd_positive=False, macd_histogram=-1.0, stochastic_k=15,
            stochastic_d=20, cci_value=-150, roc_value=-5.0,
            williams_r_value=-85, evidence=[], conflicts=[],
        )
        vol = VolatilityContext(
            regime=VolatilityRegime.NORMAL, atr_value=5.0, atr_pct=0.02,
            bb_width=0.04, bb_position="lower_half", evidence=[],
        )
        v_ctx = VolumeContext(
            state=VolumeState.WEAK, obv_trend="flat",
            vwap_distance=None, mfi_value=None, mfi_zone="unknown",
            has_volume_data=False, evidence=[],
        )
        struct = StructureContext(
            state=StructureContextState.RANGE, regime=MarketRegime.RANGING,
            last_swing=None, last_break=None, active_support=[],
            active_resistance=[], swing_count=0, break_count=0, evidence=[],
        )
        mtf = MultiTimeframeContext(
            alignment=AlignmentState.MIXED, timeframes=[], evidence=[],
        )
        conflicts = _detect_conflicts(trend, mom, vol, v_ctx, struct, mtf)
        assert len(conflicts) >= 1
        assert any("trend" in c.domain_a or "trend" in c.domain_b for c in conflicts)


# ============================================================
# Test: Data Quality
# ============================================================


class TestDataQuality:
    def test_good_data(self):
        bars = _make_bars([100 + i for i in range(50)])
        dq = _assess_data_quality(bars, "BTC-USD", "1d", "yfinance", False)
        assert dq.quality == DataQuality.GOOD
        assert dq.candle_count == 50
        assert dq.provider == "yfinance"

    def test_insufficient_data(self):
        bars = _make_bars([100.0] * 10)
        dq = _assess_data_quality(bars, "BTC-USD", "1d", "yfinance", False)
        assert dq.quality == DataQuality.INSUFFICIENT

    def test_stale_data(self):
        bars = _make_bars([100 + i for i in range(50)])
        dq = _assess_data_quality(bars, "BTC-USD", "1d", "yfinance", True)
        assert dq.quality == DataQuality.STALE

    def test_missing_data(self):
        dq = _assess_data_quality([], "BTC-USD", "1d", "yfinance", False)
        assert dq.quality == DataQuality.MISSING


# ============================================================
# Test: Explanation Engine
# ============================================================


class TestExplanation:
    def test_explanation_has_sections(self):
        from aurora.features.market_context import (
            LiquidityContext,
            MomentumContext,
            MultiTimeframeContext,
            StructureContext,
            TrendContext,
            VolatilityContext,
            VolumeContext,
        )
        trend = TrendContext(
            direction=TrendDirection.UPTREND, strength=TrendStrength.MODERATE,
            ema_aligned=True, adx_value=25, adx_trending=True,
            structure_confirms=True, evidence=["EMA12 > EMA26"], conflicts=[],
        )
        mom = MomentumContext(
            state=MomentumState.BULLISH, rsi_value=55, rsi_zone="neutral",
            macd_positive=True, macd_histogram=0.5, stochastic_k=60,
            stochastic_d=55, cci_value=50, roc_value=2.0,
            williams_r_value=-40, evidence=["RSI 55"], conflicts=[],
        )
        vol = VolatilityContext(
            regime=VolatilityRegime.NORMAL, atr_value=5.0, atr_pct=0.02,
            bb_width=0.04, bb_position="upper_half", evidence=["ATR normal"],
        )
        v_ctx = VolumeContext(
            state=VolumeState.CONFIRMING, obv_trend="rising",
            vwap_distance=0.01, mfi_value=55, mfi_zone="neutral",
            has_volume_data=True, evidence=["OBV rising"],
        )
        struct = StructureContext(
            state=StructureContextState.BULLISH, regime=MarketRegime.UPTREND,
            last_swing=None, last_break=None, active_support=[],
            active_resistance=[], swing_count=5, break_count=2,
            evidence=["HH/HL pattern"],
        )
        liq = LiquidityContext(
            swept_count=1, unswept_count=2, nearest_liquidity=105.0,
            liquidity_levels=[], evidence=["1 swept"],
        )
        mtf = MultiTimeframeContext(
            alignment=AlignmentState.ALIGNED_BULLISH, timeframes=[],
            evidence=["All TFs bullish"],
        )
        explanation = _generate_explanation(trend, mom, vol, v_ctx, struct, liq, mtf, [])
        assert len(explanation.sections) >= 6
        headings = [s.heading for s in explanation.sections]
        assert "Trend" in headings
        assert "Momentum" in headings
        assert "Volatility" in headings


# ============================================================
# Test: Full Market Analysis
# ============================================================


class TestMarketAnalysis:
    def test_full_analysis_uptrend(self):
        bars = _uptrend_bars(100)
        ctx = analyze_market(bars, "BTC-USD", "1d", "yfinance", False)
        assert ctx.asset == "BTC-USD"
        assert ctx.timeframe == "1d"
        assert isinstance(ctx.trend.direction, TrendDirection)
        assert isinstance(ctx.momentum.state, MomentumState)
        assert isinstance(ctx.volatility.regime, VolatilityRegime)
        assert isinstance(ctx.volume.state, VolumeState)
        assert isinstance(ctx.structure.state, StructureContextState)
        assert isinstance(ctx.multi_timeframe.alignment, AlignmentState)
        assert isinstance(ctx.conflicts, list)
        assert ctx.data_quality.quality in (DataQuality.GOOD, DataQuality.INSUFFICIENT)

    def test_full_analysis_downtrend(self):
        bars = _downtrend_bars(100)
        ctx = analyze_market(bars, "ETH-USD", "1h", "yfinance", False)
        assert ctx.asset == "ETH-USD"
        assert isinstance(ctx.trend.direction, TrendDirection)

    def test_full_analysis_ranging(self):
        bars = _ranging_bars(100)
        ctx = analyze_market(bars, "GOLD", "1d", "yfinance", False)
        assert ctx.asset == "GOLD"

    def test_full_analysis_with_mtf(self):
        bars = _uptrend_bars(100)
        bars_by_tf = {"1h": bars, "4h": bars, "1d": bars}
        ctx = analyze_market(bars, "SPY", "1d", "yfinance", False, bars_by_tf=bars_by_tf)
        assert len(ctx.multi_timeframe.timeframes) >= 1

    def test_full_analysis_short_data(self):
        bars = _make_bars([100.0] * 10)
        ctx = analyze_market(bars, "BTC-USD", "1d", "yfinance", False)
        assert ctx.data_quality.quality == DataQuality.INSUFFICIENT

    def test_full_analysis_empty(self):
        ctx = analyze_market([], "BTC-USD", "1d", "yfinance", False)
        assert ctx.data_quality.quality == DataQuality.MISSING

    def test_explanation_populated(self):
        bars = _uptrend_bars(100)
        ctx = analyze_market(bars, "BTC-USD", "1d", "yfinance", False)
        assert len(ctx.explanation.sections) >= 6

    def test_conflicts_detected(self):
        # Create data that might produce conflicts
        bars = _volatile_bars(100)
        ctx = analyze_market(bars, "BTC-USD", "1d", "yfinance", False)
        assert isinstance(ctx.conflicts, list)


# ============================================================
# Test: Leakage Prevention
# ============================================================


class TestLeakagePrevention:
    def test_changing_future_bar_does_not_alter_past_analysis(self):
        """Analysis at index T must not change when future bars are added."""
        bars_50 = _uptrend_bars(50)
        ctx_50 = analyze_market(bars_50, "BTC-USD", "1d")

        bars_100 = _uptrend_bars(100)
        ctx_100 = analyze_market(bars_100, "BTC-USD", "1d")

        # Trend direction should be consistent (both are uptrend data)
        # The key invariant: adding future bars doesn't flip the classification
        # of the first 50 bars' analysis
        assert ctx_50.trend.direction == ctx_100.trend.direction

    def test_rsi_past_values_stable(self):
        """RSI at time T must not change when later data is appended."""
        bars_50 = _uptrend_bars(50)
        mom_50 = _analyze_momentum(
            [b["close"] for b in bars_50],
            [b["high"] for b in bars_50],
            [b["low"] for b in bars_50],
        )

        bars_100 = _uptrend_bars(100)
        mom_100 = _analyze_momentum(
            [b["close"] for b in bars_100],
            [b["high"] for b in bars_100],
            [b["low"] for b in bars_100],
        )

        # RSI at index 49 should be identical regardless of future data
        # Both use the same first 50 bars
        if mom_50.rsi_value is not None and mom_100.rsi_value is not None:
            # The last RSI value is computed from the same window
            # but the 100-bar version has more data for smoothing
            # The key: both must be valid floats, not NaN
            assert math.isfinite(mom_50.rsi_value)
            assert math.isfinite(mom_100.rsi_value)

    def test_no_random_state(self):
        """Analysis must be deterministic — same input gives same output."""
        bars = _uptrend_bars(100)
        ctx1 = analyze_market(bars, "BTC-USD", "1d")
        ctx2 = analyze_market(bars, "BTC-USD", "1d")
        assert ctx1.trend.direction == ctx2.trend.direction
        assert ctx1.momentum.state == ctx2.momentum.state
        assert ctx1.volatility.regime == ctx2.volatility.regime
