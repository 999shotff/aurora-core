from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvaluationMetrics:
    directional_accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    roc_auc: float = 0.0
    brier_score: float = 0.0
    log_loss: float = 0.0
    calibration_error: float = 0.0
    average_return: float = 0.0
    volatility: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    n_observations: int = 0
    baseline_comparison: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict[str, float]:
        return {
            "directional_accuracy": self.directional_accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "roc_auc": self.roc_auc,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "calibration_error": self.calibration_error,
            "average_return": self.average_return,
            "volatility": self.volatility,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "profit_factor": self.profit_factor,
            "n_observations": self.n_observations,
        }


def compute_directional_accuracy(
    predicted: list[float], actual: list[float]
) -> float:
    if not predicted or not actual or len(predicted) != len(actual):
        return 0.0
    correct = 0
    total = 0
    for p, a in zip(predicted, actual):
        if p == 0.0 or a == 0.0:
            continue
        total += 1
        if (p > 0 and a > 0) or (p < 0 and a < 0):
            correct += 1
    return correct / total if total > 0 else 0.0


def compute_precision(predicted: list[float], actual: list[float]) -> float:
    if not predicted or not actual:
        return 0.0
    tp = sum(1 for p, a in zip(predicted, actual) if p > 0 and a > 0)
    fp = sum(1 for p, a in zip(predicted, actual) if p > 0 and a <= 0)
    return tp / (tp + fp) if (tp + fp) > 0 else 0.0


def compute_recall(predicted: list[float], actual: list[float]) -> float:
    if not predicted or not actual:
        return 0.0
    tp = sum(1 for p, a in zip(predicted, actual) if p > 0 and a > 0)
    fn = sum(1 for p, a in zip(predicted, actual) if p <= 0 and a > 0)
    return tp / (tp + fn) if (tp + fn) > 0 else 0.0


def compute_f1(precision: float, recall: float) -> float:
    if precision + recall == 0.0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_roc_auc(probabilities: list[float], actual: list[float]) -> float:
    if not probabilities or not actual:
        return 0.0
    pos_probs = [p for p, a in zip(probabilities, actual) if a > 0]
    neg_probs = [p for p, a in zip(probabilities, actual) if a <= 0]
    if not pos_probs or not neg_probs:
        return 0.5
    n_pos = len(pos_probs)
    n_neg = len(neg_probs)
    n_correct = 0.0
    for pp in pos_probs:
        for np_ in neg_probs:
            if pp > np_:
                n_correct += 1
            elif pp == np_:
                n_correct += 0.5
    return n_correct / (n_pos * n_neg) if (n_pos * n_neg) > 0 else 0.5


def compute_brier_score(probabilities: list[float], actual: list[float]) -> float:
    if not probabilities or not actual:
        return 0.0
    total = 0.0
    for p, a in zip(probabilities, actual):
        target = 1.0 if a > 0 else 0.0
        total += (p - target) ** 2
    return total / len(probabilities)


def compute_log_loss(probabilities: list[float], actual: list[float]) -> float:
    if not probabilities or not actual:
        return 0.0
    eps = 1e-15
    total = 0.0
    for p, a in zip(probabilities, actual):
        target = 1.0 if a > 0 else 0.0
        p_clipped = max(eps, min(1 - eps, p))
        total -= target * math.log(p_clipped) + (1 - target) * math.log(1 - p_clipped)
    return total / len(probabilities)


def compute_calibration_error(
    probabilities: list[float], actual: list[float], n_bins: int = 10
) -> float:
    if not probabilities or not actual:
        return 0.0
    bins: dict[int, list[tuple[float, float]]] = {}
    for p, a in zip(probabilities, actual):
        bin_idx = min(int(p * n_bins), n_bins - 1)
        bins.setdefault(bin_idx, []).append((p, a))
    total_error = 0.0
    total_count = 0
    for bin_idx, items in bins.items():
        bin_start = bin_idx / n_bins
        bin_end = (bin_idx + 1) / n_bins
        expected_prob = (bin_start + bin_end) / 2.0
        actual_positive_rate = sum(1 for _, a in items if a > 0) / len(items)
        bin_error = abs(expected_prob - actual_positive_rate)
        total_error += bin_error * len(items)
        total_count += len(items)
    return total_error / total_count if total_count > 0 else 0.0


def compute_average_return(returns: list[float]) -> float:
    if not returns:
        return 0.0
    return sum(returns) / len(returns)


def compute_volatility(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return var**0.5


def compute_max_drawdown(returns: list[float]) -> float:
    if not returns:
        return 0.0
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        cumulative *= 1 + r
        peak = max(peak, cumulative)
        dd = (peak - cumulative) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def compute_sharpe_ratio(
    returns: list[float], risk_free_rate: float = 0.0
) -> float:
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free_rate for r in returns]
    mean = sum(excess) / len(excess)
    var = sum((r - mean) ** 2 for r in excess) / (len(excess) - 1)
    std = var**0.5
    return mean / std if std > 0 else 0.0


def compute_profit_factor(returns: list[float]) -> float:
    if not returns:
        return 0.0
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    return gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0


def compute_all_metrics(
    predicted: list[float],
    actual: list[float],
    probabilities: list[float] | None = None,
    returns: list[float] | None = None,
    baseline_returns: list[float] | None = None,
) -> EvaluationMetrics:
    da = compute_directional_accuracy(predicted, actual)
    prec = compute_precision(predicted, actual)
    rec = compute_recall(predicted, actual)
    f1 = compute_f1(prec, rec)
    probs = probabilities if probabilities else [0.5] * len(predicted)
    roc = compute_roc_auc(probs, actual)
    brier = compute_brier_score(probs, actual)
    ll = compute_log_loss(probs, actual)
    cal = compute_calibration_error(probs, actual)
    rets = returns if returns else [0.0] * len(predicted)
    avg_ret = compute_average_return(rets)
    vol = compute_volatility(rets)
    mdd = compute_max_drawdown(rets)
    sr = compute_sharpe_ratio(rets)
    pf = compute_profit_factor(rets)
    baseline_comp = {}
    if baseline_returns:
        baseline_avg = compute_average_return(baseline_returns)
        baseline_comp["excess_return"] = avg_ret - baseline_avg
        baseline_vol = compute_volatility(baseline_returns)
        baseline_comp["volatility_ratio"] = vol / baseline_vol if baseline_vol > 0 else 0.0
    return EvaluationMetrics(
        directional_accuracy=da,
        precision=prec,
        recall=rec,
        f1=f1,
        roc_auc=roc,
        brier_score=brier,
        log_loss=ll,
        calibration_error=cal,
        average_return=avg_ret,
        volatility=vol,
        max_drawdown=mdd,
        sharpe_ratio=sr,
        profit_factor=pf,
        n_observations=len(predicted),
        baseline_comparison=baseline_comp,
    )
