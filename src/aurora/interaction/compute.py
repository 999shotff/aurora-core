"""Feature computation from raw OHLCV data."""

from __future__ import annotations

from aurora.benchmark.data import OHLCVDataset
from aurora.benchmark.features import (
    atr_ratio as _atr_ratio,
)
from aurora.benchmark.features import (
    fibonacci_retracement_level as _fib_distance,
)
from aurora.benchmark.features import (
    liquidity_sweep as _liquidity_sweep,
)
from aurora.benchmark.features import (
    market_structure_break as _market_structure,
)
from aurora.benchmark.features import (
    momentum_signal as _momentum,
)
from aurora.benchmark.features import (
    rsi_signal as _rsi_signal,
)
from aurora.benchmark.features import (
    volume_price_divergence as _volume_div,
)
from aurora.benchmark.features import (
    vwap_deviation as _vwap_dev,
)


def compute_all_features(dataset: OHLCVDataset) -> dict[str, list[float | None]]:
    closes = dataset.closes()
    highs = dataset.highs()
    lows = dataset.lows()
    volumes = dataset.volumes()
    return {
        "liquidity_sweep": [float(v) if v is not None else None for v in _liquidity_sweep(highs, lows, closes, 20)],
        "market_structure_bos": [float(v) if v is not None else None for v in _market_structure(highs, lows, closes, 20)],
        "rsi_signal": [float(v) if v is not None else None for v in _rsi_signal(closes, 14)],
        "momentum_14": _momentum(closes, 14),
        "atr_ratio": _atr_ratio(highs, lows, closes, 14, 50),
        "volume_divergence": [float(v) if v is not None else None for v in _volume_div(closes, volumes, 20)],
        "vwap_deviation": _vwap_dev(closes, volumes, 20),
        "fibonacci_distance": _fib_distance(closes, 20, 0.618),
    }


def compute_interactions(features: dict[str, list[float | None]]) -> dict[str, list[float | None]]:
    interactions: dict[str, list[float | None]] = {}
    liq = features.get("liquidity_sweep", [])
    bos = features.get("market_structure_bos", [])
    rsi = features.get("rsi_signal", [])
    mom = features.get("momentum_14", [])
    atr = features.get("atr_ratio", [])
    vol = features.get("volume_divergence", [])
    n = min(len(liq), len(bos), len(rsi), len(mom), len(atr), len(vol))

    liq_x_bos: list[float | None] = []
    for i in range(n):
        lv = liq[i]
        bv = bos[i]
        if lv is not None and bv is not None:
            liq_x_bos.append(float(lv) * float(bv))
        else:
            liq_x_bos.append(None)
    interactions["liquidity_x_structure"] = liq_x_bos

    rsi_x_bos: list[float | None] = []
    for i in range(n):
        rv = rsi[i]
        bv = bos[i]
        if rv is not None and bv is not None:
            rsi_x_bos.append(float(rv) if bv == 0 else float(bv))
        else:
            rsi_x_bos.append(None)
    interactions["rsi_x_structure"] = rsi_x_bos

    mom_x_atr: list[float | None] = []
    for i in range(n):
        mv = mom[i]
        av = atr[i]
        if mv is not None and av is not None:
            mom_x_atr.append(float(mv) * float(av))
        else:
            mom_x_atr.append(None)
    interactions["momentum_x_volatility"] = mom_x_atr

    vol_x_bos: list[float | None] = []
    for i in range(n):
        vv = vol[i]
        bv = bos[i]
        if vv is not None and bv is not None:
            vol_x_bos.append(float(vv) * float(bv))
        else:
            vol_x_bos.append(None)
    interactions["volume_x_structure"] = vol_x_bos

    liq_x_atr: list[float | None] = []
    for i in range(n):
        lv = liq[i]
        av = atr[i]
        if lv is not None and av is not None:
            liq_x_atr.append(float(lv) * float(av))
        else:
            liq_x_atr.append(None)
    interactions["liquidity_x_volatility"] = liq_x_atr

    return interactions


def compute_targets(
    closes: list[float],
    horizon: int = 4,
) -> list[float | None]:
    n = len(closes)
    targets: list[float | None] = []
    for i in range(n):
        if i + horizon >= n:
            targets.append(None)
        else:
            ret = (closes[i + horizon] - closes[i]) / closes[i] if closes[i] != 0 else 0.0
            targets.append(1.0 if ret > 0 else 0.0)
    return targets
