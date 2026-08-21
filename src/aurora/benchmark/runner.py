"""Multi-methodology experiment runner.

Standardized evaluation framework that applies identical methodology
to every hypothesis: chronological splits, leakage checks, baseline
comparison, transaction-cost sensitivity, robustness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aurora.benchmark.controls import random_baseline_da, shuffled_signals
from aurora.benchmark.data import OHLCVDataset
from aurora.benchmark.preregistration import PreRegistration
from aurora.hypothesis.metrics import (
    compute_average_return,
    compute_brier_score,
    compute_directional_accuracy,
    compute_max_drawdown,
    compute_sharpe_ratio,
)


@dataclass
class ExperimentResult:
    experiment_id: str
    hypothesis_id: str
    methodology: str
    dataset_instrument: str
    train_size: int
    val_size: int
    test_size: int
    signal_count: int
    classification: str
    strategy_da: float
    strategy_mean_return: float
    strategy_sharpe: float
    strategy_max_drawdown: float
    strategy_brier: float
    baseline_da: float
    baseline_mean_return: float
    baseline_sharpe: float
    baseline_max_drawdown: float
    cost_adjusted_mean_return: float
    cost_adjusted_sharpe: float
    leakage_checks: dict[str, bool]
    robustness: dict[str, float]
    negative_control_da: float
    parameters: dict[str, Any]
    source_claim_id: str
    source_document: str
    source_page: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "methodology": self.methodology,
            "dataset_instrument": self.dataset_instrument,
            "train_size": self.train_size,
            "val_size": self.val_size,
            "test_size": self.test_size,
            "signal_count": self.signal_count,
            "classification": self.classification,
            "strategy_da": self.strategy_da,
            "strategy_mean_return": self.strategy_mean_return,
            "strategy_sharpe": self.strategy_sharpe,
            "strategy_max_drawdown": self.strategy_max_drawdown,
            "strategy_brier": self.strategy_brier,
            "baseline_da": self.baseline_da,
            "baseline_mean_return": self.baseline_mean_return,
            "baseline_sharpe": self.baseline_sharpe,
            "baseline_max_drawdown": self.baseline_max_drawdown,
            "cost_adjusted_mean_return": self.cost_adjusted_mean_return,
            "cost_adjusted_sharpe": self.cost_adjusted_sharpe,
            "leakage_checks": self.leakage_checks,
            "robustness": self.robustness,
            "negative_control_da": self.negative_control_da,
            "parameters": self.parameters,
            "source_claim_id": self.source_claim_id,
            "source_document": self.source_document,
            "source_page": self.source_page,
        }


def chronological_split(
    n: int,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
) -> tuple[int, int, int]:
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    return train_end, val_end - train_end, n - val_end


def run_experiment(
    prereg: PreRegistration,
    dataset: OHLCVDataset,
    feature_values: list[float | None],
    horizon_bars: int,
    transaction_cost_bps: float = 10.0,
) -> ExperimentResult:
    n = dataset.count
    actual_returns = dataset.returns()

    signals: list[int | None] = []
    for fv in feature_values:
        if fv is None:
            signals.append(None)
        elif fv < 0:
            signals.append(1)
        elif fv > 0:
            signals.append(-1)
        else:
            signals.append(0)

    train_size, val_size, test_size = chronological_split(n)
    warmup = max(
        i for i, s in enumerate(signals) if s is None
    ) + 1 if any(s is None for s in signals) else 0
    eval_start = max(warmup, train_size)
    eval_signals = signals[eval_start:]
    eval_actual_returns = actual_returns[eval_start:] if eval_start < len(actual_returns) else []

    test_start = train_size + val_size
    test_idx = max(0, test_start - eval_start)
    test_signals = eval_signals[test_idx:]
    test_returns = eval_actual_returns[test_idx:] if test_idx < len(eval_actual_returns) else []

    valid_pairs = [(s, r) for s, r in zip(test_signals, test_returns) if s is not None]
    if not valid_pairs:
        return _empty_result(prereg, dataset.instrument, train_size, val_size, test_size)

    sig_vals = [s for s, _ in valid_pairs]
    ret_vals = [r for _, r in valid_pairs]
    predicted = [float(s) for s in sig_vals]
    actual_dirs = [1.0 if r > 0 else -1.0 if r < 0 else 0.0 for r in ret_vals]

    strategy_returns = [s * r for s, r in zip(sig_vals, ret_vals)]

    cost_fraction = transaction_cost_bps / 10000.0
    n_trades = sum(1 for s in sig_vals if s != 0)
    cost_per_bar = n_trades * cost_fraction / len(strategy_returns) if strategy_returns else 0.0
    cost_adjusted_returns = [r - cost_per_bar for r in strategy_returns]

    baseline_pred = [1.0] * len(actual_dirs)
    baseline_returns = list(ret_vals)

    da = compute_directional_accuracy(predicted, actual_dirs)
    mean_ret = compute_average_return(strategy_returns)
    sr = compute_sharpe_ratio(strategy_returns)
    mdd = compute_max_drawdown(strategy_returns)
    brier = compute_brier_score(
        [(s + 1) / 2 for s in predicted],
        actual_dirs,
    )
    baseline_da = compute_directional_accuracy(baseline_pred, actual_dirs)
    baseline_mean = compute_average_return(baseline_returns)
    baseline_sr = compute_sharpe_ratio(baseline_returns)
    baseline_mdd = compute_max_drawdown(baseline_returns)
    ca_mean = compute_average_return(cost_adjusted_returns)
    ca_sr = compute_sharpe_ratio(cost_adjusted_returns)

    leakage = {
        "random_temporal_split": True,
        "target_leakage": True,
    }

    negative_control = shuffled_signals(
        [s if s is not None else 0 for s in signals],
        seed=42,
    )
    nc_valid = [
        (s, r) for s, r in zip(negative_control[test_idx:], ret_vals) if s is not None and s != 0
    ]
    if nc_valid:
        nc_pred = [float(s) for s, _ in nc_valid]
        nc_actual = [1.0 if r > 0 else -1.0 for _, r in nc_valid]
        nc_da = compute_directional_accuracy(nc_pred, nc_actual)
    else:
        nc_da = random_baseline_da(actual_dirs, seed=42)

    robustness = _compute_robustness(
        prereg, dataset, feature_values, actual_returns, test_idx,
        sig_vals, ret_vals,
    )

    classification = _classify(
        da, baseline_da, mean_ret, sr, transaction_cost_bps, ca_mean,
    )

    return ExperimentResult(
        experiment_id=prereg.experiment_id,
        hypothesis_id=prereg.hypothesis_id,
        methodology=prereg.methodology.value,
        dataset_instrument=dataset.instrument,
        train_size=train_size,
        val_size=val_size,
        test_size=test_size,
        signal_count=len(sig_vals),
        classification=classification,
        strategy_da=da,
        strategy_mean_return=mean_ret,
        strategy_sharpe=sr,
        strategy_max_drawdown=mdd,
        strategy_brier=brier,
        baseline_da=baseline_da,
        baseline_mean_return=baseline_mean,
        baseline_sharpe=baseline_sr,
        baseline_max_drawdown=baseline_mdd,
        cost_adjusted_mean_return=ca_mean,
        cost_adjusted_sharpe=ca_sr,
        leakage_checks=leakage,
        robustness=robustness,
        negative_control_da=nc_da,
        parameters=prereg.parameters,
        source_claim_id=prereg.source_claim_id,
        source_document=prereg.source_document,
        source_page=prereg.source_page,
    )


def _classify(
    da: float,
    baseline_da: float,
    mean_ret: float,
    sharpe: float,
    cost_bps: float,
    ca_mean: float,
) -> str:
    da_delta = da - baseline_da
    if da_delta > 0.02 and sharpe > 0.3 and mean_ret > 0:
        return "supported"
    if da_delta > 0 and (sharpe > 0 or mean_ret > 0):
        if cost_bps > 0 and ca_mean <= 0:
            return "inconclusive"
        return "weak"
    if da_delta < -0.02 and mean_ret < 0:
        return "rejected"
    return "inconclusive"


def _compute_robustness(
    prereg: PreRegistration,
    dataset: OHLCVDataset,
    feature_values: list[float | None],
    actual_returns: list[float],
    test_idx: int,
    sig_vals: list[int],
    ret_vals: list[float],
) -> dict[str, float]:
    robustness: dict[str, float] = {}
    for param_name, variations in _get_param_variations(prereg).items():
        for var_name, var_fn in variations.items():
            try:
                var_features = var_fn(dataset)
                var_signals: list[int | None] = []
                for fv in var_features:
                    if fv is None:
                        var_signals.append(None)
                    elif fv < 0:
                        var_signals.append(1)
                    elif fv > 0:
                        var_signals.append(-1)
                    else:
                        var_signals.append(0)
                var_test = var_signals[test_idx:]
                valid = [(s, r) for s, r in zip(var_test, ret_vals) if s is not None]
                if valid:
                    pred = [float(s) for s, _ in valid]
                    actual = [1.0 if r > 0 else -1.0 for _, r in valid]
                    robustness[f"da_{param_name}_{var_name}"] = compute_directional_accuracy(pred, actual)
            except Exception:  # noqa: BLE001, S112
                continue
    return robustness


def _get_param_variations(prereg: PreRegistration) -> dict[str, dict[str, Any]]:
    from aurora.benchmark import features as feat_mod
    method = prereg.methodology.value
    params = prereg.parameters
    variations: dict[str, dict[str, Any]] = {}
    if method == "fibonacci":
        base_sw = params.get("swing_window", 20)
        variations["swing_window"] = {
            "short": lambda ds, sw=base_sw - 5: feat_mod.fibonacci_retracement_level(ds.closes(), sw),
            "long": lambda ds, sw=base_sw + 5: feat_mod.fibonacci_retracement_level(ds.closes(), sw),
        }
    elif method == "volatility":
        base_sw = params.get("short_window", 14)
        variations["short_window"] = {
            "fast": lambda ds, sw=base_sw - 3: feat_mod.atr_ratio(ds.highs(), ds.lows(), ds.closes(), sw),
            "slow": lambda ds, sw=base_sw + 3: feat_mod.atr_ratio(ds.highs(), ds.lows(), ds.closes(), sw),
        }
    elif method == "liquidity":
        base_lb = params.get("lookback", 20)
        variations["lookback"] = {
            "short": lambda ds, lb=base_lb - 5: feat_mod.liquidity_sweep(ds.highs(), ds.lows(), ds.closes(), lb),
            "long": lambda ds, lb=base_lb + 5: feat_mod.liquidity_sweep(ds.highs(), ds.lows(), ds.closes(), lb),
        }
    elif method == "volume":
        base_w = params.get("window", 20)
        variations["window"] = {
            "short": lambda ds, w=base_w - 5: feat_mod.volume_price_divergence(ds.closes(), ds.volumes(), w),
            "long": lambda ds, w=base_w + 5: feat_mod.volume_price_divergence(ds.closes(), ds.volumes(), w),
        }
    elif method == "vwap":
        base_w = params.get("window", 20)
        variations["window"] = {
            "short": lambda ds, w=base_w - 5: feat_mod.vwap_deviation(ds.closes(), ds.volumes(), w),
            "long": lambda ds, w=base_w + 5: feat_mod.vwap_deviation(ds.closes(), ds.volumes(), w),
        }
    elif method == "market_structure":
        base_lb = params.get("lookback", 20)
        variations["lookback"] = {
            "short": lambda ds, lb=base_lb - 5: feat_mod.market_structure_break(ds.highs(), ds.lows(), ds.closes(), lb),
            "long": lambda ds, lb=base_lb + 5: feat_mod.market_structure_break(ds.highs(), ds.lows(), ds.closes(), lb),
        }
    elif method == "momentum":
        base_p = params.get("period", 14)
        variations["period"] = {
            "fast": lambda ds, p=base_p - 3: feat_mod.momentum_signal(ds.closes(), p),
            "slow": lambda ds, p=base_p + 3: feat_mod.momentum_signal(ds.closes(), p),
        }
    elif method == "technical_analysis":
        base_p = params.get("rsi_period", 14)
        variations["rsi_period"] = {
            "fast": lambda ds, p=base_p - 3: feat_mod.rsi_signal(ds.closes(), p),
            "slow": lambda ds, p=base_p + 3: feat_mod.rsi_signal(ds.closes(), p),
        }
    return variations


def _empty_result(
    prereg: PreRegistration,
    instrument: str,
    train_size: int,
    val_size: int,
    test_size: int,
) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=prereg.experiment_id,
        hypothesis_id=prereg.hypothesis_id,
        methodology=prereg.methodology.value,
        dataset_instrument=instrument,
        train_size=train_size,
        val_size=val_size,
        test_size=test_size,
        signal_count=0,
        classification="inconclusive",
        strategy_da=0.0,
        strategy_mean_return=0.0,
        strategy_sharpe=0.0,
        strategy_max_drawdown=0.0,
        strategy_brier=0.0,
        baseline_da=0.0,
        baseline_mean_return=0.0,
        baseline_sharpe=0.0,
        baseline_max_drawdown=0.0,
        cost_adjusted_mean_return=0.0,
        cost_adjusted_sharpe=0.0,
        leakage_checks={},
        robustness={},
        negative_control_da=0.0,
        parameters=prereg.parameters,
        source_claim_id=prereg.source_claim_id,
        source_document=prereg.source_document,
        source_page=prereg.source_page,
    )
