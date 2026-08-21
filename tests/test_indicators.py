import pytest

from aurora.features.indicators import (
    atr,
    ema_indicator,
    momentum_indicator,
    rsi,
    sma_indicator,
    volatility,
)


def test_atr_basic():
    highs = [110.0, 112.0, 115.0, 113.0, 118.0]
    lows = [95.0, 98.0, 100.0, 97.0, 102.0]
    closes = [105.0, 108.0, 110.0, 105.0, 115.0]
    result = atr(highs, lows, closes, window=3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] is not None
    assert result[2] > 0


def test_atr_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        atr([1.0, 2.0], [1.0], [1.0, 2.0], window=2)


def test_atr_window_1():
    highs = [110.0, 112.0]
    lows = [95.0, 98.0]
    closes = [105.0, 108.0]
    result = atr(highs, lows, closes, window=1)
    assert result[0] == pytest.approx(15.0)
    assert result[1] == pytest.approx(14.0)


def test_rsi_basic():
    closes = [44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84]
    result = rsi(closes, window=3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] is None
    assert result[3] is not None
    for v in result[3:]:
        assert 0.0 <= v <= 100.0


def test_rsi_all_gains():
    closes = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = rsi(closes, window=3)
    for v in result[3:]:
        assert v == pytest.approx(100.0)


def test_rsi_all_losses():
    closes = [5.0, 4.0, 3.0, 2.0, 1.0]
    result = rsi(closes, window=3)
    for v in result[3:]:
        assert v == pytest.approx(0.0)


def test_rsi_short():
    closes = [1.0]
    result = rsi(closes, window=14)
    assert result == [None]


def test_ema_indicator():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = ema_indicator(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] is not None
    assert result[3] is not None


def test_sma_indicator():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = sma_indicator(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)


def test_momentum_indicator():
    values = [10.0, 12.0, 11.0, 13.0, 15.0]
    result = momentum_indicator(values, 2)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(1.0)
    assert result[3] == pytest.approx(1.0)


def test_volatility():
    closes = [100.0, 102.0, 98.0, 105.0, 101.0]
    result = volatility(closes, window=3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] is not None
    assert result[2] > 0


def test_atr_no_lookahead():
    highs = [110.0, 112.0, 115.0, 113.0, 118.0]
    lows = [95.0, 98.0, 100.0, 97.0, 102.0]
    closes = [105.0, 108.0, 110.0, 105.0, 115.0]
    result = atr(highs, lows, closes, window=2)
    tr0 = max(110.0 - 95.0, abs(110.0 - 105.0), abs(95.0 - 105.0))
    tr1 = max(112.0 - 98.0, abs(112.0 - 105.0), abs(98.0 - 105.0))
    assert result[1] == pytest.approx((tr0 + tr1) / 2)


def test_rsi_no_lookahead():
    closes = [44.0, 44.34, 44.09, 43.61, 44.33]
    result = rsi(closes, window=2)
    gains = [0.34, 0.0, 0.0, 0.72]
    losses = [0.0, 0.25, 0.48, 0.0]
    avg_gain = (gains[0] + gains[1]) / 2
    avg_loss = (losses[0] + losses[1]) / 2
    rs = avg_gain / avg_loss
    expected = 100.0 - (100.0 / (1.0 + rs))
    assert result[2] == pytest.approx(expected)


def test_deterministic_repeated_execution():
    highs = [110.0, 112.0, 115.0]
    lows = [95.0, 98.0, 100.0]
    closes = [105.0, 108.0, 110.0]
    r1 = atr(highs, lows, closes, window=2)
    r2 = atr(highs, lows, closes, window=2)
    assert r1 == r2
