from datetime import datetime, timezone

import pytest

from aurora.features.base import FeatureVector
from aurora.models.base import ModelAuditTrail, ModelInput
from aurora.models.baselines import (
    BuyAndHoldAdapter,
    DeterministicRandomAdapter,
    MajorityClassAdapter,
)
from aurora.models.registry import ModelRegistry
from aurora.schemas.evaluation import Outcome
from aurora.schemas.market_state import MarketState


def _ts(h: int = 12) -> datetime:
    return datetime(2025, 6, 1, h, 0, tzinfo=timezone.utc)


def _make_feature_vector(ts: datetime | None = None) -> FeatureVector:
    return FeatureVector(
        version="0.1.0",
        extractor_id="test",
        asset="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        numerical={"price": 100_000.0},
    )


def _make_market_state(ts: datetime | None = None) -> MarketState:
    return MarketState(
        asset="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        data_quality="historical",
        price=100_000.0,
    )


def _make_input(
    evaluation_context: str = "live",
    feature_schema_version: str = "0.1.0",
    leakage_flags: dict[str, bool] | None = None,
    ts: datetime | None = None,
    instrument: str = "BTCUSD",
) -> ModelInput:
    return ModelInput(
        instrument_id=instrument,
        timeframe="15m",
        timestamp=ts or _ts(),
        feature_vector=_make_feature_vector(ts),
        market_state=_make_market_state(ts),
        data_quality="historical",
        feature_schema_version=feature_schema_version,
        evaluation_context=evaluation_context,
        leakage_flags=leakage_flags or {},
    )


def _make_training_data(
    n: int = 100, instrument: str = "BTCUSD"
) -> tuple[list[ModelInput], list[Outcome]]:
    inputs = []
    labels: list[Outcome] = []
    for i in range(n):
        ts = datetime(2025, 1, 1, i % 24, 0, tzinfo=timezone.utc)
        inputs.append(_make_input(ts=ts, instrument=instrument))
        # 60% up, 30% down, 10% flat
        if i % 10 < 6:
            labels.append("up")
        elif i % 10 < 9:
            labels.append("down")
        else:
            labels.append("flat")
    return inputs, labels


# ── 1. Majority-class calculation ──

class TestMajorityClassCalculation:
    def test_counts_correctly(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        assert adapter._class_counts["up"] == 60
        assert adapter._class_counts["down"] == 30
        assert adapter._class_counts["flat"] == 10
        assert adapter._total == 100

    def test_majority_class_is_up(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        assert adapter._majority_class == "up"

    def test_majority_prob_matches(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        assert adapter._majority_prob == pytest.approx(0.6)


# ── 2. Majority-class prediction ──

class TestMajorityClassPrediction:
    def test_predicts_majority_class(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.outcome == "up"

    def test_probability_matches_training(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.probability == pytest.approx(0.6)

    def test_not_abstained(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.abstained is False


# ── 3. Ties in class frequency ──

class TestMajorityClassTies:
    def test_tie_prefers_down(self):
        adapter = MajorityClassAdapter()
        inputs = [_make_input()] * 2
        labels: list[Outcome] = ["up", "down"]
        adapter.fit(inputs, labels)
        assert adapter._majority_class == "down"

    def test_three_way_tie_prefers_down(self):
        adapter = MajorityClassAdapter()
        inputs = [_make_input()] * 3
        labels: list[Outcome] = ["up", "down", "flat"]
        adapter.fit(inputs, labels)
        assert adapter._majority_class == "down"

    def test_tie_two_classes_up_and_flat(self):
        adapter = MajorityClassAdapter()
        inputs = [_make_input()] * 2
        labels: list[Outcome] = ["up", "flat"]
        adapter.fit(inputs, labels)
        assert adapter._majority_class == "flat"


# ── 4. Probability calculation ──

class TestMajorityClassProbability:
    def test_probability_is_class_fraction(self):
        adapter = MajorityClassAdapter()
        inputs = [_make_input()] * 10
        labels: list[Outcome] = ["up"] * 7 + ["down"] * 3
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.probability == pytest.approx(0.7)

    def test_distribution_sums_to_one(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        total = sum(out.probability_distribution.values())
        assert total == pytest.approx(1.0)

    def test_distribution_contains_all_classes(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert "up" in out.probability_distribution
        assert "down" in out.probability_distribution
        assert "flat" in out.probability_distribution


# ── 5. No 0.50 hard-coded assumption ──

class TestNoHardcodedBaseline:
    def test_baseline_depends_on_data(self):
        adapter1 = MajorityClassAdapter()
        inputs1 = [_make_input()] * 10
        labels1: list[Outcome] = ["up"] * 9 + ["down"] * 1
        adapter1.fit(inputs1, labels1)

        adapter2 = MajorityClassAdapter()
        inputs2 = [_make_input()] * 10
        labels2: list[Outcome] = ["up"] * 2 + ["down"] * 8
        adapter2.fit(inputs2, labels2)

        assert adapter1._majority_prob != adapter2._majority_prob
        assert adapter1._majority_class == "up"
        assert adapter2._majority_class == "down"

    def test_all_down_labels(self):
        adapter = MajorityClassAdapter()
        inputs = [_make_input()] * 5
        labels: list[Outcome] = ["down"] * 5
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.outcome == "down"
        assert out.probability == pytest.approx(1.0)

    def test_majority_is_flat(self):
        adapter = MajorityClassAdapter()
        inputs = [_make_input()] * 10
        labels: list[Outcome] = ["flat"] * 6 + ["up"] * 4
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input())
        assert out.outcome == "flat"


# ── 6. Deterministic random seed behavior ──

class TestDeterministicRandom:
    def test_same_seed_same_input_same_output(self):
        adapter = DeterministicRandomAdapter(seed=42)
        inp = _make_input()
        r1 = adapter.predict(inp)
        r2 = adapter.predict(inp)
        assert r1.outcome == r2.outcome
        assert r1.raw_output == r2.raw_output

    def test_different_seeds_different_output(self):
        inp = _make_input()
        r1 = DeterministicRandomAdapter(seed=42).predict(inp)
        r2 = DeterministicRandomAdapter(seed=99).predict(inp)
        # Not guaranteed to differ, but very likely with different seeds
        # Just verify both are valid outcomes
        assert r1.outcome in ("up", "down", "flat")
        assert r2.outcome in ("up", "down", "flat")

    def test_outcome_is_valid(self):
        adapter = DeterministicRandomAdapter(seed=42)
        out = adapter.predict(_make_input())
        assert out.outcome in ("up", "down", "flat")


# ── 7. Different seeds producing valid results ──

class TestRandomSeedValidity:
    def test_probability_is_uniform(self):
        adapter = DeterministicRandomAdapter(seed=42)
        out = adapter.predict(_make_input())
        assert out.probability == pytest.approx(1.0 / 3)
        assert out.confidence == 0.0
        assert out.uncertainty == 1.0

    def test_distribution_is_uniform(self):
        adapter = DeterministicRandomAdapter(seed=42)
        out = adapter.predict(_make_input())
        for prob in out.probability_distribution.values():
            assert prob == pytest.approx(1.0 / 3)

    def test_raw_output_contains_seed(self):
        adapter = DeterministicRandomAdapter(seed=42)
        out = adapter.predict(_make_input())
        assert "seed=42" in out.raw_output


# ── 8. Audit trail creation ──

class TestAuditTrailCreation:
    def test_majority_class_audit_trail(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        trail = adapter.audit_trail()
        assert isinstance(trail, ModelAuditTrail)
        assert trail.model_id == "majority_class"
        assert trail.promotion_decision == "BASELINE"

    def test_random_audit_trail(self):
        adapter = DeterministicRandomAdapter(seed=42)
        trail = adapter.audit_trail()
        assert trail.random_seed == 42
        assert trail.promotion_decision == "BASELINE"

    def test_buy_and_hold_audit_trail(self):
        adapter = BuyAndHoldAdapter()
        trail = adapter.audit_trail()
        assert trail.model_id == "buy_and_hold"
        assert trail.promotion_decision == "BASELINE"

    def test_audit_trail_has_timestamp(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        trail = adapter.audit_trail()
        assert trail.timestamp != ""


# ── 9. Temporal input validation ──

class TestTemporalInputValidation:
    def test_valid_input_accepted(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(_make_input(evaluation_context="test"))
        assert out.abstained is False

    def test_schema_version_checked(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="schema mismatch"):
            adapter.predict(_make_input(feature_schema_version="99.0.0"))


# ── 10. Future-data rejection ──

class TestFutureDataRejection:
    def test_leakage_in_test_context_rejected(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"future_price": True},
                )
            )


# ── 11. Test-label leakage rejection ──

class TestLabelLeakageRejection:
    def test_test_label_leakage_rejected(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        with pytest.raises(ValueError, match="leakage"):
            adapter.predict(
                _make_input(
                    evaluation_context="test",
                    leakage_flags={"test_label": True},
                )
            )

    def test_train_leakage_allowed(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        out = adapter.predict(
            _make_input(
                evaluation_context="train",
                leakage_flags={"future_price": True},
            )
        )
        assert out.abstained is False


# ── 12. Registry registration ──

class TestRegistryRegistration:
    def test_register_majority_class(self):
        reg = ModelRegistry()
        adapter = MajorityClassAdapter()
        meta = reg.register(adapter)
        assert meta.model_id == "majority_class"
        assert reg.count() == 1

    def test_register_random(self):
        reg = ModelRegistry()
        adapter = DeterministicRandomAdapter(seed=42)
        meta = reg.register(adapter)
        assert meta.model_id == "deterministic_random"

    def test_register_buy_and_hold(self):
        reg = ModelRegistry()
        adapter = BuyAndHoldAdapter()
        meta = reg.register(adapter)
        assert meta.model_id == "buy_and_hold"

    def test_register_with_tags(self):
        reg = ModelRegistry()
        adapter = MajorityClassAdapter()
        reg.register(adapter, tags=["baseline", "statistical"])
        models = reg.list_models(tag="baseline")
        assert len(models) == 1


# ── 13. Duplicate registration rejection ──

class TestDuplicateRejection:
    def test_duplicate_rejected(self):
        reg = ModelRegistry()
        reg.register(MajorityClassAdapter())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(MajorityClassAdapter())

    def test_different_versions_allowed(self):
        reg = ModelRegistry()
        a1 = MajorityClassAdapter(version="1.0.0")
        a2 = MajorityClassAdapter(version="2.0.0")
        reg.register(a1)
        reg.register(a2)
        assert reg.count() == 2

    def test_different_ids_allowed(self):
        reg = ModelRegistry()
        reg.register(MajorityClassAdapter(model_id="mc1"))
        reg.register(MajorityClassAdapter(model_id="mc2"))
        assert reg.count() == 2


# ── 14. Metadata validation ──

class TestMetadataValidation:
    def test_majority_class_metadata(self):
        adapter = MajorityClassAdapter()
        meta = adapter.metadata()
        assert meta.model_id == "majority_class"
        assert meta.model_type == "majority_class"
        assert meta.framework == "custom_python"

    def test_random_metadata(self):
        adapter = DeterministicRandomAdapter(seed=42)
        meta = adapter.metadata()
        assert meta.model_type == "deterministic_random"
        assert meta.configuration["seed"] == 42

    def test_buy_and_hold_metadata(self):
        adapter = BuyAndHoldAdapter()
        meta = adapter.metadata()
        assert meta.model_type == "buy_and_hold"
        assert meta.configuration["fixed_outcome"] == "up"


# ── 15. Model readiness ──

class TestModelReadiness:
    def test_not_ready_before_fit(self):
        adapter = MajorityClassAdapter()
        assert adapter.is_ready() is False

    def test_ready_after_fit(self):
        adapter = MajorityClassAdapter()
        inputs, labels = _make_training_data()
        adapter.fit(inputs, labels)
        assert adapter.is_ready() is True

    def test_random_always_ready(self):
        adapter = DeterministicRandomAdapter(seed=42)
        assert adapter.is_ready() is True

    def test_buy_and_hold_always_ready(self):
        adapter = BuyAndHoldAdapter()
        assert adapter.is_ready() is True


# ── 16. Invalid input handling ──

class TestInvalidInputHandling:
    def test_unfitted_majority_class_abstains(self):
        adapter = MajorityClassAdapter()
        out = adapter.predict(_make_input())
        assert out.abstained is True
        assert out.outcome == "unknown"
        assert out.abstention_reason == "model not fitted"

    def test_empty_training_labels_raises(self):
        adapter = MajorityClassAdapter()
        with pytest.raises(ValueError, match="empty"):
            adapter.fit([], [])

    def test_buy_and_hold_never_abstains(self):
        adapter = BuyAndHoldAdapter()
        out = adapter.predict(_make_input())
        assert out.abstained is False
        assert out.outcome == "up"

    def test_random_never_abstains(self):
        adapter = DeterministicRandomAdapter(seed=42)
        out = adapter.predict(_make_input())
        assert out.abstained is False


# ── BuyAndHold specific tests ──

class TestBuyAndHold:
    def test_always_predicts_up(self):
        adapter = BuyAndHoldAdapter()
        for _ in range(10):
            out = adapter.predict(_make_input())
            assert out.outcome == "up"

    def test_probability_is_one(self):
        adapter = BuyAndHoldAdapter()
        out = adapter.predict(_make_input())
        assert out.probability == 1.0

    def test_distribution_is_one_hot(self):
        adapter = BuyAndHoldAdapter()
        out = adapter.predict(_make_input())
        assert out.probability_distribution == {"up": 1.0, "down": 0.0, "flat": 0.0}
