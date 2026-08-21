"""Regime analysis: evaluate performance across market regimes."""

from __future__ import annotations

from dataclasses import dataclass

from aurora.benchmark.data import OHLCVDataset
from aurora.benchmark.features import atr_ratio, momentum_signal


class RegimeType:
    HIGH_VOL = "high_volatility"
    LOW_VOL = "low_volatility"
    TRENDING = "trending"
    RANGING = "ranging"


MIN_REGIME_SAMPLES = 30


@dataclass
class RegimeResult:
    regime_name: str
    n_observations: int
    majority_class_accuracy: float
    model_da: float
    da_delta: float
    sufficient_samples: bool
    status: str


def detect_regimes(
    dataset: OHLCVDataset,
    vol_window: int = 50,
    trend_window: int = 20,
) -> dict[str, list[bool]]:
    closes = dataset.closes()
    highs = dataset.highs()
    lows = dataset.lows()
    n = len(closes)

    atr_vals = atr_ratio(highs, lows, closes, 14, vol_window)
    mom_vals = momentum_signal(closes, trend_window)

    high_vol = []
    low_vol = []
    trending = []
    ranging = []

    for i in range(n):
        atr_raw = atr_vals[i]
        atr_v = atr_raw if atr_raw is not None else 1.0
        mom_raw = mom_vals[i]
        mom_v = abs(mom_raw) if mom_raw is not None else 0.0
        high_vol.append(atr_v > 1.2)
        low_vol.append(atr_v < 0.8)
        trending.append(mom_v > 0.02)
        ranging.append(mom_v < 0.01)

    return {
        RegimeType.HIGH_VOL: high_vol,
        RegimeType.LOW_VOL: low_vol,
        RegimeType.TRENDING: trending,
        RegimeType.RANGING: ranging,
    }


def evaluate_by_regime(
    predictions: list[float],
    actuals: list[float],
    regimes: dict[str, list[bool]],
    regime_name: str,
) -> dict[str, float]:
    mask = regimes.get(regime_name, [False] * len(predictions))
    subset_pred = [p for p, m in zip(predictions, mask) if m]
    subset_actual = [a for a, m in zip(actuals, mask) if m]
    n = len(subset_pred)
    if n == 0:
        return {"regime_da": 0.0, "regime_n": 0.0}
    correct = sum(1 for p, a in zip(subset_pred, subset_actual) if p == a)
    return {"regime_da": correct / n, "regime_n": float(n)}


def evaluate_regime_conditional(
    targets: list[float],
    predictions: list[float],
    valid_indices: list[int],
    regimes: dict[str, list[bool]],
    min_samples: int = MIN_REGIME_SAMPLES,
) -> list[RegimeResult]:
    results = []

    for regime_name, regime_mask in regimes.items():
        subset_indices = [i for i in valid_indices if i < len(regime_mask) and regime_mask[i]]
        subset_n = len(subset_indices)
        if subset_n < min_samples:
            results.append(RegimeResult(
                regime_name=regime_name,
                n_observations=subset_n,
                majority_class_accuracy=0.0,
                model_da=0.0,
                da_delta=0.0,
                sufficient_samples=False,
                status="INCONCLUSIVE",
            ))
            continue
        subset_pos = sum(1 for i in subset_indices if targets[i] == 1.0)
        subset_neg = sum(1 for i in subset_indices if targets[i] == 0.0)
        subset_total = subset_pos + subset_neg
        subset_majority_da = max(subset_pos, subset_neg) / subset_total if subset_total > 0 else 0.5
        subset_preds = [predictions[i] for i in subset_indices if i < len(predictions)]
        subset_targets = [targets[i] for i in subset_indices]
        if not subset_preds:
            results.append(RegimeResult(
                regime_name=regime_name,
                n_observations=subset_n,
                majority_class_accuracy=subset_majority_da,
                model_da=0.0,
                da_delta=0.0,
                sufficient_samples=False,
                status="INCONCLUSIVE",
            ))
            continue
        correct = sum(1 for p, t in zip(subset_preds, subset_targets) if p == t)
        model_da = correct / len(subset_preds)
        da_delta = model_da - subset_majority_da
        if da_delta > 0.02:
            status = "WEAK"
        elif da_delta < -0.02:
            status = "REJECTED"
        else:
            status = "INCONCLUSIVE"
        results.append(RegimeResult(
            regime_name=regime_name,
            n_observations=subset_n,
            majority_class_accuracy=subset_majority_da,
            model_da=model_da,
            da_delta=da_delta,
            sufficient_samples=True,
            status=status,
        ))
    return results
