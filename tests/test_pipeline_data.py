from aurora.data.pipeline import (
    MarketDataPipeline,
    ohlcv_sequence_to_market_state_sequence,
)
from aurora.data.synthetic import generate_synthetic_ohlcv
from aurora.features.technical import TechnicalFeatures


def test_ohlcv_to_market_state_sequence():
    seq = generate_synthetic_ohlcv(asset="SYNTH", num_bars=5)
    mss = ohlcv_sequence_to_market_state_sequence(seq)
    assert mss.asset == seq.asset
    assert mss.timeframe == seq.timeframe
    assert mss.window_size == 5
    for snap in mss.snapshots:
        assert snap.price > 0


def test_pipeline_empty_extractors():
    seq = generate_synthetic_ohlcv(asset="SYNTH", num_bars=5)
    pipeline = MarketDataPipeline()
    mss, vectors = pipeline.run(seq)
    assert mss.window_size == 5
    assert len(vectors) == 0


def test_pipeline_with_technical():
    seq = generate_synthetic_ohlcv(asset="SYNTH", num_bars=10)
    pipeline = MarketDataPipeline(extractors=[TechnicalFeatures()])
    _mss, vectors = pipeline.run(seq)
    assert len(vectors) == 1
    vec = vectors[0]
    assert vec.extractor_id == "technical_v1"
    assert "price" in vec.numerical
    assert vec.numerical["price"] > 0
    assert "data_quality" in vec.categorical


def test_pipeline_run_single():
    seq = generate_synthetic_ohlcv(asset="SYNTH", num_bars=10)
    pipeline = MarketDataPipeline()
    vec = pipeline.run_single(seq, TechnicalFeatures())
    assert vec.extractor_id == "technical_v1"
    assert "price" in vec.numerical
