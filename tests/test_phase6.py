from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aurora.hypothesis.baselines import (
    BaselineModel,
    create_all_baselines,
)
from aurora.hypothesis.bridge import ClaimFeatureBridge
from aurora.hypothesis.engine import (
    HypothesisEngine,
    TestableHypothesis,
)
from aurora.hypothesis.metrics import (
    EvaluationMetrics,
    compute_all_metrics,
    compute_average_return,
    compute_brier_score,
    compute_calibration_error,
    compute_directional_accuracy,
    compute_f1,
    compute_log_loss,
    compute_max_drawdown,
    compute_precision,
    compute_profit_factor,
    compute_recall,
    compute_roc_auc,
    compute_sharpe_ratio,
)
from aurora.hypothesis.metrics import (
    compute_volatility as compute_volatility_metric,
)
from aurora.hypothesis.multiple_testing import (
    MultipleTestingRecorder,
)
from aurora.hypothesis.provenance import (
    FeatureProvenanceRegistry,
    ProvenanceRecord,
)
from aurora.hypothesis.registry import (
    ExperimentFamily,
    ExperimentRecord,
    ExperimentRegistry,
)
from aurora.hypothesis.synthetic import (
    SyntheticGenerator,
)
from aurora.hypothesis.targets import (
    TargetCalculator,
    TargetDefinition,
    compute_future_direction,
    compute_future_return,
    compute_maximum_adverse_excursion,
    compute_maximum_favorable_excursion,
    compute_volatility,
)
from aurora.hypothesis.timestamps import (
    TimestampValidator,
)
from aurora.research.claims import ResearchClaim
from aurora.research.hypotheses import ResearchHypothesis
from aurora.schemas.market_data import OHLCVBar, OHLCVSequence
from aurora.temporal.leakage import (
    LeakageDetector,
    check_feature_timestamp_leakage,
    check_normalization_leakage,
    check_overlapping_horizons,
    check_random_temporal_split,
    check_target_leakage,
)
from aurora.temporal.splits import (
    ChronologicalSplitter,
    ExpandingWindowSplitter,
    RollingWindowSplitter,
    WalkForwardSplitter,
)


def _make_bars(n: int = 100, start_price: float = 100.0) -> list[OHLCVBar]:
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = start_price
    for i in range(n):
        ret = 0.001 * ((-1) ** i)
        new_price = price * (1 + ret)
        bars.append(
            OHLCVBar(
                timestamp=base + timedelta(hours=i),
                open=price,
                high=max(price, new_price) * 1.001,
                low=min(price, new_price) * 0.999,
                close=new_price,
                volume=1000.0 + i,
                asset="BTCUSD",
                timeframe="1h",
            )
        )
        price = new_price
    return bars


def _make_sequence(n: int = 100) -> OHLCVSequence:
    return OHLCVSequence(
        asset="BTCUSD",
        timeframe="1h",
        bars=_make_bars(n),
    )


def _make_claim() -> ResearchClaim:
    return ResearchClaim(
        claim_id="claim_001",
        document_id="doc_001",
        page=1,
        source_text="When RSI is below 30, expect bullish reversal",
        normalized_text="RSI below 30 predicts bullish reversal",
        claim_type="hypothesis",
        methodology="technical_analysis",
        methodology_confidence=0.8,
        methodology_evidence=["RSI", "bullish", "reversal"],
        extraction_method="rule_based",
        extraction_confidence=0.9,
        validation_status="unreviewed",
        source_file="test.pdf",
        source_sha256="abc123",
        source_hash="def456",
    )


def _make_research_hypothesis() -> ResearchHypothesis:
    return ResearchHypothesis(
        hypothesis_id="hyp_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        methodology="technical_analysis",
        condition="RSI < 30",
        expected_effect="bullish reversal",
        target_variable="future_return",
        horizon="swing",
        direction="long",
        confidence=0.6,
        test_status="untested",
    )


class TestHypothesisSchema:
    def test_create_hypothesis(self) -> None:
        h = TestableHypothesis(
            hypothesis_id="h1",
            methodology="fibonacci",
            condition="price at 0.618 retracement",
            target="future_return",
            direction="long",
        )
        assert h.hypothesis_id == "h1"
        assert h.methodology == "fibonacci"
        assert h.validation_status == "untested"

    def test_transition_untested_to_implemented(self) -> None:
        h = TestableHypothesis(
            hypothesis_id="h1",
            methodology="fibonacci",
        )
        h.transition_to("implemented")
        assert h.validation_status == "implemented"

    def test_transition_untested_to_supported_rejected(self) -> None:
        h = TestableHypothesis(
            hypothesis_id="h1",
            methodology="gann",
        )
        with pytest.raises(ValueError):
            h.transition_to("supported")

    def test_transition_testing_to_supported(self) -> None:
        h = TestableHypothesis(
            hypothesis_id="h1",
            methodology="astrology",
        )
        h.transition_to("implemented")
        h.transition_to("testing")
        h.transition_to("supported")
        assert h.validation_status == "supported"

    def test_transition_supported_to_rejected(self) -> None:
        h = TestableHypothesis(
            hypothesis_id="h1",
            methodology="liquidity",
        )
        h.transition_to("implemented")
        h.transition_to("testing")
        h.transition_to("supported")
        h.transition_to("rejected")
        assert h.validation_status == "rejected"

    def test_invalid_transition_blocked(self) -> None:
        h = TestableHypothesis(
            hypothesis_id="h1",
            methodology="market_structure",
        )
        with pytest.raises(ValueError, match="Invalid transition"):
            h.transition_to("testing")

    def test_all_methodologies_equal(self) -> None:
        methods = ["fibonacci", "gann", "astrology", "liquidity", "market_structure", "news", "time_cycles", "technical_analysis"]
        for m in methods:
            h = TestableHypothesis(
                hypothesis_id=f"h_{m}",
                methodology=m,
            )
            assert h.validation_status == "untested"
            assert h.methodology == m


class TestHypothesisEngine:
    def test_register_and_get(self) -> None:
        engine = HypothesisEngine()
        h = TestableHypothesis(hypothesis_id="h1", methodology="test")
        engine.register(h)
        assert engine.get("h1") is h
        assert engine.get("nonexistent") is None

    def test_duplicate_registration_blocked(self) -> None:
        engine = HypothesisEngine()
        h = TestableHypothesis(hypothesis_id="h1", methodology="test")
        engine.register(h)
        with pytest.raises(ValueError, match="already registered"):
            engine.register(h)

    def test_list_by_status(self) -> None:
        engine = HypothesisEngine()
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="a"))
        engine.register(TestableHypothesis(hypothesis_id="h2", methodology="b"))
        engine.transition("h1", "implemented")
        assert len(engine.list_by_status("untested")) == 1
        assert len(engine.list_by_status("implemented")) == 1

    def test_list_by_methodology(self) -> None:
        engine = HypothesisEngine()
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="fibonacci"))
        engine.register(TestableHypothesis(hypothesis_id="h2", methodology="gann"))
        engine.register(TestableHypothesis(hypothesis_id="h3", methodology="fibonacci"))
        assert len(engine.list_by_methodology("fibonacci")) == 2
        assert len(engine.list_by_methodology("gann")) == 1

    def test_count(self) -> None:
        engine = HypothesisEngine()
        assert engine.count() == 0
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="a"))
        assert engine.count() == 1

    def test_mark_not_implementable(self) -> None:
        engine = HypothesisEngine()
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="a"))
        engine.mark_not_implementable("h1", "No mathematical definition")
        h = engine.get("h1")
        assert h is not None
        assert h.implementation_status == "not_implementable"
        assert h.notes == "No mathematical definition"


class TestTargets:
    def test_future_return(self) -> None:
        closes = [100.0, 101.0, 102.0, 103.0, 104.0]
        assert compute_future_return(closes, 0, 2) == pytest.approx(0.02, abs=1e-6)
        assert compute_future_return(closes, 1, 2) == pytest.approx(0.0198, abs=1e-4)

    def test_future_return_zero_division(self) -> None:
        closes = [0.0, 1.0, 2.0]
        assert compute_future_return(closes, 0, 1) == 0.0

    def test_future_direction(self) -> None:
        closes = [100.0, 101.0]
        assert compute_future_direction(closes, 0, 1) == 1.0
        closes = [100.0, 99.0]
        assert compute_future_direction(closes, 0, 1) == -1.0
        closes = [100.0, 100.0]
        assert compute_future_direction(closes, 0, 1) == 0.0

    def test_volatility(self) -> None:
        highs = [102.0, 103.0, 104.0]
        lows = [98.0, 99.0, 100.0]
        closes = [100.0, 101.0, 102.0]
        vol = compute_volatility(highs, lows, closes, 0, 2)
        assert vol > 0

    def test_max_favorable_excursion(self) -> None:
        highs = [100.0, 105.0, 103.0]
        mfe = compute_maximum_favorable_excursion(highs, 0, 2)
        assert mfe == pytest.approx(0.05, abs=1e-6)

    def test_max_adverse_excursion(self) -> None:
        lows = [100.0, 95.0, 97.0]
        mae = compute_maximum_adverse_excursion(lows, 0, 2)
        assert mae == pytest.approx(-0.05, abs=1e-6)

    def test_target_calculator(self) -> None:
        defs = {
            "ret": TargetDefinition(
                target_id="ret",
                target_type="future_return",
                horizon_bars=2,
                calculation="(close[t+2] - close[t]) / close[t]",
            ),
        }
        calc = TargetCalculator(definitions=defs)
        timestamps = [datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(10)]
        result = calc.compute(
            "ret",
            closes=[100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
            highs=[101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0],
            lows=[99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0],
            timestamps=timestamps,
            index=0,
        )
        assert result.valid
        assert result.target_type == "future_return"

    def test_target_insufficient_data(self) -> None:
        defs = {
            "ret": TargetDefinition(
                target_id="ret",
                target_type="future_return",
                horizon_bars=10,
            ),
        }
        calc = TargetCalculator(definitions=defs)
        timestamps = [datetime(2020, 1, 1, tzinfo=timezone.utc)]
        result = calc.compute("ret", [100.0], [101.0], [99.0], timestamps, 0)
        assert not result.valid


class TestTemporalSplits:
    def test_chronological_splitter(self) -> None:
        seq = _make_sequence(100)
        splitter = ChronologicalSplitter()
        windows = splitter.split(seq)
        assert len(windows) == 3
        types = [w.split_type for w in windows]
        assert types == ["train", "validation", "test"]
        total_bars = sum(w.bar_count for w in windows)
        assert total_bars == 100

    def test_chronological_no_overlap(self) -> None:
        seq = _make_sequence(100)
        splitter = ChronologicalSplitter()
        windows = splitter.split(seq)
        for i in range(len(windows) - 1):
            assert windows[i].end < windows[i + 1].start

    def test_walk_forward_splitter(self) -> None:
        seq = _make_sequence(1000)
        splitter = WalkForwardSplitter(train_bars=500, test_bars=100, step_bars=100)
        windows = splitter.split(seq)
        assert len(windows) > 0
        folds = [w.fold_index for w in windows]
        unique_folds = sorted(set(folds))
        assert len(unique_folds) > 1
        for fold in unique_folds:
            train = [w for w in windows if w.fold_index == fold and w.split_type == "train"]
            test = [w for w in windows if w.fold_index == fold and w.split_type == "test"]
            assert len(train) == 1
            assert len(test) == 1
            assert train[0].end < test[0].start

    def test_expanding_window_splitter(self) -> None:
        seq = _make_sequence(1000)
        splitter = ExpandingWindowSplitter(min_train_bars=500, test_bars=100, step_bars=100)
        windows = splitter.split(seq)
        assert len(windows) > 0
        folds = sorted({w.fold_index for w in windows})
        assert len(folds) > 1
        for fold in folds:
            train = [w for w in windows if w.fold_index == fold and w.split_type == "train"]
            test = [w for w in windows if w.fold_index == fold and w.split_type == "test"]
            assert len(train) == 1
            assert len(test) == 1
            assert train[0].end < test[0].start

    def test_rolling_window_splitter(self) -> None:
        seq = _make_sequence(1000)
        splitter = RollingWindowSplitter(train_bars=300, test_bars=100, step_bars=100)
        windows = splitter.split(seq)
        assert len(windows) > 0
        folds = sorted({w.fold_index for w in windows})
        assert len(folds) > 1

    def test_no_random_splits(self) -> None:
        for splitter_cls, kwargs in [
            (ChronologicalSplitter, {}),
            (WalkForwardSplitter, {"train_bars": 500, "test_bars": 100, "step_bars": 100}),
            (ExpandingWindowSplitter, {"min_train_bars": 500, "test_bars": 100, "step_bars": 100}),
            (RollingWindowSplitter, {"train_bars": 300, "test_bars": 100, "step_bars": 100}),
        ]:
            seq = _make_sequence(1000)
            splitter = splitter_cls(**kwargs)
            windows = splitter.split(seq)
            for w in windows:
                assert w.bar_count > 0

    def test_splitter_validation(self) -> None:
        with pytest.raises(ValueError):
            WalkForwardSplitter(train_bars=-1)
        with pytest.raises(ValueError):
            WalkForwardSplitter(test_bars=-1)
        with pytest.raises(ValueError):
            WalkForwardSplitter(step_bars=-1)
        with pytest.raises(ValueError):
            WalkForwardSplitter(gap_bars=-1)


class TestLeakageDetection:
    def test_feature_timestamp_leakage_pass(self) -> None:
        features = [
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 2, tzinfo=timezone.utc),
        ]
        predictions = [
            datetime(2020, 1, 2, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
        ]
        check = check_feature_timestamp_leakage(features, predictions)
        assert check.passed

    def test_feature_timestamp_leakage_fail(self) -> None:
        features = [
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 2, tzinfo=timezone.utc),
        ]
        predictions = [
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
        ]
        check = check_feature_timestamp_leakage(features, predictions)
        assert not check.passed

    def test_normalization_leakage_pass(self) -> None:
        train = {"mean": 100.0, "std": 10.0}
        test = {"mean": 101.0, "std": 10.5}
        check = check_normalization_leakage(train, test, tolerance=0.1)
        assert check.passed

    def test_normalization_leakage_fail(self) -> None:
        train = {"mean": 100.0, "std": 10.0}
        test = {"mean": 200.0, "std": 20.0}
        check = check_normalization_leakage(train, test, tolerance=0.1)
        assert not check.passed

    def test_random_temporal_split_pass(self) -> None:
        train = [
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 2, tzinfo=timezone.utc),
        ]
        test = [
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 4, tzinfo=timezone.utc),
        ]
        check = check_random_temporal_split(train, test)
        assert check.passed

    def test_random_temporal_split_fail(self) -> None:
        train = [
            datetime(2020, 1, 3, tzinfo=timezone.utc),
            datetime(2020, 1, 1, tzinfo=timezone.utc),
        ]
        test = [
            datetime(2020, 1, 2, tzinfo=timezone.utc),
            datetime(2020, 1, 4, tzinfo=timezone.utc),
        ]
        check = check_random_temporal_split(train, test)
        assert not check.passed

    def test_target_leakage_pass(self) -> None:
        features = [datetime(2020, 1, 1, tzinfo=timezone.utc)]
        targets = [datetime(2020, 1, 3, tzinfo=timezone.utc)]
        check = check_target_leakage(features, targets)
        assert check.passed

    def test_target_leakage_fail(self) -> None:
        features = [datetime(2020, 1, 3, tzinfo=timezone.utc)]
        targets = [datetime(2020, 1, 1, tzinfo=timezone.utc)]
        check = check_target_leakage(features, targets)
        assert not check.passed

    def test_overlapping_horizons_pass(self) -> None:
        windows = [
            (datetime(2020, 1, 1, tzinfo=timezone.utc), datetime(2020, 1, 2, tzinfo=timezone.utc)),
            (datetime(2020, 1, 3, tzinfo=timezone.utc), datetime(2020, 1, 4, tzinfo=timezone.utc)),
        ]
        check = check_overlapping_horizons(windows)
        assert check.passed

    def test_overlapping_horizons_fail(self) -> None:
        windows = [
            (datetime(2020, 1, 1, tzinfo=timezone.utc), datetime(2020, 1, 3, tzinfo=timezone.utc)),
            (datetime(2020, 1, 2, tzinfo=timezone.utc), datetime(2020, 1, 4, tzinfo=timezone.utc)),
        ]
        check = check_overlapping_horizons(windows)
        assert not check.passed

    def test_leakage_detector(self) -> None:
        detector = LeakageDetector()
        detector.add_check(check_feature_timestamp_leakage(
            [datetime(2020, 1, 1, tzinfo=timezone.utc)],
            [datetime(2020, 1, 2, tzinfo=timezone.utc)],
        ))
        assert detector.all_passed()
        detector.add_check(check_feature_timestamp_leakage(
            [datetime(2020, 1, 3, tzinfo=timezone.utc)],
            [datetime(2020, 1, 1, tzinfo=timezone.utc)],
        ))
        assert not detector.all_passed()
        assert len(detector.critical_failures()) == 1


class TestFeatureTimestamps:
    def test_valid_timestamp(self) -> None:
        validator = TimestampValidator()
        ft = datetime(2020, 1, 1, tzinfo=timezone.utc)
        pt = datetime(2020, 1, 2, tzinfo=timezone.utc)
        result = validator.validate_feature(ft, pt, "test_feature")
        assert result.is_valid

    def test_invalid_timestamp(self) -> None:
        validator = TimestampValidator()
        ft = datetime(2020, 1, 3, tzinfo=timezone.utc)
        pt = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = validator.validate_feature(ft, pt, "test_feature")
        assert not result.is_valid
        assert "after prediction" in result.validation_error

    def test_target_timestamp(self) -> None:
        validator = TimestampValidator()
        ft = datetime(2020, 1, 1, tzinfo=timezone.utc)
        ts = datetime(2020, 1, 2, tzinfo=timezone.utc)
        te = datetime(2020, 1, 5, tzinfo=timezone.utc)
        result = validator.validate_target(ft, ts, te, 3, "t1")
        assert result.valid

    def test_batch_validation(self) -> None:
        validator = TimestampValidator()
        fts = [
            datetime(2020, 1, 1, tzinfo=timezone.utc),
            datetime(2020, 1, 2, tzinfo=timezone.utc),
        ]
        pts = [
            datetime(2020, 1, 2, tzinfo=timezone.utc),
            datetime(2020, 1, 3, tzinfo=timezone.utc),
        ]
        results = validator.validate_batch(fts, pts, ["f1", "f2"])
        assert validator.all_valid(results)


class TestProvenance:
    def test_register_and_get(self) -> None:
        reg = FeatureProvenanceRegistry()
        record = ProvenanceRecord(
            feature_name="rsi_14",
            source="close",
            formula="wilder_smoothing(close, 14)",
            parameters={"period": 14},
            methodology="technical_analysis",
        )
        reg.register(record)
        assert reg.get("rsi_14") is record
        assert reg.has_feature("rsi_14")
        assert not reg.has_feature("nonexistent")

    def test_list_by_methodology(self) -> None:
        reg = FeatureProvenanceRegistry()
        reg.register(ProvenanceRecord(
            feature_name="fib_0618",
            source="close",
            formula="close * 0.618",
            methodology="fibonacci",
        ))
        reg.register(ProvenanceRecord(
            feature_name="rsi_14",
            source="close",
            formula="rsi(close, 14)",
            methodology="technical_analysis",
        ))
        assert len(reg.list_by_methodology("fibonacci")) == 1
        assert len(reg.list_by_methodology("technical_analysis")) == 1


class TestBridge:
    def test_claim_to_hypothesis(self) -> None:
        engine = HypothesisEngine()
        provenance = FeatureProvenanceRegistry()
        bridge = ClaimFeatureBridge(hypothesis_engine=engine, provenance_registry=provenance)
        claim = _make_claim()
        h = bridge.claim_to_hypothesis(claim, "h1", ["rsi_14"])
        assert h.hypothesis_id == "h1"
        assert h.source_claim_ids == ["claim_001"]
        assert engine.get("h1") is h

    def test_research_hypothesis_to_testable(self) -> None:
        engine = HypothesisEngine()
        provenance = FeatureProvenanceRegistry()
        bridge = ClaimFeatureBridge(hypothesis_engine=engine, provenance_registry=provenance)
        rh = _make_research_hypothesis()
        h = bridge.research_hypothesis_to_testable(rh)
        assert h.methodology == "technical_analysis"
        assert h.target == "future_return"

    def test_register_feature_for_hypothesis(self) -> None:
        engine = HypothesisEngine()
        provenance = FeatureProvenanceRegistry()
        bridge = ClaimFeatureBridge(hypothesis_engine=engine, provenance_registry=provenance)
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="test"))
        record = bridge.register_feature_for_hypothesis(
            "h1", "rsi_14", "close", "rsi(close, 14)", {"period": 14}, "technical_analysis"
        )
        assert record.feature_name == "rsi_14"
        assert provenance.has_feature("rsi_14")

    def test_mark_implementable(self) -> None:
        engine = HypothesisEngine()
        provenance = FeatureProvenanceRegistry()
        bridge = ClaimFeatureBridge(hypothesis_engine=engine, provenance_registry=provenance)
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="test"))
        bridge.register_feature_for_hypothesis("h1", "f1", "close", "f1()")
        bridge.mark_implementable("h1")
        h = engine.get("h1")
        assert h is not None
        assert h.implementation_status == "implemented"

    def test_mark_not_implementable_no_features(self) -> None:
        engine = HypothesisEngine()
        provenance = FeatureProvenanceRegistry()
        bridge = ClaimFeatureBridge(hypothesis_engine=engine, provenance_registry=provenance)
        engine.register(TestableHypothesis(hypothesis_id="h1", methodology="test"))
        bridge.mark_implementable("h1")
        h = engine.get("h1")
        assert h is not None
        assert h.implementation_status == "not_implementable"


class TestBaselines:
    def test_majority_class(self) -> None:
        model = BaselineModel(baseline_type="majority_class")
        features = [[1.0, 2.0], [3.0, 4.0]]
        targets = [1.0, -1.0]
        pred = model.predict(features, targets)
        assert pred.baseline_type == "majority_class"
        assert len(pred.predictions) == 1

    def test_random(self) -> None:
        model = BaselineModel(baseline_type="random", seed=42)
        features = [[1.0], [2.0], [3.0]]
        pred = model.predict(features)
        assert len(pred.predictions) == 3
        assert all(p in [-1.0, 0.0, 1.0] for p in pred.predictions)

    def test_buy_and_hold(self) -> None:
        model = BaselineModel(baseline_type="buy_and_hold")
        features = [[1.0], [2.0], [3.0]]
        pred = model.predict(features)
        assert all(p == 1.0 for p in pred.predictions)

    def test_logistic_regression(self) -> None:
        model = BaselineModel(baseline_type="logistic_regression")
        features = [[1.0], [2.0], [3.0], [4.0], [5.0]]
        targets = [1.0, 1.0, -1.0, -1.0, 1.0]
        pred = model.predict(features, targets)
        assert len(pred.predictions) == 5
        assert len(pred.probabilities) == 5

    def test_simple_tree(self) -> None:
        model = BaselineModel(baseline_type="simple_tree")
        features = [[1.0], [2.0], [3.0], [4.0], [5.0]]
        targets = [1.0, 1.0, -1.0, -1.0, 1.0]
        pred = model.predict(features, targets)
        assert len(pred.predictions) == 5

    def test_create_all_baselines(self) -> None:
        baselines = create_all_baselines()
        assert len(baselines) == 5
        types = {b.baseline_type for b in baselines}
        assert types == {"majority_class", "random", "buy_and_hold", "logistic_regression", "simple_tree"}


class TestMetrics:
    def test_directional_accuracy(self) -> None:
        predicted = [1.0, -1.0, 1.0, -1.0]
        actual = [1.0, -1.0, -1.0, -1.0]
        assert compute_directional_accuracy(predicted, actual) == 0.75

    def test_precision(self) -> None:
        predicted = [1.0, 1.0, -1.0, -1.0]
        actual = [1.0, -1.0, 1.0, -1.0]
        assert compute_precision(predicted, actual) == 0.5

    def test_recall(self) -> None:
        predicted = [1.0, 1.0, -1.0, -1.0]
        actual = [1.0, -1.0, 1.0, -1.0]
        assert compute_recall(predicted, actual) == 0.5

    def test_f1(self) -> None:
        assert compute_f1(0.5, 0.5) == 0.5
        assert compute_f1(0.0, 0.0) == 0.0

    def test_brier_score(self) -> None:
        probs = [0.9, 0.1, 0.8, 0.2]
        actual = [1.0, 0.0, 1.0, 0.0]
        score = compute_brier_score(probs, actual)
        assert 0.0 <= score <= 1.0

    def test_log_loss(self) -> None:
        probs = [0.9, 0.1, 0.8, 0.2]
        actual = [1.0, 0.0, 1.0, 0.0]
        loss = compute_log_loss(probs, actual)
        assert loss >= 0.0

    def test_calibration_error(self) -> None:
        probs = [0.5, 0.5, 0.5, 0.5]
        actual = [1.0, 0.0, 1.0, 0.0]
        ce = compute_calibration_error(probs, actual, n_bins=5)
        assert ce >= 0.0

    def test_roc_auc(self) -> None:
        probs = [0.9, 0.8, 0.3, 0.1]
        actual = [1.0, 1.0, 0.0, 0.0]
        auc = compute_roc_auc(probs, actual)
        assert auc > 0.5

    def test_average_return(self) -> None:
        assert compute_average_return([0.01, 0.02, 0.03]) == 0.02

    def test_volatility_metric(self) -> None:
        vol = compute_volatility_metric([0.01, -0.01, 0.02, -0.02])
        assert vol > 0

    def test_max_drawdown(self) -> None:
        returns = [0.1, -0.2, 0.1, -0.3]
        mdd = compute_max_drawdown(returns)
        assert mdd > 0

    def test_sharpe_ratio(self) -> None:
        returns = [0.01, 0.02, 0.01, 0.02, 0.01]
        sr = compute_sharpe_ratio(returns)
        assert sr > 0

    def test_profit_factor(self) -> None:
        returns = [0.1, -0.05, 0.2, -0.1]
        pf = compute_profit_factor(returns)
        assert pf > 0

    def test_compute_all_metrics(self) -> None:
        predicted = [1.0, -1.0, 1.0, -1.0, 1.0]
        actual = [1.0, -1.0, -1.0, -1.0, 1.0]
        probs = [0.8, 0.2, 0.3, 0.1, 0.9]
        returns = [0.01, 0.02, -0.01, 0.03, 0.02]
        metrics = compute_all_metrics(predicted, actual, probs, returns)
        assert isinstance(metrics, EvaluationMetrics)
        assert metrics.n_observations == 5
        assert 0.0 <= metrics.directional_accuracy <= 1.0


class TestExperimentRegistry:
    def test_register_and_get(self) -> None:
        reg = ExperimentRegistry()
        record = ExperimentRecord(
            experiment_id="exp1",
            hypothesis_id="h1",
            model="baseline_random",
        )
        reg.register(record)
        assert reg.get("exp1") is record
        assert reg.count() == 1

    def test_list_by_hypothesis(self) -> None:
        reg = ExperimentRegistry()
        reg.register(ExperimentRecord(experiment_id="exp1", hypothesis_id="h1"))
        reg.register(ExperimentRecord(experiment_id="exp2", hypothesis_id="h1"))
        reg.register(ExperimentRecord(experiment_id="exp3", hypothesis_id="h2"))
        assert len(reg.list_by_hypothesis("h1")) == 2

    def test_best_by_metric(self) -> None:
        reg = ExperimentRegistry()
        reg.register(ExperimentRecord(
            experiment_id="exp1",
            hypothesis_id="h1",
            metrics=EvaluationMetrics(directional_accuracy=0.6),
        ))
        reg.register(ExperimentRecord(
            experiment_id="exp2",
            hypothesis_id="h1",
            metrics=EvaluationMetrics(directional_accuracy=0.8),
        ))
        best = reg.best_by_metric("directional_accuracy", "h1")
        assert best is not None
        assert best.experiment_id == "exp2"

    def test_family(self) -> None:
        reg = ExperimentRegistry()
        family = ExperimentFamily(
            family_id="fam1",
            description="Test family",
            hypothesis_ids=["h1", "h2"],
        )
        reg.register_family(family)
        reg.register(ExperimentRecord(experiment_id="exp1", hypothesis_id="h1"))
        reg.register(ExperimentRecord(experiment_id="exp2", hypothesis_id="h2"))
        assert reg.get_family("fam1") is not None
        assert reg.get_family("fam1").total_experiments == 2


class TestMultipleTesting:
    def test_bonferroni(self) -> None:
        recorder = MultipleTestingRecorder()
        for i in range(100):
            pval = 0.01 if i < 5 else 0.5
            recorder.record_pvalue("family1", f"exp{i}", pval)
        result = recorder.bonferroni_correction("family1", alpha=0.05)
        assert result.total_tests == 100
        assert result.significant_before_correction == 5
        assert result.bonferroni_threshold == pytest.approx(0.0005, abs=1e-6)
        assert result.significant_after_bonferroni == 0

    def test_bonferroni_strong_signal(self) -> None:
        recorder = MultipleTestingRecorder()
        for i in range(100):
            pval = 0.0001 if i < 5 else 0.5
            recorder.record_pvalue("family1", f"exp{i}", pval)
        result = recorder.bonferroni_correction("family1", alpha=0.05)
        assert result.total_tests == 100
        assert result.significant_before_correction == 5
        assert result.significant_after_bonferroni == 5

    def test_bh_fdr(self) -> None:
        recorder = MultipleTestingRecorder()
        for i in range(100):
            pval = 0.01 if i < 5 else 0.5
            recorder.record_pvalue("family1", f"exp{i}", pval)
        result = recorder.benjamini_hochberg_fdr("family1", alpha=0.05)
        assert result.total_tests == 100
        assert result.significant_before_correction == 5
        assert len(result.adjusted_pvalues) == 100


class TestSyntheticValidation:
    def test_known_signal(self) -> None:
        gen = SyntheticGenerator(seed=42)
        dataset = gen.generate_with_known_signal(n_bars=200)
        assert dataset.known_signal
        assert len(dataset.bars) == 200
        assert dataset.signal_strength > 0

    def test_no_signal(self) -> None:
        gen = SyntheticGenerator(seed=42)
        dataset = gen.generate_without_signal(n_bars=200)
        assert not dataset.known_signal
        assert len(dataset.bars) == 200

    def test_leakage(self) -> None:
        gen = SyntheticGenerator(seed=42)
        dataset = gen.generate_with_leakage(n_bars=200)
        assert dataset.known_leakage
        assert len(dataset.bars) == 200

    def test_regime_change(self) -> None:
        gen = SyntheticGenerator(seed=42)
        dataset = gen.generate_with_regime_change(n_bars=200)
        assert dataset.has_regime_change
        assert len(dataset.bars) == 200

    def test_generate_all(self) -> None:
        gen = SyntheticGenerator(seed=42)
        datasets = gen.generate_all()
        assert len(datasets) == 4
        names = {d.name for d in datasets}
        assert names == {"known_signal", "no_signal", "leakage", "regime_change"}

    def test_synthetic_leakage_detection(self) -> None:
        gen = SyntheticGenerator(seed=42)
        dataset = gen.generate_with_leakage(n_bars=200)
        assert dataset.known_leakage
        n = len(dataset.bars)
        feature_ts = [dataset.bars[i].timestamp for i in range(10, n)]
        target_end_ts = [dataset.bars[i].timestamp for i in range(n - 10)]
        check = check_target_leakage(feature_ts, target_end_ts)
        assert not check.passed
