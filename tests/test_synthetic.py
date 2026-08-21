from aurora.data.synthetic import generate_synthetic_ohlcv


def test_synthetic_default():
    seq = generate_synthetic_ohlcv(asset="SYNTH")
    assert seq.asset == "SYNTH"
    assert seq.timeframe == "1h"
    assert seq.bar_count == 100


def test_synthetic_custom_params():
    seq = generate_synthetic_ohlcv(asset="SYNTH_ETH", num_bars=50, timeframe="4h")
    assert seq.asset == "SYNTH_ETH"
    assert seq.bar_count == 50
    for bar in seq.bars:
        assert bar.timeframe == "4h"
        assert bar.source == "synthetic"
        assert bar.data_quality == "simulated"


def test_synthetic_deterministic():
    seq1 = generate_synthetic_ohlcv(asset="SYNTH", seed=42, num_bars=10)
    seq2 = generate_synthetic_ohlcv(asset="SYNTH", seed=42, num_bars=10)
    for b1, b2 in zip(seq1.bars, seq2.bars):
        assert b1.open == b2.open
        assert b1.close == b2.close
        assert b1.volume == b2.volume


def test_synthetic_different_seeds():
    seq1 = generate_synthetic_ohlcv(asset="SYNTH", seed=1, num_bars=10)
    seq2 = generate_synthetic_ohlcv(asset="SYNTH", seed=2, num_bars=10)
    assert seq1.bars[0].close != seq2.bars[0].close


def test_synthetic_ohlc_valid():
    seq = generate_synthetic_ohlcv(asset="SYNTH", num_bars=50)
    for bar in seq.bars:
        assert bar.high >= bar.low
        assert bar.high >= bar.open
        assert bar.high >= bar.close
        assert bar.low <= bar.open
        assert bar.low <= bar.close
