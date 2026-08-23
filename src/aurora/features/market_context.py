"""Deterministic Market Analysis Engine.

NO_DEPLOYMENT_SIGNAL — This module produces descriptive analytical context.
Nothing produced by this module constitutes a trading signal, buy/sell
recommendation, or claim of predictive power.

All outputs are derived from observable data. No future-data access.
Every output depends only on data at or before its timestamp.

Architecture:
  OHLCV → indicators → structure → market context → structured JSON → optional LLM

The LLM layer receives structured facts and cannot modify raw data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from aurora.features.indicators import (
    adx_dmi,
    atr,
    bollinger_bands,
    cci,
    ema_indicator,
    mfi,
    obv,
    roc,
    rsi,
    stochastic,
    vwap,
    williams_r,
)
from aurora.features.structure import (
    LiquidityLevel,
    MarketRegime,
    SRLevel,
    StructureBreak,
    SwingPoint,
    analyze_structure,
)

# ============================================================
# Enums
# ============================================================


class TrendDirection(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGING = "ranging"
    TRANSITION = "transition"


class TrendStrength(Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class MomentumState(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"


class VolatilityRegime(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXPANDING = "expanding"
    CONTRACTING = "contracting"


class VolumeState(Enum):
    CONFIRMING = "confirming"
    WEAK = "weak"
    MIXED = "mixed"
    DIVERGING = "diverging"
    UNAVAILABLE = "unavailable"


class StructureContextState(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGE = "range"
    TRANSITION = "transition"
    MIXED = "mixed"


class AlignmentState(Enum):
    ALIGNED_BULLISH = "aligned_bullish"
    ALIGNED_BEARISH = "aligned_bearish"
    MIXED = "mixed"
    CONFLICTING = "conflicting"
    INSUFFICIENT_DATA = "insufficient_data"


class DataQuality(Enum):
    GOOD = "good"
    STALE = "stale"
    INSUFFICIENT = "insufficient"
    MISSING = "missing"
    INVALID = "invalid"


# ============================================================
# Structured Context Dataclasses
# ============================================================


@dataclass(frozen=True)
class TrendContext:
    direction: TrendDirection
    strength: TrendStrength
    ema_aligned: bool
    adx_value: float | None
    adx_trending: bool
    structure_confirms: bool
    evidence: list[str]
    conflicts: list[str]


@dataclass(frozen=True)
class MomentumContext:
    state: MomentumState
    rsi_value: float | None
    rsi_zone: str
    macd_positive: bool
    macd_histogram: float | None
    stochastic_k: float | None
    stochastic_d: float | None
    cci_value: float | None
    roc_value: float | None
    williams_r_value: float | None
    evidence: list[str]
    conflicts: list[str]


@dataclass(frozen=True)
class VolatilityContext:
    regime: VolatilityRegime
    atr_value: float | None
    atr_pct: float | None
    bb_width: float | None
    bb_position: str
    evidence: list[str]


@dataclass(frozen=True)
class VolumeContext:
    state: VolumeState
    obv_trend: str
    vwap_distance: float | None
    mfi_value: float | None
    mfi_zone: str
    has_volume_data: bool
    evidence: list[str]


@dataclass(frozen=True)
class StructureContext:
    state: StructureContextState
    regime: MarketRegime
    last_swing: SwingPoint | None
    last_break: StructureBreak | None
    active_support: list[SRLevel]
    active_resistance: list[SRLevel]
    swing_count: int
    break_count: int
    evidence: list[str]


@dataclass(frozen=True)
class LiquidityContext:
    swept_count: int
    unswept_count: int
    nearest_liquidity: float | None
    liquidity_levels: list[LiquidityLevel]
    evidence: list[str]


@dataclass(frozen=True)
class TimeframeAnalysis:
    timeframe: str
    trend: TrendDirection
    structure: StructureContextState
    regime: MarketRegime
    momentum: MomentumState


@dataclass(frozen=True)
class MultiTimeframeContext:
    alignment: AlignmentState
    timeframes: list[TimeframeAnalysis]
    evidence: list[str]


@dataclass(frozen=True)
class ConflictItem:
    domain_a: str
    state_a: str
    domain_b: str
    state_b: str
    description: str


@dataclass(frozen=True)
class DataQualityContext:
    quality: DataQuality
    candle_count: int
    latest_timestamp: str | None
    provider: str
    stale: bool
    missing_fields: list[str]
    invalid_candles_removed: int
    timeframe: str
    asset: str


@dataclass(frozen=True)
class AnalysisExplanation:
    sections: list[ExplanationSection]


@dataclass(frozen=True)
class ExplanationSection:
    heading: str
    content: str
    evidence: list[str]


@dataclass(frozen=True)
class MarketContext:
    asset: str
    timeframe: str
    trend: TrendContext
    momentum: MomentumContext
    volatility: VolatilityContext
    volume: VolumeContext
    structure: StructureContext
    liquidity: LiquidityContext
    multi_timeframe: MultiTimeframeContext
    conflicts: list[ConflictItem]
    data_quality: DataQualityContext
    explanation: AnalysisExplanation


# ============================================================
# Last-value helper
# ============================================================


def _last(values: list[float | None], offset: int = 0) -> float | None:
    """Return last non-None value from a list, with optional offset from end."""
    idx = len(values) - 1 - offset
    while idx >= 0:
        if values[idx] is not None:
            return values[idx]
        idx -= 1
    return None


def _count_non_none(values: list[float | None]) -> int:
    return sum(1 for v in values if v is not None)


# ============================================================
# Trend Analysis (Phase 3)
# ============================================================


def _analyze_trend(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    structure_result: dict,
) -> TrendContext:
    """Classify trend direction, strength, and supporting evidence."""
    evidence: list[str] = []
    conflicts: list[str] = []

    n = len(closes)
    if n < 26:
        return TrendContext(
            direction=TrendDirection.RANGING,
            strength=TrendStrength.WEAK,
            ema_aligned=False,
            adx_value=None,
            adx_trending=False,
            structure_confirms=False,
            evidence=["Insufficient data for trend analysis (need >= 26 bars)"],
            conflicts=[],
        )

    # EMA alignment: EMA12 > EMA26 = bullish
    ema12 = ema_indicator(closes, 12)
    ema26 = ema_indicator(closes, 26)
    last_ema12 = _last(ema12)
    last_ema26 = _last(ema26)

    ema_aligned = False
    if last_ema12 is not None and last_ema26 is not None:
        ema_aligned = last_ema12 > last_ema26
        if ema_aligned:
            evidence.append(f"EMA12 ({last_ema12:.2f}) above EMA26 ({last_ema26:.2f})")
        else:
            evidence.append(f"EMA12 ({last_ema12:.2f}) below EMA26 ({last_ema26:.2f})")

    # ADX trend strength
    adx_data = adx_dmi(highs, lows, closes, 14)
    last_adx = _last(adx_data["adx"])
    last_plus_di = _last(adx_data["plus_di"])
    last_minus_di = _last(adx_data["minus_di"])

    adx_trending = False
    if last_adx is not None:
        adx_trending = last_adx > 20
        if last_adx > 25:
            evidence.append(f"ADX ({last_adx:.1f}) indicates strong trend")
        elif last_adx > 20:
            evidence.append(f"ADX ({last_adx:.1f}) indicates moderate trend")
        else:
            evidence.append(f"ADX ({last_adx:.1f}) indicates weak/no trend")

    # Structure classification
    regime = structure_result.get("regime", MarketRegime.RANGING)
    classified = structure_result.get("classified", [])

    hh_count = sum(1 for _, label in classified if label == "HH")
    hl_count = sum(1 for _, label in classified if label == "HL")
    lh_count = sum(1 for _, label in classified if label == "LH")
    ll_count = sum(1 for _, label in classified if label == "LL")

    structure_bullish = hh_count > 0 and hl_count > 0
    structure_bearish = lh_count > 0 and ll_count > 0

    if structure_bullish:
        evidence.append(f"Structure shows HH ({hh_count}) / HL ({hl_count}) pattern")
    elif structure_bearish:
        evidence.append(f"Structure shows LH ({lh_count}) / LL ({ll_count}) pattern")
    else:
        evidence.append("Structure shows no clear HH/HL or LH/LL dominance")

    # Composite direction
    bullish_signals = sum([
        ema_aligned,
        regime == MarketRegime.UPTREND,
        structure_bullish,
        last_plus_di is not None and last_minus_di is not None and last_plus_di > last_minus_di,
    ])
    bearish_signals = sum([
        not ema_aligned and last_ema12 is not None and last_ema26 is not None,
        regime == MarketRegime.DOWNTREND,
        structure_bearish,
        last_plus_di is not None and last_minus_di is not None and last_minus_di > last_plus_di,
    ])

    if bullish_signals >= 3:
        direction = TrendDirection.UPTREND
    elif bearish_signals >= 3:
        direction = TrendDirection.DOWNTREND
    elif bullish_signals >= 1 and bearish_signals >= 1:
        direction = TrendDirection.TRANSITION
    else:
        direction = TrendDirection.RANGING

    # Strength
    if last_adx is not None:
        if last_adx > 30:
            strength = TrendStrength.STRONG
        elif last_adx > 20:
            strength = TrendStrength.MODERATE
        else:
            strength = TrendStrength.WEAK
    else:
        strength = TrendStrength.WEAK

    # Conflicts
    if direction == TrendDirection.UPTREND and structure_bearish:
        conflicts.append("Trend bullish but structure shows bearish pattern")
    if direction == TrendDirection.DOWNTREND and structure_bullish:
        conflicts.append("Trend bearish but structure shows bullish pattern")
    if ema_aligned and regime == MarketRegime.DOWNTREND:
        conflicts.append("EMA alignment bullish but regime is downtrend")

    return TrendContext(
        direction=direction,
        strength=strength,
        ema_aligned=ema_aligned,
        adx_value=last_adx,
        adx_trending=adx_trending,
        structure_confirms=(direction == TrendDirection.UPTREND and structure_bullish) or
                           (direction == TrendDirection.DOWNTREND and structure_bearish),
        evidence=evidence,
        conflicts=conflicts,
    )


# ============================================================
# Momentum Analysis (Phase 4)
# ============================================================


def _analyze_momentum(
    closes: list[float],
    highs: list[float],
    lows: list[float],
) -> MomentumContext:
    """Classify momentum state from multiple oscillators."""
    evidence: list[str] = []
    conflicts: list[str] = []

    # RSI
    rsi_vals = rsi(closes, 14)
    rsi_val = _last(rsi_vals)
    rsi_zone = "neutral"
    if rsi_val is not None:
        if rsi_val > 70:
            rsi_zone = "overbought"
        elif rsi_val > 60:
            rsi_zone = "elevated"
        elif rsi_val < 30:
            rsi_zone = "oversold"
        elif rsi_val < 40:
            rsi_zone = "depressed"
        evidence.append(f"RSI(14) = {rsi_val:.1f} ({rsi_zone})")

    # MACD
    ema12 = ema_indicator(closes, 12)
    ema26 = ema_indicator(closes, 26)
    macd_line = []
    for i in range(len(closes)):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line.append(ema12[i] - ema26[i])
        else:
            macd_line.append(None)

    macd_valid = [v for v in macd_line if v is not None]
    signal_line = ema_indicator(macd_valid, 9) if len(macd_valid) >= 9 else []
    last_macd = _last(macd_line)
    last_signal = None
    if signal_line:
        last_signal = signal_line[-1] if signal_line[-1] is not None else None

    macd_positive = last_macd is not None and last_macd > 0
    macd_histogram = None
    if last_macd is not None and last_signal is not None:
        macd_histogram = last_macd - last_signal

    if last_macd is not None:
        evidence.append(f"MACD = {last_macd:.4f} ({'positive' if macd_positive else 'negative'})")
    if macd_histogram is not None:
        evidence.append(f"MACD histogram = {macd_histogram:.4f}")

    # Stochastic
    stoch = stochastic(highs, lows, closes)
    stoch_k = _last(stoch["k"])
    stoch_d = _last(stoch["d"])
    if stoch_k is not None:
        stoch_zone = "overbought" if stoch_k > 80 else "oversold" if stoch_k < 20 else "neutral"
        evidence.append(f"Stochastic %K = {stoch_k:.1f} ({stoch_zone})")

    # CCI
    cci_vals = cci(highs, lows, closes, 20)
    cci_val = _last(cci_vals)
    if cci_val is not None:
        cci_zone = "overbought" if cci_val > 100 else "oversold" if cci_val < -100 else "neutral"
        evidence.append(f"CCI(20) = {cci_val:.1f} ({cci_zone})")

    # ROC
    roc_vals = roc(closes, 12)
    roc_val = _last(roc_vals)
    if roc_val is not None:
        evidence.append(f"ROC(12) = {roc_val:.2f}%")

    # Williams %R
    wr_vals = williams_r(highs, lows, closes, 14)
    wr_val = _last(wr_vals)
    if wr_val is not None:
        wr_zone = "overbought" if wr_val > -20 else "oversold" if wr_val < -80 else "neutral"
        evidence.append(f"Williams %R = {wr_val:.1f} ({wr_zone})")

    # Composite momentum state
    bullish_count = 0
    bearish_count = 0
    extreme_count = 0

    if rsi_val is not None:
        if rsi_val > 50:
            bullish_count += 1
        elif rsi_val < 50:
            bearish_count += 1
        if rsi_val > 70 or rsi_val < 30:
            extreme_count += 1

    if macd_positive:
        bullish_count += 1
    else:
        bearish_count += 1

    if stoch_k is not None:
        if stoch_k > 50:
            bullish_count += 1
        elif stoch_k < 50:
            bearish_count += 1
        if stoch_k > 80 or stoch_k < 20:
            extreme_count += 1

    if cci_val is not None:
        if cci_val > 0:
            bullish_count += 1
        elif cci_val < 0:
            bearish_count += 1

    # Determine state
    if extreme_count >= 2 and rsi_val is not None:
        if rsi_val > 70:
            state = MomentumState.OVERBOUGHT
        elif rsi_val < 30:
            state = MomentumState.OVERSOLD
        elif bullish_count > bearish_count:
            state = MomentumState.BULLISH
        else:
            state = MomentumState.BEARISH
    elif bullish_count >= 3 and bearish_count == 0:
        state = MomentumState.BULLISH
    elif bearish_count >= 3 and bullish_count == 0:
        state = MomentumState.BEARISH
    elif bullish_count >= 1 and bearish_count >= 1:
        state = MomentumState.MIXED
    else:
        state = MomentumState.NEUTRAL

    # Conflicts
    if state == MomentumState.BULLISH and rsi_val is not None and rsi_val > 70:
        conflicts.append("Momentum bullish but RSI is overbought")
    if state == MomentumState.BEARISH and rsi_val is not None and rsi_val < 30:
        conflicts.append("Momentum bearish but RSI is oversold")
    if macd_positive and stoch_k is not None and stoch_k < 20:
        conflicts.append("MACD positive but Stochastic is oversold")

    return MomentumContext(
        state=state,
        rsi_value=rsi_val,
        rsi_zone=rsi_zone,
        macd_positive=macd_positive,
        macd_histogram=macd_histogram,
        stochastic_k=stoch_k,
        stochastic_d=stoch_d,
        cci_value=cci_val,
        roc_value=roc_val,
        williams_r_value=wr_val,
        evidence=evidence,
        conflicts=conflicts,
    )


# ============================================================
# Volatility Analysis (Phase 5)
# ============================================================


def _analyze_volatility(
    closes: list[float],
    highs: list[float],
    lows: list[float],
) -> VolatilityContext:
    """Classify volatility regime from ATR and Bollinger Bands."""
    evidence: list[str] = []

    # ATR
    atr_vals = atr(highs, lows, closes, 14)
    atr_val = _last(atr_vals)
    atr_pct = None
    last_close = closes[-1] if closes else None

    if atr_val is not None and last_close and last_close > 0:
        atr_pct = atr_val / last_close
        if atr_pct > 0.04:
            regime = VolatilityRegime.HIGH
        elif atr_pct < 0.01:
            regime = VolatilityRegime.LOW
        else:
            regime = VolatilityRegime.NORMAL
        evidence.append(f"ATR(14) = {atr_val:.2f} ({atr_pct:.2%} of price)")
    else:
        regime = VolatilityRegime.NORMAL
        evidence.append("ATR unavailable")

    # Bollinger Bands
    bb = bollinger_bands(closes, 20, 2.0)
    bb_upper = _last(bb["upper"])
    bb_lower = _last(bb["lower"])
    bb_middle = _last(bb["middle"])

    bb_width = None
    bb_position = "unknown"
    if bb_upper is not None and bb_lower is not None and bb_middle is not None and bb_middle > 0:
        bb_width = (bb_upper - bb_lower) / bb_middle
        if last_close is not None:
            if last_close > bb_upper:
                bb_position = "above_upper"
            elif last_close < bb_lower:
                bb_position = "below_lower"
            elif last_close > bb_middle:
                bb_position = "upper_half"
            else:
                bb_position = "lower_half"
        evidence.append(f"BB width = {bb_width:.4f}, price position: {bb_position}")

        # Expansion/contraction: compare current width to recent average
        bb_widths = []
        for i in range(len(closes)):
            if bb["upper"][i] is not None and bb["lower"][i] is not None and bb["middle"][i] is not None and bb["middle"][i] > 0:
                bb_widths.append((bb["upper"][i] - bb["lower"][i]) / bb["middle"][i])
        if len(bb_widths) >= 20:
            recent_avg = sum(bb_widths[-20:]) / 20
            if bb_width > recent_avg * 1.2:
                regime = VolatilityRegime.EXPANDING
                evidence.append("Bollinger width expanding above average")
            elif bb_width < recent_avg * 0.8:
                regime = VolatilityRegime.CONTRACTING
                evidence.append("Bollinger width contracting below average")

    return VolatilityContext(
        regime=regime,
        atr_value=atr_val,
        atr_pct=atr_pct,
        bb_width=bb_width,
        bb_position=bb_position,
        evidence=evidence,
    )


# ============================================================
# Volume Analysis (Phase 6)
# ============================================================


def _analyze_volume(
    closes: list[float],
    volumes: list[float],
    highs: list[float],
    lows: list[float],
) -> VolumeContext:
    """Classify volume state from OBV, VWAP, MFI."""
    evidence: list[str] = []

    has_volume = any(v > 0 for v in volumes) if volumes else False
    if not has_volume:
        return VolumeContext(
            state=VolumeState.UNAVAILABLE,
            obv_trend="unknown",
            vwap_distance=None,
            mfi_value=None,
            mfi_zone="unknown",
            has_volume_data=False,
            evidence=["No volume data available"],
        )

    # OBV trend
    obv_vals = obv(closes, volumes)
    obv_trend = "flat"
    if len(obv_vals) >= 20:
        obv_recent = obv_vals[-20:]
        obv_slope = obv_recent[-1] - obv_recent[0]
        if obv_slope > 0:
            obv_trend = "rising"
            evidence.append("OBV trend: rising (accumulation)")
        elif obv_slope < 0:
            obv_trend = "falling"
            evidence.append("OBV trend: falling (distribution)")
        else:
            evidence.append("OBV trend: flat")

    # VWAP
    vwap_vals = vwap(highs, lows, closes, volumes)
    vwap_val = _last(vwap_vals)
    vwap_distance = None
    if vwap_val is not None and vwap_val > 0:
        last_close = closes[-1] if closes else None
        if last_close is not None:
            vwap_distance = (last_close - vwap_val) / vwap_val
            if vwap_distance > 0:
                evidence.append(f"Price {vwap_distance:.2%} above VWAP")
            else:
                evidence.append(f"Price {abs(vwap_distance):.2%} below VWAP")

    # MFI
    mfi_vals = mfi(highs, lows, closes, volumes, 14)
    mfi_val = _last(mfi_vals)
    mfi_zone = "neutral"
    if mfi_val is not None:
        if mfi_val > 80:
            mfi_zone = "overbought"
        elif mfi_val < 20:
            mfi_zone = "oversold"
        evidence.append(f"MFI(14) = {mfi_val:.1f} ({mfi_zone})")

    # Volume confirmation: price up + OBV up = confirming
    if len(closes) >= 2:
        price_up = closes[-1] > closes[-2]
        obv_up = len(obv_vals) >= 2 and obv_vals[-1] > obv_vals[-2]

        if price_up and obv_up or not price_up and not obv_up:
            state = VolumeState.CONFIRMING
        elif price_up and not obv_up:
            state = VolumeState.DIVERGING
            evidence.append("Price rising but OBV falling (divergence)")
        elif not price_up and obv_up:
            state = VolumeState.DIVERGING
            evidence.append("Price falling but OBV rising (divergence)")
        else:
            state = VolumeState.WEAK
    else:
        state = VolumeState.WEAK

    return VolumeContext(
        state=state,
        obv_trend=obv_trend,
        vwap_distance=vwap_distance,
        mfi_value=mfi_val,
        mfi_zone=mfi_zone,
        has_volume_data=True,
        evidence=evidence,
    )


# ============================================================
# Structure Integration (Phase 7)
# ============================================================


def _analyze_structure_context(
    structure_result: dict,
    closes: list[float],
) -> StructureContext:
    """Integrate existing M24 structure analysis into context."""
    evidence: list[str] = []

    swings = structure_result.get("swings", [])
    breaks = structure_result.get("breaks", [])
    sr = structure_result.get("support_resistance", [])
    regime = structure_result.get("regime", MarketRegime.RANGING)

    # Active support/resistance
    active_support = [s for s in sr if s.level_type == "support" and s.active]
    active_resistance = [s for s in sr if s.level_type == "resistance" and s.active]

    if active_support:
        nearest_sup = max(s.level for s in active_support)
        evidence.append(f"Active support levels: {len(active_support)} (nearest: {nearest_sup:.2f})")
    if active_resistance:
        nearest_res = min(s.level for s in active_resistance)
        evidence.append(f"Active resistance levels: {len(active_resistance)} (nearest: {nearest_res:.2f})")

    # Last swing
    last_swing = swings[-1] if swings else None
    if last_swing:
        evidence.append(f"Last swing: {last_swing.swing_type.value} at {last_swing.price:.2f}")

    # Last break
    last_break = breaks[-1] if breaks else None
    if last_break:
        evidence.append(f"Last structure break: {last_break.break_type.value} at {last_break.price:.2f}")

    # Structure state
    classified = structure_result.get("classified", [])
    hh_hl = sum(1 for _, l in classified if l in ("HH", "HL"))
    lh_ll = sum(1 for _, l in classified if l in ("LH", "LL"))

    if regime == MarketRegime.UPTREND and hh_hl > lh_ll:
        state = StructureContextState.BULLISH
        evidence.append(f"Structure bullish: {hh_hl} HH/HL vs {lh_ll} LH/LL")
    elif regime == MarketRegime.DOWNTREND and lh_ll > hh_hl:
        state = StructureContextState.BEARISH
        evidence.append(f"Structure bearish: {lh_ll} LH/LL vs {hh_hl} HH/HL")
    elif hh_hl > 0 and lh_ll > 0:
        state = StructureContextState.MIXED
        evidence.append(f"Structure mixed: {hh_hl} HH/HL vs {lh_ll} LH/LL")
    else:
        state = StructureContextState.RANGE
        evidence.append("Structure: ranging (no clear directional pattern)")

    return StructureContext(
        state=state,
        regime=regime,
        last_swing=last_swing,
        last_break=last_break,
        active_support=active_support,
        active_resistance=active_resistance,
        swing_count=len(swings),
        break_count=len(breaks),
        evidence=evidence,
    )


# ============================================================
# Liquidity Context (Phase 8)
# ============================================================


def _analyze_liquidity_context(
    liquidity_levels: list[LiquidityLevel],
    closes: list[float],
) -> LiquidityContext:
    """Describe liquidity structure without predictive claims."""
    evidence: list[str] = []

    swept = [l for l in liquidity_levels if l.swept]
    unswept = [l for l in liquidity_levels if not l.swept]

    if swept:
        evidence.append(f"Swept liquidity levels: {len(swept)}")
    if unswept:
        evidence.append(f"Unswept liquidity levels: {len(unswept)}")

    nearest = None
    if liquidity_levels and closes:
        last_price = closes[-1]
        distances = [(abs(l.price - last_price), l.price) for l in liquidity_levels]
        if distances:
            distances.sort()
            nearest = distances[0][1]
            evidence.append(f"Nearest liquidity level: {nearest:.2f}")

    return LiquidityContext(
        swept_count=len(swept),
        unswept_count=len(unswept),
        nearest_liquidity=nearest,
        liquidity_levels=liquidity_levels,
        evidence=evidence,
    )


# ============================================================
# Multi-Timeframe Analysis (Phase 9)
# ============================================================


def _analyze_multi_timeframe(
    bars_by_tf: dict[str, list[dict]],
) -> MultiTimeframeContext:
    """Analyze trend/structure across multiple timeframes."""
    evidence: list[str] = []
    tf_analyses: list[TimeframeAnalysis] = []

    for tf_name, tf_bars in bars_by_tf.items():
        if len(tf_bars) < 30:
            continue

        closes = [b["close"] for b in tf_bars]
        highs = [b["high"] for b in tf_bars]
        lows = [b["low"] for b in tf_bars]

        result = analyze_structure(highs, lows, closes, left=3, right=3)
        regime = result.get("regime", MarketRegime.RANGING)

        # Quick trend via EMA
        ema12 = ema_indicator(closes, 12)
        ema26 = ema_indicator(closes, 26)
        last_e12 = _last(ema12)
        last_e26 = _last(ema26)

        if last_e12 is not None and last_e26 is not None:
            trend = TrendDirection.UPTREND if last_e12 > last_e26 else TrendDirection.DOWNTREND
        else:
            trend = TrendDirection.RANGING

        # Quick momentum via RSI
        rsi_vals = rsi(closes, 14)
        rsi_val = _last(rsi_vals)
        if rsi_val is not None:
            if rsi_val > 60:
                momentum = MomentumState.BULLISH
            elif rsi_val < 40:
                momentum = MomentumState.BEARISH
            else:
                momentum = MomentumState.NEUTRAL
        else:
            momentum = MomentumState.NEUTRAL

        # Structure state
        classified = result.get("classified", [])
        hh_hl = sum(1 for _, l in classified if l in ("HH", "HL"))
        lh_ll = sum(1 for _, l in classified if l in ("LH", "LL"))
        if hh_hl > lh_ll:
            struct_state = StructureContextState.BULLISH
        elif lh_ll > hh_hl:
            struct_state = StructureContextState.BEARISH
        else:
            struct_state = StructureContextState.RANGE

        tf_analyses.append(TimeframeAnalysis(
            timeframe=tf_name,
            trend=trend,
            structure=struct_state,
            regime=regime,
            momentum=momentum,
        ))

    # Alignment
    if len(tf_analyses) < 2:
        alignment = AlignmentState.INSUFFICIENT_DATA
        evidence.append("Insufficient timeframes for alignment analysis")
    else:
        trends = [t.trend for t in tf_analyses]
        bullish_tfs = sum(1 for t in trends if t == TrendDirection.UPTREND)
        bearish_tfs = sum(1 for t in trends if t == TrendDirection.DOWNTREND)
        total = len(trends)

        if bullish_tfs == total:
            alignment = AlignmentState.ALIGNED_BULLISH
            evidence.append(f"All {total} timeframes aligned bullish")
        elif bearish_tfs == total:
            alignment = AlignmentState.ALIGNED_BEARISH
            evidence.append(f"All {total} timeframes aligned bearish")
        elif bullish_tfs > 0 and bearish_tfs > 0:
            alignment = AlignmentState.CONFLICTING
            evidence.append(f"Conflicting: {bullish_tfs} bullish vs {bearish_tfs} bearish timeframes")
        else:
            alignment = AlignmentState.MIXED
            evidence.append("Mixed alignment across timeframes")

    return MultiTimeframeContext(
        alignment=alignment,
        timeframes=tf_analyses,
        evidence=evidence,
    )


# ============================================================
# Conflict Detection (Phase 10)
# ============================================================


def _detect_conflicts(
    trend: TrendContext,
    momentum: MomentumContext,
    volatility: VolatilityContext,
    volume: VolumeContext,
    structure: StructureContext,
    mtf: MultiTimeframeContext,
) -> list[ConflictItem]:
    """Detect contradictions between analysis domains."""
    conflicts: list[ConflictItem] = []

    # Trend vs Momentum
    if trend.direction == TrendDirection.UPTREND and momentum.state in (MomentumState.BEARISH, MomentumState.OVERSOLD):
        conflicts.append(ConflictItem(
            domain_a="trend", state_a=trend.direction.value,
            domain_b="momentum", state_b=momentum.state.value,
            description="Trend is bullish but momentum is bearish/oversold",
        ))
    if trend.direction == TrendDirection.DOWNTREND and momentum.state in (MomentumState.BULLISH, MomentumState.OVERBOUGHT):
        conflicts.append(ConflictItem(
            domain_a="trend", state_a=trend.direction.value,
            domain_b="momentum", state_b=momentum.state.value,
            description="Trend is bearish but momentum is bullish/overbought",
        ))

    # Trend vs Structure
    if trend.direction == TrendDirection.UPTREND and structure.state == StructureContextState.BEARISH:
        conflicts.append(ConflictItem(
            domain_a="trend", state_a=trend.direction.value,
            domain_b="structure", state_b=structure.state.value,
            description="Trend is bullish but market structure is bearish",
        ))
    if trend.direction == TrendDirection.DOWNTREND and structure.state == StructureContextState.BULLISH:
        conflicts.append(ConflictItem(
            domain_a="trend", state_a=trend.direction.value,
            domain_b="structure", state_b=structure.state.value,
            description="Trend is bearish but market structure is bullish",
        ))

    # Momentum vs Structure
    if momentum.state == MomentumState.BULLISH and structure.state == StructureContextState.BEARISH:
        conflicts.append(ConflictItem(
            domain_a="momentum", state_a=momentum.state.value,
            domain_b="structure", state_b=structure.state.value,
            description="Momentum is bullish but structure is bearish",
        ))
    if momentum.state == MomentumState.BEARISH and structure.state == StructureContextState.BULLISH:
        conflicts.append(ConflictItem(
            domain_a="momentum", state_a=momentum.state.value,
            domain_b="structure", state_b=structure.state.value,
            description="Momentum is bearish but structure is bullish",
        ))

    # Volatility vs Trend
    if volatility.regime == VolatilityRegime.HIGH and trend.direction == TrendDirection.RANGING:
        conflicts.append(ConflictItem(
            domain_a="volatility", state_a=volatility.regime.value,
            domain_b="trend", state_b=trend.direction.value,
            description="High volatility with no clear trend direction",
        ))

    # Volume divergence
    if volume.state == VolumeState.DIVERGING:
        conflicts.append(ConflictItem(
            domain_a="volume", state_a=volume.state.value,
            domain_b="price", state_b="movement",
            description="Volume diverging from price direction",
        ))

    # Multi-timeframe conflict
    if mtf.alignment == AlignmentState.CONFLICTING:
        conflicts.append(ConflictItem(
            domain_a="multi_timeframe", state_a=mtf.alignment.value,
            domain_b="timeframes", state_b="conflicting",
            description="Different timeframes show conflicting directional bias",
        ))

    # Momentum extreme vs structure
    if momentum.state == MomentumState.OVERBOUGHT and structure.state == StructureContextState.BEARISH:
        conflicts.append(ConflictItem(
            domain_a="momentum", state_a="overbought",
            domain_b="structure", state_b="bearish",
            description="Overbought momentum with bearish structure",
        ))
    if momentum.state == MomentumState.OVERSOLD and structure.state == StructureContextState.BULLISH:
        conflicts.append(ConflictItem(
            domain_a="momentum", state_a="oversold",
            domain_b="structure", state_b="bullish",
            description="Oversold momentum with bullish structure",
        ))

    return conflicts


# ============================================================
# Data Quality (Phase 11)
# ============================================================


def _assess_data_quality(
    bars: list[dict],
    asset: str,
    timeframe: str,
    provider: str,
    stale: bool,
) -> DataQualityContext:
    """Assess data quality from observable properties."""
    candle_count = len(bars)
    latest_ts = bars[-1].get("timestamp", "") if bars else None

    missing_fields: list[str] = []
    invalid_removed = 0

    for b in bars:
        for field_name in ("open", "high", "low", "close", "volume"):
            val = b.get(field_name)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                missing_fields.append(field_name)
                break

    if not bars:
        quality = DataQuality.MISSING
    elif stale:
        quality = DataQuality.STALE
    elif candle_count < 30:
        quality = DataQuality.INSUFFICIENT
    else:
        quality = DataQuality.GOOD

    return DataQualityContext(
        quality=quality,
        candle_count=candle_count,
        latest_timestamp=latest_ts,
        provider=provider,
        stale=stale,
        missing_fields=list(set(missing_fields)),
        invalid_candles_removed=invalid_removed,
        timeframe=timeframe,
        asset=asset,
    )


# ============================================================
# Explanation Engine (Phase 12)
# ============================================================


def _generate_explanation(
    trend: TrendContext,
    momentum: MomentumContext,
    volatility: VolatilityContext,
    volume: VolumeContext,
    structure: StructureContext,
    liquidity: LiquidityContext,
    mtf: MultiTimeframeContext,
    conflicts: list[ConflictItem],
) -> AnalysisExplanation:
    """Generate structured explanation from analytical facts."""
    sections: list[ExplanationSection] = []

    # Trend
    trend_content = f"{trend.direction.value.upper()} ({trend.strength.value})"
    sections.append(ExplanationSection(
        heading="Trend",
        content=trend_content,
        evidence=trend.evidence,
    ))

    # Momentum
    sections.append(ExplanationSection(
        heading="Momentum",
        content=momentum.state.value.upper(),
        evidence=momentum.evidence,
    ))

    # Volatility
    sections.append(ExplanationSection(
        heading="Volatility",
        content=volatility.regime.value.upper(),
        evidence=volatility.evidence,
    ))

    # Volume
    sections.append(ExplanationSection(
        heading="Volume",
        content=volume.state.value.upper(),
        evidence=volume.evidence,
    ))

    # Structure
    sections.append(ExplanationSection(
        heading="Structure",
        content=structure.state.value.upper(),
        evidence=structure.evidence,
    ))

    # Liquidity
    liq_evidence = liquidity.evidence if liquidity.evidence else ["No liquidity data"]
    sections.append(ExplanationSection(
        heading="Liquidity",
        content=f"{liquidity.swept_count} swept, {liquidity.unswept_count} unswept",
        evidence=liq_evidence,
    ))

    # Multi-timeframe
    sections.append(ExplanationSection(
        heading="Multi-Timeframe Alignment",
        content=mtf.alignment.value.upper(),
        evidence=mtf.evidence,
    ))

    # Conflicts
    if conflicts:
        conflict_evidence = [c.description for c in conflicts]
        sections.append(ExplanationSection(
            heading="Conflicts / Uncertainty",
            content=f"{len(conflicts)} conflict(s) detected",
            evidence=conflict_evidence,
        ))
    else:
        sections.append(ExplanationSection(
            heading="Conflicts / Uncertainty",
            content="No significant conflicts detected",
            evidence=[],
        ))

    return AnalysisExplanation(sections=sections)


# ============================================================
# Main Entry Point
# ============================================================


def analyze_market(
    bars: list[dict],
    asset: str,
    timeframe: str,
    provider: str = "unknown",
    stale: bool = False,
    bars_by_tf: dict[str, list[dict]] | None = None,
) -> MarketContext:
    """Produce complete market analysis from OHLCV data.

    This is the main entry point. It orchestrates all analysis modules
    and returns a structured MarketContext.

    All calculations are deterministic and use no future data.
    """
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    volumes = [b.get("volume", 0.0) for b in bars]

    # Run structure analysis (reuses M24 engine)
    structure_result = analyze_structure(highs, lows, closes)

    # Phase 3: Trend
    trend = _analyze_trend(closes, highs, lows, structure_result)

    # Phase 4: Momentum
    momentum = _analyze_momentum(closes, highs, lows)

    # Phase 5: Volatility
    volatility = _analyze_volatility(closes, highs, lows)

    # Phase 6: Volume
    volume_ctx = _analyze_volume(closes, volumes, highs, lows)

    # Phase 7: Structure
    structure_ctx = _analyze_structure_context(structure_result, closes)

    # Phase 8: Liquidity
    liquidity_ctx = _analyze_liquidity_context(
        structure_result.get("liquidity", []),
        closes,
    )

    # Phase 9: Multi-timeframe
    if bars_by_tf:
        mtf = _analyze_multi_timeframe(bars_by_tf)
    else:
        mtf = MultiTimeframeContext(
            alignment=AlignmentState.INSUFFICIENT_DATA,
            timeframes=[],
            evidence=["No multi-timeframe data provided"],
        )

    # Phase 10: Conflicts
    conflicts = _detect_conflicts(trend, momentum, volatility, volume_ctx, structure_ctx, mtf)

    # Phase 11: Data quality
    data_quality = _assess_data_quality(bars, asset, timeframe, provider, stale)

    # Phase 12: Explanation
    explanation = _generate_explanation(trend, momentum, volatility, volume_ctx, structure_ctx, liquidity_ctx, mtf, conflicts)

    return MarketContext(
        asset=asset,
        timeframe=timeframe,
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        volume=volume_ctx,
        structure=structure_ctx,
        liquidity=liquidity_ctx,
        multi_timeframe=mtf,
        conflicts=conflicts,
        data_quality=data_quality,
        explanation=explanation,
    )
