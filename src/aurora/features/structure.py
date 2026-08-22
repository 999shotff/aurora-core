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


@dataclass(frozen=True)
class StructureBreak:
    index: int
    price: float
    break_type: StructureBreakType
    reference_index: int
    reference_price: float


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
) -> list[SwingPoint]:
    """Detect swing highs and lows.

    Swing high at i: highs[i] > all highs in [i-left, i) AND > all highs in (i, i+right].
    Swing low at i: lows[i] < all lows in [i-left, i) AND < all lows in (i, i+right].

    Near edges: uses available neighbors only.

    CRITICAL: The right-neighbor check means a swing is *detected* at i+right
    but *placed* at index i.  Historical values are never retroactively altered.

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
                swings.append(SwingPoint(i, highs[i], SwingType.HIGH))

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
                swings.append(SwingPoint(i, lows[i], SwingType.LOW))

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
                else:
                    bt = StructureBreakType.BOS_BULL
                breaks.append(StructureBreak(
                    index=i,
                    price=closes[i],
                    break_type=bt,
                    reference_index=sw.index,
                    reference_price=sw.price,
                ))
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
                else:
                    bt = StructureBreakType.BOS_BEAR
                breaks.append(StructureBreak(
                    index=i,
                    price=closes[i],
                    break_type=bt,
                    reference_index=sw.index,
                    reference_price=sw.price,
                ))
                broken_levels.add(sw.index)
                break

    return breaks

def detect_support_resistance(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    swings: list[SwingPoint],
    tolerance: float = 0.005,
) -> list[dict]:
    """Cluster nearby swing points into support and resistance levels.

    High swings map to resistance; low swings map to support.
    Levels within tolerance fraction of each other are grouped.
    Each cluster must have at least 2 touches.

    Returns list of dicts:
      {"level": float, "type": "support"|"resistance", "touches": int, "indices": list[int]}

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

    results: list[dict] = []
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

        results.append({
            "level": avg_price,
            "type": level_type,
            "touches": len(cluster),
            "indices": [sw.index for sw in cluster],
        })

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
    if not swings or not closes:
        return MarketRegime.RANGING

    classified = classify_swing_sequence(swings)
    n = len(closes)
    window_start = max(0, n - lookback)

    recent = [(sw, label) for sw, label in classified if sw.index >= window_start]

    if not recent:
        return MarketRegime.RANGING

    bullish = sum(1 for _, label in recent if label in ("HH", "HL"))
    bearish = sum(1 for _, label in recent if label in ("LH", "LL"))
    total = len(recent)

    bull_pct = bullish / total
    bear_pct = bearish / total

    if bull_pct > 0.6:
        return MarketRegime.UPTREND
    elif bear_pct > 0.6:
        return MarketRegime.DOWNTREND
    else:
        return MarketRegime.RANGING

def analyze_structure(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    left: int = 3,
    right: int = 3,
) -> dict:
    """Master function that runs all structure analyses.

    Returns dict with keys: swings, classified, breaks,
    support_resistance, liquidity, regime.

    This is the main entry point for the engine.

    Outputs are descriptive only; no predictive claims.
    """
    _validate_lengths(highs, lows, closes)

    swings = detect_swing_points(highs, lows, left, right)
    classified = classify_swing_sequence(swings)
    breaks = detect_structure_breaks(highs, lows, closes, swings, left, right)
    sr = detect_support_resistance(highs, lows, closes, swings)
    liquidity = detect_liquidity(highs, lows, closes, swings)
    regime = classify_market_regime(swings, closes)

    return {
        "swings": swings,
        "classified": classified,
        "breaks": breaks,
        "support_resistance": sr,
        "liquidity": liquidity,
        "regime": regime,
    }



