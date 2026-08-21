from datetime import datetime, timezone

import pytest

from aurora.features import FeatureRegistry, FeatureVector, TechnicalFeatures
from aurora.schemas.market_state import MarketState, MarketStateSequence


def _make_state(**overrides) -> MarketState:
    defaults = {
        "asset": "BTCUSD",
        "timeframe": "15m",
        "timestamp": datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        "data_quality": "historical",
        "price": 100_000.0,
    }
    defaults.update(overrides)
    return MarketState(**defaults)


def _make_sequence(prices: list[float], asset: str = "BTCUSD") -> MarketStateSequence:
    snapshots = []
    for i, price in enumerate(prices):
        snapshots.append(
            MarketState(
                asset=asset,
                timeframe="15m",
                timestamp=datetime(2025, 1, 1, 12, i, tzinfo=timezone.utc),
                data_quality="historical",
                price=price,
            )
        )
    return MarketStateSequence(asset=asset, timeframe="15m", snapshots=snapshots)


def test_technical_features_basic():
    extractor = TechnicalFeatures()
    state = _make_state()
    vec = extractor.extract_single(state)
    assert isinstance(vec, FeatureVector)
    assert vec.extractor_id == "technical_v1"
    assert vec.asset == "BTCUSD"
    assert vec.numerical["price"] == 100_000.0


def test_technical_features_with_returns():
    state = _make_state(return_1h=0.02, return_4h=-0.01)
    vec = TechnicalFeatures().extract_single(state)
    assert vec.numerical["return_1h"] == 0.02
    assert vec.numerical["return_4h"] == -0.01


def test_technical_features_swing_range():
    state = _make_state()
    state.structure.swing_high = 110_000.0
    state.structure.swing_low = 90_000.0
    vec = TechnicalFeatures().extract_single(state)
    assert vec.numerical["swing_range"] == 20_000.0
    assert vec.numerical["price_position_in_range"] == 0.5


def test_technical_features_vwap():
    state = _make_state(vwap_distance_pct=2.5)
    vec = TechnicalFeatures().extract_single(state)
    assert vec.numerical["vwap_distance_pct"] == 2.5


def test_technical_features_categorical_vs_numerical():
    state = _make_state()
    vec = TechnicalFeatures().extract_single(state)
    assert "structure_direction" in vec.categorical
    assert "data_quality" in vec.categorical
    assert "volatility_regime" in vec.categorical
    assert "price" in vec.numerical
    assert "structure_bos" in vec.numerical
    assert "structure_choch" in vec.numerical
    assert "liquidity_strength" in vec.numerical
    assert "liquidity_buy_sweep" in vec.numerical


def test_technical_features_windowed():
    seq = _make_sequence([100.0, 102.0, 98.0, 105.0, 101.0])
    vec = TechnicalFeatures().extract(seq)
    assert vec.numerical["seq_mean_return"] == pytest.approx(
        ((0.02) + (-0.0392156862745098) + (0.0714285714285714) + (-0.0380952380952381)) / 4,
        abs=1e-8,
    )
    assert vec.numerical["seq_price_range"] == 7.0
    assert vec.metadata["window_size"] == 5


def test_technical_features_single_window_no_seq_features():
    state = _make_state()
    vec = TechnicalFeatures().extract_single(state)
    assert "seq_mean_return" not in vec.numerical
    assert vec.metadata["window_size"] == 1


def test_feature_registry():
    registry = FeatureRegistry()
    ext = TechnicalFeatures()
    registry.register(ext)
    assert ext.extractor_id in registry.list_extractors()

    seq = _make_sequence([100.0])
    results = registry.extract_all(seq)
    assert ext.extractor_id in results
    assert isinstance(results[ext.extractor_id], FeatureVector)


def test_feature_registry_duplicate():
    registry = FeatureRegistry()
    ext = TechnicalFeatures()
    registry.register(ext)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ext)


def test_feature_registry_missing():
    registry = FeatureRegistry()
    with pytest.raises(KeyError, match="not found"):
        registry.get("nonexistent")


def test_market_state_sequence_validation():
    s1 = _make_state(price=100.0, timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))
    s2 = _make_state(price=101.0, timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc))
    seq = MarketStateSequence(asset="BTCUSD", timeframe="15m", snapshots=[s1, s2])
    assert seq.window_size == 2
    assert seq.latest.price == 101.0
    assert seq.prices() == [100.0, 101.0]


def test_market_state_sequence_rejects_unordered():
    s1 = _make_state(price=100.0, timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc))
    s2 = _make_state(price=101.0, timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="ordered by timestamp"):
        MarketStateSequence(asset="BTCUSD", timeframe="15m", snapshots=[s1, s2])


def test_market_state_sequence_rejects_mismatched_asset():
    s1 = _make_state(price=100.0, asset="BTCUSD")
    s2 = _make_state(price=101.0, asset="ETHUSD")
    with pytest.raises(ValueError, match="snapshot asset"):
        MarketStateSequence(asset="BTCUSD", timeframe="15m", snapshots=[s1, s2])


def test_market_state_sequence_rejects_empty():
    with pytest.raises(ValueError):
        MarketStateSequence(asset="BTCUSD", timeframe="15m", snapshots=[])


def test_market_state_sequence_rejects_duplicate_timestamps():
    ts = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    s1 = _make_state(price=100.0, timestamp=ts)
    s2 = _make_state(price=101.0, timestamp=ts)
    with pytest.raises(ValueError, match="duplicate timestamps"):
        MarketStateSequence(asset="BTCUSD", timeframe="15m", snapshots=[s1, s2])


def test_market_state_sequence_serialization_round_trip():
    s1 = _make_state(price=100.0, timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc))
    s2 = _make_state(price=101.0, timestamp=datetime(2025, 1, 1, 12, 1, tzinfo=timezone.utc))
    seq = MarketStateSequence(asset="BTCUSD", timeframe="15m", snapshots=[s1, s2])
    dumped = seq.model_dump()
    restored = MarketStateSequence.model_validate(dumped)
    assert restored.asset == "BTCUSD"
    assert restored.window_size == 2
    assert restored.latest.price == 101.0
