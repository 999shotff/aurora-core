"""Market structure analysis engine.

NO_DEPLOYMENT_SIGNAL -- This module is descriptive only. All outputs
describe historical price structure for human review. Nothing produced
by this module constitutes a trading signal, buy/sell recommendation,
or claim of predictive power.

All functions are deterministic and stateless. No future-data access:
every output at index i depends only on data at or before i.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SwingType(Enum):
    HIGH = "high"
    LOW = "low"


class StructureBreakType(Enum):
    BOS_BULL = "bos_bull"
    BOS_BEAR = "bos_bear"
    CHOCH_BULL = "choch_bull"
    CHOCH_BEAR = "choch_bear"


class MarketRegime(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGING = "ranging"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    price: float
    swing_type: SwingType
    strength: float = 0.0
    confirmed: bool = True
    left_index: int = 0
    right_index: int = 0


@dataclass(frozen=True)
class StructureBreak:
    index: int
    price: float
    break_type: StructureBreakType
    reference_index: int
    reference_price: float
    strength: float = 0.0
    regime_before: str = ""
    regime_after: str = ""
    is_choch: bool = False


@dataclass(frozen=True)
class SRLevel:
    level: float
    level_type: str
    touches: int
    touch_weight: float
    strength: float
    active: bool
    first_touch_index: int
    last_touch_index: int
    price_range: float = 0.0


@dataclass(frozen=True)
class LiquidityLevel:
    index: int
    price: float
    swing_type: SwingType
    swept: bool
    swept_at_index: int | None = None


def _validate_lengths(*arrays: list) -> None:
    """Raise ValueError if arrays have different lengths."""
    if not arrays:
        return
    lengths = [len(a) for a in arrays]
    if len(set(lengths)) > 1:
        raise ValueError(f"Array length mismatch: {lengths}")

def detect_swing_points(
    highs: list[float],
    lows: list[float],
    left: int = 3,
    right: int = 3,
    confirm_bars: int = 0,
) -> list[SwingPoint]:
    """Detect swing highs and lows with confirmation and strength.

    Swing high at i: highs[i] > all highs in [i-left, i) AND > all highs in (i, i+right].
    Swing low at i: lows[i] < all lows in [i-left, i) AND < all lows in (i, i+right].

    Near edges: uses available neighbors only.

    CRITICAL: The right-neighbor check means a swing is *detected* at i+right
    but *placed* at index i.  Historical values are never retroactively altered.

    Args:
        confirm_bars: If >0, a swing is only confirmed if price reverses
            within confirm_bars bars after the swing.

    Outputs are descriptive only; no predictive claims.
    """
    _validate_lengths(highs, lows)
    n = len(highs)
    if n == 0:
        return []

    swings: list[SwingPoint] = []

    for i in range(n):
        left_start = max(0, i - left)
        right_end = min(n - 1, i + right)

        left_ok = True
        for j in range(left_start, i):
            if highs[i] <= highs[j]:
                left_ok = False
                break
        if left_ok:
            right_ok = True
            for j in range(i + 1, right_end + 1):
                if highs[i] <= highs[j]:
                    right_ok = False
                    break
            if right_ok:
                # Compute strength: max distance to neighbors normalized by price
                max_drop = 0.0
                for j in range(left_start, right_end + 1):
                    if j != i:
                        max_drop = max(max_drop, highs[i] - lows[j])
                strength = round(max_drop / highs[i] * 10000, 2) if highs[i] > 0 else 0.0

                # Confirmation: price must drop below swing low within confirm_bars
                confirmed = True
                if confirm_bars > 0:
                    confirmed = False
                    end = min(i + confirm_bars + 1, n)
                    for j in range(i + 1, end):
                        if lows[j] < highs[i]:
                            confirmed = True
                            break

                swings.append(SwingPoint(
                    index=i,
                    price=highs[i],
                    swing_type=SwingType.HIGH,
                    strength=strength,
                    confirmed=confirmed,
                    left_index=left_start,
                    right_index=right_end,
                ))

        left_ok_low = True
        for j in range(left_start, i):
            if lows[i] >= lows[j]:
                left_ok_low = False
                break
        if left_ok_low:
            right_ok_low = True
            for j in range(i + 1, right_end + 1):
                if lows[i] >= lows[j]:
                    right_ok_low = False
                    break
            if right_ok_low:
                # Strength: max distance to neighbors normalized by price
                max_rise = 0.0
                for j in range(left_start, right_end + 1):
                    if j != i:
                        max_rise = max(max_rise, highs[j] - lows[i])
                strength = round(max_rise / lows[i] * 10000, 2) if lows[i] > 0 else 0.0

                confirmed = True
                if confirm_bars > 0:
                    confirmed = False
                    end = min(i + confirm_bars + 1, n)
                    for j in range(i + 1, end):
                        if highs[j] > lows[i]:
                            confirmed = True
                            break

                swings.append(SwingPoint(
                    index=i,
                    price=lows[i],
                    swing_type=SwingType.LOW,
                    strength=strength,
                    confirmed=confirmed,
                    left_index=left_start,
                    right_index=right_end,
                ))

    swings.sort(key=lambda s: s.index)
    return swings

def classify_swing_sequence(
    swings: list[SwingPoint],
) -> list[tuple[SwingPoint, str]]:
    """Classify each swing relative to the previous swing of the same type.

    Swing highs: HH (higher high), LH (lower high), EQH (equal high).
    Swing lows: HL (higher low), LL (lower low), EQL (equal low).
    First swing of each type is labelled "first".

    Outputs are descriptive only; no predictive claims.
    """
    if not swings:
        return []

    last_high: SwingPoint | None = None
    last_low: SwingPoint | None = None
    result: list[tuple[SwingPoint, str]] = []

    for sw in swings:
        if sw.swing_type == SwingType.HIGH:
            if last_high is None:
                label = "first"
            elif sw.price > last_high.price:
                label = "HH"
            elif sw.price < last_high.price:
                label = "LH"
            else:
                label = "EQH"
            result.append((sw, label))
            last_high = sw
        else:
            if last_low is None:
                label = "first"
            elif sw.price > last_low.price:
                label = "HL"
            elif sw.price < last_low.price:
                label = "LL"
            else:
                label = "EQL"
            result.append((sw, label))
            last_low = sw

    return result

def detect_structure_breaks(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    swings: list[SwingPoint],
    left: int = 3,
    right: int = 3,
) -> list[StructureBreak]:
    """Detect break of structure (BOS) and change of character (CHOCH) events.

    BOS_BULL: close breaks above a previous swing high in uptrend context.
    BOS_BEAR: close breaks below a previous swing low in downtrend context.
    CHOCH_BULL: close breaks above last lower high after downtrend LH sequence.
    CHOCH_BEAR: close breaks below last higher low after uptrend HL sequence.

    Enhanced with strength (break distance in bps) and regime transition tracking.

    Only one break is detected per bar (first broken level).
    Each swing level can only be broken once.

    Outputs are descriptive only; no predictive claims.
    """
    _validate_lengths(highs, lows, closes)
    n = len(closes)
    if n == 0 or not swings:
        return []

    classified = classify_swing_sequence(swings)

    broken_levels: set[int] = set()
    breaks: list[StructureBreak] = []
    trend_state: str | None = None
    last_lh_index: int | None = None
    last_hl_index: int | None = None

    # Pre-classify trend from swing sequence
    for sw, label in classified:
        if sw.swing_type == SwingType.HIGH:
            if label == "HH":
                trend_state = "uptrend"
            elif label == "LH":
                last_lh_index = sw.index
                if trend_state == "uptrend":
                    trend_state = "downtrend_start"
                elif trend_state != "downtrend":
                    trend_state = "downtrend"
        else:
            if label == "HL":
                last_hl_index = sw.index
                trend_state = "uptrend"
            elif label == "LL":
                if trend_state == "downtrend":
                    trend_state = "uptrend_start"
                elif trend_state != "uptrend":
                    trend_state = "downtrend"

    current_regime = trend_state or "ranging"

    for i in range(n):
        break_found = False

        for sw in reversed(swings):
            if sw.swing_type != SwingType.HIGH:
                continue
            if sw.index >= i or sw.index in broken_levels:
                continue
            if closes[i] > sw.price:
                is_choch = (
                    last_lh_index is not None
                    and sw.index <= last_lh_index
                    and trend_state in ("downtrend", "downtrend_start")
                )
                if is_choch:
                    bt = StructureBreakType.CHOCH_BULL
                    regime_after = "uptrend"
                else:
                    bt = StructureBreakType.BOS_BULL
                    regime_after = "uptrend"

                strength = round(
                    (closes[i] - sw.price) / sw.price * 10000, 2
                ) if sw.price > 0 else 0.0

                breaks.append(StructureBreak(
                    index=i,
                    price=closes[i],
                    break_type=bt,
                    reference_index=sw.index,
                    reference_price=sw.price,
                    strength=strength,
                    regime_before=current_regime,
                    regime_after=regime_after,
                    is_choch=is_choch,
                ))
                current_regime = regime_after
                broken_levels.add(sw.index)
                break_found = True
                break

        if break_found:
            continue

        for sw in reversed(swings):
            if sw.swing_type != SwingType.LOW:
                continue
            if sw.index >= i or sw.index in broken_levels:
                continue
            if closes[i] < sw.price:
                is_choch = (
                    last_hl_index is not None
                    and sw.index <= last_hl_index
                    and trend_state in ("uptrend", "uptrend_start")
                )
                if is_choch:
                    bt = StructureBreakType.CHOCH_BEAR
                    regime_after = "downtrend"
                else:
                    bt = StructureBreakType.BOS_BEAR
                    regime_after = "downtrend"

                strength = round(
                    (sw.price - closes[i]) / sw.price * 10000, 2
                ) if sw.price > 0 else 0.0

                breaks.append(StructureBreak(
                    index=i,
                    price=closes[i],
                    break_type=bt,
                    reference_index=sw.index,
                    reference_price=sw.price,
                    strength=strength,
                    regime_before=current_regime,
                    regime_after=regime_after,
                    is_choch=is_choch,
                ))
                current_regime = regime_after
                broken_levels.add(sw.index)
                break

    return breaks

def detect_support_resistance(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    swings: list[SwingPoint],
    tolerance: float = 0.005,
    touch_decay: float = 0.9,
) -> list[SRLevel]:
    """Cluster nearby swing points into support and resistance levels.

    High swings map to resistance; low swings map to support.
    Levels within tolerance fraction of each other are grouped.
    Touch weight decays exponentially: most recent touch has weight 1,
    earlier touches decay by touch_decay per touch.

    Enhanced with active/inactive status (level is active if no break
    has occurred beyond it) and price range of the cluster.

    Returns list of SRLevel dataclass instances.

    Outputs are descriptive only; no predictive claims.
    """
    _validate_lengths(highs, lows, closes)
    if not swings:
        return []

    sorted_swings = sorted(swings, key=lambda s: s.price)
    clusters: list[list[SwingPoint]] = []
    current_cluster: list[SwingPoint] = [sorted_swings[0]]

    for sw in sorted_swings[1:]:
        ref_price = current_cluster[0].price
        if ref_price == 0 or abs(sw.price - ref_price) / abs(ref_price) <= tolerance:
            current_cluster.append(sw)
        else:
            clusters.append(current_cluster)
            current_cluster = [sw]
    clusters.append(current_cluster)

    n = len(highs)
    results: list[SRLevel] = []
    for cluster in clusters:
        if len(cluster) < 2:
            continue

        avg_price = sum(sw.price for sw in cluster) / len(cluster)
        any_high = any(sw.swing_type == SwingType.HIGH for sw in cluster)
        any_low = any(sw.swing_type == SwingType.LOW for sw in cluster)

        if any_high and not any_low:
            level_type = "resistance"
        elif any_low and not any_high:
            level_type = "support"
        else:
            level_type = "resistance"

        # Touch weight with exponential decay (most recent = weight 1)
        sorted_indices = sorted([sw.index for sw in cluster])
        touch_weight = 0.0
        for rank, idx in enumerate(reversed(sorted_indices)):
            touch_weight += touch_decay ** rank

        # Strength: number of touches normalized by total bars
        strength = round(len(cluster) / max(n, 1) * 100, 2)

        # Price range of the cluster
        prices = [sw.price for sw in cluster]
        price_range = max(prices) - min(prices)

        # Active: level is active if no bar has broken significantly beyond it
        active = True
        for i in range(n):
            if (level_type == "support" and lows[i] < avg_price * 0.99) or \
               (level_type == "resistance" and highs[i] > avg_price * 1.01):
                active = False
                break

        results.append(SRLevel(
            level=avg_price,
            level_type=level_type,
            touches=len(cluster),
            touch_weight=round(touch_weight, 2),
            strength=strength,
            active=active,
            first_touch_index=sorted_indices[0],
            last_touch_index=sorted_indices[-1],
            price_range=round(price_range, 4),
        ))

    return results

def detect_liquidity(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    swings: list[SwingPoint],
) -> list[LiquidityLevel]:
    """Identify liquidity levels at swing points and mark swept status.

    A swing high is swept if any subsequent high exceeds it.
    A swing low is swept if any subsequent low goes below it.

    Outputs are descriptive only; no predictive claims.
    """
    _validate_lengths(highs, lows, closes)
    n = len(highs)
    if n == 0:
        return []

    levels: list[LiquidityLevel] = []

    for sw in swings:
        swept = False
        swept_at: int | None = None

        if sw.swing_type == SwingType.HIGH:
            for j in range(sw.index + 1, n):
                if highs[j] > sw.price:
                    swept = True
                    swept_at = j
                    break
        else:
            for j in range(sw.index + 1, n):
                if lows[j] < sw.price:
                    swept = True
                    swept_at = j
                    break

        levels.append(LiquidityLevel(
            index=sw.index,
            price=sw.price,
            swing_type=sw.swing_type,
            swept=swept,
            swept_at_index=swept_at,
        ))

    return levels

def classify_market_regime(
    swings: list[SwingPoint],
    closes: list[float],
    lookback: int = 20,
) -> MarketRegime:
    """Classify current market regime from recent swing classifications.

    Looks at the last lookback bars of closes and counts swing
    classifications in that window.

    If mostly HH+HL: UPTREND.
    If mostly LH+LL: DOWNTREND.
    Otherwise: RANGING.
    Threshold: >60% of one direction => that trend, else RANGING.

    Outputs are descriptive only; no predictive claims.
    """
    regime, _ = classify_market_regime_with_confidence(swings, closes, lookback)
    return regime


def classify_market_regime_with_confidence(
    swings: list[SwingPoint],
    closes: list[float],
    lookback: int = 20,
) -> tuple[MarketRegime, float]:
    """Classify current market regime with confidence score.

    Confidence = max(bull_pct, bear_pct) for trend, 1 - |bull_pct - bear_pct| for ranging.

    Returns (regime, confidence) where confidence is 0.0-1.0.

    Outputs are descriptive only; no predictive claims.
    """
    if not swings or not closes:
        return MarketRegime.RANGING, 0.0

    classified = classify_swing_sequence(swings)
    n = len(closes)
    window_start = max(0, n - lookback)

    recent = [(sw, label) for sw, label in classified if sw.index >= window_start]

    if not recent:
        return MarketRegime.RANGING, 0.0

    bullish = sum(1 for _, label in recent if label in ("HH", "HL"))
    bearish = sum(1 for _, label in recent if label in ("LH", "LL"))
    total = len(recent)

    bull_pct = bullish / total
    bear_pct = bearish / total

    if bull_pct > 0.6:
        return MarketRegime.UPTREND, round(bull_pct, 2)
    elif bear_pct > 0.6:
        return MarketRegime.DOWNTREND, round(bear_pct, 2)
    else:
        # Confidence for ranging = how balanced the signals are
        confidence = round(1.0 - abs(bull_pct - bear_pct), 2)
        return MarketRegime.RANGING, confidence

def analyze_structure(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    left: int = 3,
    right: int = 3,
    confirm_bars: int = 0,
) -> dict:
    """Master function that runs all structure analyses.

    Returns dict with keys: swings, classified, breaks,
    support_resistance, liquidity, regime, regime_confidence.

    This is the main entry point for the engine.

    Outputs are descriptive only; no predictive claims.
    """
    _validate_lengths(highs, lows, closes)

    swings = detect_swing_points(highs, lows, left, right, confirm_bars)
    classified = classify_swing_sequence(swings)
    breaks = detect_structure_breaks(highs, lows, closes, swings, left, right)
    sr = detect_support_resistance(highs, lows, closes, swings)
    liquidity = detect_liquidity(highs, lows, closes, swings)
    regime, regime_confidence = classify_market_regime_with_confidence(swings, closes)

    return {
        "swings": swings,
        "classified": classified,
        "breaks": breaks,
        "support_resistance": sr,
        "liquidity": liquidity,
        "regime": regime,
        "regime_confidence": regime_confidence,
    }


# ---------------------------------------------------------------------------
# Multi-timeframe aggregation
# ---------------------------------------------------------------------------

def aggregate_to_higher_timeframe(
    timestamps: list[str],
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    target_tf_minutes: int,
) -> dict:
    """Aggregate lower-timeframe OHLCV data to a higher timeframe.

    Groups bars by target_tf_minutes boundary and aggregates:
    - Open: first bar's open
    - High: max of all bars' highs
    - Low: min of all bars' lows
    - Close: last bar's close
    - Volume: sum of all bars' volumes

    Args:
        timestamps: ISO format timestamps for each bar.
        opens, highs, lows, closes, volumes: Price/volume arrays.
        target_tf_minutes: Target timeframe in minutes (e.g. 60 for 1h, 1440 for 1d).

    Returns:
        Dict with keys: timestamps, opens, highs, lows, closes, volumes.

    Outputs are descriptive only; no predictive claims.
    """
    n = len(timestamps)
    if n == 0:
        return {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}

    # Group bars by target timeframe boundary
    from datetime import datetime

    groups: dict[str, list[int]] = {}
    for i, ts in enumerate(timestamps):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            # Truncate to target timeframe
            minutes = dt.minute
            truncated_minutes = (minutes // target_tf_minutes) * target_tf_minutes
            key_dt = dt.replace(minute=truncated_minutes, second=0, microsecond=0)
            key = key_dt.isoformat()
        except (ValueError, AttributeError):
            # Fallback: group by index ranges
            key = str(i // max(target_tf_minutes, 1))

        if key not in groups:
            groups[key] = []
        groups[key].append(i)

    # Aggregate each group
    out_timestamps: list[str] = []
    out_opens: list[float] = []
    out_highs: list[float] = []
    out_lows: list[float] = []
    out_closes: list[float] = []
    out_volumes: list[float] = []

    for key in sorted(groups.keys()):
        indices = groups[key]
        out_timestamps.append(timestamps[indices[0]])
        out_opens.append(opens[indices[0]])
        out_highs.append(max(highs[i] for i in indices))
        out_lows.append(min(lows[i] for i in indices))
        out_closes.append(closes[indices[-1]])
        out_volumes.append(sum(volumes[i] for i in indices))

    return {
        "timestamps": out_timestamps,
        "opens": out_opens,
        "highs": out_highs,
        "lows": out_lows,
        "closes": out_closes,
        "volumes": out_volumes,
    }


def analyze_structure_multi_timeframe(
    timestamps: list[str],
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    timeframes_minutes: list[int] | None = None,
    left: int = 3,
    right: int = 3,
) -> dict:
    """Run structure analysis across multiple timeframes.

    Aggregates data to each timeframe and runs analyze_structure on each.

    Args:
        timestamps: ISO format timestamps for each bar.
        opens, highs, lows, closes, volumes: Price/volume arrays.
        timeframes_minutes: List of timeframes in minutes. Default: [5, 15, 60, 240, 1440].
        left, right: Swing detection parameters.

    Returns:
        Dict mapping timeframe label to analyze_structure result.

    Outputs are descriptive only; no predictive claims.
    """
    if timeframes_minutes is None:
        timeframes_minutes = [5, 15, 60, 240, 1440]

    tf_labels = {
        1: "1m", 5: "5m", 15: "15m", 30: "30m",
        60: "1h", 240: "4h", 1440: "1d",
    }

    results: dict[str, dict] = {}
    for tf in timeframes_minutes:
        label = tf_labels.get(tf, f"{tf}m")
        agg = aggregate_to_higher_timeframe(
            timestamps, opens, highs, lows, closes, volumes, tf
        )
        if len(agg["highs"]) < left + right + 1:
            results[label] = {
                "swings": [], "classified": [], "breaks": [],
                "support_resistance": [], "liquidity": [],
                "regime": MarketRegime.RANGING, "regime_confidence": 0.0,
            }
            continue

        result = analyze_structure(
            agg["highs"], agg["lows"], agg["closes"], left, right
        )
        results[label] = result

    return results



