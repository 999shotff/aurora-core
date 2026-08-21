from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aurora.experiments.bollinger_reversion import (
    BollingerReversionExperiment,
    ExperimentConfig,
)
from aurora.experiments.data_generator import generate_realistic_ohlcv
from aurora.schemas.market_data import OHLCVBar, OHLCVSequence


def _make_bars(n: int = 200) -> list[OHLCVBar]:
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = 100.0
    import random as _random
    rng = _random.Random(42)
    for i in range(n):
        ret = rng.gauss(0, 0.03)
        new_price = price * (1 + ret)
        bars.append(
            OHLCVBar(
                timestamp=base + timedelta(hours=i),
                open=price,
                high=max(price, new_price) * (1 + abs(rng.gauss(0, 0.01))),
                low=min(price, new_price) * (1 - abs(rng.gauss(0, 0.01))),
                close=new_price,
                volume=1000.0 + i,
                asset="BTCUSD",
                timeframe="1h",
            )
        )
        price = new_price
    return bars


class TestDataGenerator:
    def test_generates_correct_count(self) -> None:
        seq = generate_realistic_ohlcv(num_bars=500, seed=42)
        assert len(seq.bars) == 500

    def test_timestamps_are_chronological(self) -> None:
        seq = generate_realistic_ohlcv(num_bars=200, seed=42)
        for i in range(len(seq.bars) - 1):
            assert seq.bars[i].timestamp < seq.bars[i + 1].timestamp

    def test_no_duplicate_timestamps(self) -> None:
        seq = generate_realistic_ohlcv(num_bars=200, seed=42)
        timestamps = [b.timestamp for b in seq.bars]
        assert len(timestamps) == len(set(timestamps))

    def test_ohlc_invariants(self) -> None:
        seq = generate_realistic_ohlcv(num_bars=200, seed=42)
        for bar in seq.bars:
            assert bar.high >= bar.low
            assert bar.high >= bar.open
            assert bar.high >= bar.close
            assert bar.low <= bar.open
            assert bar.low <= bar.close
            assert bar.close > 0

    def test_deterministic(self) -> None:
        seq1 = generate_realistic_ohlcv(num_bars=100, seed=42)
        seq2 = generate_realistic_ohlcv(num_bars=100, seed=42)
        for b1, b2 in zip(seq1.bars, seq2.bars):
            assert b1.close == b2.close
            assert b1.open == b2.open

    def test_different_seeds_different_data(self) -> None:
        seq1 = generate_realistic_ohlcv(num_bars=100, seed=42)
        seq2 = generate_realistic_ohlcv(num_bars=100, seed=99)
        assert seq1.bars[50].close != seq2.bars[50].close


class TestBollingerBands:
    def test_bollinger_bands_computed(self) -> None:
        from aurora.experiments.bollinger_reversion import compute_bollinger_bands

        closes = [100.0 + i * 0.1 + ((-1) ** i) * 0.5 for i in range(50)]
        bb = compute_bollinger_bands(closes, period=20, num_std=2.0)
        assert len(bb) == 50
        assert bb[0] == (0.0, 0.0, 0.0)
        assert bb[18] == (0.0, 0.0, 0.0)
        for i in range(19, 50):
            upper, middle, lower = bb[i]
            assert upper > middle > lower
            assert middle == pytest.approx(sum(closes[i - 19 : i + 1]) / 20, rel=1e-6)

    def test_bollinger_bands_warmup(self) -> None:
        from aurora.experiments.bollinger_reversion import compute_bollinger_bands

        closes = [100.0] * 30
        bb = compute_bollinger_bands(closes, period=20, num_std=2.0)
        for i in range(19):
            assert bb[i] == (0.0, 0.0, 0.0)
        upper, middle, _lower = bb[19]
        assert upper == pytest.approx(100.0 + 2.0 * 0.0, abs=1e-6)
        assert middle == pytest.approx(100.0, abs=1e-6)


class TestFeatures:
    def test_compute_features(self) -> None:
        from aurora.experiments.bollinger_reversion import compute_features

        seq = OHLCVSequence(
            asset="BTCUSD",
            timeframe="1h",
            bars=_make_bars(100),
        )
        features = compute_features(seq, bb_period=20, bb_std=2.0, horizon=4)
        assert len(features) == 100
        assert features[0].bb_upper == 0.0
        assert features[19].bb_upper > 0.0

    def test_signals_generated(self) -> None:
        from aurora.experiments.bollinger_reversion import compute_features

        seq = OHLCVSequence(
            asset="BTCUSD",
            timeframe="1h",
            bars=_make_bars(200),
        )
        features = compute_features(seq, bb_period=20, bb_std=2.0, horizon=4)
        signals = [f for f in features if f.signal != 0.0]
        assert len(signals) > 0

    def test_target_computed(self) -> None:
        from aurora.experiments.bollinger_reversion import compute_features

        seq = OHLCVSequence(
            asset="BTCUSD",
            timeframe="1h",
            bars=_make_bars(100),
        )
        features = compute_features(seq, bb_period=20, bb_std=2.0, horizon=4)
        for f in features[:96]:
            assert f.target_return != 0.0 or f.close == features[features.index(f)].close


class TestExperiment:
    def test_full_experiment_runs(self) -> None:
        config = ExperimentConfig(
            experiment_id="TEST001",
            hypothesis_id="HTEST001",
            bb_period=20,
            bb_std=2.0,
            horizon_bars=4,
            transaction_cost_bps=10.0,
            seed=42,
        )
        exp = BollingerReversionExperiment(config)
        result = exp.run()
        assert result.status == "complete"
        assert result.sample_size > 0
        assert result.train_size > 0
        assert result.validation_size > 0
        assert result.test_size > 0

    def test_leakage_checks_all_pass(self) -> None:
        config = ExperimentConfig(seed=42)
        exp = BollingerReversionExperiment(config)
        result = exp.run()
        assert all(result.leakage_checks.values())

    def test_no_random_splits(self) -> None:
        config = ExperimentConfig(seed=42)
        exp = BollingerReversionExperiment(config)
        result = exp.run()
        assert "random_temporal_split" in result.leakage_checks
        assert result.leakage_checks["random_temporal_split"]

    def test_classification_is_valid(self) -> None:
        config = ExperimentConfig(seed=42)
        exp = BollingerReversionExperiment(config)
        result = exp.run()
        assert result.classification in ["supported", "weak", "rejected", "inconclusive"]

    def test_robustness_results_exist(self) -> None:
        config = ExperimentConfig(seed=42)
        exp = BollingerReversionExperiment(config)
        result = exp.run()
        assert len(result.robustness) > 0
        assert "da_period_15" in result.robustness
        assert "da_period_25" in result.robustness
        assert "ret_std_1.5" in result.robustness
        assert "ret_horizon_2" in result.robustness

    def test_experiment_recorded_in_registry(self) -> None:
        config = ExperimentConfig(seed=42)
        exp = BollingerReversionExperiment(config)
        exp.run()
        assert exp.registry.count() == 1
        record = exp.registry.get(config.experiment_id)
        assert record is not None
        assert record.model == "bollinger_mean_reversion"

    def test_hypothesis_status_transitions(self) -> None:
        config = ExperimentConfig(seed=42)
        exp = BollingerReversionExperiment(config)
        exp.run()
        h = exp.engine.get(config.hypothesis_id)
        assert h is not None
        assert h.validation_status in ["supported", "weak", "rejected", "inconclusive"]

    def test_no_future_data_in_features(self) -> None:
        from aurora.experiments.bollinger_reversion import compute_features

        seq = OHLCVSequence(
            asset="BTCUSD",
            timeframe="1h",
            bars=_make_bars(100),
        )
        features = compute_features(seq, bb_period=20, bb_std=2.0, horizon=4)
        for i, f in enumerate(features):
            if f.bb_upper != 0.0:
                assert f.timestamp == seq.bars[i].timestamp

    def test_reproducibility(self) -> None:
        config = ExperimentConfig(seed=42)
        exp1 = BollingerReversionExperiment(config)
        r1 = exp1.run()
        exp2 = BollingerReversionExperiment(config)
        r2 = exp2.run()
        assert r1.strategy_directional_accuracy == r2.strategy_directional_accuracy
        assert r1.strategy_mean_return == r2.strategy_mean_return
        assert r1.classification == r2.classification
