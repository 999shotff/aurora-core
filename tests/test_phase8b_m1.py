import dataclasses
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aurora.features.base import FeatureVector
from aurora.models.base import (
    ModelAdapter,
    ModelAuditTrail,
    ModelInput,
    ModelMetadata,
    ModelOutput,
)
from aurora.models.registry import ModelRegistry
from aurora.models.stub import StubAdapter
from aurora.schemas.market_state import MarketState


def _ts(h: int = 12) -> datetime:
    return datetime(2025, 6, 1, h, 0, tzinfo=timezone.utc)


def _make_feature_vector(ts: datetime | None = None) -> FeatureVector:
    return FeatureVector(
        version="0.1.0",
        extractor_id="test_extractor",
        asset="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        numerical={"price": 100_000.0, "return_1h": 0.01},
    )


def _make_market_state(ts: datetime | None = None) -> MarketState:
    return MarketState(
        asset="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        data_quality="historical",
        price=100_000.0,
    )


def _make_model_input(
    evaluation_context: str = "live",
    feature_schema_version: str = "0.1.0",
    leakage_flags: dict[str, bool] | None = None,
    ts: datetime | None = None,
) -> ModelInput:
    return ModelInput(
        instrument_id="BTCUSD",
        timeframe="15m",
        timestamp=ts or _ts(),
        feature_vector=_make_feature_vector(ts),
        market_state=_make_market_state(ts),
        research_evidence={},
        regime_label="unknown",
        data_quality="historical",
        feature_schema_version=feature_schema_version,
        dataset_version="v1",
        evaluation_context=evaluation_context,
        leakage_flags=leakage_flags or {},
    )


def _make_model_output(
    probability: float = 0.6,
    confidence: float = 0.5,
    uncertainty: float = 0.5,
    outcome: str = "up",
    abstained: bool = False,
) -> ModelOutput:
    return ModelOutput(
        model_id="test_model",
        model_version="1.0.0",
        outcome=outcome,
        probability=probability,
        probability_distribution={"up": probability, "down": 1.0 - probability},
        confidence=confidence,
        uncertainty=uncertainty,
        calibration_status="none",
        abstained=abstained,
        reasoning="test",
    )


class _DummyAdapter(ModelAdapter):
    @property
    def model_id(self) -> str:
        return "dummy"

    @property
    def model_version(self) -> str:
        return "0.0.1"

    def predict(self, model_input: ModelInput) -> ModelOutput:
        self.validate_input(model_input)
        return ModelOutput(
            model_id=self.model_id,
            model_version=self.model_version,
            outcome="up",
            probability=0.6,
            confidence=0.5,
            uncertainty=0.5,
            calibration_status="none",
        )


# ── ModelInput tests ──

class TestModelInput:
    def test_valid_construction(self):
        inp = _make_model_input()
        assert inp.instrument_id == "BTCUSD"
        assert inp.evaluation_context == "live"

    def test_frozen(self):
        inp = _make_model_input()
        with pytest.raises(ValidationError):
            inp.instrument_id = "ETHUSD"  # type: ignore[misc]

    def test_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            ModelInput(
                instrument_id="BTCUSD",
                timeframe="15m",
                timestamp=_ts(),
                feature_vector=_make_feature_vector(),
                market_state=_make_market_state(),
                data_quality="historical",
                feature_schema_version="0.1.0",
                bogus_field="nope",  # type: ignore[call-arg]
            )

    def test_evaluation_context_literal(self):
        for ctx in ("train", "validation", "test", "shadow", "live"):
            inp = _make_model_input(evaluation_context=ctx)
            assert inp.evaluation_context == ctx

    def test_default_leakage_flags_empty(self):
        inp = _make_model_input()
        assert inp.leakage_flags == {}

    def test_leakage_flags_populated(self):
        flags = {"future_price": True, "future_volume": False}
        inp = _make_model_input(leakage_flags=flags)
        assert inp.leakage_flags == flags


# ── ModelOutput tests ──

class TestModelOutput:
    def test_valid_construction(self):
        out = _make_model_output()
        assert out.model_id == "test_model"
        assert out.outcome == "up"

    def test_frozen(self):
        out = _make_model_output()
        with pytest.raises(ValidationError):
            out.model_id = "other"  # type: ignore[misc]

    def test_probability_bounds(self):
        _make_model_output(probability=0.0)
        _make_model_output(probability=1.0)
        with pytest.raises(ValidationError):
            _make_model_output(probability=-0.1)
        with pytest.raises(ValidationError):
            _make_model_output(probability=1.1)

    def test_confidence_bounds(self):
        _make_model_output(confidence=0.0)
        _make_model_output(confidence=1.0)
        with pytest.raises(ValidationError):
            _make_model_output(confidence=-0.1)
        with pytest.raises(ValidationError):
            _make_model_output(confidence=1.1)

    def test_uncertainty_bounds(self):
        _make_model_output(uncertainty=0.0)
        _make_model_output(uncertainty=1.0)
        with pytest.raises(ValidationError):
            _make_model_output(uncertainty=-0.1)
        with pytest.raises(ValidationError):
            _make_model_output(uncertainty=1.1)

    def test_calibration_status_literal(self):
        for status in ("none", "platt", "isotonic", "unknown"):
            out = ModelOutput(
                model_id="m",
                model_version="1",
                outcome="up",
                probability=0.5,
                confidence=0.5,
                uncertainty=0.5,
                calibration_status=status,
            )
            assert out.calibration_status == status

    def test_abstention_representation(self):
        out = _make_model_output(
            outcome="unknown",
            probability=0.5,
            confidence=0.0,
            uncertainty=1.0,
            abstained=True,
        )
        assert out.abstained is True
        assert out.outcome == "unknown"
        assert out.confidence == 0.0
        assert out.uncertainty == 1.0

    def test_abstention_reason_optional(self):
        out = _make_model_output(abstained=True)
        assert out.abstention_reason is None
        out2 = ModelOutput(
            model_id="m",
            model_version="1",
            outcome="unknown",
            probability=0.5,
            confidence=0.0,
            uncertainty=1.0,
            abstained=True,
            abstention_reason="low confidence",
        )
        assert out2.abstention_reason == "low confidence"

    def test_raw_output_optional(self):
        out = _make_model_output()
        assert out.raw_output is None

    def test_metadata_dict(self):
        out = ModelOutput(
            model_id="m",
            model_version="1",
            outcome="up",
            probability=0.6,
            confidence=0.5,
            uncertainty=0.5,
            metadata={"key": "value"},
        )
        assert out.metadata["key"] == "value"


# ── ModelMetadata tests ──

class TestModelMetadata:
    def test_valid_construction(self):
        meta = ModelMetadata(
            model_id="test",
            model_version="1.0",
            model_type="stub",
        )
        assert meta.model_id == "test"

    def test_frozen(self):
        meta = ModelMetadata(
            model_id="test",
            model_version="1.0",
            model_type="stub",
        )
        with pytest.raises(ValidationError):
            meta.model_id = "other"  # type: ignore[misc]

    def test_defaults(self):
        meta = ModelMetadata(
            model_id="test",
            model_version="1.0",
            model_type="stub",
        )
        assert meta.framework == "custom_python"
        assert meta.supported_input_schema == "0.1.0"
        assert meta.supported_output_schema == "0.1.0"


# ── ModelAuditTrail tests ──

class TestModelAuditTrail:
    def test_valid_construction(self):
        trail = ModelAuditTrail(
            model_id="m",
            model_version="1.0",
            training_period=("2024-01-01", "2024-06-01"),
            validation_period=("2024-06-01", "2024-09-01"),
            test_period=("2024-09-01", "2024-12-01"),
        )
        assert trail.model_id == "m"
        assert trail.training_period == ("2024-01-01", "2024-06-01")

    def test_frozen(self):
        trail = ModelAuditTrail(model_id="m", model_version="1.0")
        with pytest.raises(dataclasses.FrozenInstanceError):
            trail.model_id = "other"  # type: ignore[misc]

    def test_timestamp_auto_populated(self):
        trail = ModelAuditTrail(model_id="m", model_version="1.0")
        assert trail.timestamp != ""

    def test_default_promotion_decision(self):
        trail = ModelAuditTrail(model_id="m", model_version="1.0")
        assert trail.promotion_decision == "INCONCLUSIVE"

    def test_custom_metrics(self):
        trail = ModelAuditTrail(
            model_id="m",
            model_version="1.0",
            evaluation_metrics={"da": 0.55, "sharpe": 0.3},
        )
        assert trail.evaluation_metrics["da"] == 0.55


# ── ModelAdapter tests ──

class TestModelAdapter:
    def test_is_ready_default(self):
        adapter = _DummyAdapter()
        assert adapter.is_ready() is True

    def test_feature_requirements_default(self):
        adapter = _DummyAdapter()
        assert adapter.feature_requirements() == []

    def test_metadata_returns_model_metadata(self):
        adapter = _DummyAdapter()
        meta = adapter.metadata()
        assert isinstance(meta, ModelMetadata)
        assert meta.model_id == "dummy"

    def test_validate_input_passes(self):
        adapter = _DummyAdapter()
        inp = _make_model_input()
        adapter.validate_input(inp)

    def test_validate_input_rejects_leakage_in_test(self):
        adapter = _DummyAdapter()
        inp = _make_model_input(
            evaluation_context="test",
            leakage_flags={"future_price": True},
        )
        with pytest.raises(ValueError, match="leakage flags"):
            adapter.validate_input(inp)

    def test_validate_input_allows_leakage_in_train(self):
        adapter = _DummyAdapter()
        inp = _make_model_input(
            evaluation_context="train",
            leakage_flags={"future_price": True},
        )
        adapter.validate_input(inp)

    def test_validate_input_schema_mismatch(self):
        adapter = _DummyAdapter()
        inp = _make_model_input(feature_schema_version="99.0.0")
        with pytest.raises(ValueError, match="schema mismatch"):
            adapter.validate_input(inp)

    def test_predict_returns_model_output(self):
        adapter = _DummyAdapter()
        inp = _make_model_input()
        out = adapter.predict(inp)
        assert isinstance(out, ModelOutput)
        assert out.model_id == "dummy"


# ── ModelRegistry tests ──

class TestModelRegistry:
    def test_register_and_get(self):
        reg = ModelRegistry()
        adapter = StubAdapter(model_id="reg_test", abstain_threshold=0.3)
        reg.register(adapter)
        got = reg.get("reg_test")
        assert got.model_id == "reg_test"

    def test_duplicate_rejection(self):
        reg = ModelRegistry()
        a1 = StubAdapter(model_id="dup", abstain_threshold=0.3)
        a2 = StubAdapter(model_id="dup", abstain_threshold=0.5)
        reg.register(a1)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(a2)

    def test_get_nonexistent_raises(self):
        reg = ModelRegistry()
        with pytest.raises(KeyError, match="not found"):
            reg.get("no_such_model")

    def test_list_models(self):
        reg = ModelRegistry()
        reg.register(StubAdapter(model_id="a"))
        reg.register(StubAdapter(model_id="b"))
        models = reg.list_models()
        assert len(models) == 2
        ids = {m.model_id for m in models}
        assert ids == {"a", "b"}

    def test_list_with_status_filter(self):
        reg = ModelRegistry()
        reg.register(StubAdapter(model_id="active_one"))
        reg.register(StubAdapter(model_id="to_deprecate"))
        reg.deactivate("to_deprecate")
        active = reg.list_models(status="active")
        assert len(active) == 1
        assert active[0].model_id == "active_one"

    def test_list_with_tag_filter(self):
        reg = ModelRegistry()
        reg.register(StubAdapter(model_id="tagged"), tags=["experimental"])
        reg.register(StubAdapter(model_id="untagged"))
        tagged = reg.list_models(tag="experimental")
        assert len(tagged) == 1
        assert tagged[0].model_id == "tagged"

    def test_deactivate(self):
        reg = ModelRegistry()
        reg.register(StubAdapter(model_id="dep"))
        reg.deactivate("dep")
        models = reg.list_models(status="deprecated")
        assert len(models) == 1

    def test_deactivate_nonexistent_raises(self):
        reg = ModelRegistry()
        with pytest.raises(KeyError):
            reg.deactivate("nope")

    def test_list_versions(self):
        reg = ModelRegistry()
        a1 = StubAdapter(model_id="multi")
        a1._model_version = "1.0.0"
        a2 = StubAdapter(model_id="multi")
        a2._model_version = "2.0.0"
        reg.register(a1)
        reg.register(a2)
        versions = reg.list_versions("multi")
        assert versions == ["1.0.0", "2.0.0"]

    def test_get_specific_version(self):
        reg = ModelRegistry()
        a1 = StubAdapter(model_id="ver")
        a1._model_version = "1.0.0"
        a2 = StubAdapter(model_id="ver")
        a2._model_version = "2.0.0"
        reg.register(a1)
        reg.register(a2)
        got = reg.get("ver", version="1.0.0")
        assert got.model_version == "1.0.0"

    def test_count(self):
        reg = ModelRegistry()
        assert reg.count() == 0
        reg.register(StubAdapter(model_id="x"))
        assert reg.count() == 1

    def test_validate_compatibility(self):
        reg = ModelRegistry()
        reg.register(StubAdapter(model_id="compat"))
        assert reg.validate_compatibility("compat", "0.1.0") is True
        assert reg.validate_compatibility("compat", "99.0.0") is False
        assert reg.validate_compatibility("nonexistent", "0.1.0") is False


# ── Audit trail integration tests ──

class TestAuditTrailIntegration:
    def test_add_and_get_audit_trails(self):
        reg = ModelRegistry()
        reg.register(StubAdapter(model_id="audit_m"))
        trail = ModelAuditTrail(
            model_id="audit_m",
            model_version="1.0.0",
            promotion_decision="WEAK",
        )
        reg.add_audit_trail("audit_m", "1.0.0", trail)
        trails = reg.get_audit_trails("audit_m", "1.0.0")
        assert len(trails) == 1
        assert trails[0].promotion_decision == "WEAK"

    def test_add_audit_trail_nonexistent_model(self):
        reg = ModelRegistry()
        trail = ModelAuditTrail(model_id="x", model_version="1.0")
        with pytest.raises(KeyError):
            reg.add_audit_trail("x", "1.0", trail)


# ── Leakage protection tests ──

class TestLeakageProtection:
    def test_test_context_with_leakage_rejected(self):
        adapter = _DummyAdapter()
        inp = _make_model_input(
            evaluation_context="test",
            leakage_flags={"future_target": True},
        )
        with pytest.raises(ValueError, match="leakage"):
            adapter.validate_input(inp)

    def test_test_context_without_leakage_accepted(self):
        adapter = _DummyAdapter()
        inp = _make_model_input(
            evaluation_context="test",
            leakage_flags={},
        )
        adapter.validate_input(inp)

    def test_all_contexts_except_test_allow_leakage_flags(self):
        adapter = _DummyAdapter()
        for ctx in ("train", "validation", "shadow", "live"):
            inp = _make_model_input(
                evaluation_context=ctx,
                leakage_flags={"future_data": True},
            )
            adapter.validate_input(inp)

    def test_multiple_leakage_flags(self):
        adapter = _DummyAdapter()
        flags = {
            "future_price": True,
            "future_volume": True,
            "test_label": False,
        }
        inp = _make_model_input(
            evaluation_context="test",
            leakage_flags=flags,
        )
        with pytest.raises(ValueError, match="leakage"):
            adapter.validate_input(inp)


# ── Probability validity tests ──

class TestProbabilityValidity:
    def test_probability_zero_accepted(self):
        out = _make_model_output(probability=0.0)
        assert out.probability == 0.0

    def test_probability_one_accepted(self):
        out = _make_model_output(probability=1.0)
        assert out.probability == 1.0

    def test_probability_half_accepted(self):
        out = _make_model_output(probability=0.5)
        assert out.probability == 0.5

    def test_probability_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make_model_output(probability=-0.01)

    def test_probability_above_one_rejected(self):
        with pytest.raises(ValidationError):
            _make_model_output(probability=1.01)


# ── StubAdapter integration tests ──

class TestStubAdapterIntegration:
    def test_deterministic(self):
        inp = _make_model_input()
        adapter = StubAdapter()
        r1 = adapter.predict(inp)
        r2 = adapter.predict(inp)
        assert r1.outcome == r2.outcome
        assert r1.probability == r2.probability

    def test_abstains_below_threshold(self):
        inp = _make_model_input()
        adapter = StubAdapter(abstain_threshold=1.0)
        out = adapter.predict(inp)
        assert out.abstained is True
        assert out.outcome == "unknown"

    def test_metadata_type(self):
        adapter = StubAdapter()
        meta = adapter.metadata()
        assert isinstance(meta, ModelMetadata)
        assert meta.model_type == "stub"
