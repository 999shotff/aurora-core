"""Phase 7.5: Multi-Methodology Evidence Benchmark tests."""

from __future__ import annotations

from aurora.benchmark.controls import (
    noise_features,
    random_baseline_da,
    reversed_signals,
    shuffled_signals,
)
from aurora.benchmark.data import OHLCVBar, OHLCVDataset, fetch_yfinance
from aurora.benchmark.features import (
    atr_ratio,
    fibonacci_extension_level,
    fibonacci_retracement_level,
    liquidity_sweep,
    market_structure_break,
    momentum_signal,
    rsi_signal,
    sma_crossover,
    volume_price_divergence,
    vwap_deviation,
)
from aurora.benchmark.orchestrator import (
    NO_COMPUTABLE_HYPOTHESIS,
    create_all_preregistrations,
    run_all_experiments,
)
from aurora.benchmark.preregistration import MethodologyFamily
from aurora.benchmark.registry import CandidateRegistry, EvidenceStatus, FeatureCandidate
from aurora.benchmark.runner import ExperimentResult, chronological_split, run_experiment
from aurora.benchmark.scorecard import (
    format_scorecard,
    generate_scorecard,
)


def _make_dataset(n: int = 200, instrument: str = "TEST") -> OHLCVDataset:
    from datetime import datetime, timedelta, timezone
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = 100.0
    import random
    rng = random.Random(42)
    for i in range(n):
        ts = base + timedelta(days=i)
        ret = rng.gauss(0.0001, 0.02)
        price *= 1 + ret
        h = price * (1 + abs(rng.gauss(0, 0.01)))
        l = price * (1 - abs(rng.gauss(0, 0.01)))
        v = rng.uniform(1e6, 1e7)
        bars.append(OHLCVBar(ts, price, h, l, price, v))
    return OHLCVDataset(instrument=instrument, timeframe="1d", bars=tuple(bars))


class TestDataAcquisition:
    def test_make_dataset(self):
        ds = _make_dataset(200)
        assert ds.count == 200
        assert ds.instrument == "TEST"
        assert len(ds.closes()) == 200
        assert len(ds.highs()) == 200
        assert len(ds.lows()) == 200
        assert len(ds.volumes()) == 200

    def test_returns_length(self):
        ds = _make_dataset(200)
        rets = ds.returns()
        assert len(rets) == 199

    def test_fetch_yfinance(self):
        ds = fetch_yfinance("BTC-USD", period="5d", interval="1d")
        assert ds.count > 0
        assert ds.instrument == "BTC-USD"
        assert len(ds.closes()) == ds.count


class TestFeatures:
    def test_fibonacci_retracement(self):
        closes = [100.0 + i * 0.5 for i in range(50)]
        result = fibonacci_retracement_level(closes, 20, 0.618)
        assert len(result) == 50
        assert result[19] is None or isinstance(result[19], float)
        assert all(r is not None for r in result[20:])

    def test_fibonacci_extension(self):
        closes = [100.0 + i * 0.5 for i in range(50)]
        result = fibonacci_extension_level(closes, 20, 1.618)
        assert len(result) == 50

    def test_atr_ratio(self):
        n = 100
        highs = [100.0 + i * 0.1 + 1.0 for i in range(n)]
        lows = [100.0 + i * 0.1 - 1.0 for i in range(n)]
        closes = [100.0 + i * 0.1 for i in range(n)]
        result = atr_ratio(highs, lows, closes, 14, 50)
        assert len(result) == n
        assert all(r is not None for r in result[50:])

    def test_liquidity_sweep(self):
        n = 50
        highs = [100.0 + (i % 10) * 0.5 for i in range(n)]
        lows = [99.0 - (i % 10) * 0.5 for i in range(n)]
        closes = [99.5 for _ in range(n)]
        result = liquidity_sweep(highs, lows, closes, 20)
        assert len(result) == n
        assert all(r is not None for r in result[21:])

    def test_volume_price_divergence(self):
        closes = [100.0 + i * 0.1 for i in range(50)]
        volumes = [1e6 - i * 10000 for i in range(50)]
        result = volume_price_divergence(closes, volumes, 20)
        assert len(result) == 50
        assert all(r is not None for r in result[20:])

    def test_vwap_deviation(self):
        closes = [100.0 for _ in range(50)]
        volumes = [1e6 for _ in range(50)]
        result = vwap_deviation(closes, volumes, 20)
        assert len(result) == 50
        for r in result[20:]:
            assert r is not None
            assert abs(r) < 0.001

    def test_market_structure_break(self):
        n = 60
        closes = [100.0 + i * 0.5 for i in range(n)]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        result = market_structure_break(highs, lows, closes, 20)
        assert len(result) == n

    def test_momentum_signal(self):
        closes = [100.0 + i * 0.5 for i in range(50)]
        result = momentum_signal(closes, 14)
        assert len(result) == 50
        assert result[14] is not None
        assert result[14] > 0

    def test_rsi_signal(self):
        closes = [100.0 + i * 0.5 for i in range(50)]
        result = rsi_signal(closes, 14)
        assert len(result) == 50

    def test_sma_crossover(self):
        closes = [100.0 + i * 0.5 for i in range(100)]
        result = sma_crossover(closes, 10, 50)
        assert len(result) == 100


class TestPreRegistration:
    def test_create_all(self):
        log = create_all_preregistrations()
        assert log.count() == 8
        for exp_id in log.all_ids():
            p = log.get(exp_id)
            assert p is not None
            assert p.experiment_id == exp_id
            assert isinstance(p.methodology, MethodologyFamily)

    def test_prereg_to_dict(self):
        log = create_all_preregistrations()
        p = log.get("EXP002")
        d = p.to_dict()
        assert d["experiment_id"] == "EXP002"
        assert "methodology" in d
        assert "registered_at" in d


class TestControls:
    def test_shuffled_signals(self):
        signals = [1, -1, 0, 1, -1, 1, 0, -1]
        result = shuffled_signals(signals, seed=42)
        assert len(result) == len(signals)
        assert sum(1 for s in result if s == 0) == sum(1 for s in signals if s == 0)
        assert sorted(s for s in result if s != 0) == sorted(s for s in signals if s != 0)

    def test_noise_features(self):
        result = noise_features(100, seed=42)
        assert len(result) == 100
        assert all(isinstance(x, float) for x in result)

    def test_reversed_signals(self):
        signals = [1, -1, 0, 1, -1]
        result = reversed_signals(signals)
        assert result == [-1, 1, 0, -1, 1]

    def test_random_baseline_da(self):
        actual = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
        da = random_baseline_da(actual, seed=42)
        assert 0.0 <= da <= 1.0


class TestRegistry:
    def test_register_and_get(self):
        reg = CandidateRegistry()
        c = FeatureCandidate(
            feature_id="test_feat",
            methodology="fibonacci",
            hypothesis_id="H002",
            evidence_status=EvidenceStatus.WEAK,
            oos_directional_accuracy=0.52,
            oos_mean_return=0.001,
            oos_sharpe=0.1,
            robustness_score=0.5,
            dataset_coverage=("BTC-USD",),
            implementation_version="1.0.0",
            source_claim_id="claim123",
        )
        reg.register(c)
        assert reg.count() == 1
        assert reg.get("test_feat") is not None
        assert reg.by_status(EvidenceStatus.WEAK) == [c]

    def test_by_methodology(self):
        reg = CandidateRegistry()
        c1 = FeatureCandidate(
            feature_id="f1", methodology="fibonacci", hypothesis_id="H002",
            evidence_status=EvidenceStatus.WEAK, oos_directional_accuracy=0.52,
            oos_mean_return=0.001, oos_sharpe=0.1, robustness_score=0.5,
            dataset_coverage=("BTC-USD",), implementation_version="1.0.0",
            source_claim_id="c1",
        )
        c2 = FeatureCandidate(
            feature_id="f2", methodology="volatility", hypothesis_id="H003",
            evidence_status=EvidenceStatus.SUPPORTED, oos_directional_accuracy=0.55,
            oos_mean_return=0.002, oos_sharpe=0.3, robustness_score=0.7,
            dataset_coverage=("SPY",), implementation_version="1.0.0",
            source_claim_id="c2",
        )
        reg.register(c1)
        reg.register(c2)
        assert len(reg.by_methodology("fibonacci")) == 1
        assert len(reg.by_methodology("volatility")) == 1


class TestRunner:
    def test_chronological_split(self):
        train, val, test = chronological_split(100, 0.6, 0.2)
        assert train == 60
        assert val == 20
        assert test == 20
        assert train + val + test == 100

    def test_run_experiment(self):
        ds = _make_dataset(200)
        from aurora.benchmark.features import momentum_signal
        features = momentum_signal(ds.closes(), 14)
        log = create_all_preregistrations()
        prereg = log.get("EXP008")
        result = run_experiment(prereg, ds, features, 4, 10.0)
        assert isinstance(result, ExperimentResult)
        assert result.experiment_id == "EXP008"
        assert result.methodology == "momentum"
        assert result.test_size > 0
        assert result.classification in ("supported", "weak", "rejected", "inconclusive")

    def test_run_all_experiments(self):
        ds = _make_dataset(200)
        datasets = {"TEST": ds}
        results, _log, registry = run_all_experiments(datasets)
        assert len(results) == 8
        assert registry.count() == 8


class TestScorecard:
    def test_generate_scorecard(self):
        ds = _make_dataset(200)
        datasets = {"TEST": ds}
        results, log, registry = run_all_experiments(datasets)
        scorecard = generate_scorecard(results, log, registry)
        assert len(scorecard) == 8
        formatted = format_scorecard(scorecard)
        assert "METHODOLOGY SCORECARD" in formatted


class TestNoComputableHypothesis:
    def test_rejected_methodologies(self):
        assert MethodologyFamily.ASTROLOGY in NO_COMPUTABLE_HYPOTHESIS
        assert MethodologyFamily.GANN in NO_COMPUTABLE_HYPOTHESIS
        assert MethodologyFamily.TIME_CYCLES in NO_COMPUTABLE_HYPOTHESIS
