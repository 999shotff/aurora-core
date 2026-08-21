"""Benchmark orchestrator: defines hypotheses, runs all experiments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aurora.benchmark.data import OHLCVDataset
from aurora.benchmark.features import (
    atr_ratio,
    fibonacci_retracement_level,
    liquidity_sweep,
    market_structure_break,
    momentum_signal,
    rsi_signal,
    volume_price_divergence,
    vwap_deviation,
)
from aurora.benchmark.preregistration import MethodologyFamily, PreRegistration, PreRegistrationLog
from aurora.benchmark.registry import CandidateRegistry, EvidenceStatus, FeatureCandidate
from aurora.benchmark.runner import ExperimentResult, run_experiment


def create_all_preregistrations() -> PreRegistrationLog:
    log = PreRegistrationLog()
    log.register(PreRegistration(
        experiment_id="EXP002",
        hypothesis_id="H002",
        methodology=MethodologyFamily.FIBONACCI,
        hypothesis_text="Price respects Fibonacci 0.618 retracement level as support/resistance",
        expected_direction="mean_reversion toward 0.618 level",
        feature_formula="fib_distance = (close - (low + 0.618 * (high - low))) / close",
        parameters={"swing_window": 20, "ratio": 0.618},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="3d88aa766403f953_p295_cadcf2be2",
        source_document="Carolyn_Borden_Fibonacci_Trading (1).pdf",
        source_page=295,
    ))
    log.register(PreRegistration(
        experiment_id="EXP003",
        hypothesis_id="H003",
        methodology=MethodologyFamily.VOLATILITY,
        hypothesis_text="ATR expansion predicts continued elevated volatility and directional movement",
        expected_direction="ATR ratio > 1 predicts trending continuation",
        feature_formula="atr_ratio = ATR(14) / ATR(50)",
        parameters={"short_window": 14, "long_window": 50},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="0973976867d6b506_p97_c32ec2c40",
        source_document="Trading-Volatility (1).pdf",
        source_page=97,
    ))
    log.register(PreRegistration(
        experiment_id="EXP004",
        hypothesis_id="H004",
        methodology=MethodologyFamily.LIQUIDITY,
        hypothesis_text="Liquidity sweep of recent high/low followed by reversal predicts price direction",
        expected_direction="buy after sell-side sweep, sell after buy-side sweep",
        feature_formula="sweep = 1 if low < prev_low and close > prev_low; -1 if high > prev_high and close < prev_high",
        parameters={"lookback": 20},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="b2280f4443f2611f_p9_c07acebd0",
        source_document="Liquidity-Sweep-in-Trading.pdf",
        source_page=9,
    ))
    log.register(PreRegistration(
        experiment_id="EXP005",
        hypothesis_id="H005",
        methodology=MethodologyFamily.VOLUME,
        hypothesis_text="Volume divergence (price up, volume down) precedes price reversals",
        expected_direction="bearish divergence when price rising and volume falling",
        feature_formula="div = -1 if price_slope > 0 and vol_slope < 0; 1 if price_slope < 0 and vol_slope > 0",
        parameters={"window": 20},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="6cc3bf8840a7e6d9",
        source_document="Volume-Divergence.pdf",
        source_page=1,
    ))
    log.register(PreRegistration(
        experiment_id="EXP006",
        hypothesis_id="H006",
        methodology=MethodologyFamily.VWAP,
        hypothesis_text="Price reverts to VWAP when far from it; VWAP acts as fair value",
        expected_direction="mean reversion toward VWAP",
        feature_formula="vwap_dev = (close - VWAP) / VWAP",
        parameters={"window": 20},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="2e15dafca208257c_p7_c33570093",
        source_document="vwap.pdf",
        source_page=7,
    ))
    log.register(PreRegistration(
        experiment_id="EXP007",
        hypothesis_id="H007",
        methodology=MethodologyFamily.MARKET_STRUCTURE,
        hypothesis_text="Break of Structure (BOS) predicts directional continuation",
        expected_direction="buy on bullish BOS, sell on bearish BOS",
        feature_formula="bos = 1 if close > prev_swing_high; -1 if close < prev_swing_low",
        parameters={"lookback": 20},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="5fcfe5efce295a41_p24_c0f91a7e9",
        source_document="15_Scalping_Strategies (1).pdf",
        source_page=24,
    ))
    log.register(PreRegistration(
        experiment_id="EXP008",
        hypothesis_id="H008",
        methodology=MethodologyFamily.MOMENTUM,
        hypothesis_text="14-period momentum predicts continuation in same direction",
        expected_direction="momentum > 0 predicts positive return",
        feature_formula="mom = (close - close[14]) / close[14]",
        parameters={"period": 14},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="5fcfe5efce295a41_p5_ce70606c3",
        source_document="15_Scalping_Strategies (1).pdf",
        source_page=5,
    ))
    log.register(PreRegistration(
        experiment_id="EXP009",
        hypothesis_id="H009",
        methodology=MethodologyFamily.TECHNICAL_ANALYSIS,
        hypothesis_text="RSI oversold/overbought predicts mean reversion",
        expected_direction="RSI < 30 buy, RSI > 70 sell",
        feature_formula="rsi_signal = 1 if RSI(14) < 30; -1 if RSI(14) > 70",
        parameters={"rsi_period": 14, "oversold": 30, "overbought": 70},
        target="future_return over 4-bar horizon",
        horizon_bars=4,
        evaluation_metrics=("directional_accuracy", "sharpe", "mean_return", "max_drawdown", "brier"),
        baseline="buy_and_hold",
        classification_criteria={
            "supported": "DA > baseline+2%, Sharpe>0.3, mean_return>0",
            "weak": "DA > baseline, Sharpe>0 or mean_return>0",
            "rejected": "DA < baseline-2%, mean_return<0",
            "inconclusive": "all others",
        },
        transaction_cost_bps=10.0,
        source_claim_id="5fcfe5efce295a41_p3_c58d9f01b",
        source_document="15_Scalping_Strategies (1).pdf",
        source_page=3,
    ))
    return log


HYPOTHESIS_FEATURE_MAP: dict[str, Callable[..., Any]] = {
    "EXP002": lambda ds: fibonacci_retracement_level(ds.closes(), 20, 0.618),
    "EXP003": lambda ds: atr_ratio(ds.highs(), ds.lows(), ds.closes(), 14, 50),
    "EXP004": lambda ds: liquidity_sweep(ds.highs(), ds.lows(), ds.closes(), 20),
    "EXP005": lambda ds: volume_price_divergence(ds.closes(), ds.volumes(), 20),
    "EXP006": lambda ds: vwap_deviation(ds.closes(), ds.volumes(), 20),
    "EXP007": lambda ds: market_structure_break(ds.highs(), ds.lows(), ds.closes(), 20),
    "EXP008": lambda ds: momentum_signal(ds.closes(), 14),
    "EXP009": lambda ds: rsi_signal(ds.closes(), 14),
}


NO_COMPUTABLE_HYPOTHESIS = [
    MethodologyFamily.ASTROLOGY,
    MethodologyFamily.GANN,
    MethodologyFamily.TIME_CYCLES,
    MethodologyFamily.NO_COMPUTABLE_HYPOTHESIS,
]


def run_all_experiments(
    datasets: dict[str, OHLCVDataset],
) -> tuple[list[ExperimentResult], PreRegistrationLog, CandidateRegistry]:
    log = create_all_preregistrations()
    results: list[ExperimentResult] = []
    registry = CandidateRegistry()

    for exp_id in log.all_ids():
        prereg = log.get(exp_id)
        assert prereg is not None
        feat_fn = HYPOTHESIS_FEATURE_MAP.get(exp_id)
        if feat_fn is None:
            continue
        for instrument, dataset in datasets.items():
            feature_values = feat_fn(dataset)
            result = run_experiment(
                prereg=prereg,
                dataset=dataset,
                feature_values=feature_values,
                horizon_bars=prereg.horizon_bars,
                transaction_cost_bps=prereg.transaction_cost_bps,
            )
            results.append(result)
            status_map = {
                "supported": EvidenceStatus.SUPPORTED,
                "weak": EvidenceStatus.WEAK,
                "rejected": EvidenceStatus.REJECTED,
                "inconclusive": EvidenceStatus.INCONCLUSIVE,
            }
            robustness_score = len([v for v in result.robustness.values() if v > 0.5]) / max(len(result.robustness), 1)
            registry.register(FeatureCandidate(
                feature_id=f"{exp_id}_{instrument}",
                methodology=prereg.methodology.value,
                hypothesis_id=prereg.hypothesis_id,
                evidence_status=status_map.get(result.classification, EvidenceStatus.INCONCLUSIVE),
                oos_directional_accuracy=result.strategy_da,
                oos_mean_return=result.strategy_mean_return,
                oos_sharpe=result.strategy_sharpe,
                robustness_score=robustness_score,
                dataset_coverage=(instrument,),
                implementation_version="1.0.0",
                source_claim_id=prereg.source_claim_id,
            ))
    return results, log, registry
