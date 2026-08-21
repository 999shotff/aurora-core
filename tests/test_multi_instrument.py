from aurora.data.pipeline import (
    MarketDataPipeline,
    ohlcv_sequence_to_market_state_sequence,
)
from aurora.data.splits import TimeBasedSplitter
from aurora.data.synthetic import generate_synthetic_ohlcv
from aurora.data.validation import validate_ohlcv
from aurora.features.base import FeatureRegistry
from aurora.features.technical import TechnicalFeatures
from aurora.schemas.market_data import OHLCVSequence

INSTRUMENTS = [
    {"symbol": "BTCUSD", "asset_class": "crypto", "exchange": "binance", "base_price": 50000.0},
    {"symbol": "ETHUSD", "asset_class": "crypto", "exchange": "binance", "base_price": 3000.0},
    {"symbol": "AAPL", "asset_class": "equity", "exchange": "NASDAQ", "base_price": 180.0},
    {"symbol": "EURUSD", "asset_class": "forex", "exchange": "forex", "base_price": 1.1},
    {"symbol": "XAUUSD", "asset_class": "commodity", "exchange": "comex", "base_price": 2000.0},
]


def _make_sequences(num_bars: int = 50) -> dict[str, OHLCVSequence]:
    sequences = {}
    for inst in INSTRUMENTS:
        seq = generate_synthetic_ohlcv(
            asset=inst["symbol"],
            timeframe="1h",
            num_bars=num_bars,
            base_price=inst["base_price"],
            seed=hash(inst["symbol"]) % 10000,
        )
        sequences[inst["symbol"]] = seq
    return sequences


def test_multi_instrument_symbol_preserved():
    sequences = _make_sequences()
    for symbol, seq in sequences.items():
        assert seq.asset == symbol
        for bar in seq.bars:
            assert bar.asset == symbol


def test_multi_instrument_no_cross_contamination():
    sequences = _make_sequences()
    prices_by_symbol = {}
    for symbol, seq in sequences.items():
        prices_by_symbol[symbol] = set(seq.closes())

    all_closes = list(prices_by_symbol.values())
    for i in range(len(all_closes)):
        for j in range(i + 1, len(all_closes)):
            assert all_closes[i] != all_closes[j], "price sets should differ across instruments"


def test_multi_instrument_features_independent():
    sequences = _make_sequences()
    ext = TechnicalFeatures()
    results = {}
    for symbol, seq in sequences.items():
        mss = ohlcv_sequence_to_market_state_sequence(seq)
        vec = ext.extract(mss)
        results[symbol] = vec
        assert vec.asset == symbol
        assert "price" in vec.numerical

    btc_prices = results["BTCUSD"].numerical["price"]
    eth_prices = results["ETHUSD"].numerical["price"]
    assert btc_prices != eth_prices


def test_multi_instrument_sequences_separated():
    sequences = _make_sequences()
    for symbol, seq in sequences.items():
        mss = ohlcv_sequence_to_market_state_sequence(seq)
        assert mss.asset == symbol
        for snap in mss.snapshots:
            assert snap.asset == symbol


def test_multi_instrument_validation_independent():
    sequences = _make_sequences()
    for symbol, seq in sequences.items():
        _accepted, report = validate_ohlcv(seq.bars, symbol, "1h")
        assert report.asset == symbol
        assert report.rows_accepted == len(seq.bars)


def test_multi_instrument_splits_isolated():
    sequences = _make_sequences(num_bars=100)
    splitter = TimeBasedSplitter()
    for symbol, seq in sequences.items():
        splits = splitter.split(seq)
        for split_seq in splits.values():
            assert split_seq.asset == symbol
            for bar in split_seq.bars:
                assert bar.asset == symbol
        assert splitter.validate_no_leakage(splits)


def test_multi_instrument_pipeline():
    sequences = _make_sequences(num_bars=10)
    pipeline = MarketDataPipeline(extractors=[TechnicalFeatures()])
    for symbol, seq in sequences.items():
        mss, vectors = pipeline.run(seq)
        assert mss.asset == symbol
        assert len(vectors) == 1
        assert vectors[0].asset == symbol


def test_multi_instrument_serialization_preserves_identity():
    sequences = _make_sequences(num_bars=5)
    for symbol, seq in sequences.items():
        data = seq.model_dump()
        restored = OHLCVSequence.model_validate(data)
        assert restored.asset == symbol
        assert restored.timeframe == seq.timeframe
        for bar in restored.bars:
            assert bar.asset == symbol


def test_multi_instrument_registry():
    sequences = _make_sequences(num_bars=10)
    registry = FeatureRegistry()
    registry.register(TechnicalFeatures())
    for symbol, seq in sequences.items():
        mss = ohlcv_sequence_to_market_state_sequence(seq)
        vectors = registry.extract_all(mss)
        for vec in vectors.values():
            assert vec.asset == symbol


def test_multi_instrument_feature_provenance_independent():
    from aurora.features.provenance import get_provenance

    sequences = _make_sequences(num_bars=10)
    ext = TechnicalFeatures()
    for symbol, seq in sequences.items():
        mss = ohlcv_sequence_to_market_state_sequence(seq)
        vec = ext.extract(mss)
        assert vec.asset == symbol
        prov = get_provenance("sma")
        assert prov is not None
        assert "close" in prov.source_columns
