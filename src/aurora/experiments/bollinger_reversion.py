from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from aurora.experiments.data_generator import generate_realistic_ohlcv
from aurora.hypothesis.engine import HypothesisEngine, TestableHypothesis
from aurora.hypothesis.metrics import (
    compute_average_return,
    compute_brier_score,
    compute_directional_accuracy,
    compute_max_drawdown,
    compute_sharpe_ratio,
)
from aurora.hypothesis.multiple_testing import MultipleTestingRecorder
from aurora.hypothesis.provenance import FeatureProvenanceRegistry, ProvenanceRecord
from aurora.hypothesis.registry import ExperimentRecord, ExperimentRegistry
from aurora.schemas.market_data import OHLCVSequence
from aurora.temporal.leakage import (
    LeakageDetector,
    check_feature_timestamp_leakage,
    check_overlapping_horizons,
    check_random_temporal_split,
    check_target_leakage,
)


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    dataset_id: str
    dataset_version: str = "1.0.0"
    source: str = "synthetic"
    instrument: str = "BTCUSD"
    timeframe: str = "1h"
    start_date: datetime
    end_date: datetime
    bar_count: int
    has_volume: bool = True


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    experiment_id: str = "EXP001"
    hypothesis_id: str = "H001"
    bb_period: int = 20
    bb_std: float = 2.0
    horizon_bars: int = 4
    transaction_cost_bps: float = 10.0
    train_ratio: float = 0.6
    validation_ratio: float = 0.2
    test_ratio: float = 0.2
    seed: int = 42
    annual_vol: float = 0.8
    mean_revert_speed: float = 0.01


class ExperimentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    experiment_id: str
    hypothesis_id: str
    dataset_id: str
    status: str = "pending"
    config: ExperimentConfig
    dataset_spec: DatasetSpec
    sample_size: int = 0
    train_size: int = 0
    validation_size: int = 0
    test_size: int = 0
    signal_count: int = 0
    baseline_directional_accuracy: float = 0.0
    strategy_directional_accuracy: float = 0.0
    baseline_mean_return: float = 0.0
    strategy_mean_return: float = 0.0
    baseline_sharpe: float = 0.0
    strategy_sharpe: float = 0.0
    baseline_max_drawdown: float = 0.0
    strategy_max_drawdown: float = 0.0
    baseline_brier: float = 0.0
    strategy_brier: float = 0.0
    leakage_checks: dict[str, bool] = Field(default_factory=dict)
    robustness: dict[str, float] = Field(default_factory=dict)
    classification: str = "pending"
    notes: str = ""


@dataclass
class BarFeatures:
    timestamp: datetime
    close: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    signal: float
    direction: float
    target_return: float
    target_direction: float


def compute_bollinger_bands(
    closes: list[float], period: int = 20, num_std: float = 2.0
) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append((0.0, 0.0, 0.0))
            continue
        window = closes[i - period + 1 : i + 1]
        mean = sum(window) / period
        var = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(var)
        upper = mean + num_std * std
        lower = mean - num_std * std
        result.append((upper, mean, lower))
    return result


def compute_features(
    sequence: OHLCVSequence,
    bb_period: int = 20,
    bb_std: float = 2.0,
    horizon: int = 4,
) -> list[BarFeatures]:
    bars = sequence.bars
    closes = [b.close for b in bars]
    bb = compute_bollinger_bands(closes, bb_period, bb_std)
    features: list[BarFeatures] = []
    for i in range(len(bars)):
        upper, middle, lower = bb[i]
        if upper == 0.0 and middle == 0.0 and lower == 0.0:
            features.append(
                BarFeatures(
                    timestamp=bars[i].timestamp,
                    close=closes[i],
                    bb_upper=0.0,
                    bb_middle=0.0,
                    bb_lower=0.0,
                    signal=0.0,
                    direction=0.0,
                    target_return=0.0,
                    target_direction=0.0,
                )
            )
            continue
        price = closes[i]
        signal = 0.0
        if price <= lower:
            signal = 1.0
        elif price >= upper:
            signal = -1.0
        end_idx = i + horizon
        if end_idx < len(closes):
            entry = closes[i]
            exit_price = closes[end_idx]
            ret = (exit_price - entry) / entry if entry != 0 else 0.0
            if exit_price > entry:
                direction = 1.0
            elif exit_price < entry:
                direction = -1.0
            else:
                direction = 0.0
        else:
            ret = 0.0
            direction = 0.0
        features.append(
            BarFeatures(
                timestamp=bars[i].timestamp,
                close=price,
                bb_upper=upper,
                bb_middle=middle,
                bb_lower=lower,
                signal=signal,
                direction=direction,
                target_return=ret,
                target_direction=direction,
            )
        )
    return features


def split_features(
    features: list[BarFeatures],
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
) -> tuple[list[BarFeatures], list[BarFeatures], list[BarFeatures]]:
    warmup = 0
    for i, f in enumerate(features):
        if f.bb_upper != 0.0:
            warmup = i
            break
    usable = features[warmup:]
    n_usable = len(usable)
    train_end = int(n_usable * train_ratio)
    val_end = train_end + int(n_usable * val_ratio)
    return usable[:train_end], usable[train_end:val_end], usable[val_end:]


def evaluate_strategy(
    features: list[BarFeatures],
    cost_bps: float = 10.0,
) -> dict[str, float]:
    if not features:
        return {
            "directional_accuracy": 0.0,
            "mean_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "brier": 0.0,
            "n_signals": 0.0,
        }
    signals = [(f.signal, f.target_return, f.target_direction) for f in features if f.signal != 0.0]
    if not signals:
        return {
            "directional_accuracy": 0.0,
            "mean_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "brier": 0.0,
            "n_signals": 0.0,
        }
    predicted = [s[0] for s in signals]
    actual_returns = [s[1] for s in signals]
    actual_dirs = [s[2] for s in signals]
    strategy_returns = []
    for sig, ret in zip(predicted, actual_returns):
        cost = cost_bps / 10000.0
        strat_ret = sig * ret - cost
        strategy_returns.append(strat_ret)
    da = compute_directional_accuracy(predicted, actual_dirs)
    mean_ret = compute_average_return(strategy_returns)
    sr = compute_sharpe_ratio(strategy_returns)
    mdd = compute_max_drawdown(strategy_returns)
    probs = [max(0.0, min(1.0, 0.5 + 0.5 * p)) for p in predicted]
    brier = compute_brier_score(probs, [d > 0 for d in actual_dirs])
    return {
        "directional_accuracy": da,
        "mean_return": mean_ret,
        "sharpe": sr,
        "max_drawdown": mdd,
        "brier": brier,
        "n_signals": float(len(signals)),
    }


def evaluate_baseline(
    features: list[BarFeatures],
    cost_bps: float = 10.0,
) -> dict[str, float]:
    if not features:
        return {
            "directional_accuracy": 0.0,
            "mean_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "brier": 0.0,
        }
    actual_returns = [f.target_return for f in features]
    actual_dirs = [f.target_direction for f in features]
    buy_hold_returns = [r - cost_bps / 10000.0 for r in actual_returns]
    da = 0.0
    if actual_dirs:
        positive = sum(1 for d in actual_dirs if d > 0)
        da = positive / len(actual_dirs)
    mean_ret = compute_average_return(buy_hold_returns)
    sr = compute_sharpe_ratio(buy_hold_returns)
    mdd = compute_max_drawdown(buy_hold_returns)
    probs = [0.5] * len(features)
    brier = compute_brier_score(probs, [d > 0 for d in actual_dirs])
    return {
        "directional_accuracy": da,
        "mean_return": mean_ret,
        "sharpe": sr,
        "max_drawdown": mdd,
        "brier": brier,
    }


class BollingerReversionExperiment:
    def __init__(self, config: ExperimentConfig | None = None) -> None:
        self.config = config or ExperimentConfig()
        self.engine = HypothesisEngine()
        self.provenance = FeatureProvenanceRegistry()
        self.registry = ExperimentRegistry()
        self.multiple_testing = MultipleTestingRecorder()
        self.leakage_detector = LeakageDetector()

    def run(self) -> ExperimentResult:
        self._create_hypothesis()
        self._register_features()
        dataset_spec = self._get_dataset_spec()
        sequence = self._load_dataset()
        features = compute_features(
            sequence,
            bb_period=self.config.bb_period,
            bb_std=self.config.bb_std,
            horizon=self.config.horizon_bars,
        )
        train, val, test = split_features(
            features,
            train_ratio=self.config.train_ratio,
            val_ratio=self.config.validation_ratio,
        )
        self._run_leakage_checks(features, train, val, test)
        if not self.leakage_detector.all_passed():
            self.engine.transition(self.config.hypothesis_id, "implemented")
            self.engine.transition(self.config.hypothesis_id, "testing")
            self.engine.transition(self.config.hypothesis_id, "rejected")
            return ExperimentResult(
                experiment_id=self.config.experiment_id,
                hypothesis_id=self.config.hypothesis_id,
                dataset_id=dataset_spec.dataset_id,
                status="EXPERIMENT_FAILED_LEAKAGE",
                config=self.config,
                dataset_spec=dataset_spec,
                sample_size=len(features),
                train_size=len(train),
                validation_size=len(val),
                test_size=len(test),
                leakage_checks={
                    c.leakage_type: c.passed for c in self.leakage_detector.checks
                },
                classification="rejected",
                notes="Leakage detected. Results invalid.",
            )
        strategy_test = evaluate_strategy(test, self.config.transaction_cost_bps)
        baseline_test = evaluate_baseline(test, self.config.transaction_cost_bps)
        strategy_val = evaluate_strategy(val, self.config.transaction_cost_bps)
        robustness = self._run_robustness(sequence)
        self._record_experiment(
            dataset_spec, strategy_test, baseline_test, len(train), len(val), len(test)
        )
        classification = self._classify(strategy_test, baseline_test)
        self.engine.transition(self.config.hypothesis_id, "implemented")
        self.engine.transition(self.config.hypothesis_id, "testing")
        self.engine.transition(self.config.hypothesis_id, classification)  # type: ignore[arg-type]
        notes = self._build_notes(
            strategy_test, baseline_test, strategy_val, robustness, classification
        )
        return ExperimentResult(
            experiment_id=self.config.experiment_id,
            hypothesis_id=self.config.hypothesis_id,
            dataset_id=dataset_spec.dataset_id,
            status="complete",
            config=self.config,
            dataset_spec=dataset_spec,
            sample_size=len(features),
            train_size=len(train),
            validation_size=len(val),
            test_size=len(test),
            signal_count=int(strategy_test["n_signals"]),
            baseline_directional_accuracy=baseline_test["directional_accuracy"],
            strategy_directional_accuracy=strategy_test["directional_accuracy"],
            baseline_mean_return=baseline_test["mean_return"],
            strategy_mean_return=strategy_test["mean_return"],
            baseline_sharpe=baseline_test["sharpe"],
            strategy_sharpe=strategy_test["sharpe"],
            baseline_max_drawdown=baseline_test["max_drawdown"],
            strategy_max_drawdown=strategy_test["max_drawdown"],
            baseline_brier=baseline_test["brier"],
            strategy_brier=strategy_test["brier"],
            leakage_checks={
                c.leakage_type: c.passed for c in self.leakage_detector.checks
            },
            robustness=robustness,
            classification=classification,
            notes=notes,
        )

    def _create_hypothesis(self) -> TestableHypothesis:
        hypothesis = TestableHypothesis(
            hypothesis_id=self.config.hypothesis_id,
            source_claim_ids=["5fcfe5efce295a41_p7_cceea66a0"],
            methodology="technical_analysis",
            condition=(
                f"close <= BB_lower({self.config.bb_period},{self.config.bb_std}) => BUY; "
                f"close >= BB_upper({self.config.bb_period},{self.config.bb_std}) => SELL"
            ),
            feature_requirements=["bb_upper", "bb_middle", "bb_lower", "bb_signal"],
            target="future_return",
            horizon=f"{self.config.horizon_bars}h",
            direction="mean_reversion",
            assumptions=[
                "Price tends to revert to the middle band after touching outer bands",
                "Bollinger Bands parameters: period=20, std=2.0",
                "Transaction costs: 10 bps per trade",
                "No position sizing optimization",
                "Synthetic data with mean-revert properties",
            ],
            implementation_status="not_implemented",
            validation_status="untested",
            notes="Bollinger Band mean-reversion hypothesis from scalping strategies research",
        )
        self.engine.register(hypothesis)
        return hypothesis

    def _register_features(self) -> None:
        features: list[tuple[str, str, dict[str, str | int | float | bool]]] = [
            (
                "bb_upper",
                f"SMA(close, {self.config.bb_period}) + {self.config.bb_std} * StdDev(close, {self.config.bb_period})",
                {"period": self.config.bb_period, "num_std": self.config.bb_std},
            ),
            (
                "bb_middle",
                f"SMA(close, {self.config.bb_period})",
                {"period": self.config.bb_period},
            ),
            (
                "bb_lower",
                f"SMA(close, {self.config.bb_period}) - {self.config.bb_std} * StdDev(close, {self.config.bb_period})",
                {"period": self.config.bb_period, "num_std": self.config.bb_std},
            ),
            (
                "bb_signal",
                "1.0 if close <= bb_lower else (-1.0 if close >= bb_upper else 0.0)",
                {"entry_rule": "mean_reversion"},
            ),
        ]
        for name, formula, params in features:
            self.provenance.register(
                ProvenanceRecord(
                    feature_name=name,
                    source="close",
                    formula=formula,
                    parameters=params,
                    methodology="technical_analysis",
                    source_claim_id="5fcfe5efce295a41_p7_cceea66a0",
                    implementation_version="1.0.0",
                )
            )

    def _get_dataset_spec(self) -> DatasetSpec:
        return DatasetSpec(
            dataset_id="synthetic_btc_1h",
            dataset_version="1.0.0",
            source="synthetic_realistic",
            instrument="BTCUSD",
            timeframe="1h",
            start_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2022, 12, 31, 23, 0, tzinfo=timezone.utc),
            bar_count=8760,
            has_volume=True,
        )

    def _load_dataset(self) -> OHLCVSequence:
        return generate_realistic_ohlcv(
            asset="BTCUSD",
            timeframe="1h",
            num_bars=8760,
            base_price=30000.0,
            annual_drift=0.0,
            annual_vol=self.config.annual_vol,
            mean_revert_speed=self.config.mean_revert_speed,
            mean_revert_target=0.0,
            seed=self.config.seed,
        )

    def _run_leakage_checks(
        self,
        all_features: list[BarFeatures],
        train: list[BarFeatures],
        val: list[BarFeatures],
        test: list[BarFeatures],
    ) -> None:
        from datetime import timedelta

        self.leakage_detector.reset()
        feature_ts = [f.timestamp for f in all_features]
        pred_ts = [f.timestamp for f in all_features]
        self.leakage_detector.add_check(
            check_feature_timestamp_leakage(feature_ts, pred_ts)
        )
        train_ts = [f.timestamp for f in train]
        test_ts = [f.timestamp for f in test]
        self.leakage_detector.add_check(
            check_random_temporal_split(train_ts, test_ts)
        )
        horizon = self.config.horizon_bars
        target_end_ts = [f.timestamp + timedelta(hours=horizon) for f in all_features]
        self.leakage_detector.add_check(
            check_target_leakage(feature_ts, target_end_ts)
        )
        windows = [
            (train[0].timestamp, train[-1].timestamp),
            (val[0].timestamp, val[-1].timestamp),
            (test[0].timestamp, test[-1].timestamp),
        ]
        self.leakage_detector.add_check(check_overlapping_horizons(windows))

    def _classify(
        self,
        strategy: dict[str, float],
        baseline: dict[str, float],
    ) -> str:
        da = strategy["directional_accuracy"]
        baseline_da = baseline["directional_accuracy"]
        sr = strategy["sharpe"]
        mean_ret = strategy["mean_return"]
        if da > baseline_da + 0.02 and sr > 0.3 and mean_ret > 0:
            return "supported"
        elif da > baseline_da and (sr > 0.0 or mean_ret > 0):
            return "weak"
        elif da < baseline_da - 0.02 and mean_ret < 0:
            return "rejected"
        else:
            return "inconclusive"

    def _run_robustness(self, sequence: OHLCVSequence) -> dict[str, float]:
        results: dict[str, float] = {}
        for period in [15, 20, 25]:
            features = compute_features(
                sequence,
                bb_period=period,
                bb_std=self.config.bb_std,
                horizon=self.config.horizon_bars,
            )
            _, _, test = split_features(
                features,
                train_ratio=self.config.train_ratio,
                val_ratio=self.config.validation_ratio,
            )
            ev = evaluate_strategy(test, self.config.transaction_cost_bps)
            results[f"da_period_{period}"] = ev["directional_accuracy"]
            results[f"ret_period_{period}"] = ev["mean_return"]
        for std_val in [1.5, 2.0, 2.5]:
            features = compute_features(
                sequence,
                bb_period=self.config.bb_period,
                bb_std=std_val,
                horizon=self.config.horizon_bars,
            )
            _, _, test = split_features(
                features,
                train_ratio=self.config.train_ratio,
                val_ratio=self.config.validation_ratio,
            )
            ev = evaluate_strategy(test, self.config.transaction_cost_bps)
            results[f"da_std_{std_val}"] = ev["directional_accuracy"]
            results[f"ret_std_{std_val}"] = ev["mean_return"]
        for horizon in [2, 4, 8]:
            features = compute_features(
                sequence,
                bb_period=self.config.bb_period,
                bb_std=self.config.bb_std,
                horizon=horizon,
            )
            _, _, test = split_features(
                features,
                train_ratio=self.config.train_ratio,
                val_ratio=self.config.validation_ratio,
            )
            ev = evaluate_strategy(test, self.config.transaction_cost_bps)
            results[f"da_horizon_{horizon}"] = ev["directional_accuracy"]
            results[f"ret_horizon_{horizon}"] = ev["mean_return"]
        for cost in [0.0, 5.0, 10.0, 20.0]:
            features = compute_features(
                sequence,
                bb_period=self.config.bb_period,
                bb_std=self.config.bb_std,
                horizon=self.config.horizon_bars,
            )
            _, _, test = split_features(
                features,
                train_ratio=self.config.train_ratio,
                val_ratio=self.config.validation_ratio,
            )
            ev = evaluate_strategy(test, cost)
            results[f"ret_cost_{cost}bps"] = ev["mean_return"]
        return results

    def _record_experiment(
        self,
        dataset_spec: DatasetSpec,
        strategy: dict[str, float],
        baseline: dict[str, float],
        train_size: int,
        val_size: int,
        test_size: int,
    ) -> None:
        from aurora.hypothesis.metrics import EvaluationMetrics

        record = ExperimentRecord(
            experiment_id=self.config.experiment_id,
            hypothesis_id=self.config.hypothesis_id,
            dataset_version=dataset_spec.dataset_version,
            feature_version="1.0.0",
            model="bollinger_mean_reversion",
            parameters={
                "bb_period": self.config.bb_period,
                "bb_std": self.config.bb_std,
                "horizon_bars": self.config.horizon_bars,
                "transaction_cost_bps": self.config.transaction_cost_bps,
            },
            temporal_split=f"train={train_size},val={val_size},test={test_size}",
            metrics=EvaluationMetrics(
                directional_accuracy=strategy["directional_accuracy"],
                brier_score=strategy["brier"],
                average_return=strategy["mean_return"],
                volatility=0.0,
                max_drawdown=strategy["max_drawdown"],
                sharpe_ratio=strategy["sharpe"],
                n_observations=test_size,
            ),
            code_version="0.1.0",
            status="complete",
        )
        self.registry.register(record)
        self.multiple_testing.record_pvalue(
            self.config.hypothesis_id,
            self.config.experiment_id,
            1.0 - strategy["directional_accuracy"],
        )

    def _build_notes(
        self,
        strategy: dict[str, float],
        baseline: dict[str, float],
        val_strategy: dict[str, float],
        robustness: dict[str, float],
        classification: str,
    ) -> str:
        lines = [
            f"Classification: {classification}",
            f"Test DA: {strategy['directional_accuracy']:.4f} vs baseline {baseline['directional_accuracy']:.4f}",
            f"Test Mean Return: {strategy['mean_return']:.6f} vs baseline {baseline['mean_return']:.6f}",
            f"Test Sharpe: {strategy['sharpe']:.4f} vs baseline {baseline['sharpe']:.4f}",
            f"Test Max DD: {strategy['max_drawdown']:.4f} vs baseline {baseline['max_drawdown']:.4f}",
            f"Val DA: {val_strategy['directional_accuracy']:.4f}",
            f"Val Mean Return: {val_strategy['mean_return']:.6f}",
            f"Val Sharpe: {val_strategy['sharpe']:.4f}",
            f"Signals: {strategy['n_signals']:.0f}",
            "Robustness:",
        ]
        for k, v in robustness.items():
            lines.append(f"  {k}: {v:.4f}")
        return "\n".join(lines)
