from datetime import datetime, timezone

from aurora.features.base import FeatureVector
from aurora.models.base import ModelInput
from aurora.models.stub import StubAdapter
from aurora.schemas.market_state import MarketState


def _make_input(asset: str = "BTCUSD", ts_hour: int = 12) -> ModelInput:
    state = MarketState(
        asset=asset,
        timeframe="15m",
        timestamp=datetime(2025, 1, 1, ts_hour, 0, tzinfo=timezone.utc),
        data_quality="historical",
        price=100_000.0,
    )
    fv = FeatureVector(
        version="0.1.0",
        extractor_id="test",
        asset=asset,
        timeframe="15m",
        timestamp=state.timestamp,
        numerical={"price": state.price},
    )
    return ModelInput(
        instrument_id=asset,
        timeframe="15m",
        timestamp=state.timestamp,
        feature_vector=fv,
        market_state=state,
        data_quality="historical",
        feature_schema_version="0.1.0",
    )


def test_stub_adapter_deterministic():
    model_input = _make_input()
    adapter = StubAdapter()
    r1 = adapter.predict(model_input)
    r2 = adapter.predict(model_input)
    assert r1.outcome == r2.outcome
    assert r1.probability == r2.probability
    assert r1.raw_output == r2.raw_output


def test_stub_adapter_metadata():
    adapter = StubAdapter(model_id="test_stub", abstain_threshold=0.5)
    meta = adapter.metadata()
    assert meta.model_id == "test_stub"
    assert meta.model_type == "stub"


def test_stub_adapter_varies_by_input():
    inp1 = _make_input(asset="BTCUSD")
    inp2 = _make_input(asset="ETHUSD")
    adapter = StubAdapter()
    r1 = adapter.predict(inp1)
    r2 = adapter.predict(inp2)
    assert r1.raw_output != r2.raw_output
