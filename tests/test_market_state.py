from datetime import datetime, timezone

from aurora.schemas import MarketState


def test_market_state_round_trip():
    state = MarketState(
        asset="BTCUSD",
        timeframe="15m",
        timestamp=datetime.now(timezone.utc),
        data_quality="historical",
        price=100_000,
    )
    restored = MarketState.model_validate(state.model_dump())
    assert restored.asset == "BTCUSD"
    assert restored.price == 100_000
    assert restored.schema_version == "0.1.0"
